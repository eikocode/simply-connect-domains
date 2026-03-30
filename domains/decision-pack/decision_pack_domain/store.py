from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SubmissionStore:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.submissions_dir = self.root_dir / "submissions"
        self.submissions_dir.mkdir(parents=True, exist_ok=True)
        self.latest_path = self.root_dir / "latest.json"

    def _submission_path(self, submission_id: str) -> Path:
        return self.submissions_dir / f"{submission_id}.json"

    def create_submission(self, record: dict[str, Any]) -> dict[str, Any]:
        submission_id = str(record["submission_id"])
        path = self._submission_path(submission_id)
        if path.exists():
            raise ValueError(f"Submission {submission_id} already exists.")
        self._write(path, record)
        self._write(self.latest_path, {"submission_id": submission_id})
        return record

    def read_submission(self, submission_id: str) -> dict[str, Any] | None:
        path = self._submission_path(submission_id)
        if not path.exists():
            return None
        return self._read(path)

    def read_latest_submission(self) -> dict[str, Any] | None:
        if not self.latest_path.exists():
            return None
        latest = self._read(self.latest_path)
        return self.read_submission(str(latest.get("submission_id", "")))

    def update_submission(self, submission_id: str, record: dict[str, Any]) -> dict[str, Any]:
        path = self._submission_path(submission_id)
        if not path.exists():
            raise ValueError(f"Submission {submission_id} does not exist.")
        self._write(path, record)
        self._write(self.latest_path, {"submission_id": submission_id})
        return record

    def list_submissions(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(self.submissions_dir.glob("*.json")):
            records.append(self._read(path))
        records.sort(key=lambda item: str(item.get("updated_at", item.get("created_at", ""))), reverse=True)
        return records

    def _read(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text())

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
