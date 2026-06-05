from datetime import datetime, timezone


class ResponseSchema:
    def __init__(self, status: int, message: str, path: str, data: dict | None = None):
        self.status = status
        self.message = message
        self.data = data or {}
        self.timestamp = (datetime.now(timezone.utc),)
        self.path = path

    def to_dict(self):
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
            "path": self.path,
        }
