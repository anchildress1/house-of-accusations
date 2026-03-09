"""Tests for session management endpoints."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from house_of_accusations.main import app

SESSION_ID = str(uuid4())
NOW = datetime.now(tz=UTC).isoformat()


def _mock_session(
    state: str = "created",
    accusation_text: str | None = None,
) -> dict[str, str | None]:
    return {
        "session_id": SESSION_ID,
        "state": state,
        "accusation_text": accusation_text,
        "created_at": NOW,
        "updated_at": NOW,
    }


def _mock_supabase_chain(return_data: list[dict[str, str | None]]) -> MagicMock:
    """Build a fluent mock chain: client.schema().table().method().execute()."""
    execute_result = MagicMock()
    execute_result.data = return_data

    chain = MagicMock()
    chain.insert.return_value.execute.return_value = execute_result
    chain.select.return_value.eq.return_value.execute.return_value = execute_result
    chain.update.return_value.eq.return_value.execute.return_value = execute_result

    schema_mock = MagicMock()
    schema_mock.table.return_value = chain

    client_mock = MagicMock()
    client_mock.schema.return_value = schema_mock
    return client_mock


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestCreateSession:
    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_create_session_default(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([_mock_session()])
        response = await client.post("/sessions")
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == SESSION_ID
        assert data["state"] == "created"

    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_create_session_with_accusation(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain(
            [_mock_session(accusation_text="Accused of excellence")]
        )
        response = await client.post(
            "/sessions",
            json={"accusation_text": "Accused of excellence"},
        )
        assert response.status_code == 201
        assert response.json()["accusation_text"] == "Accused of excellence"

    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_create_session_failure(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([])
        response = await client.post("/sessions")
        assert response.status_code == 500


class TestGetSession:
    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_get_session_found(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([_mock_session()])
        response = await client.get(f"/sessions/{SESSION_ID}")
        assert response.status_code == 200
        assert response.json()["session_id"] == SESSION_ID

    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_get_session_not_found(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([])
        response = await client.get(f"/sessions/{uuid4()}")
        assert response.status_code == 404


class TestAdvanceSessionState:
    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_valid_transition_created_to_exploring(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        select_result = MagicMock()
        select_result.data = [_mock_session(state="created")]
        update_result = MagicMock()
        update_result.data = [_mock_session(state="exploring")]

        table_mock = MagicMock()
        table_mock.select.return_value.eq.return_value.execute.return_value = select_result
        table_mock.update.return_value.eq.return_value.execute.return_value = update_result

        schema_mock = MagicMock()
        schema_mock.table.return_value = table_mock
        mock_client = MagicMock()
        mock_client.schema.return_value = schema_mock
        mock_get_client.return_value = mock_client

        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "exploring"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "exploring"

    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_valid_transition_exploring_to_deciding(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_client = _mock_supabase_chain([_mock_session(state="exploring")])

        # Override the first select to return exploring, then update returns deciding
        select_result = MagicMock()
        select_result.data = [_mock_session(state="exploring")]
        update_result = MagicMock()
        update_result.data = [_mock_session(state="deciding")]

        table_mock = MagicMock()
        table_mock.select.return_value.eq.return_value.execute.return_value = select_result
        table_mock.update.return_value.eq.return_value.execute.return_value = update_result

        schema_mock = MagicMock()
        schema_mock.table.return_value = table_mock
        mock_client.schema.return_value = schema_mock
        mock_get_client.return_value = mock_client

        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "deciding"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "deciding"

    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_invalid_transition_created_to_deciding(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([_mock_session(state="created")])
        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "deciding"},
        )
        assert response.status_code == 409

    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_invalid_transition_resolved_to_anything(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([_mock_session(state="resolved")])
        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "exploring"},
        )
        assert response.status_code == 409

    @patch("house_of_accusations.sessions.get_supabase_client")
    async def test_advance_nonexistent_session(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([])
        response = await client.patch(
            f"/sessions/{uuid4()}/state",
            json={"state": "exploring"},
        )
        assert response.status_code == 404


class TestSessionStateTransitions:
    """Verify the state transition map is correct."""

    def test_created_allows_only_exploring(self) -> None:
        from house_of_accusations.models import SESSION_TRANSITIONS, SessionState

        assert SESSION_TRANSITIONS[SessionState.created] == {SessionState.exploring}

    def test_exploring_allows_only_deciding(self) -> None:
        from house_of_accusations.models import SESSION_TRANSITIONS, SessionState

        assert SESSION_TRANSITIONS[SessionState.exploring] == {SessionState.deciding}

    def test_deciding_allows_only_resolved(self) -> None:
        from house_of_accusations.models import SESSION_TRANSITIONS, SessionState

        assert SESSION_TRANSITIONS[SessionState.deciding] == {SessionState.resolved}

    def test_resolved_allows_nothing(self) -> None:
        from house_of_accusations.models import SESSION_TRANSITIONS, SessionState

        assert SESSION_TRANSITIONS[SessionState.resolved] == set()

    def test_all_states_have_transition_rules(self) -> None:
        from house_of_accusations.models import SESSION_TRANSITIONS, SessionState

        for state in SessionState:
            assert state in SESSION_TRANSITIONS
