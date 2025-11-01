"""
FastAPI backend with auto-generated CRUD operations.

This uses FastAPI + SQLModel to automatically generate:
- REST API endpoints for all models
- OpenAPI/Swagger documentation at /docs
- ReDoc documentation at /redoc
- Input validation
- Response serialization

Run with: uvicorn api:app --reload --port 8000
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, create_engine, select
from typing import List, Optional
import os

from models import Candidate, CandidateTask, ActionState

# Database setup
DATA_DIR = os.path.expanduser("~/.hiring-app")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "hiring.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Create all tables"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session


# Create FastAPI app
app = FastAPI(
    title="Hiring Process API",
    description="Simple API for managing candidates through hiring workflows",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ============================================================================
# Candidate endpoints
# ============================================================================

@app.get("/api/candidates", response_model=List[Candidate])
def list_candidates(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    session: Session = Depends(get_session)
):
    """List all candidates"""
    query = select(Candidate)
    if not include_deleted:
        query = query.where(Candidate.deleted == False)
    candidates = session.exec(query.offset(skip).limit(limit)).all()
    return candidates


@app.get("/api/candidates/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str, session: Session = Depends(get_session)):
    """Get a specific candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@app.post("/api/candidates", response_model=Candidate)
def create_candidate(candidate: Candidate, session: Session = Depends(get_session)):
    """Create a new candidate"""
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


@app.patch("/api/candidates/{candidate_id}", response_model=Candidate)
def update_candidate(
    candidate_id: str,
    candidate_update: dict,
    session: Session = Depends(get_session)
):
    """Update a candidate (partial update)"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    for key, value in candidate_update.items():
        if hasattr(candidate, key):
            setattr(candidate, key, value)

    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: str, session: Session = Depends(get_session)):
    """Soft delete a candidate"""
    from datetime import datetime
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.deleted = True
    candidate.deleted_at = datetime.utcnow()
    session.add(candidate)
    session.commit()
    return {"message": "Candidate deleted"}


# ============================================================================
# CandidateTask endpoints
# ============================================================================

@app.get("/api/candidates/{candidate_id}/tasks", response_model=List[CandidateTask])
def list_candidate_tasks(candidate_id: str, session: Session = Depends(get_session)):
    """List all tasks for a candidate"""
    tasks = session.exec(
        select(CandidateTask).where(CandidateTask.candidate_id == candidate_id)
    ).all()
    return tasks


@app.get("/api/tasks/{candidate_id}/{task_identifier}", response_model=CandidateTask)
def get_task(
    candidate_id: str,
    task_identifier: str,
    session: Session = Depends(get_session)
):
    """Get a specific task"""
    task = session.get(CandidateTask, (candidate_id, task_identifier))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/api/tasks/{candidate_id}/{task_identifier}", response_model=CandidateTask)
def upsert_task(
    candidate_id: str,
    task_identifier: str,
    status: str,
    session: Session = Depends(get_session)
):
    """Create or update a task"""
    task = session.get(CandidateTask, (candidate_id, task_identifier))

    if task:
        task.status = status
    else:
        task = CandidateTask(
            candidate_id=candidate_id,
            task_identifier=task_identifier,
            status=status
        )

    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# ============================================================================
# ActionState endpoints
# ============================================================================

@app.get("/api/action-states/{candidate_id}/{action_id}", response_model=ActionState)
def get_action_state(
    candidate_id: str,
    action_id: str,
    session: Session = Depends(get_session)
):
    """Get action state"""
    state = session.get(ActionState, (candidate_id, action_id))
    if not state:
        raise HTTPException(status_code=404, detail="Action state not found")
    return state


@app.put("/api/action-states/{candidate_id}/{action_id}", response_model=ActionState)
def upsert_action_state(
    candidate_id: str,
    action_id: str,
    state_data: dict,
    session: Session = Depends(get_session)
):
    """Create or update action state"""
    action_state = session.get(ActionState, (candidate_id, action_id))

    if action_state:
        action_state.state = state_data
    else:
        action_state = ActionState(
            candidate_id=candidate_id,
            action_id=action_id,
            state=state_data
        )

    session.add(action_state)
    session.commit()
    session.refresh(action_state)
    return action_state


# ============================================================================
# Health check
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": DB_PATH
    }
