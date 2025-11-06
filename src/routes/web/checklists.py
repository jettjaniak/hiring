"""
Checklist web UI routes
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
import json
from datetime import datetime, timezone

from ...models import Checklist, TaskTemplate
from ...dependencies import get_session

# Get project root directory
project_root = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(project_root / "templates"))

router = APIRouter(tags=["web-checklists"])


@router.get("/checklists", response_class=HTMLResponse)
def checklists_page(request: Request, session: Session = Depends(get_session)):
    """List all checklists"""
    statement = select(Checklist).order_by(Checklist.name)
    checklists = session.exec(statement).all()

    # Get task info for each checklist
    checklist_tasks = {}
    for checklist in checklists:
        task = session.get(TaskTemplate, checklist.task_template_id)
        checklist_tasks[checklist.id] = task

    return templates.TemplateResponse("checklists.html", {
        "request": request,
        "checklists": checklists,
        "checklist_tasks": checklist_tasks
    })


@router.get("/checklists/add", response_class=HTMLResponse)
def add_checklist_page(request: Request, session: Session = Depends(get_session)):
    """Show form to add new checklist"""
    # Get all tasks
    tasks = session.exec(select(TaskTemplate).order_by(TaskTemplate.name)).all()

    # Get tasks that already have checklists
    existing_checklists = session.exec(select(Checklist)).all()
    used_task_ids = {c.task_template_id for c in existing_checklists}

    # Filter to only show tasks without checklists
    available_tasks = [t for t in tasks if t.task_id not in used_task_ids]

    return templates.TemplateResponse("checklist_edit.html", {
        "request": request,
        "checklist": None,
        "mode": "add",
        "available_tasks": available_tasks
    })


@router.post("/checklists/add")
def add_checklist(
    request: Request,
    checklist_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    task_id: str = Form(...),
    items: str = Form(...),
    session: Session = Depends(get_session)
):
    """Create new checklist"""
    # Check if checklist already exists
    existing_checklist = session.get(Checklist, checklist_id)
    if existing_checklist:
        raise HTTPException(status_code=400, detail=f"Checklist {checklist_id} already exists")

    # Check if task exists
    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check if task already has a checklist
    existing_for_task = session.exec(
        select(Checklist).where(Checklist.task_template_id == task_id)
    ).first()
    if existing_for_task:
        raise HTTPException(status_code=400, detail=f"Task {task_id} already has a checklist")

    # Parse items (newline separated) and convert to JSON string
    items_list = [item.strip() for item in items.split('\n') if item.strip()]
    items_json = json.dumps(items_list)

    checklist = Checklist(
        id=checklist_id,
        name=name,
        description=description,
        task_template_id=task_id,
        items=items_json
    )

    session.add(checklist)
    session.commit()

    return RedirectResponse(url="/checklists", status_code=302)


@router.get("/checklists/{checklist_id}/edit", response_class=HTMLResponse)
def edit_checklist_page(checklist_id: str, request: Request, session: Session = Depends(get_session)):
    """Show form to edit checklist"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Get the task
    task = session.get(TaskTemplate, checklist.task_template_id)

    # Parse items JSON to display as text
    items_list = json.loads(checklist.items)
    items_text = '\n'.join(items_list)

    return templates.TemplateResponse("checklist_edit.html", {
        "request": request,
        "checklist": checklist,
        "mode": "edit",
        "available_tasks": [task] if task else [],
        "items_text": items_text
    })


@router.post("/checklists/{checklist_id}/edit")
def edit_checklist(
    checklist_id: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    items: str = Form(...),
    session: Session = Depends(get_session)
):
    """Update checklist"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Parse items (newline separated) and convert to JSON string
    items_list = [item.strip() for item in items.split('\n') if item.strip()]
    items_json = json.dumps(items_list)

    checklist.name = name
    checklist.description = description
    checklist.items = items_json
    checklist.updated_at = datetime.now(timezone.utc)

    session.add(checklist)
    session.commit()

    return RedirectResponse(url="/checklists", status_code=302)


@router.post("/checklists/{checklist_id}/delete")
def delete_checklist_form(checklist_id: str, session: Session = Depends(get_session)):
    """Delete checklist"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        return RedirectResponse(url="/checklists", status_code=302)

    session.delete(checklist)
    session.commit()

    return RedirectResponse(url="/checklists", status_code=302)


@router.get("/candidate/{candidate_email}/checklist/{checklist_id}", response_class=HTMLResponse)
def view_checklist(
    candidate_email: str,
    checklist_id: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """View checklist for a candidate"""
    from ...models import Candidate, CandidateChecklistState

    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    candidate = session.get(Candidate, candidate_email)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get or create checklist state
    state = session.exec(
        select(CandidateChecklistState).where(
            CandidateChecklistState.candidate_email == candidate_email,
            CandidateChecklistState.checklist_id == checklist_id
        )
    ).first()

    if not state:
        # Create new state with all items unchecked
        items_list = json.loads(checklist.items)
        state_dict = {item: False for item in items_list}
        state = CandidateChecklistState(
            candidate_email=candidate_email,
            checklist_id=checklist_id,
            state=json.dumps(state_dict)
        )
        session.add(state)
        session.commit()

    # Parse items and state
    items_list = json.loads(checklist.items)
    state_dict = json.loads(state.state)

    return templates.TemplateResponse("checklist_view.html", {
        "request": request,
        "checklist": checklist,
        "candidate": candidate,
        "items": items_list,
        "state": state_dict
    })


@router.post("/candidate/{candidate_email}/checklist/{checklist_id}/update")
def update_checklist_state(
    candidate_email: str,
    checklist_id: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """Update checklist state for a candidate"""
    from ...models import CandidateChecklistState

    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Get existing state
    state = session.exec(
        select(CandidateChecklistState).where(
            CandidateChecklistState.candidate_email == candidate_email,
            CandidateChecklistState.checklist_id == checklist_id
        )
    ).first()

    if not state:
        raise HTTPException(status_code=404, detail="Checklist state not found")

    # Parse form data to update state
    items_list = json.loads(checklist.items)
    state_dict = {}

    # Get form data (will be a multipart/form-data request with checkboxes)
    import asyncio
    form = asyncio.run(request.form())

    for item in items_list:
        # Checkbox is checked if its name appears in form data
        state_dict[item] = item in form

    state.state = json.dumps(state_dict)
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.commit()

    return RedirectResponse(
        url=f"/candidate/{candidate_email}/checklist/{checklist_id}",
        status_code=302
    )
