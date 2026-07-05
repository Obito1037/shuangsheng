from __future__ import annotations

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import load_settings  # noqa: E402


def main() -> int:
    settings = load_settings()
    if not settings.database_url.startswith("sqlite:///"):
        print("backup_db currently supports local sqlite files only")
        return 1
    source = Path(settings.database_url.replace("sqlite:///", "", 1))
    if not source.is_absolute():
        source = BACKEND_ROOT / source
    backup_dir = BACKEND_ROOT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"echolearn_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(source, target)
    print(str(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

