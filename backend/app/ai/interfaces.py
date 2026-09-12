from dataclasses import dataclass

from app.models.enums import ComplaintCategory


@dataclass(frozen=True)
class ClassificationResult:
    category: ComplaintCategory
    confidence: float
    source: str


class ComplaintClassifier:
    def classify(self, image: bytes | None, text: str) -> ClassificationResult:
        raise NotImplementedError


@dataclass(frozen=True)
class DuplicateMatch:
    similarity_score: float
    distance_meters: float
    is_duplicate: bool
    source: str
    combined_score: float = 0.0


class DuplicateDetector:
    def compute_similarity(self, text_a: str, text_b: str) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class SignalResult:
    name: str
    passed: bool
    score: float
    weight: float
    status: str
    details: str
    metrics: dict


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    status: str
    composite_score: float
    signals: dict
    recommendation: str
    flags: list[str]
    evaluated_at: str
    source: str


class ResolutionVerifier:
    def verify(
        self,
        before_image: bytes | None,
        after_image: bytes | None,
        metadata: dict,
    ) -> VerificationResult:
        raise NotImplementedError

