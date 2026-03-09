"""Validate the evidence index view migration structure.

Ensures the player-facing view excludes fact, and the full view includes it.
Verifies access control and filtering expectations.
"""

from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "supabase" / "migrations"


def _read_migration(filename: str) -> str:
    path = MIGRATIONS_DIR / filename
    assert path.exists(), f"Migration file not found: {path}"
    return path.read_text()


class TestEvidenceIndexView:
    """Verify the player-facing evidence_index view."""

    sql = _read_migration("20260308000002_create_evidence_index_view.sql")

    def test_creates_evidence_index_view(self) -> None:
        assert "accusations.evidence_index" in self.sql

    def test_player_view_excludes_fact(self) -> None:
        """The evidence_index view must not select the fact column."""
        lines = self.sql.split("\n")
        in_player_view = False
        in_full_view = False
        for line in lines:
            if "accusations.evidence_index" in line:
                in_player_view = True
                in_full_view = False
            elif "accusations.evidence_full" in line:
                in_player_view = False
                in_full_view = True

            if in_player_view and not in_full_view:
                stripped = line.strip()
                if stripped.startswith("--"):
                    continue
                # fact should not appear as a selected column in player view
                if stripped.startswith("fact"):
                    raise AssertionError("evidence_index must not select fact column")

    def test_player_view_selects_expected_columns(self) -> None:
        expected = ["objectID", "title", "blurb", "category", "signal", "url", "tags"]
        for col in expected:
            assert col in self.sql

    def test_filters_by_signal(self) -> None:
        assert "signal > 2" in self.sql

    def test_excludes_soft_deleted(self) -> None:
        assert "deleted_at IS NULL" in self.sql

    def test_grants_anon_select(self) -> None:
        assert "GRANT SELECT ON accusations.evidence_index TO anon" in self.sql


class TestEvidenceFullView:
    """Verify the AI-only evidence_full view."""

    sql = _read_migration("20260308000002_create_evidence_index_view.sql")

    def test_creates_full_view(self) -> None:
        assert "accusations.evidence_full" in self.sql

    def test_full_view_includes_fact(self) -> None:
        """The evidence_full view must include the fact column."""
        lines = self.sql.split("\n")
        in_full_view = False
        found_fact = False
        for line in lines:
            if "CREATE" in line and "evidence_full" in line:
                in_full_view = True
            elif in_full_view and line.strip().startswith("FROM"):
                break
            if in_full_view and "fact" in line.strip() and not line.strip().startswith("--"):
                found_fact = True
        assert found_fact, "evidence_full must select the fact column"

    def test_revokes_anon_from_full_view(self) -> None:
        assert "REVOKE ALL ON accusations.evidence_full FROM anon" in self.sql

    def test_no_anon_grant_on_full_view(self) -> None:
        """Anon must not have SELECT on the full view."""
        lines = self.sql.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            if "GRANT" in stripped and "evidence_full" in stripped and "anon" in stripped:
                raise AssertionError("Must not grant anon access to evidence_full")

    def test_revokes_authenticated_from_full_view(self) -> None:
        assert "REVOKE ALL ON accusations.evidence_full FROM authenticated" in self.sql
