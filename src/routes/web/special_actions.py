"""
Special action web UI routes - Document generation
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from pathlib import Path

from ...models import Candidate
from ...dependencies import get_session

# Get project root directory
project_root = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(project_root / "templates"))

router = APIRouter(tags=["web-special-actions"])


@router.get("/action/fill_offer_letter", response_class=HTMLResponse)
def fill_offer_letter_form(
    request: Request,
    candidate: str,
    task: str,
    session: Session = Depends(get_session)
):
    """Form to fill offer letter for a candidate"""
    from src.document_generator import extract_placeholders_from_docx

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Extract required fields from template
    try:
        placeholders = extract_placeholders_from_docx("offer_letter_template.docx")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Template file not found")

    # Pre-fill some fields from candidate data
    prefilled = {
        "CANDIDATE_NAME": cand.name or "",
        "CANDIDATE_EMAIL": cand.email or "",
    }

    return templates.TemplateResponse("action_offer_letter.html", {
        "request": request,
        "candidate": cand,
        "task_id": task,
        "placeholders": placeholders,
        "prefilled": prefilled
    })


@router.post("/action/fill_offer_letter")
async def generate_offer_letter(
    request: Request,
    candidate: str = Form(...),
    task: str = Form(...),
    session: Session = Depends(get_session)
):
    """Generate and download filled offer letter"""
    from src.document_generator import fill_docx_template

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get all form fields
    form_data = await request.form()

    # Build replacements dictionary
    replacements = {}
    for key, value in form_data.items():
        if key not in ["candidate", "task"] and value:
            replacements[f"{{{{{key}}}}}"] = value

    # Generate document
    try:
        doc_bytes = fill_docx_template("offer_letter_template.docx", replacements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")

    # Return as downloadable file
    filename = f"offer_letter_{cand.name.replace(' ', '_') if cand.name else cand.email}.docx"
    return StreamingResponse(
        doc_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/action/fill_background_check", response_class=HTMLResponse)
def fill_background_check_form(
    request: Request,
    candidate: str,
    task: str,
    session: Session = Depends(get_session)
):
    """Form to fill background check for a candidate"""
    from src.document_generator import extract_placeholders_from_xlsx

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Extract required fields from template
    try:
        placeholders = extract_placeholders_from_xlsx("background_check_template.xlsx")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Template file not found")

    # Pre-fill some fields from candidate data
    prefilled = {
        "CANDIDATE_NAME": cand.name or "",
        "CANDIDATE_EMAIL": cand.email or "",
        "CANDIDATE_PHONE": cand.phone or "",
    }

    return templates.TemplateResponse("action_background_check.html", {
        "request": request,
        "candidate": cand,
        "task_id": task,
        "placeholders": placeholders,
        "prefilled": prefilled
    })


@router.post("/action/fill_background_check")
async def generate_background_check(
    request: Request,
    candidate: str = Form(...),
    task: str = Form(...),
    session: Session = Depends(get_session)
):
    """Generate and download filled background check"""
    from src.document_generator import fill_xlsx_template

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get all form fields
    form_data = await request.form()

    # Build replacements dictionary
    replacements = {}
    for key, value in form_data.items():
        if key not in ["candidate", "task"] and value:
            replacements[f"{{{{{key}}}}}"] = value

    # Generate document
    try:
        doc_bytes = fill_xlsx_template("background_check_template.xlsx", replacements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")

    # Return as downloadable file
    filename = f"background_check_{cand.name.replace(' ', '_') if cand.name else cand.email}.xlsx"
    return StreamingResponse(
        doc_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
