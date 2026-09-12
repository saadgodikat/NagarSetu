from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
import uuid

import pytest

from app.ai.duplicates import (
    JaccardDuplicateDetector,
    SemanticDuplicateDetector,
    TfidfDuplicateDetector,
    compute_spatiotemporal_duplicate_score,
    find_possible_duplicates,
    get_duplicate_detector,
    haversine_m,
    record_possible_duplicates,
    token_overlap,
)
from app.config import settings
from app.models.complaint import Complaint
from app.models.enums import ComplaintCategory, RelationType
from app.models.ops import ComplaintRelation


def test_token_overlap_and_jaccard_detector():
    det = JaccardDuplicateDetector()
    assert det.compute_similarity("pothole on road", "pothole on road") == 1.0
    assert det.compute_similarity("pothole on road", "garbage dump near corner") == 0.0
    assert det.compute_similarity("", "") == 0.0
    sim = det.compute_similarity("huge pothole near station", "small pothole near station")
    assert 0.4 <= sim <= 0.8


def test_tfidf_char_ngram_detector():
    det = TfidfDuplicateDetector()
    # Identical
    assert pytest.approx(det.compute_similarity("burst water pipe", "burst water pipe"), 0.01) == 1.0
    # Empty
    assert det.compute_similarity("", "something") == 0.0
    # Subword/spelling variations
    sim = det.compute_similarity("potholes on main road", "pothole on main road")
    assert sim >= 0.70


def test_semantic_duplicate_detector_embeddings():
    det = SemanticDuplicateDetector()
    
    # Paraphrased complaint pair with 0% lexical overlap
    text_a = "Huge pothole on asphalt road creating severe hazard"
    text_b = "Deep crater in street surface causing dangerous driving"
    
    sim = det.compute_similarity(text_a, text_b)
    # Dense semantic model should recognize high similarity despite low exact word overlap
    assert sim >= 0.50
    
    # Dissimilar complaints
    unrelated = "Municipal streetlight pole bulb extinguished and dark"
    unrelated_sim = det.compute_similarity(text_a, unrelated)
    assert unrelated_sim < sim
    
    # Cache verification
    assert text_a in det._cache
    cached_sim = det.compute_similarity(text_a, text_b)
    assert cached_sim == sim


def test_spatiotemporal_scoring_fusion():
    # 0 distance, 0 age -> maximum score
    score_max = compute_spatiotemporal_duplicate_score(
        text_similarity=1.0,
        distance_meters=0.0,
        max_distance=300.0,
        age_seconds=0.0,
        window_days=7,
    )
    assert pytest.approx(score_max, 0.01) == 1.0

    # Large distance (300m) and max age (7 days)
    score_min = compute_spatiotemporal_duplicate_score(
        text_similarity=0.0,
        distance_meters=300.0,
        max_distance=300.0,
        age_seconds=7 * 86400.0,
        window_days=7,
    )
    assert pytest.approx(score_min, 0.01) == 0.0

    # Moderate values
    score_mid = compute_spatiotemporal_duplicate_score(
        text_similarity=0.80,
        distance_meters=50.0,
        max_distance=300.0,
        age_seconds=3600.0,
        window_days=7,
    )
    assert 0.70 <= score_mid <= 0.99


def test_find_possible_duplicates_spatial_and_semantic_gating():
    db = MagicMock()
    now = datetime.now(UTC)

    c1 = MagicMock(spec=Complaint)
    c1.id = uuid.uuid4()
    c1.title = "Deep pothole"
    c1.description = "Dangerous road crater near station"
    c1.location_lat = 17.6599
    c1.location_lng = 75.9064
    c1.created_at = now - timedelta(hours=2)

    # c2 is far away (>1 km)
    c2 = MagicMock(spec=Complaint)
    c2.id = uuid.uuid4()
    c2.title = "Deep pothole"
    c2.description = "Dangerous road crater near distant market"
    c2.location_lat = 17.6800  # ~2.2 km away
    c2.location_lng = 75.9064
    c2.created_at = now - timedelta(hours=3)

    db.scalars.return_value.all.return_value = [c1, c2]

    # Query location very close to c1 (10 meters away)
    matches = find_possible_duplicates(
        db,
        category=ComplaintCategory.pothole,
        lat=17.6600,
        lng=75.9064,
        text="Deep crater on road near station",
        exclude_id=None,
    )

    # c1 should be matched, c2 should be excluded due to distance > 300m
    matched_ids = [m[0].id for m in matches]
    assert c1.id in matched_ids
    assert c2.id not in matched_ids


def test_record_possible_duplicates():
    db = MagicMock()
    primary = MagicMock(spec=Complaint)
    primary.id = uuid.uuid4()

    other = MagicMock(spec=Complaint)
    other.id = uuid.uuid4()

    matches = [(other, 0.85, 25.0)]
    record_possible_duplicates(db, primary, matches)

    assert db.add.called
    added = db.add.call_args[0][0]
    assert isinstance(added, ComplaintRelation)
    assert added.complaint_id == primary.id
    assert added.related_complaint_id == other.id
    assert added.relation_type == RelationType.possible_duplicate
    assert added.similarity_score == 0.85
    assert added.distance_meters == 25.0
