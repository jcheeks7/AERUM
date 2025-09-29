import threading
import time

import pytest

from interface.dashboard import create_app
from interface.event_store import EventStore


@pytest.fixture
def store():
    return EventStore(max_events=10)


@pytest.fixture
def app(store):
    return create_app(store)


def test_event_store_records_events(store):
    store.record_event("AgentA", "Event 1")
    store.record_event("AgentB", "Event 2")

    events = store.get_events(limit=5)
    assert events[0]["message"] == "Event 2"
    assert events[1]["agent"] == "AgentA"

    statuses = {s["agent"]: s for s in store.get_statuses()}
    assert statuses["AgentB"]["status"] == "Event 2"


def test_api_endpoints_return_recent_events(app, store):
    client = app.test_client()
    store.record_event("Agent", "Ready")

    events_resp = client.get("/api/events?limit=1")
    data = events_resp.get_json()
    assert data["events"][0]["message"] == "Ready"

    agents_resp = client.get("/api/agents")
    agent_payload = agents_resp.get_json()
    assert agent_payload["agents"][0]["status"] == "Ready"


def test_event_store_streams_updates(store):
    subscriber = store.subscribe()

    def push_event():
        time.sleep(0.05)
        store.record_event("Agent", "Streaming")

    threading.Thread(target=push_event, daemon=True).start()

    payload = subscriber.get(timeout=1.0)
    assert payload["type"] == "event"
    assert payload["event"]["message"] == "Streaming"

    status_payload = subscriber.get(timeout=1.0)
    assert status_payload["type"] == "status"

    store.unsubscribe(subscriber)
