from __future__ import annotations

from fastapi.testclient import TestClient


def test_m1_profile_attempt_and_mistake_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    twin = client.post(
        "/api/twins",
        json={"name": "数学分身", "subject": "数学", "goal": "掌握函数与导数"},
        headers=auth_headers,
    )
    assert twin.status_code == 200
    twin_id = twin.json()["id"]

    avatar_update = client.patch(
        f"/api/twins/{twin_id}",
        json={"avatar_data_url": "data:image/jpeg;base64,QUFB"},
        headers=auth_headers,
    )
    assert avatar_update.status_code == 200
    assert avatar_update.json()["avatar_data_url"] == "data:image/jpeg;base64,QUFB"

    parsed = client.post(
        "/api/documents/parse",
        json={
            "twin_id": twin_id,
            "title": "函数与导数笔记",
            "text": "# 导数定义\n导数定义用于描述函数变化率。\n\n## 链式法则\n链式法则用于复合函数求导。",
        },
        headers=auth_headers,
    )
    assert parsed.status_code == 200

    profile = client.get(f"/api/twins/{twin_id}/profile", headers=auth_headers)
    assert profile.status_code == 200
    profile_body = profile.json()
    assert profile_body["evidence_mode"] == "启动方案"
    assert profile_body["mastery"]

    questions = client.get(f"/api/twins/{twin_id}/questions", headers=auth_headers)
    assert questions.status_code == 200
    question = questions.json()[0]

    correct = client.post(
        "/api/attempts",
        json={
            "twin_id": twin_id,
            "question_id": question["id"],
            "is_correct": True,
            "self_rating": "good",
            "answer_text": "导数描述函数变化率。",
        },
        headers=auth_headers,
    )
    assert correct.status_code == 200
    update = correct.json()["mastery_updates"][0]
    assert update["after_p_mastery"] > update["before_p_mastery"]
    assert update["after_ability_elo"] > update["before_ability_elo"]

    wrong = client.post(
        "/api/attempts",
        json={
            "twin_id": twin_id,
            "question_id": question["id"],
            "is_correct": False,
            "self_rating": "hard",
            "answer_text": "我把复合函数拆错了。",
            "error_type": "方法选择错误",
        },
        headers=auth_headers,
    )
    assert wrong.status_code == 200
    assert wrong.json()["mistake"]["error_type"] == "方法选择错误"

    mistakes = client.get(f"/api/mistakes?twin_id={twin_id}", headers=auth_headers)
    assert mistakes.status_code == 200
    assert len(mistakes.json()) == 1

    profile_after = client.get(f"/api/twins/{twin_id}/profile", headers=auth_headers).json()
    assert profile_after["attempts_used"] == 2
    assert profile_after["error_distribution"][0]["error_type"] == "方法选择错误"

    other = client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "StrongPass123", "display_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['tokens']['access_token']}"}
    assert client.patch(f"/api/twins/{twin_id}", json={"avatar_data_url": ""}, headers=other_headers).status_code == 404
    assert client.get(f"/api/twins/{twin_id}/profile", headers=other_headers).status_code == 404
    assert client.get(f"/api/mistakes?twin_id={twin_id}", headers=other_headers).status_code == 404


def test_m2_diagnose_review_queue_and_variants(client: TestClient, auth_headers: dict[str, str]) -> None:
    twin = client.post(
        "/api/twins",
        json={"name": "数据库分身", "subject": "数据库", "goal": "补齐 GROUP BY"},
        headers=auth_headers,
    )
    twin_id = twin.json()["id"]

    diagnose = client.post(f"/api/twins/{twin_id}/diagnose", headers=auth_headers)
    assert diagnose.status_code == 200
    diagnose_body = diagnose.json()
    assert diagnose_body["evidence_mode"] == "启动方案"
    assert len(diagnose_body["questions"]) >= 4
    first_question = diagnose_body["questions"][0]
    assert first_question["selection_score"] is not None

    wrong = client.post(
        "/api/attempts",
        json={
            "twin_id": twin_id,
            "question_id": first_question["id"],
            "is_correct": False,
            "self_rating": "again",
            "answer_text": "没有分清聚合前后的字段。",
            "error_type": "概念不清",
        },
        headers=auth_headers,
    )
    assert wrong.status_code == 200
    mistake_id = wrong.json()["mistake"]["id"]

    queue = client.get(f"/api/twins/{twin_id}/review-queue", headers=auth_headers)
    assert queue.status_code == 200
    queue_body = queue.json()
    assert queue_body
    assert any(item["type"] == "mistake" and item["mistake_id"] == mistake_id for item in queue_body)

    variants = client.post(f"/api/mistakes/{mistake_id}/variants", headers=auth_headers)
    assert variants.status_code == 200
    variant_questions = variants.json()["questions"]
    assert len(variant_questions) == 2
    assert variant_questions[0]["source"] == "variant"

    practice = client.get(f"/api/twins/{twin_id}/questions?mode=practice", headers=auth_headers)
    assert practice.status_code == 200
    assert any(question["id"] == variant_questions[0]["id"] for question in practice.json())


