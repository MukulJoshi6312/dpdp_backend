"""Smoke + behaviour tests for the Nyaykosh backend."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def _token() -> str:
    resp = client.post(
        "/v1/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_list_laws_and_get_one():
    laws = client.get("/v1/laws").json()
    assert len(laws) >= 1
    slug = laws[0]["apiSlug"]
    one = client.get(f"/v1/laws/{slug}").json()
    assert one["apiSlug"] == slug
    assert "provisions" in one and "penalties" in one


def test_law_subresources():
    slug = client.get("/v1/laws").json()[0]["apiSlug"]
    assert isinstance(client.get(f"/v1/laws/{slug}/penalties").json(), list)
    provisions = client.get(f"/v1/laws/{slug}/provisions").json()
    assert isinstance(provisions, list)


def test_law_filters():
    dp = client.get("/v1/laws", params={"category": "Data Protection"}).json()
    assert all(l["category"] == "Data Protection" for l in dp)


def test_simulator_personas_and_evaluate():
    personas = client.get("/v1/simulator/personas").json()
    assert len(personas) >= 1
    p = personas[0]
    t = p["triggers"][0]
    rule = t["rules"][0]

    # Nothing checked -> non-compliant for that rule, critical-ish overall.
    empty = client.post(
        "/v1/simulator/evaluate",
        json={"personaId": p["id"], "triggerId": t["id"], "checkedKeys": []},
    ).json()
    assert empty["applicable"] == len(t["rules"])
    assert empty["overallPercent"] == 0

    # Check every item of the first rule.
    keys = [f"{rule['id']}::action::{i}" for i in range(len(rule["actions"]))]
    keys += [f"{rule['id']}::artifact::{i}" for i in range(len(rule["artifacts"]))]
    partial = client.post(
        "/v1/simulator/evaluate",
        json={"personaId": p["id"], "triggerId": t["id"], "checkedKeys": keys},
    ).json()
    first = next(r for r in partial["perRule"] if r["rule"]["id"] == rule["id"])
    assert first["status"] == "compliant"
    assert first["percent"] == 100


def test_auth_required_for_admin():
    assert client.get("/v1/admin/stats").status_code == 401


def test_admin_stats_with_token():
    token = _token()
    resp = client.get("/v1/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["laws"] >= 1
    assert stats["rules"] >= 1


def test_template_download():
    token = _token()
    resp = client.get(
        "/v1/admin/rules/template", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )
