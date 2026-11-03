import asyncio
import io
import json
import logging
import os
import sys
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from app.graph.engine import IntakeNodes
from app.graph.resources import Resources
from app.graph.state import IntakeState
from app.integrations.gnani import Gnani
from app.integrations.ollama import OllamaClient
from scripts import age_v2_run as runner

CHECKS = [
    "TCP reachable at localhost:5432",
    "login accepted for role khoj",
    "current database is khoj_eval",
    "inet_server_port() is 5432",
    "current_user is khoj",
]
SECRET = "stub-credential"
LOCAL_URL = f"postgresql+asyncpg://khoj:{SECRET}@localhost:5432/khoj_eval"
IDENTITY_QUERY = "select current_database(), current_user, inet_server_port()"


@pytest.fixture(autouse=True)
def no_provider_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    ollama = AsyncMock(side_effect=AssertionError("Ollama call"))
    gnani = AsyncMock(side_effect=AssertionError("Gnani request"))
    monkeypatch.setattr(OllamaClient, "chat", ollama)
    monkeypatch.setattr(Gnani, "_post", gnani)
    yield
    ollama.assert_not_called()
    gnani.assert_not_called()


@pytest.fixture
def local_stubs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    writer = SimpleNamespace(close=Mock(), wait_closed=AsyncMock())
    tcp = AsyncMock(return_value=(None, writer))
    connection = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(one=lambda: ("khoj_eval", "khoj", 5432))),
        close=AsyncMock(),
    )
    engine = SimpleNamespace(connect=AsyncMock(return_value=connection), dispose=AsyncMock())
    create_engine = Mock(return_value=engine)
    evaluate = AsyncMock(side_effect=AssertionError("Evaluation called"))
    env = {"EVAL_DATABASE_URL": LOCAL_URL, "OLLAMA_API_KEY": SECRET}
    monkeypatch.setattr(runner, "dotenv_values", lambda *args, **kwargs: env)
    monkeypatch.setattr(runner, "os", SimpleNamespace(environ={}, devnull=os.devnull))
    monkeypatch.setattr(asyncio, "open_connection", tcp)
    monkeypatch.setattr(runner, "create_async_engine", create_engine)
    monkeypatch.setattr(runner, "evaluate", evaluate)
    monkeypatch.setattr(runner, "DRY_RUN_MARKER", tmp_path / "artifacts" / ".dryrun_ok")
    return SimpleNamespace(
        tcp=tcp,
        engine=engine,
        connection=connection,
        evaluate=evaluate,
        env=env,
        create_engine=create_engine,
    )


@pytest.mark.parametrize("failed", range(len(CHECKS)))
def test_dry_run_exits_at_first_identity_failure(
    failed: int,
    local_stubs: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stubs = local_stubs
    if failed == 0:
        stubs.tcp.side_effect = ConnectionRefusedError(SECRET)
    elif failed == 1:
        stubs.engine.connect.side_effect = RuntimeError(SECRET)
    else:
        row = (
            (SECRET, "khoj", 5432),
            ("khoj_eval", "khoj", None),
            ("khoj_eval", SECRET, 5432),
        )[failed - 2]
        stubs.connection.execute.return_value = SimpleNamespace(one=lambda: row)

    monkeypatch.setattr(sys, "argv", ["age_v2_run", "--dry-run"])
    monkeypatch.setattr(logging, "disable", Mock())
    with pytest.raises(SystemExit) as exc:
        runner.main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        *(f"PASS {check}" for check in CHECKS[:failed]),
        f"FAIL {CHECKS[failed]}",
    ]
    assert not captured.err
    stubs.tcp.assert_awaited_once_with("localhost", 5432)
    assert stubs.engine.connect.await_count == (failed >= 1)
    assert stubs.connection.execute.await_count == (failed >= 2)
    assert stubs.connection.close.await_count == (failed >= 2)
    stubs.evaluate.assert_not_called()
    assert not runner.DRY_RUN_MARKER.exists()


async def test_dry_run_rejects_nonlocal_configuration(
    local_stubs: SimpleNamespace, capsys: pytest.CaptureFixture[str]
) -> None:
    local_stubs.env["EVAL_DATABASE_URL"] = LOCAL_URL.replace("localhost", "outside.invalid")

    with pytest.raises(runner.StopRun):
        await runner.run(dry_run=True)

    assert capsys.readouterr().out.splitlines() == [f"FAIL {CHECKS[0]}"]
    local_stubs.tcp.assert_not_called()
    local_stubs.create_engine.assert_not_called()
    local_stubs.evaluate.assert_not_called()


