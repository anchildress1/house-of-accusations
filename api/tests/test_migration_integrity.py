"""Validate that the accusations schema migration is well-formed.

These tests parse the SQL migration file and verify structural expectations
without requiring a live database connection.
"""

from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "supabase" / "migrations"


def _read_migration(filename: str) -> str:
    path = MIGRATIONS_DIR / filename
    assert path.exists(), f"Migration file not found: {path}"
    return path.read_text()


class TestAccusationsSchema:
    """Verify structural expectations of the accusations schema migration."""

    sql = _read_migration("20260308000001_create_accusations_schema.sql")

    def test_creates_accusations_schema(self) -> None:
        assert "CREATE SCHEMA" in self.sql
        assert "accusations" in self.sql

    def test_creates_session_state_enum(self) -> None:
        assert "session_state" in self.sql
        for state in ("created", "exploring", "deciding", "resolved"):
            assert f"'{state}'" in self.sql

    def test_creates_user_position_enum(self) -> None:
        assert "user_position" in self.sql
        for position in ("proof", "objection"):
            assert f"'{position}'" in self.sql

    def test_creates_sessions_table(self) -> None:
        assert "CREATE TABLE accusations.sessions" in self.sql
        assert "session_id" in self.sql
        assert "accusation_text" in self.sql

    def test_creates_evidence_selections_table(self) -> None:
        assert "CREATE TABLE accusations.evidence_selections" in self.sql
        assert "card_id" in self.sql
        assert "user_position" in self.sql
        assert "ai_score" in self.sql

    def test_creates_ai_audit_run_table(self) -> None:
        assert "CREATE TABLE accusations.ai_audit_run" in self.sql
        assert "chosen_card_id" in self.sql
        assert "contract_name" in self.sql
        assert "final_score" in self.sql
        assert "raw_output_text" in self.sql

    def test_foreign_keys_reference_public_cards(self) -> None:
        assert 'REFERENCES public.cards("objectID")' in self.sql

    def test_foreign_keys_reference_sessions(self) -> None:
        assert "REFERENCES accusations.sessions(session_id)" in self.sql

    def test_score_constraints(self) -> None:
        assert "ai_score >= -1.0" in self.sql
        assert "ai_score <= 1.0" in self.sql
        assert "final_score >= -1.0" in self.sql
        assert "final_score <= 1.0" in self.sql

    def test_rls_enabled_on_all_tables(self) -> None:
        for table in ("sessions", "evidence_selections", "ai_audit_run"):
            assert f"ALTER TABLE accusations.{table} ENABLE ROW LEVEL SECURITY" in self.sql

    def test_indexes_created(self) -> None:
        expected_indexes = [
            "idx_sessions_state",
            "idx_evidence_session_id",
            "idx_evidence_card_session",
            "idx_audit_session_id",
        ]
        for idx in expected_indexes:
            assert idx in self.sql, f"Missing index: {idx}"

    def test_updated_at_trigger(self) -> None:
        assert "set_updated_at" in self.sql
        assert "trg_sessions_updated_at" in self.sql

    def test_no_delete_policies(self) -> None:
        assert "FOR DELETE" not in self.sql

    def test_no_write_grants_to_public_schema(self) -> None:
        lines = self.sql.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            if "GRANT" in stripped and "INSERT" in stripped and "public.cards" in stripped:
                raise AssertionError("Must not grant INSERT on public.cards")
            if "GRANT" in stripped and "UPDATE" in stripped and "public.cards" in stripped:
                raise AssertionError("Must not grant UPDATE on public.cards")
