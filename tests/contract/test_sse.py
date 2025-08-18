"""
Contract Tests for /sse Endpoint

Task P1.2.3 — Non-MCP /sse (contract-only)
Verifies SSE stream contract compliance: event order, JSON schema, resumability.
"""

import pytest
import json
import re
from fastapi.testclient import TestClient
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))

from main import app
from surfaces.contracts import (
    SSEEvent,
    ExecuteResponse,
    validate_contract_structure,
    get_contract_hash,
)

client = TestClient(app)


class TestSSEEndpointContract:
    """Test contract compliance for /sse endpoint"""

    def test_sse_endpoint_exists(self):
        """Test that /sse endpoint is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        # Verify endpoint is documented in OpenAPI
        openapi_data = response.json()
        assert "/sse" in openapi_data["paths"]

    def test_sse_stream_response_format(self):
        """Test that SSE stream returns proper event stream format"""
        response = client.get("/sse")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "Cache-Control" in response.headers
        assert "Connection" in response.headers

    def test_sse_event_order(self):
        """Test that events are emitted in correct order: progress → section → done"""
        response = client.get("/sse")
        assert response.status_code == 200

        content = response.text
        lines = content.strip().split("\n")

        # Parse events
        events = []
        current_event = {}

        for line in lines:
            if line.startswith("event: "):
                if current_event:
                    events.append(current_event)
                current_event = {"type": line[7:], "data": None}
            elif line.startswith("data: "):
                if current_event:
                    try:
                        current_event["data"] = json.loads(line[6:])
                    except json.JSONDecodeError:
                        current_event["data"] = line[6:]
            elif line == "" and current_event:
                events.append(current_event)
                current_event = {}

        if current_event:
            events.append(current_event)

        # Verify event order
        event_types = [event["type"] for event in events if event.get("type")]

        # Should have progress events first
        progress_events = [e for e in event_types if e == "progress"]
        assert len(progress_events) >= 1, "Should have at least one progress event"

        # Should have section event
        assert "section" in event_types, "Should have section event"

        # Should have done event last
        assert "done" in event_types, "Should have done event"

        # Verify order: progress events come before section, section before done
        progress_indices = [i for i, e in enumerate(event_types) if e == "progress"]
        section_index = event_types.index("section")
        done_index = event_types.index("done")

        assert all(
            i < section_index for i in progress_indices
        ), "Progress events should come before section"
        assert section_index < done_index, "Section should come before done"

    def test_sse_progress_events_structure(self):
        """Test that progress events have correct structure"""
        response = client.get("/sse")
        assert response.status_code == 200

        content = response.text
        progress_events = []

        # Extract progress events
        for line in content.split("\n"):
            if line.startswith("event: progress"):
                # Find corresponding data line
                pass

        # Parse events more carefully
        events = self._parse_sse_events(content)
        progress_events = [e for e in events if e["type"] == "progress"]

        assert len(progress_events) >= 1, "Should have at least one progress event"

        for event in progress_events:
            assert "data" in event, "Progress event should have data"
            assert "percent" in event["data"], "Progress data should have percent"
            assert isinstance(
                event["data"]["percent"], int
            ), "Percent should be integer"
            assert 0 <= event["data"]["percent"] <= 100, "Percent should be 0-100"

    def test_sse_section_event_structure(self):
        """Test that section event has correct structure"""
        response = client.get("/sse")
        assert response.status_code == 200

        events = self._parse_sse_events(response.text)
        section_events = [e for e in events if e["type"] == "section"]

        assert len(section_events) == 1, "Should have exactly one section event"

        section_event = section_events[0]
        assert "data" in section_event, "Section event should have data"

        data = section_event["data"]
        assert "section_id" in data, "Section data should have section_id"
        assert "title" in data, "Section data should have title"
        assert "status" in data, "Section data should have status"
        assert "result" in data, "Section data should have result"

    def test_sse_done_event_structure(self):
        """Test that done event has ExecuteResponse-compatible structure"""
        response = client.get("/sse")
        assert response.status_code == 200

        events = self._parse_sse_events(response.text)
        done_events = [e for e in events if e["type"] == "done"]

        assert len(done_events) == 1, "Should have exactly one done event"

        done_event = done_events[0]
        assert "data" in done_event, "Done event should have data"

        data = done_event["data"]

        # Verify ExecuteResponse structure
        assert "logic_output" in data, "Done data should have logic_output"
        assert "execution_time_ms" in data, "Done data should have execution_time_ms"
        assert "cache_hit" in data, "Done data should have cache_hit"
        assert "metadata" in data, "Done data should have metadata"

        # Verify logic_output structure
        logic_output = data["logic_output"]
        assert "result" in logic_output, "Logic output should have result"
        assert "provenance" in logic_output, "Logic output should have provenance"
        assert "confidence" in logic_output, "Logic output should have confidence"
        assert "alerts" in logic_output, "Logic output should have alerts"
        assert (
            "applied_rule_set" in logic_output
        ), "Logic output should have applied_rule_set"
        assert "explanation" in logic_output, "Logic output should have explanation"

    def test_sse_resumability_cursor_echo(self):
        """Test that cursor parameter is echoed back for resumability"""
        test_cursor = "test_cursor_123"
        response = client.get(f"/sse?cursor={test_cursor}")
        assert response.status_code == 200

        events = self._parse_sse_events(response.text)
        cursor_events = [e for e in events if e["type"] == "cursor"]

        assert (
            len(cursor_events) == 1
        ), "Should have exactly one cursor event when cursor provided"

        cursor_event = cursor_events[0]
        assert "data" in cursor_event, "Cursor event should have data"
        assert "cursor" in cursor_event["data"], "Cursor data should have cursor field"
        assert (
            cursor_event["data"]["cursor"] == test_cursor
        ), "Cursor should be echoed back"

    def test_sse_no_cursor_when_not_provided(self):
        """Test that no cursor event is sent when cursor parameter is not provided"""
        response = client.get("/sse")
        assert response.status_code == 200

        events = self._parse_sse_events(response.text)
        cursor_events = [e for e in events if e["type"] == "cursor"]

        assert (
            len(cursor_events) == 0
        ), "Should have no cursor event when cursor not provided"

    def test_sse_deterministic_behavior(self):
        """Test that SSE stream is deterministic (same events on multiple calls)"""
        response1 = client.get("/sse")
        response2 = client.get("/sse")

        assert response1.status_code == 200
        assert response2.status_code == 200

        events1 = self._parse_sse_events(response1.text)
        events2 = self._parse_sse_events(response2.text)

        # Should have same number of events
        assert len(events1) == len(events2), "Should have same number of events"

        # Should have same event types in same order
        types1 = [e["type"] for e in events1]
        types2 = [e["type"] for e in events2]
        assert types1 == types2, "Should have same event types in same order"

        # Progress events should have same percent values
        progress1 = [e for e in events1 if e["type"] == "progress"]
        progress2 = [e for e in events2 if e["type"] == "progress"]

        assert len(progress1) == len(
            progress2
        ), "Should have same number of progress events"

        for p1, p2 in zip(progress1, progress2):
            assert (
                p1["data"]["percent"] == p2["data"]["percent"]
            ), "Progress events should have same percent values"

    def test_sse_contract_hash_stability(self):
        """Test that SSE contract hashes are stable"""
        # Get contract hashes
        sse_event_hash = get_contract_hash(SSEEvent)

        # Hashes should be deterministic
        assert len(sse_event_hash) == 16

        # Re-generate hashes to ensure stability
        assert get_contract_hash(SSEEvent) == sse_event_hash

    def _parse_sse_events(self, content: str) -> list:
        """Helper method to parse SSE events from content"""
        events = []
        current_event = {}

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("event: "):
                if current_event:
                    events.append(current_event)
                current_event = {"type": line[7:], "data": None}
            elif line.startswith("data: "):
                if current_event:
                    try:
                        current_event["data"] = json.loads(line[6:])
                    except json.JSONDecodeError:
                        current_event["data"] = line[6:]
            elif line == "" and current_event:
                events.append(current_event)
                current_event = {}

        if current_event:
            events.append(current_event)

        return events
