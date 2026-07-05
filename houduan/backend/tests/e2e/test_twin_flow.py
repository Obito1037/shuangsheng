from __future__ import annotations

from fastapi.testclient import TestClient


def test_learning_twin_flow_create_sync_simulate_outputs(client: TestClient, auth_headers: dict[str, str]) -> None:
    listed = client.get("/api/twins", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json() == []

    created = client.post(
        "/api/twins",
        headers=auth_headers,
        json={"name": "数据库考试分身", "subject": "数据库", "goal": "补齐 SQL 聚合函数"},
    )
    assert created.status_code == 200
    twin_id = created.json()["id"]
    assert "current_work" in created.json()

    updated = client.patch(f"/api/twins/{twin_id}", headers=auth_headers, json={"stage": "期末冲刺"})
    assert updated.status_code == 200
    assert updated.json()["stage"] == "期末冲刺"

    synced = client.post(f"/api/twins/{twin_id}/sync", headers=auth_headers)
    assert synced.status_code == 200
    assert "learned_assets" in synced.json()

    simulation = client.post(f"/api/twins/{twin_id}/simulate", headers=auth_headers)
    assert simulation.status_code == 200
    body = simulation.json()
    assert body["recommended_route"]["score"] >= 80
    assert len(body["routes"]) == 3
    assert len(body["optimal_path"]) == 4
    assert body["outputs"]

    outputs = client.get(f"/api/twins/{twin_id}/outputs", headers=auth_headers)
    assert outputs.status_code == 200
    output_types = {item["type"] for item in outputs.json()}
    assert {"路径", "黑板", "视频", "PDF", "Word"} <= output_types

    weak_points = client.get(f"/api/twins/{twin_id}/weak-points", headers=auth_headers)
    assert weak_points.status_code == 200
    assert weak_points.json()[0]["next_action"]

    blackboard = client.post(f"/api/twins/{twin_id}/blackboard", headers=auth_headers, json={"topic": "HAVING"})
    assert blackboard.status_code == 200
    assert blackboard.json()["topic"] == "HAVING"
    assert len(blackboard.json()["steps"]) >= 3

    deleted = client.delete(f"/api/twins/{twin_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True
