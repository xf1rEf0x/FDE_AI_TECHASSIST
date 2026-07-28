"""Tests for support summary storage layer."""

import json
from datetime import datetime
from src.storage.summary_store import SupportSummary, SummaryStore


class TestSummaryStoreInit:
    def test_init_creates_store_path(self, tmp_path):
        store_path = tmp_path / "sub" / "summaries.json"
        SummaryStore(str(store_path))
        assert store_path.parent.exists()

    def test_init_creates_empty_json_file(self, tmp_path):
        store_path = tmp_path / "summaries.json"
        SummaryStore(str(store_path))
        assert store_path.exists()
        with open(store_path) as f:
            assert json.load(f) == []


class TestSaveSummary:
    def test_save_summary_fields(self, tmp_path):
        store = SummaryStore(str(tmp_path / "summaries.json"))
        record = store.save_summary(
            "alice@example.com", "VPN ticket created and warranty checked.", ticket_id="tkt-1"
        )
        assert record.user_email == "alice@example.com"
        assert record.summary == "VPN ticket created and warranty checked."
        assert record.ticket_id == "tkt-1"
        assert record.id
        datetime.fromisoformat(record.created_at)

    def test_save_summary_persists(self, tmp_path):
        store_path = tmp_path / "summaries.json"
        store = SummaryStore(str(store_path))
        store.save_summary("bob@example.com", "Summary text")
        with open(store_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["user_email"] == "bob@example.com"


class TestListSummaries:
    def test_list_returns_only_users_summaries(self, tmp_path):
        store = SummaryStore(str(tmp_path / "summaries.json"))
        store.save_summary("alice@example.com", "A summary")
        store.save_summary("bob@example.com", "B summary")
        alice_summaries = store.list_summaries("alice@example.com")
        assert len(alice_summaries) == 1
        assert alice_summaries[0].user_email == "alice@example.com"

    def test_list_empty_for_unknown_user(self, tmp_path):
        store = SummaryStore(str(tmp_path / "summaries.json"))
        assert store.list_summaries("nobody@example.com") == []
