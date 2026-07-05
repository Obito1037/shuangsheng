from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Any

from app.core.config import VivoSettings, load_settings
from app.core.errors import ProviderError, ProviderErrorType, provider_error
from app.core.http_client import ProviderHttpClient, join_url
from app.integrations.vision.base import OcrProvider
from app.schemas.common import BoundingBox
from app.schemas.vision import OcrBlock, OcrResult


class VivoOcrProvider(OcrProvider):
    provider = "vivo"
    capability = "ocr"
    supported_extensions = {".jpg", ".jpeg", ".png", ".bmp"}

    def __init__(
        self,
        *,
        settings: VivoSettings | None = None,
        http_client: Any | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.http_client = http_client or ProviderHttpClient(
            provider=self.provider,
            app_key=self.settings.vivo_app_key,
            timeout=self.settings.http_timeout_seconds,
            max_retries=self.settings.http_max_retries,
            backoff_seconds=self.settings.http_backoff_seconds,
        )

    def recognize(self, image_path: str, *, pos: int = 2) -> OcrResult:
        request_id = str(uuid.uuid4())
        path = self._validate_image_path(image_path, request_id)
        if pos not in {0, 1, 2}:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "OCR pos must be 0, 1, or 2.",
                request_id=request_id,
            )
        self.settings.require_credentials(self.capability)
        payload = {
            "image": base64.b64encode(path.read_bytes()).decode("ascii"),
            "pos": pos,
            "businessid": f"aigc{self.settings.vivo_app_id}",
        }
        try:
            data = self.http_client.post_form(
                join_url(self.settings.vivo_base_url, "/ocr/general_recognition"),
                capability=self.capability,
                request_id=request_id,
                request_id_param="requestId",
                data=payload,
            )
            return self._parse_result(data, request_id=request_id)
        except ProviderError:
            raise
        except Exception as exc:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNKNOWN_ERROR,
                "OCR provider call failed.",
                request_id=request_id,
                raw_error=str(exc),
            ) from exc

    def _validate_image_path(self, image_path: str, request_id: str) -> Path:
        path = Path(image_path)
        if not path.exists():
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "OCR image file does not exist.",
                request_id=request_id,
                raw_error=image_path,
            )
        if path.suffix.lower() not in self.supported_extensions:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNSUPPORTED_FORMAT,
                "OCR only supports jpg, png, and bmp images.",
                request_id=request_id,
                raw_error=path.suffix,
            )
        return path

    def _parse_result(self, data: Any, *, request_id: str) -> OcrResult:
        error_code = data.get("error_code")
        if error_code not in (0, "0", None):
            error_type = ProviderErrorType.UNSUPPORTED_FORMAT if error_code == 2 else ProviderErrorType.UNKNOWN_ERROR
            raise provider_error(
                self.provider,
                self.capability,
                error_type,
                "OCR provider failed to recognize the image.",
                request_id=request_id,
                raw_error=data,
            )
        result = data.get("result")
        if not isinstance(result, dict):
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "OCR provider response shape is invalid.",
                request_id=request_id,
                raw_error=data,
            )
        angle = result.get("angle")
        blocks = self._parse_ocr_blocks(result)
        full_text = "\n".join(block.text for block in blocks if block.text)
        return OcrResult(full_text=full_text, blocks=blocks, angle=angle, provider=self.provider)

    def _parse_ocr_blocks(self, result: dict[str, Any]) -> list[OcrBlock]:
        ocr_items = result.get("OCR")
        if isinstance(ocr_items, list) and ocr_items:
            return [
                OcrBlock(
                    text=str(item.get("words", "")),
                    confidence=self._to_float(item.get("confidence")),
                    bounding_box=self._location_to_box(item.get("location")),
                )
                for item in ocr_items
            ]
        word_items = result.get("words")
        if isinstance(word_items, list):
            return [
                OcrBlock(
                    text=str(item.get("words", "")),
                    confidence=self._to_float(item.get("confidence")),
                    bounding_box=None,
                )
                for item in word_items
            ]
        return []

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _location_to_box(location: Any) -> BoundingBox | None:
        if not isinstance(location, dict):
            return None
        points = {
            key: {"x": float(value["x"]), "y": float(value["y"])}
            for key, value in location.items()
            if isinstance(value, dict) and "x" in value and "y" in value
        }
        if not points:
            return None
        xs = [point["x"] for point in points.values()]
        ys = [point["y"] for point in points.values()]
        return BoundingBox(
            x_min=min(xs),
            y_min=min(ys),
            x_max=max(xs),
            y_max=max(ys),
            points=points,
        )
