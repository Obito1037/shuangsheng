from __future__ import annotations

from fastapi.testclient import TestClient


def test_file_document_flow_upload_parse_index(client: TestClient, auth_headers: dict[str, str]) -> None:
    upload = client.post(
        "/api/files/upload",
        files={"upload": ("notes.txt", b"EchoLearn file content for document parsing.", "text/plain")},
        headers=auth_headers,
    )
    assert upload.status_code == 200
    upload_body = upload.json()
    file_id = upload_body["id"]
    assert upload_body["file"]["id"] == file_id
    assert upload_body["document"]["parse_status"] == "uploaded"

    parsed = client.post("/api/documents/parse", json={"file_id": file_id, "title": "Notes"}, headers=auth_headers)
    assert parsed.status_code == 200
    document_id = parsed.json()["id"]

    listed_documents = client.get("/api/documents", headers=auth_headers)
    assert listed_documents.status_code == 200
    assert listed_documents.json()[0]["id"] == document_id

    document_detail = client.get(f"/api/documents/{document_id}", headers=auth_headers)
    assert document_detail.status_code == 200
    assert document_detail.json()["chunks"]

    kb = client.post("/api/knowledge-bases", json={"name": "File KB"}, headers=auth_headers).json()
    indexed = client.post(
        "/api/rag/index-document",
        json={"knowledge_base_id": kb["id"], "document_id": document_id},
        headers=auth_headers,
    )
    assert indexed.status_code == 200
    assert indexed.json()["chunks"] >= 1


def test_document_parse_rejects_saved_but_unsupported_binary_type(client: TestClient, auth_headers: dict[str, str]) -> None:
    upload = client.post(
        "/api/files/upload",
        files={"upload": ("slide.pptx", b"not-a-real-pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
        headers=auth_headers,
    )
    assert upload.status_code == 200

    parsed = client.post("/api/documents/parse", json={"file_id": upload.json()["id"]}, headers=auth_headers)
    assert parsed.status_code == 400
    assert parsed.json()["code"] == "FILE_UNSUPPORTED_TYPE"
