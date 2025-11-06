"""
Checklist API routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List
import json
from datetime import datetime, timezone

from ...models import Checklist, CandidateChecklistState, Candidate
from ...dependencies import get_session

router = APIRouter(prefix="/api", tags=["checklists"])


class SaveChecklistRequest(BaseModel):
    candidate_id: str
    task_identifier: str
    items_state: List[bool]


@router.post("/checklist/{checklist_id}/save")
def save_checklist_state(
    checklist_id: str,
    request: SaveChecklistRequest,
    session: Session = Depends(get_session)
):
    """Save checklist state for a candidate"""
    # Validate checklist exists
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Validate candidate exists
    candidate = session.get(Candidate, request.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get items list from checklist
    items_list = json.loads(checklist.items)

    # Validate items_state length matches
    if len(request.items_state) != len(items_list):
        raise HTTPException(
            status_code=400,
            detail=f"items_state length {len(request.items_state)} does not match checklist items length {len(items_list)}"
        )

    # Convert items_state list to dict mapping item name to checked status
    state_dict = {item: request.items_state[i] for i, item in enumerate(items_list)}

    # Get or create checklist state
    state = session.exec(
        select(CandidateChecklistState).where(
            CandidateChecklistState.candidate_id == request.candidate_id,
            CandidateChecklistState.checklist_id == checklist_id,
            CandidateChecklistState.task_identifier == request.task_identifier
        )
    ).first()

    if state:
        # Update existing state
        state.items_state = json.dumps(state_dict)
        state.updated_at = datetime.now(timezone.utc)
        session.add(state)
    else:
        # Create new state
        state = CandidateChecklistState(
            candidate_id=request.candidate_id,
            checklist_id=checklist_id,
            task_identifier=request.task_identifier,
            items_state=json.dumps(state_dict)
        )
        session.add(state)

    session.commit()

    return {"success": True, "message": "Checklist saved successfully"}
