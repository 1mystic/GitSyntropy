"""Tests for team management CRUD endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture()
def created_team():
    resp = client.post(
        "/api/v1/teams",
        json={"name": "Turing Squad", "description": "Test team", "created_by": "user_turing"},
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_team_returns_201() -> None:
    resp = client.post(
        "/api/v1/teams",
        json={"name": "Apollo", "description": None, "created_by": "user_apollo"},
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["name"] == "Apollo"
    assert payload["created_by"] == "user_apollo"
    assert payload["invite_token"]
    assert len(payload["members"]) == 1  # creator auto-added
    assert payload["members"][0]["role"] == "owner"


def test_get_team_by_id(created_team) -> None:
    team_id = created_team["id"]
    resp = client.get(f"/api/v1/teams/{team_id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == team_id
    assert payload["name"] == created_team["name"]


def test_get_team_not_found() -> None:
    resp = client.get("/api/v1/teams/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_list_teams_for_user(created_team) -> None:
    user_id = created_team["created_by"]
    resp = client.get("/api/v1/teams", params={"user_id": user_id})
    assert resp.status_code == 200
    teams = resp.json()
    assert isinstance(teams, list)
    team_ids = [t["id"] for t in teams]
    assert created_team["id"] in team_ids


def test_add_and_remove_member(created_team) -> None:
    team_id = created_team["id"]

    add_resp = client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": "user_newmember", "github_handle": "newmember", "role": "engineer"},
    )
    assert add_resp.status_code == 201
    member = add_resp.json()
    assert member["user_id"] == "user_newmember"
    assert member["role"] == "engineer"

    # Duplicate add should 409
    dup_resp = client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": "user_newmember", "role": "engineer"},
    )
    assert dup_resp.status_code == 409

    # Remove member
    del_resp = client.delete(f"/api/v1/teams/{team_id}/members/user_newmember")
    assert del_resp.status_code == 204

    # Remove again → 404
    del2_resp = client.delete(f"/api/v1/teams/{team_id}/members/user_newmember")
    assert del2_resp.status_code == 404


def test_create_team_name_too_short() -> None:
    resp = client.post(
        "/api/v1/teams",
        json={"name": "A", "created_by": "user_short"},
    )
    assert resp.status_code == 422


def test_add_member_to_nonexistent_team() -> None:
    resp = client.post(
        "/api/v1/teams/00000000-dead-beef-0000-000000000000/members",
        json={"user_id": "user_orphan"},
    )
    assert resp.status_code == 404
