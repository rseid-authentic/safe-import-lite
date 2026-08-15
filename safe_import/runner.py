import json
import subprocess
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError


class RunnerError(RuntimeError):
    """Single visible application error for any codex exec failure."""


CODEX_MODEL = "gpt-5.6-luna"
CALL_TIMEOUT_SECONDS = 120
AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "codex_audit.jsonl"

# Fail-closed audit, confirmed against codex-cli 0.147.0 preflight output.
# A clean no-tool run emits only lifecycle events plus agent_message/reasoning
# items; command, file, MCP, and web activity surface as other item types and
# anything unrecognized is rejected.
ALLOWED_EVENT_TYPES = {
    "thread.started",
    "turn.started",
    "turn.completed",
    "item.started",
    "item.updated",
    "item.completed",
}
ALLOWED_ITEM_TYPES = {"agent_message", "reasoning"}

M = TypeVar("M", bound=BaseModel)


def strict_schema(response_model: type[BaseModel]) -> dict:
    """The structured-output endpoint requires additionalProperties: false on
    every object node; Pydantic does not emit it."""
    schema = response_model.model_json_schema()

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                node.setdefault("additionalProperties", False)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    return schema


def audit_events(stdout: str) -> None:
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RunnerError(f"unparseable codex event: {line[:200]}") from exc
        event_type = event.get("type")
        if event_type not in ALLOWED_EVENT_TYPES:
            raise RunnerError(
                f"rejected codex run: disallowed event type {event_type!r}"
            )
        if event_type.startswith("item."):
            item_type = event.get("item", {}).get("type")
            if item_type not in ALLOWED_ITEM_TYPES:
                raise RunnerError(
                    f"rejected codex run: disallowed item type {item_type!r}"
                )


def parse_last_message(raw: str, response_model: type[M]) -> M:
    try:
        return response_model.model_validate_json(raw)
    except ValidationError as exc:
        raise RunnerError(
            f"codex output failed {response_model.__name__} validation: {exc}"
        ) from exc


def run_structured(
    prompt: str, response_model: type[M], record_to: Path | None = None
) -> M:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        workdir = tmp / "work"
        workdir.mkdir()
        schema_file = tmp / "schema.json"
        schema_file.write_text(json.dumps(strict_schema(response_model)))
        last_message_file = tmp / "last.txt"
        command = [
            "codex", "exec",
            "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--sandbox", "read-only", "--skip-git-repo-check",
            "--model", CODEX_MODEL,
            "-c", 'model_reasoning_effort="low"',
            "-C", str(workdir),
            "--json",
            "--output-schema", str(schema_file),
            "-o", str(last_message_file),
            "-",
        ]
        try:
            process = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=CALL_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RunnerError(f"codex exec did not run: {exc}") from exc

        with AUDIT_LOG_PATH.open("a") as audit_log:
            audit_log.write(process.stdout)

        audit_events(process.stdout)
        if process.returncode != 0:
            raise RunnerError(
                f"codex exec failed with exit code {process.returncode}: "
                f"{process.stderr.strip()[:500]}"
            )
        try:
            raw = last_message_file.read_text()
        except OSError as exc:
            raise RunnerError("codex exec wrote no last message") from exc

    parsed = parse_last_message(raw, response_model)
    if record_to is not None:
        record_to.parent.mkdir(parents=True, exist_ok=True)
        record_to.write_text(raw)
    return parsed
