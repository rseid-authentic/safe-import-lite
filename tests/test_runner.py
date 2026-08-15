import pytest

from safe_import.models import MappingProposal, ToolRequest
from safe_import.runner import RunnerError, audit_events, parse_last_message

# Recorded from the codex-cli 0.147.0 preflight call (2026-08-15).
CLEAN_STREAM = """\
{"type":"thread.started","thread_id":"01a0072d-9eb1-7153-9295-1871ce763aba"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"{\\"tool\\":\\"inspect_import_context\\",\\"fixture_id\\":\\"exact_headers\\"}"}}
{"type":"turn.completed","usage":{"input_tokens":14146,"cached_input_tokens":0,"cache_write_input_tokens":0,"output_tokens":36,"reasoning_output_tokens":11}}
"""


def test_clean_stream_accepted():
    audit_events(CLEAN_STREAM)


def test_command_item_rejected():
    stream = (
        '{"type":"item.completed","item":{"id":"item_0",'
        '"type":"command_execution","command":"cat fixtures/exact_headers.csv"}}\n'
    )
    with pytest.raises(RunnerError, match="disallowed item type"):
        audit_events(stream)


def test_unknown_event_type_rejected_fail_closed():
    with pytest.raises(RunnerError, match="disallowed event type"):
        audit_events('{"type":"turn.failed","error":{"message":"boom"}}\n')


def test_unparseable_event_rejected():
    with pytest.raises(RunnerError, match="unparseable"):
        audit_events("not json\n")


def test_valid_tool_request_parses():
    parsed = parse_last_message(
        '{"tool":"inspect_import_context","fixture_id":"exact_headers"}', ToolRequest
    )
    assert parsed.fixture_id == "exact_headers"


def test_malformed_tool_request_fails_visibly():
    with pytest.raises(RunnerError, match="ToolRequest validation"):
        parse_last_message(
            '{"tool":"read_file","fixture_id":"exact_headers"}', ToolRequest
        )


def test_malformed_proposal_fails_visibly():
    with pytest.raises(RunnerError, match="MappingProposal validation"):
        parse_last_message('{"mappings":"not a list"}', MappingProposal)
