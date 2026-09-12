import logging
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.interfaces import DuplicateDetector
from app.config import settings
from app.models.complaint import Complaint
from app.models.enums import ComplaintCategory, RelationType
from app.models.ops import ComplaintRelation

logger = logging.getLogger(__name__)


def duration_days_from_text(text: str) -> int:
    match = re.search(r"(\d+)\s*days?", (text or "").lower())
    return int(match.group(1)) if match else 0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def token_overlap(a: str, b: str) -> float:
    sa, sb = set(re.findall(r"[a-z0-9]+", (a or "").lower())), set(
        re.findall(r"[a-z0-9]+", (b or "").lower())
    )
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class JaccardDuplicateDetector(DuplicateDetector):
    """Zero-dependency baseline token overlap duplicate detector."""

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        return float(token_overlap(text_a, text_b))


class TfidfDuplicateDetector(DuplicateDetector):
    """Subword char-ngram + unigram TF-IDF cosine similarity duplicate detector."""

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            lowercase=True,
            min_df=1,
        )

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b or not text_a.strip() or not text_b.strip():
            return 0.0
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            mat = self.vectorizer.fit_transform([text_a, text_b])
            sim = cosine_similarity(mat[0:1], mat[1:2])[0][0]
            return float(np.clip(sim, 0.0, 1.0))
        except Exception as exc:
            logger.warning("TF-IDF similarity calculation failed: %s. Falling back to Jaccard.", exc)
            return float(token_overlap(text_a, text_b))


class SemanticDuplicateDetector(DuplicateDetector):
    """Deep semantic sentence embedding duplicate detector using SentenceTransformers."""

    _instance = None
    _model = None

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.duplicate_embedding_model
        self._cache: dict[str, np.ndarray] = {}
        self._fallback_detector = TfidfDuplicateDetector()

    def _get_model(self) -> Any:
        if SemanticDuplicateDetector._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading sentence-transformer model: %s", self.model_name)
                SemanticDuplicateDetector._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                logger.error("Failed to load sentence-transformer model '%s': %s", self.model_name, exc)
                return None
        return SemanticDuplicateDetector._model

    def _encode(self, text: str) -> np.ndarray | None:
        clean = (text or "").strip()
        if not clean:
            return None
        if clean in self._cache:
            return self._cache[clean]

        model = self._get_model()
        if model is None:
            return None

        try:
            emb = model.encode(clean, convert_to_numpy=True, normalize_embeddings=True)
            if len(self._cache) > 2000:
                self._cache.clear()
            self._cache[clean] = emb
            return emb
        except Exception as exc:
            logger.warning("Encoding text failed: %s", exc)
            return None

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        clean_a, clean_b = (text_a or "").strip(), (text_b or "").strip()
        if not clean_a or not clean_b:
            return 0.0

        emb_a = self._encode(clean_a)
        emb_b = self._encode(clean_b)

        if emb_a is None or emb_b is None:
            return self._fallback_detector.compute_similarity(clean_a, clean_b)

        sim = float(np.dot(emb_a, emb_b))
        return float(np.clip(sim, 0.0, 1.0))


_global_detector: DuplicateDetector | None = None


def get_duplicate_detector() -> DuplicateDetector:
    global _global_detector
    if _global_detector is not None:
        return _global_detector

    if getattr(settings, "semantic_duplicates_enabled", False):
        try:
            _global_detector = SemanticDuplicateDetector(
                model_name=getattr(settings, "duplicate_embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
            )
            return _global_detector
        except Exception as exc:
            logger.warning("Failed to initialize SemanticDuplicateDetector (%s), falling back to Jaccard.", exc)

    _global_detector = JaccardDuplicateDetector()
    return _global_detector


def compute_spatiotemporal_duplicate_score(
    text_similarity: float,
    distance_meters: float,
    max_distance: float = 300.0,
    age_seconds: float = 0.0,
    window_days: int = 7,
) -> float:
    """Computes a multi-signal combined duplicate likelihood score between 0.0 and 1.0."""
    geo_score = max(0.0, 1.0 - (distance_meters / max(1.0, max_distance)))
    total_window_sec = max(1.0, float(window_days * 86400))
    time_score = max(0.0, 1.0 - (age_seconds / total_window_sec))

    combined = (0.60 * text_similarity) + (0.25 * geo_score) + (0.15 * time_score)
    return float(np.clip(combined, 0.0, 1.0))


def find_possible_duplicates(
    db: Session,
    *,
    category: ComplaintCategory,
    lat: float,
    lng: float,
    text: str,
    exclude_id=None,
) -> list[tuple[Complaint, float, float]]:
    window_days = getattr(settings, "duplicate_window_days", 7)
    max_distance = getattr(settings, "duplicate_max_distance_meters", 300.0)
    sim_threshold = getattr(settings, "duplicate_similarity_threshold", 0.60)
    semantic_enabled = getattr(settings, "semantic_duplicates_enabled", False)

    detector = get_duplicate_detector()
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=window_days)

    rows = db.scalars(
        select(Complaint).where(
            Complaint.category == category,
            Complaint.created_at >= cutoff,
        )
    ).all()

    found: list[tuple[Complaint, float, float]] = []
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue

        metres = haversine_m(lat, lng, row.location_lat, row.location_lng)
        if metres > max_distance:
            continue

        other_text = f"{row.title} {row.description}"
        sim = detector.compute_similarity(text, other_text)

        if semantic_enabled:
            age_sec = max(0.0, (now - row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else (now - row.created_at)).total_seconds())
            combined = compute_spatiotemporal_duplicate_score(
                text_similarity=sim,
                distance_meters=metres,
                max_distance=max_distance,
                age_seconds=age_sec,
                window_days=window_days,
            )
            if sim >= sim_threshold or combined >= 0.65:
                found.append((row, sim, metres))
        else:
            # Baseline Jaccard threshold
            if sim >= 0.20:
                found.append((row, sim, metres))

    return found


def record_possible_duplicates(
    db: Session, complaint: Complaint, matches: list[tuple[Complaint, float, float]]
) -> None:
    for other, sim, metres in matches:
        db.add(
            ComplaintRelation(
                complaint_id=complaint.id,
                related_complaint_id=other.id,
                relation_type=RelationType.possible_duplicate,
                similarity_score=sim,
                distance_meters=metres,
            )
        )

