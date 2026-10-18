from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from collective.auth import Principal
from collective.graph import graph_name
from collective.memory import priority, visible
from collective.sandbox import safe_path
from collective.settings import DependencyUnavailable, configured, require_key
from collective.decisions import decision_yes
from src.memory_influence import MemoryInfluenceLayer
from src.models import MemoryCategory, RetrievalResult, create_memory_node


@pytest.mark.parametrize("value", ["", "****", "your-key", "sk-****"])
def test_placeholder_is_never_a_working_credential(value):
    assert not configured(value)
    with pytest.raises(DependencyUnavailable):
        require_key("TEST_KEY", value)


@pytest.mark.parametrize("path", ["../secret", "/etc/passwd", "/workspace/../../secret", "C:\\secrets", "a\x00b"])
def test_sandbox_rejects_host_and_traversal_paths(path):
    with pytest.raises(HTTPException):
        safe_path(path)


def test_sandbox_allows_nested_workspace_file():
    assert safe_path("src/app.py") == "/workspace/src/app.py"


def test_scopes_are_independent_of_retrieval_relevance():
    actor = Principal("alice", "tenant", "member", "Alice")
    record = {"project_id": "p", "visibility": "user", "owner_id": "bob"}
    assert not visible(record, actor, "p")
    record.update(visibility="agent", owner_id="alice", agent_id="researcher")
    assert not visible(record, actor, "p", "builder")
    assert visible(record, actor, "p", "researcher")
    assert not visible(record, actor, "other", "researcher")


def test_graph_namespace_rejects_injection():
    with pytest.raises(ValueError):
        graph_name("tenant; MATCH (n) DETACH DELETE n")


def test_retention_does_not_mutate_truth_confidence():
    old = {
        "created_at": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
        "category": "temporary",
        "confidence": 1,
    }
    fresh = {**old, "created_at": datetime.now(timezone.utc).isoformat()}
    assert priority(fresh, 0.8) > priority(old, 0.8)
    assert old["confidence"] == 1


def test_legacy_custom_pinned_and_temporary_survive_injection():
    temp = create_memory_node("Call the project owner this afternoon", MemoryCategory.TEMPORARY)
    text = MemoryInfluenceLayer().inject(
        RetrievalResult({"identity": "My name is SamplePerson"}, [temp], 100), "What next?"
    )
    assert "SamplePerson" in text
    assert "this afternoon" in text


def test_viewer_cannot_write():
    with pytest.raises(HTTPException) as exc:
        Principal("a", "t", "viewer", "A").write()
    assert exc.value.status_code == 403


def test_policy_booleans_are_not_calibrated_probabilities():
    assert decision_yes({"decision": True}, 0.99)
    assert not decision_yes({"decision": False}, 0.01)
    assert decision_yes({"noul": 0.9}, 0.8)
    assert not decision_yes({"noul": 0.6}, 0.8)
    with pytest.raises(ValueError):
        decision_yes({"decision": "true"}, 0.5)


def test_changed_files_need_fresh_checks_and_matching_published_bytes():
    from collective.evidence import builder_completion_problem

    progress = {
        "written_files": [{"event_id": 20, "path": "/workspace/app.py", "sha256": "current-bytes"}],
        "recent_checks": [{"id": 19, "exit_code": 0, "verified_passed": True}],
        "published_artifacts": [{"name": "app.py", "sha256": "previous-bytes"}],
    }
    assert builder_completion_problem(progress)  # Old checks cannot attest changed files.
    progress["recent_checks"] = [{"id": 21, "exit_code": 0, "verified_passed": True}]
    assert builder_completion_problem(progress)  # Checked bytes still need publication.
    progress["published_artifacts"] = [{"name": "app.py", "sha256": "current-bytes"}]
    assert builder_completion_problem(progress) is None


def test_shell_success_and_printed_pass_text_are_not_test_evidence():
    from collective.evidence import verified_check

    assert not verified_check({"command": "cat > app.py", "exit_code": 0, "stdout": "1 passed"})
    assert not verified_check({"command": "python -c 'print(\"1 passed\")'", "exit_code": 0, "stdout": "1 passed"})
    assert not verified_check({"command": "pytest --collect-only", "exit_code": 0, "stdout": "1 test collected"})
    assert not verified_check({"command": "pytest -q || true", "exit_code": 0, "stdout": "1 passed"})
    assert verified_check({"command": "python -m pytest -q", "exit_code": 0, "stdout": "1 passed in 0.01s"})
    assert verified_check({"command": "cd /workspace && python -m pytest -q", "exit_code": 0, "stdout": "1 passed in 0.01s"})
    assert not verified_check({"command": "cd /tmp && python -m pytest -q", "exit_code": 0, "stdout": "1 passed"})
    assert not verified_check({"command": "cd /workspace && python -m pytest -q || true", "exit_code": 0, "stdout": "1 passed"})
    assert verified_check({"command": "python -m unittest", "exit_code": 0, "stderr": "Ran 1 test in 0.01s\n\nOK\n"})
