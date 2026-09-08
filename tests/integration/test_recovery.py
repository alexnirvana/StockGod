from datetime import timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select
from stock_god.api.main import create_app
from stock_god.db.models import Job, now
from stock_god.db.session import transaction
from stock_god.jobs.worker import claim, run_once
from test_workflows import post, order, client, register


def test_restart_recovers_frozen_funds(tmp_path):
    url = f"sqlite:///{tmp_path / 'persistent.db'}"
    with TestClient(create_app(url)) as c:
        register(c)
        created = order(c).json()
        post(c, "/courses/account/answers", {"answers": [1, 2]})
    with TestClient(create_app(url)) as c:
        assert post(c, "/auth/login", {"username": "testlearner", "password": "a-test-password-123"}).status_code == 200
        a = c.get("/api/accounts/tutorial").json()
        assert len(a["orders"]) == 1
        assert Decimal(a["frozen_cash"]) > 0
        assert c.get("/api/state").json()["player"]["xp"] == 20
        assert post(c, "/accounts/tutorial/orders/" + created["id"] + "/cancel").status_code == 200
        assert c.get("/api/accounts/tutorial").json()["cash"] == "100000.00"


def test_worker_claim_expired_lease_and_publication(client):
    job = post(client, "/experiments", {"short_window": 5, "long_window": 15, "allocation": 30}).json()
    factory = client.app.state.factory
    first = claim(factory)
    assert first[0] == job["id"]
    assert claim(factory) is None
    with transaction(factory) as s:
        s.get(Job, job["id"]).lease_until = now() - timedelta(seconds=1)
    assert run_once(factory)
    with factory() as s:
        result = s.get(Job, job["id"])
        assert result.status == "completed"
        assert result.attempts == 2
        assert result.result["data_version"] == job["params"]["data_version"]
    assert not run_once(factory)

