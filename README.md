# Safe Import Lite

A caller submits one approved CSV fixture ID. The application inspects the CSV, asks Codex to
propose a source-to-target column mapping, and deterministic code returns either a proposal
preview or a blocked reason. It never imports or persists contacts.

## Request path

`POST /imports/preview {fixture_id}` → Codex call 1 returns `ToolRequest` → Pydantic validates →
app runs `inspect_import_context` (allowlisted fixture, headers + 5 sample rows + target schema) →
Codex call 2 returns `MappingProposal` → Pydantic validates → deterministic gate decides
`proposal` or `blocked`.

## Commands

```bash
uv run uvicorn safe_import.main:app --reload   # serve; interactive docs at /docs
uv run pytest -q                               # unit tests, no model calls
uv run python -m safe_import.eval              # live three-case evaluation (~45s)
```

Expected eval output:

```text
exact_headers   proposal  required mappings and samples valid
common_aliases  proposal  required mappings and samples valid
missing_email   blocked   no credible email column
```

## Layout

- `safe_import/main.py` — FastAPI routes, prompts, two-call orchestration
- `safe_import/models.py` — Pydantic contracts (`ToolRequest`, `MappingProposal`, ...)
- `safe_import/inspection.py` — hardcoded fixture allowlist + CSV inspection tool
- `safe_import/validation.py` — deterministic gate (required mappings, source existence,
  duplicate targets, email sample credibility)
- `safe_import/runner.py` — `codex exec` adapter, strict output schema, fail-closed JSONL audit
- `safe_import/eval.py` — live three-case summary
- `fixtures/` — three approved synthetic CSVs
- `recorded/` — structured responses from successful live eval runs, retained so a Codex outage
  can be replayed through the same Pydantic + gate path (labeled as recorded). Only
  `safe_import.eval` refreshes these; serving traffic never touches them.

## Codex runner policy

Each model call runs `codex exec --ephemeral --ignore-user-config --ignore-rules --sandbox
read-only --skip-git-repo-check --model gpt-5.6-luna` with low reasoning effort, `-C` pointed at
an empty temp dir, prompt on stdin, and `--output-schema` generated from the Pydantic model
(the contracts declare `extra="forbid"`, which both rejects extra keys in responses and makes
Pydantic emit the `additionalProperties: false` the structured-output endpoint requires).
Prompts never contain a filesystem path; call 1 receives only the opaque fixture ID. JSONL
stdout — including partial output from timed-out runs — is appended to `codex_audit.jsonl`.
A non-zero exit reports the exit code and stderr; a clean exit is then audited fail-closed:
any event type outside the observed lifecycle set, or any item type other than
`agent_message`/`reasoning`, rejects the run.

## Known limitations

- `--sandbox read-only` prevents writes only. File reads outside the workdir are detected and
  rejected by the JSONL audit; they are not prevented by isolation.
- The audit allowlist was confirmed against codex-cli 0.147.0 event shapes. A CLI upgrade that
  changes event names will reject runs until the allowlist is re-confirmed (fail closed, by
  design).
- No retries: any runner failure (including the model requesting the wrong fixture in call 1)
  surfaces as one visible 502 with the reason.
- Email credibility is a shape regex over at most five non-empty samples, not deliverability or
  full RFC validation.
- The preview endpoint is synchronous and each request holds a threadpool worker for up to two
  sequential codex calls; this demo is not built for concurrent load.
- The `recorded/` replay fallback was never needed; Codex stayed available. There is no replay
  flag — replaying is a manual exercise through `parse_last_message` + the gate.
