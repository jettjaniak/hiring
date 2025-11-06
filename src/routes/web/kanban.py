"""
Kanban board web UI routes
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from pathlib import Path

from ...dependencies import get_session

# Get project root directory
project_root = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(project_root / "templates"))

router = APIRouter(tags=["web-kanban"])


@router.get("/tasks/kanban", response_class=HTMLResponse)
def view_kanban(request: Request, session: Session = Depends(get_session)):
    """Render kanban board view"""
    return templates.TemplateResponse(
        "kanban_view.html",
        {"request": request}
    )
