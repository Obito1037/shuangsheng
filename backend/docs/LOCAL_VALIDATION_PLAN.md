# Local Validation Plan

Commands:

```powershell
cd backend
python -m pytest -s
python -m pytest tests/unit -s
python -m pytest tests/contract -s
python -m pytest tests/e2e -s
python -m pytest tests/live -s
python -m ruff check .
python -m mypy app tests scripts
python -m pytest --cov=app --cov-report=term-missing -s
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Manual checks:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/docs`
- Register, login, create conversation, chat, upload text, create knowledge base, ask RAG, inspect usage.

