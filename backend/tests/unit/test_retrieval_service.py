from app.services.retrieval_service import cosine_similarity, keyword_score


def test_cosine_similarity_basic():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_handles_invalid_vectors():
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_keyword_score_counts_query_hits():
    assert keyword_score("Laplace transform", "Laplace transform table") > 0
    assert keyword_score("Laplace transform", "probability distribution") == 0
