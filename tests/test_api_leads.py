"""API tests for lead routes."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_leads_returns_202(client: AsyncClient):
    """POST /leads accepts payload and returns 202 with id."""
    resp = await client.post(
        "/leads",
        json={
            "source": "web",
            "raw_payload": "Acme Corp, VP Sales, interested in enterprise.",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_get_lead_not_found(client: AsyncClient):
    """GET /leads/99999 returns 404."""
    resp = await client.get("/leads/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_lead_after_post(client: AsyncClient):
    """POST then GET returns the stored lead."""
    post_resp = await client.post(
        "/leads",
        json={"source": "api", "raw_payload": {"company": "Test", "role": "CTO"}},
    )
    assert post_resp.status_code == 202
    lead_id = post_resp.json()["id"]
    get_resp = await client.get(f"/leads/{lead_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == lead_id
    assert data["status"] == "pending"
    assert "raw_payload" in data
    assert "events" in data
