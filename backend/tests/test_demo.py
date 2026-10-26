from __future__ import annotations

import pytest
from fastapi import status
from datetime import datetime, timezone
from app.models import Task, ScheduleBlock, Goal, FixedEvent
from app.seed import FIXED_DEMO_NOW


def test_demo_reset_endpoint(client, db_session):
    """POST /demo/reset clears and seeds workspace anchored at FIXED_DEMO_NOW."""
    response = client.post("/demo/reset")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["goals_count"] == 3
    assert data["tasks_count"] == 9
    assert data["fixed_events_count"] == 3
    assert data["blocks_count"] == 4
    assert "2026-10-26" in data["fixed_now"]


def test_demo_status_endpoint(client):
    """GET /demo/status returns demo mode configuration and the 3 scripted commands."""
    response = client.get("/demo/status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["demo_mode"] is True
    assert len(data["scripted_commands"]) == 3
    commands = [c["command"] for c in data["scripted_commands"]]
    assert any("3 hours" in c for c in commands)
    assert any("urgent" in c for c in commands)
    assert any("tomorrow" in c for c in commands)


def test_demo_simulate_end_of_day(client, db_session):
    """POST /demo/simulate-end-of-day triggers end-of-day rollover and rescheduling."""
    # First reset to fresh state
    reset_res = client.post("/demo/reset")
    assert reset_res.status_code == status.HTTP_200_OK

    # Simulate end of day
    eod_res = client.post("/demo/simulate-end-of-day")
    assert eod_res.status_code == status.HTTP_200_OK
    eod_data = eod_res.json()
    assert "Rollover complete" in eod_data["message"] or "rolled over" in eod_data["message"].lower()
    assert "blocks" in eod_data
    assert "stuck_tasks" in eod_data
