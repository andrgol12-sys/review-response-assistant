import json
from pathlib import Path

from config import get_settings


settings = get_settings()


class WorkerState:
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"notified_review_ids": [], "processed_review_ids": []})

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def is_notified(self, review_id: int) -> bool:
        return review_id in self._read()["notified_review_ids"]

    def is_processed(self, review_id: int) -> bool:
        return review_id in self._read()["processed_review_ids"]

    def mark_notified(self, review_id: int) -> None:
        payload = self._read()
        if review_id not in payload["notified_review_ids"]:
            payload["notified_review_ids"].append(review_id)
            self._write(payload)

    def mark_processed(self, review_id: int) -> None:
        payload = self._read()
        if review_id not in payload["processed_review_ids"]:
            payload["processed_review_ids"].append(review_id)
        if review_id not in payload["notified_review_ids"]:
            payload["notified_review_ids"].append(review_id)
        self._write(payload)


def get_worker_state() -> WorkerState:
    return WorkerState(settings.state_file_path)