async def test_passing_dry_run_writes_configuration_bound_marker(
    local_stubs: SimpleNamespace, capsys: pytest.CaptureFixture[str]
) -> None:
    await runner.run(dry_run=True)

    assert capsys.readouterr().out.splitlines()[:5] == [f"PASS {check}" for check in CHECKS]
    local_stubs.tcp.assert_awaited_once_with("localhost", 5432)
    assert str(local_stubs.connection.execute.await_args.args[0]) == IDENTITY_QUERY
    url = local_stubs.create_engine.call_args.args[0]
    assert (url.host, url.port) == ("localhost", 5432)
    assert SECRET not in runner.DRY_RUN_MARKER.read_text()
    fingerprint = runner.dry_run_fingerprint(url, SECRET)
    runner.require_dry_run(fingerprint)
    for changed in (
        runner.dry_run_fingerprint(url.set(password="different-db-secret"), SECRET),
        runner.dry_run_fingerprint(url, "different-api-key"),
    ):
        with pytest.raises(runner.StopRun, match="same evaluation configuration"):
            runner.require_dry_run(changed)
    local_stubs.evaluate.assert_not_called()


@pytest.mark.parametrize("marker", ["missing", "stale", "different-environment"])
async def test_paid_entry_point_refuses_invalid_marker(
    marker: str, local_stubs: SimpleNamespace
) -> None:
    if marker != "missing":
        await runner.run(dry_run=True)
    if marker == "stale":
        yesterday = datetime.combine(date.today() - timedelta(days=1), time(12)).timestamp()
        os.utime(runner.DRY_RUN_MARKER, (yesterday, yesterday))
    if marker == "different-environment":
        local_stubs.env["OLLAMA_API_KEY"] = "different-api-key"

    with pytest.raises(runner.StopRun, match="Run --dry-run successfully today"):
        await runner.run(dry_run=False)

    local_stubs.evaluate.assert_not_called()


