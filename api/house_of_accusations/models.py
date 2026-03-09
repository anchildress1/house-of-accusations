"""Pydantic models for the accusations game domain."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class SessionState(StrEnum):
    created = "created"
    exploring = "exploring"
    deciding = "deciding"
    resolved = "resolved"


class UserPosition(StrEnum):
    proof = "proof"
    objection = "objection"


# Valid state transitions: current_state -> allowed next states
SESSION_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.created: {SessionState.exploring},
    SessionState.exploring: {SessionState.deciding},
    SessionState.deciding: {SessionState.resolved},
    SessionState.resolved: set(),
}


class SessionCreate(BaseModel):
    """Request body for creating a new session."""

    accusation_text: str | None = None


class SessionResponse(BaseModel):
    """Response body for session data."""

    session_id: UUID
    state: SessionState
    accusation_text: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionStateUpdate(BaseModel):
    """Request body for advancing session state."""

    state: SessionState = Field(
        description="Target state. Must be a valid transition from current state."
    )


class EvidenceSelection(BaseModel):
    """Response body for an evidence selection."""

    id: UUID
    session_id: UUID
    card_id: UUID
    user_position: UserPosition
    ai_score: float = Field(ge=-1.0, le=1.0)
    room: str
    created_at: datetime
