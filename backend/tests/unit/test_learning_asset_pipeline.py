from app.services.learning_asset_pipeline import LearningAssetPipeline


def test_document_plan_for_pdf():
    plan = LearningAssetPipeline().plan_for("linear_algebra.pdf", "application/pdf")
    assert plan.kind == "document"
    assert plan.rag_ready is True


def test_image_plan_requires_vision_extraction():
    plan = LearningAssetPipeline().plan_for("blackboard.png", "image/png")
    assert plan.kind == "image"
    assert "OCR" in plan.user_visible_status


def test_voice_plan_stays_pending_until_speech_provider_exists():
    plan = LearningAssetPipeline().plan_for("spoken_english.m4a", "audio/mp4")
    assert plan.kind == "voice"
    assert plan.rag_ready is False