async def test_marker_consumed_after_stubbed_success(
    local_stubs: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    await runner.run(dry_run=True)
    local_stubs.evaluate.side_effect = None
    local_stubs.evaluate.return_value = []
    monkeypatch.setattr(runner, "write_report", Mock(return_value="stubbed report"))

    await runner.run(dry_run=False)

    local_stubs.evaluate.assert_awaited_once()
    assert not runner.DRY_RUN_MARKER.exists()


@pytest.mark.parametrize(
    ("schema", "repeat", "age", "gender", "age_label", "decision", "age_outcome"),
    [
        ("v2", 0, (25, 25, "twenty five"), None, (25, 25), "kept", "correct"),
        ("v2", 0, (25, 27, "twenty five"), None, (25, 27), "number_missing", "omitted"),
        ("v2", 0, (25, 25, "wrong quote"), None, (25, 25), "quote_missing", "omitted"),
        ("v2", 0, None, "female", None, None, "null_correct"),
        ("v2", 0, None, None, None, None, "null_correct"),
        ("v2", 2, (25, 25, "twenty five"), None, None, "kept", "null_wrong_value"),
        ("v1", 0, None, None, (25, 25), "kept", "correct"),
    ],
)
async def test_turn_diagnostics(
    schema: str,
    repeat: int,
    age: tuple[int, int, str] | None,
    gender: str | None,
    age_label: tuple[int, int] | None,
    decision: str | None,
    age_outcome: str,
) -> None:
    source = "Age twenty five, female, blue coat."
    fields = [{"name": "clothing", "value": " ", "evidence": "blue coat"}]
    if gender:
        fields.append({"name": "gender", "value": gender, "evidence": gender})
    if schema == "v1":
        fields.append({"name": "age", "value": "25", "evidence": "twenty five"})
    raw: dict[str, Any] = {"intent": "provide_details", "fields": fields}
    if age is not None:
        raw.update(zip(("age_min", "age_max", "age_evidence"), age, strict=True))
    gateway = cast(
        OllamaClient,
        SimpleNamespace(chat=AsyncMock(return_value={"message": {"content": json.dumps(raw)}})),
    )
    llm = runner.AuditedLLM(gateway, {"roles": {"turn": {"primary": "fake"}}}, runner.Budget())
    nodes = IntakeNodes(llm, Resources(), cast(Any, None), cast(Any, None), cast(Any, schema))
    state = cast(
        IntakeState,
        {
            "current": {"text": source, "mode": "text"},
            "lang": "en",
            "draft": {},
            "transcripts": [source],
            "asked": [],
        },
    )
    updates = cast(dict[str, Any], state)
    updates.update(await nodes.analyze_turn(state))
    updates.update(nodes.ground(state))
    updates.update(nodes.merge(state))
    turn = runner.TurnPlan(
        {"item_id": "fixture", "category": "messy", "lang": "en", "text": source}, schema, repeat
    )
    result = runner.TurnResult(
        turn, state["draft"], state.get("age_grounding_drop"), kept=state["kept"]
    )
    labels: dict[str, Any] = {"fixture": dict.fromkeys(("age", *runner.FIELDS))}
    if age_label:
        labels["fixture"]["age"] = {"value": {"min": age_label[0], "max": age_label[1]}}
    log = io.StringIO()
    runner.log_turn(log, llm, result, labels, ())
    record = json.loads(log.getvalue())
    assert source not in log.getvalue()
    assert len(log.getvalue().splitlines()) == 1
    expected_grounding = [
        {
            "field": "clothing",
            "proposal_index": 0,
            "decision": "blank_dropped",
            "reason": "blank_value",
        },
    ]
    if gender:
        expected_grounding.append(
            {
                "field": "gender",
                "proposal_index": 1,
                "decision": "kept",
                "reason": "production_grounding_passed",
            }
        )
    if decision:
        expected_grounding.append(
            {
                "field": "age",
                "proposal_index": 1 if schema == "v1" else None,
                "decision": decision,
                "reason": {
                    "kept": "production_grounding_passed",
                    "number_missing": "range_not_supported_by_quote",
                    "quote_missing": "exact_quote_check_failed",
                }[decision],
            }
        )
    expected_comparison: dict[str, dict[str, Any]] = {
        field: {"label_value": None, "outcome": "null_correct"} for field in runner.FIELDS
    }
    expected_comparison["age"] = {
        "label_value": {"min": age_label[0], "max": age_label[1]} if age_label else None,
        "outcome": age_outcome,
    }
    if gender:
        expected_comparison["gender"]["outcome"] = "null_wrong_value"
    assert record == {
        "item_id": "fixture",
        "schema": schema,
        "turn_type": "repeat" if repeat else "primary",
        "repeat": repeat,
        "extracted": raw,
        "grounding": expected_grounding,
        "comparison": expected_comparison,
        "attempts": [
            {
                "attempt": 1,
                "role": "turn",
                "model": "fake",
                "phase": "initial",
                "retry": 1,
                "chain_position": 1,
                "fallback": False,
                "think": None,
                "timeout_seconds": 6.0,
                "outcome": "success",
                "thinking_present": False,
                "wall_ms": ANY,
            }
        ],
    }
    assert record["attempts"][0]["wall_ms"] >= 0


def test_diagnostic_redaction() -> None:
    source = "Example complete fixture"
    raw = {
        "age_evidence": source,
        "age_min": 9000000001,
        "fields": [{"value": f"{SECRET} 9000000001"}],
    }
    assert runner.safe_log_value(raw, source, (SECRET,)) == {
        "age_evidence": "[TRANSCRIPT]",
        "age_min": "[PHONE]",
        "fields": [{"value": "[SECRET] [PHONE]"}],
    }


@pytest.mark.parametrize(
    ("flags", "version", "case_count", "repeat_count", "extractions"),
    [
        ([], "v2", 45, 10, 100),
        (["--corpus", "evals/heldout_v3"], "v3", 60, 0, 120),
    ],
)
def test_frozen_corpus_plan(
    flags: list[str],
    version: str,
    case_count: int,
    repeat_count: int,
    extractions: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(runner.BACKEND)
    args = runner.parse_args(["--dry-run", *flags])
    config = runner.evaluation_config(args.corpus, args.report, args.detail)
    assert config.corpus == runner.BACKEND / f"evals/heldout_{version}"
    assert config.report == runner.ROOT / f"docs/evaluation/age_{version}.md"
    assert config.detail == runner.ROOT / f"artifacts/speech-eval/age_{version}_detail_v2log.jsonl"

    plan, labels = runner.load_plan(config)
    assert len(labels) == case_count
    assert sum(bool(turn.repeat) for turn in plan) == repeat_count
    assert sum(turn.schema == "v1" and turn.repeat == 0 for turn in plan) == case_count
    assert sum(turn.schema == "v2" and turn.repeat == 0 for turn in plan) == case_count
    assert runner.planned_extractions(plan) == extractions

    runner.print_plan(plan, len(labels))
    output = capsys.readouterr().out
    assert (
        f"Cases {case_count}, primary turns {2 * case_count}, repeat turns {repeat_count}" in output
    )
    assert f"Planned extractions {extractions}/120" in output
    assert f"Planned initial chat attempts {extractions}/170" in output


@pytest.mark.parametrize(
    ("reserve", "counter", "cap", "message"),
    [
        ("reserve_extraction", "extractions", runner.EXTRACTION_CAP, "Extraction cap reached"),
        ("reserve_attempt", "attempts", runner.ATTEMPT_CAP, "Chat attempt cap reached"),
    ],
)
def test_budget_rejects_next_call(reserve: str, counter: str, cap: int, message: str) -> None:
    budget = runner.Budget()
    for _ in range(cap):
        getattr(budget, reserve)()
    with pytest.raises(runner.StopRun, match=message):
        getattr(budget, reserve)()
    assert getattr(budget, counter) == cap


@pytest.mark.parametrize("dry_run", [True, False])
@pytest.mark.parametrize("file", ["cases", "labels"])
async def test_hash_mismatch_stops_before_any_call(
    dry_run: bool, file: str, local_stubs: SimpleNamespace, tmp_path: Path
) -> None:
    config = runner.evaluation_config(runner.V3_CORPUS)
    config = replace(
        config,
        marker=tmp_path / ".dryrun_ok",
        corpus_hashes={**config.corpus_hashes, file: "0" * 64},
    )
    with pytest.raises(runner.StopRun, match=f"Corpus hash mismatch for {file}"):
        await runner.run(dry_run, config)
    local_stubs.create_engine.assert_not_called()
    local_stubs.tcp.assert_not_called()
    local_stubs.evaluate.assert_not_called()