def test_m3_plan_tasks_and_blackboard_cache_are_twin_isolated(client: TestClient, auth_headers: dict[str, str]) -> None:
    twin = client.post(
        "/api/twins",
        json={"name": "Algebra Twin", "subject": "Algebra", "goal": "master quadratic functions"},
        headers=auth_headers,
    )
    assert twin.status_code == 200
    twin_id = twin.json()["id"]

    plan = client.post(f"/api/twins/{twin_id}/plans", headers=auth_headers)
    assert plan.status_code == 200
    plan_body = plan.json()
    assert plan_body["status"] == "ready"
    assert plan_body["candidates"]
    assert plan_body["tasks"]
    assert plan_body["profile_summary"]["mode"]
    plan_id = plan_body["plan_id"]
    task_id = plan_body["tasks"][0]["id"]

    updated = client.patch(
        f"/api/plans/{plan_id}/tasks/{task_id}",
        json={"status": "done", "outcome": {"note": "completed in test"}},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["tasks"][0]["status"] == "done"
    assert updated.json()["tasks"][0]["outcome"]["note"] == "completed in test"

    first_lesson = client.post(f"/api/twins/{twin_id}/blackboard", json={"topic": "quadratic vertex"}, headers=auth_headers)
    assert first_lesson.status_code == 200
    first_body = first_lesson.json()
    assert first_body["source"] == "template-fallback"
    assert first_body["cached"] is False
    assert first_body["lesson_id"]
    assert len(first_body["steps"]) >= 3

    cached_lesson = client.post(f"/api/twins/{twin_id}/blackboard", json={"topic": "quadratic vertex"}, headers=auth_headers)
    assert cached_lesson.status_code == 200
    cached_body = cached_lesson.json()
    assert cached_body["cached"] is True
    assert cached_body["lesson_id"] == first_body["lesson_id"]

    other = client.post(
        "/api/auth/register",
        json={"email": "m3-other@example.com", "password": "StrongPass123", "display_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['tokens']['access_token']}"}
    assert client.get(f"/api/plans/{plan_id}", headers=other_headers).status_code == 404
    assert client.post(f"/api/twins/{twin_id}/blackboard", json={"topic": "quadratic vertex"}, headers=other_headers).status_code == 404


def test_m4_spoken_english_pending_and_transcript_scoring(client: TestClient, auth_headers: dict[str, str]) -> None:
    twin = client.post(
        "/api/twins",
        json={"name": "English Twin", "subject": "English", "goal": "improve spoken summaries"},
        headers=auth_headers,
    )
    twin_id = twin.json()["id"]

    uploaded = client.post(
        "/api/files/upload",
        files={"upload": ("speech.m4a", b"fake audio bytes", "audio/mp4")},
        headers=auth_headers,
    )
    assert uploaded.status_code == 200
    file_id = uploaded.json()["id"]

    pending = client.post(f"/api/speech/english/{file_id}", headers=auth_headers)
    assert pending.status_code == 200
    pending_body = pending.json()
    assert pending_body["status"] == "pending"
    assert pending_body["pronunciation"] is None

    scored = client.post(
        f"/api/speech/english/{file_id}",
        json={
            "twin_id": twin_id,
            "transcript": "I want to explain quadratic functions. The vertex shows the turning point, so I can compare values around it.",
            "prompt": "summarize a math idea",
        },
        headers=auth_headers,
    )
    assert scored.status_code == 200
    scored_body = scored.json()
    assert scored_body["status"] == "scored"
    assert scored_body["pronunciation"] is None
    assert scored_body["fluency"] is not None
    assert scored_body["attempt_id"]
    assert scored_body["mastery_updates"]

    profile = client.get(f"/api/twins/{twin_id}/profile", headers=auth_headers)
    assert profile.status_code == 200
    assert profile.json()["attempts_used"] == 1

    tts = client.post("/api/speech/tts", json={"text": "Read the current blackboard step."}, headers=auth_headers)
    assert tts.status_code == 200
    assert tts.json()["status"] == "pending"
    assert tts.json()["audio_file_id"] is None
