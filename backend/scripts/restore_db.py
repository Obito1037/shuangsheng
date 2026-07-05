from __future__ import annotations

import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import load_settings  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/restore_db.py <backup_file>")
        return 1
    settings = load_settings()
    if not settings.database_url.startswith("sqlite:///"):
        print("restore_db currently supports local sqlite files only")
        return 1
    target = Path(settings.database_url.replace("sqlite:///", "", 1))
    if not target.is_absolute():
        target = BACKEND_ROOT / target
    shutil.copy2(Path(sys.argv[1]), target)
    print("database restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

