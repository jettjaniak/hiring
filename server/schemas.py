from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CandidateCreate(BaseModel):
    id: str


class CandidateResponse(BaseModel):
    id: str
    metadata_id: str

    class Config:
        from_attributes = True


class CandidateListItem(BaseModel):
    id: str

    class Config:
        from_attributes = True


class FieldUpdate(BaseModel):
    key: str
    encrypted_value: bytes
    version: int


class FieldUpdateRequest(BaseModel):
    fields: List[FieldUpdate]


class FieldVersion(BaseModel):
    key: str
    version: int


class FieldUpdateResponse(BaseModel):
    updated: List[FieldVersion]


class FieldResponse(BaseModel):
    candidate_id: str
    field_name: str
    encrypted_value: bytes
    version: int
    updated_at: datetime

    class Config:
        from_attributes = True


class CandidateWithFields(BaseModel):
    candidate: CandidateResponse
    fields: List[FieldResponse]


class CandidateTaskCreate(BaseModel):
    candidate_id: str
    task_identifier: str


class CandidateTaskResponse(BaseModel):
    candidate_id: str
    task_identifier: str
    metadata_id: str

    class Config:
        from_attributes = True


class TaskFieldResponse(BaseModel):
    candidate_id: str
    task_identifier: str
    field_name: str
    encrypted_value: bytes
    version: int
    updated_at: datetime

    class Config:
        from_attributes = True


class ActionStateCreate(BaseModel):
    candidate_id: str
    action_id: str


class ActionStateResponse(BaseModel):
    candidate_id: str
    action_id: str
    metadata_id: str

    class Config:
        from_attributes = True


class ActionStateFieldResponse(BaseModel):
    candidate_id: str
    action_id: str
    field_name: str
    encrypted_value: bytes
    version: int
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    candidates: List[CandidateResponse]
    candidate_fields: List[FieldResponse]
    tasks: List[CandidateTaskResponse]
    task_fields: List[TaskFieldResponse]
    action_states: List[ActionStateResponse]
    action_state_fields: List[ActionStateFieldResponse]
    sync_timestamp: datetime


class KeyVerificationCreate(BaseModel):
    encrypted_canary: bytes


class KeyVerificationResponse(BaseModel):
    encrypted_canary: bytes
    created_at: datetime

    class Config:
        from_attributes = True
