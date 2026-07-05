from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import has_real_vivo_credentials, load_settings  # noqa: E402
from app.integrations.capabilities import build_capability_registry  # noqa: E402


def main() -> int:
    settings = load_settings()
    capabilities = build_capability_registry(settings)
    payload = {
        "env_example_path": str(BACKEND_ROOT / ".env.example"),
        "has_real_vivo_credentials": has_real_vivo_credentials(settings),
        "models": {
            "text": settings.vivo_llm_text_model,
            "stream": settings.vivo_llm_stream_model,
            "image_understanding": settings.vivo_image_understanding_model,
            "reasoning": settings.vivo_reasoning_model,
            "embedding": settings.vivo_embedding_model,
            "rerank": settings.vivo_rerank_model,
        },
        "http": {
            "timeout_seconds": settings.http_timeout_seconds,
            "max_retries": settings.http_max_retries,
            "backoff_seconds": settings.http_backoff_seconds,
        },
        "capabilities": {name: metadata.to_dict() for name, metadata in capabilities.items()},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

