"""Tests for session management endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient

SESSION_ID = str(uuid4())
NOW = datetime.now(tz=UTC).isoformat()

_PATCH_READ = "house_of_accusations.sessions.get_supabase_client"
_PATCH_WRITE = "house_of_accusations.sessions.get_supabase_service_client"


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
    chain.update.return_value.eq.return_value.eq.return_value.execute.return_value = execute_result

    schema_mock = MagicMock()
    schema_mock.table.return_value = chain

    client_mock = MagicMock()
    client_mock.schema.return_value = schema_mock
    return client_mock


def _mock_state_transition(from_state: str, to_state: str) -> MagicMock:
    """Return a service-role client mock for state transitions (read + write on same client)."""
    select_result = MagicMock()
    select_result.data = [_mock_session(state=from_state)]
    update_result = MagicMock()
    update_result.data = [_mock_session(state=to_state)]

    table = MagicMock()
    table.select.return_value.eq.return_value.execute.return_value = select_result
    table.update.return_value.eq.return_value.eq.return_value.execute.return_value = update_result

    schema_mock = MagicMock()
    schema_mock.table.return_value = table

    client_mock = MagicMock()
    client_mock.schema.return_value = schema_mock
    return client_mock


class TestCreateSession:
    @patch(_PATCH_WRITE)
    async def test_create_session_default(self, mock_svc: MagicMock, client: AsyncClient) -> None:
        mock_svc.return_value = _mock_supabase_chain([_mock_session()])
        response = await client.post("/sessions")
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == SESSION_ID
        assert data["state"] == "created"

    @patch(_PATCH_WRITE)
    async def test_create_session_with_accusation(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        mock_svc.return_value = _mock_supabase_chain(
            [_mock_session(accusation_text="Accused of excellence")]
        )
        response = await client.post(
            "/sessions",
            json={"accusation_text": "Accused of excellence"},
        )
        assert response.status_code == 201
        assert response.json()["accusation_text"] == "Accused of excellence"

    @patch(_PATCH_WRITE)
    async def test_create_session_failure(self, mock_svc: MagicMock, client: AsyncClient) -> None:
        mock_svc.return_value = _mock_supabase_chain([])
        response = await client.post("/sessions")
        assert response.status_code == 500


class TestGetSession:
    @patch(_PATCH_READ)
    async def test_get_session_found(self, mock_get_client: MagicMock, client: AsyncClient) -> None:
        mock_get_client.return_value = _mock_supabase_chain([_mock_session()])
        response = await client.get(f"/sessions/{SESSION_ID}")
        assert response.status_code == 200
        assert response.json()["session_id"] == SESSION_ID

    @patch(_PATCH_READ)
    async def test_get_session_not_found(
        self, mock_get_client: MagicMock, client: AsyncClient
    ) -> None:
        mock_get_client.return_value = _mock_supabase_chain([])
        response = await client.get(f"/sessions/{uuid4()}")
        assert response.status_code == 404


class TestAdvanceSessionState:
    @patch(_PATCH_WRITE)
    async def test_valid_transition_created_to_exploring(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        mock_svc.return_value = _mock_state_transition("created", "exploring")
        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "exploring"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "exploring"

    @patch(_PATCH_WRITE)
    async def test_valid_transition_exploring_to_deciding(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        mock_svc.return_value = _mock_state_transition("exploring", "deciding")
        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "deciding"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "deciding"

    @patch(_PATCH_WRITE)
    async def test_valid_transition_deciding_to_resolved(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        mock_svc.return_value = _mock_state_transition("deciding", "resolved")
        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "resolved"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "resolved"

    @patch(_PATCH_WRITE)
    async def test_invalid_transition_created_to_deciding(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        mock_svc.return_value = _mock_supabase_chain([_mock_session(state="created")])
        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "deciding"},
        )
        assert response.status_code == 409

    @patch(_PATCH_WRITE)
    async def test_invalid_transition_resolved_to_anything(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        mock_svc.return_value = _mock_supabase_chain([_mock_session(state="resolved")])
        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "exploring"},
        )
        assert response.status_code == 409

    @patch(_PATCH_WRITE)
    async def test_advance_nonexistent_session(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        mock_svc.return_value = _mock_supabase_chain([])
        response = await client.patch(
            f"/sessions/{uuid4()}/state",
            json={"state": "exploring"},
        )
        assert response.status_code == 404

    @patch(_PATCH_WRITE)
    async def test_concurrent_modification_returns_409(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """Optimistic lock: write returns no rows when state changed between read and write."""
        select_result = MagicMock()
        select_result.data = [_mock_session(state="created")]
        update_result = MagicMock()
        update_result.data = []  # Another request modified state first

        table = MagicMock()
        table.select.return_value.eq.return_value.execute.return_value = select_result
        table.update.return_value.eq.return_value.eq.return_value.execute.return_value = (
            update_result
        )
        schema_mock = MagicMock()
        schema_mock.table.return_value = table
        client_mock = MagicMock()
        client_mock.schema.return_value = schema_mock
        mock_svc.return_value = client_mock

        response = await client.patch(
            f"/sessions/{SESSION_ID}/state",
            json={"state": "exploring"},
        )
        assert response.status_code == 409
        assert "modified" in response.json()["detail"].lower()


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
