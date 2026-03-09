"""Session management: create, read, and advance session state."""

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException

from house_of_accusations.db import get_supabase_client
from house_of_accusations.models import (
    SESSION_TRANSITIONS,
    SessionCreate,
    SessionResponse,
    SessionState,
    SessionStateUpdate,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _rows(data: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """Narrow Supabase response data to a list of row dicts."""
    return cast(list[dict[str, Any]], data)


@router.post("", status_code=201)
async def create_session(body: SessionCreate | None = None) -> SessionResponse:
    """Create a new game session with a local UUID."""
    client = get_supabase_client()
    insert_data: dict[str, str | None] = {}
    if body and body.accusation_text:
        insert_data["accusation_text"] = body.accusation_text

    result = client.schema("accusations").table("sessions").insert(insert_data).execute()
    rows = _rows(result.data)

    if not rows:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return SessionResponse(**rows[0])


@router.get("/{session_id}")
async def get_session(session_id: UUID) -> SessionResponse:
    """Retrieve a session by ID."""
    client = get_supabase_client()
    result = (
        client.schema("accusations")
        .table("sessions")
        .select("*")
        .eq("session_id", str(session_id))
        .execute()
    )
    rows = _rows(result.data)

    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(**rows[0])


@router.patch("/{session_id}/state")
async def advance_session_state(
    session_id: UUID,
    body: SessionStateUpdate,
) -> SessionResponse:
    """Advance session state. Only valid forward transitions are allowed."""
    client = get_supabase_client()

    current = (
        client.schema("accusations")
        .table("sessions")
        .select("*")
        .eq("session_id", str(session_id))
        .execute()
    )
    current_rows = _rows(current.data)

    if not current_rows:
        raise HTTPException(status_code=404, detail="Session not found")

    current_state = SessionState(str(current_rows[0]["state"]))
    allowed = SESSION_TRANSITIONS[current_state]

    if body.state not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{current_state.value}' to '{body.state.value}'. "
            f"Allowed: {[s.value for s in allowed]}",
        )

    result = (
        client.schema("accusations")
        .table("sessions")
        .update({"state": body.state.value})
        .eq("session_id", str(session_id))
        .execute()
    )
    rows = _rows(result.data)

    if not rows:
        raise HTTPException(status_code=500, detail="Failed to update session state")

    return SessionResponse(**rows[0])
