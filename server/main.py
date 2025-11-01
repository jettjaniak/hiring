from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import crud
import schemas
from database import get_db, init_db

app = FastAPI(title="Hiring Process API")

# CORS for web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()


# Candidate endpoints
@app.post("/api/candidates", response_model=schemas.CandidateResponse, status_code=201)
def create_candidate(candidate: schemas.CandidateCreate, db: Session = Depends(get_db)):
    """Create a new candidate"""
    existing = crud.get_candidate(db, candidate.id)
    if existing:
        raise HTTPException(status_code=400, detail="Candidate already exists")
    return crud.create_candidate(db, candidate)


@app.get("/api/candidates/{candidate_id}", response_model=schemas.CandidateWithFields)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """Get candidate metadata and all fields"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    fields = crud.get_candidate_fields(db, candidate_id)
    return {
        "candidate": candidate,
        "fields": fields
    }


@app.get("/api/candidates", response_model=List[schemas.CandidateListItem])
def list_candidates(db: Session = Depends(get_db)):
    """List all candidates (id and workflow_id only)"""
    return crud.list_candidates(db)


@app.put("/api/candidates/{candidate_id}/fields", response_model=schemas.FieldUpdateResponse)
def update_candidate_fields(
    candidate_id: str,
    update: schemas.FieldUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update specific candidate fields with version checking"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        results = crud.update_candidate_fields(db, candidate_id, update.fields)
        return {
            "updated": [{"key": key, "version": version} for key, version in results]
        }
    except crud.VersionConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": e.message,
                "conflicting_keys": e.conflicting_keys
            }
        )


# CandidateTask endpoints
@app.get("/api/candidates/{candidate_id}/tasks", response_model=List[schemas.CandidateTaskResponse])
def get_candidate_tasks(candidate_id: str, db: Session = Depends(get_db)):
    """Get all tasks for a candidate"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return crud.get_candidate_tasks(db, candidate_id)


@app.post("/api/candidate-tasks", response_model=schemas.CandidateTaskResponse, status_code=201)
def create_candidate_task(task: schemas.CandidateTaskCreate, db: Session = Depends(get_db)):
    """Create a new candidate task"""
    candidate = crud.get_candidate(db, task.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return crud.create_candidate_task(db, task)


@app.put(
    "/api/candidate-tasks/{candidate_id}/{task_identifier}/fields",
    response_model=schemas.FieldUpdateResponse
)
def update_candidate_task_fields(
    candidate_id: str,
    task_identifier: str,
    update: schemas.FieldUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update task fields with version checking"""
    task = crud.get_candidate_tasks(db, candidate_id)
    if not any(t.task_identifier == task_identifier for t in task):
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        results = crud.update_candidate_task_fields(db, candidate_id, task_identifier, update.fields)
        return {
            "updated": [{"key": key, "version": version} for key, version in results]
        }
    except crud.VersionConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": e.message,
                "conflicting_keys": e.conflicting_keys
            }
        )


# ActionState endpoints
@app.get("/api/candidates/{candidate_id}/action-states", response_model=List[schemas.ActionStateResponse])
def get_action_states(candidate_id: str, db: Session = Depends(get_db)):
    """Get all action states for a candidate"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return crud.get_action_states(db, candidate_id)


@app.post("/api/action-states", response_model=schemas.ActionStateResponse, status_code=201)
def create_action_state(action_state: schemas.ActionStateCreate, db: Session = Depends(get_db)):
    """Create a new action state"""
    candidate = crud.get_candidate(db, action_state.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return crud.create_action_state(db, action_state)


@app.put(
    "/api/action-states/{candidate_id}/{action_id}/fields",
    response_model=schemas.FieldUpdateResponse
)
def update_action_state_fields(
    candidate_id: str,
    action_id: str,
    update: schemas.FieldUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update action state fields with version checking"""
    states = crud.get_action_states(db, candidate_id)
    if not any(s.action_id == action_id for s in states):
        raise HTTPException(status_code=404, detail="Action state not found")

    try:
        results = crud.update_action_state_fields(db, candidate_id, action_id, update.fields)
        return {
            "updated": [{"key": key, "version": version} for key, version in results]
        }
    except crud.VersionConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": e.message,
                "conflicting_keys": e.conflicting_keys
            }
        )


# Sync endpoint
@app.get("/api/sync", response_model=schemas.SyncResponse)
def sync(
    since: datetime = Query(None, description="ISO timestamp to sync from. If omitted, returns ALL data."),
    db: Session = Depends(get_db)
):
    """
    Get all changes since a given timestamp.
    If 'since' is not provided, returns ALL data (full sync).
    Returns candidates, fields, tasks, and action states that have been created or modified.
    """
    if since is None:
        # Full sync - return all data
        since = datetime(1970, 1, 1)  # Beginning of time

    changes = crud.get_changes_since(db, since)

    return {
        "candidates": changes["candidates"],
        "candidate_fields": changes["candidate_fields"],
        "tasks": changes["tasks"],
        "task_fields": changes["task_fields"],
        "action_states": changes["action_states"],
        "action_state_fields": changes["action_state_fields"],
        "sync_timestamp": datetime.utcnow()
    }


# Key verification endpoints
@app.get("/api/key-verification", response_model=schemas.KeyVerificationResponse)
def get_key_verification(db: Session = Depends(get_db)):
    """Get the encrypted canary for key verification"""
    verification = crud.get_key_verification(db)
    if not verification:
        raise HTTPException(status_code=404, detail="No key verification found. Initialize with POST first.")
    return verification


@app.post("/api/key-verification", response_model=schemas.KeyVerificationResponse, status_code=201)
def create_key_verification(
    verification: schemas.KeyVerificationCreate,
    db: Session = Depends(get_db)
):
    """Create the encrypted canary for key verification (first time only)"""
    existing = crud.get_key_verification(db)
    if existing:
        raise HTTPException(status_code=400, detail="Key verification already exists")

    return crud.create_key_verification(db, verification.encrypted_canary)


@app.get("/")
def root():
    return {"message": "Hiring Process API", "version": "1.0"}
