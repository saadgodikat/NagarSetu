import io
import logging
from pathlib import Path
from typing import Any

from PIL import Image
import torch
import torch.nn.functional as F
from torchvision import models, transforms

from app.ai.interfaces import ClassificationResult, ComplaintClassifier
from app.config import settings
from app.models.enums import ComplaintCategory

logger = logging.getLogger(__name__)

# Map string class names to ComplaintCategory enum
_CATEGORY_MAP: dict[str, ComplaintCategory] = {
    "garbage": ComplaintCategory.garbage,
    "pothole": ComplaintCategory.pothole,
    "drainage": ComplaintCategory.drainage,
    "streetlight": ComplaintCategory.streetlight,
    "water_leakage": ComplaintCategory.water_leakage,
    "other": ComplaintCategory.other,
}


class TorchVisionComplaintClassifier(ComplaintClassifier):
    """Deep Computer Vision Complaint Classifier using fine-tuned MobileNetV3-Small."""

    _model: Any = None
    _classes: list[str] = []

    def __init__(
        self,
        model_path: str | None = None,
        confidence_threshold: float | None = None,
        fallback_classifier: ComplaintClassifier | None = None,
    ):
        self.model_path = model_path or settings.vision_model_path
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.vision_confidence_threshold
        )
        self.fallback = fallback_classifier

        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self._load_model()

    def _load_model(self) -> None:
        if TorchVisionComplaintClassifier._model is not None:
            return

        resolved_path = Path(self.model_path)
        if not resolved_path.exists():
            # Check relative to backend/
            alt_backend = Path(__file__).resolve().parent.parent.parent / "models" / resolved_path.name
            if alt_backend.exists():
                resolved_path = alt_backend
            else:
                # Check relative to workspace root
                alt_root = Path(__file__).resolve().parents[2] / resolved_path
                if alt_root.exists():
                    resolved_path = alt_root

        try:
            logger.info("Loading PyTorch vision model from: %s", resolved_path)
            checkpoint = torch.load(resolved_path, map_location="cpu", weights_only=False)

            classes = checkpoint.get("classes", list(_CATEGORY_MAP.keys()))
            num_classes = len(classes)

            # Build MobileNetV3-Small architecture and load state dict
            model = models.mobilenet_v3_small(weights=None)
            in_features = model.classifier[3].in_features
            model.classifier[3] = torch.nn.Linear(in_features, num_classes)
            model.load_state_dict(checkpoint["state_dict"])
            model.eval()

            TorchVisionComplaintClassifier._model = model
            TorchVisionComplaintClassifier._classes = classes
            logger.info("Successfully loaded vision model with classes: %s", classes)
        except Exception as exc:
            logger.warning("Failed to load vision model from %s: %s. Using fallback.", self.model_path, exc)
            TorchVisionComplaintClassifier._model = None

    def classify(self, image: bytes | None, text: str) -> ClassificationResult:
        # Fallback if no image bytes provided
        if not image:
            if self.fallback:
                return self.fallback.classify(None, text)
            return ClassificationResult(
                category=ComplaintCategory.other,
                confidence=0.50,
                source="vision_no_image_fallback",
            )

        model = TorchVisionComplaintClassifier._model
        if model is None:
            if self.fallback:
                return self.fallback.classify(image, text)
            return ClassificationResult(
                category=ComplaintCategory.other,
                confidence=0.50,
                source="vision_model_missing_fallback",
            )

        try:
            # Decode image from bytes
            pil_img = Image.open(io.BytesIO(image)).convert("RGB")
            tensor_img = self.transform(pil_img).unsqueeze(0)  # (1, 3, 224, 224)

            with torch.no_grad():
                logits = model(tensor_img)
                probs = F.softmax(logits, dim=1).squeeze(0)

            top_idx = int(torch.argmax(probs).item())
            top_prob = float(probs[top_idx].item())
            class_name = TorchVisionComplaintClassifier._classes[top_idx]
            category = _CATEGORY_MAP.get(class_name, ComplaintCategory.other)

            # Check confidence threshold gate
            if top_prob < self.confidence_threshold:
                logger.info(
                    "Vision confidence (%.2f) below threshold (%.2f) for '%s'. Delegating to text fallback.",
                    top_prob,
                    self.confidence_threshold,
                    class_name,
                )
                if self.fallback:
                    return self.fallback.classify(image, text)

            return ClassificationResult(
                category=category,
                confidence=round(top_prob, 4),
                source="vision_mobilenet_v3",
            )

        except Exception as exc:
            logger.warning("Vision classification error: %s. Delegating to fallback.", exc)
            if self.fallback:
                return self.fallback.classify(image, text)
            return ClassificationResult(
                category=ComplaintCategory.other,
                confidence=0.50,
                source="vision_error_fallback",
            )
