from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json


@dataclass
class Block:
    index: int
    timestamp: str
    transactions: list
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def calculate_hash(self) -> str:
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def finalize(self) -> str:
        self.hash = self.calculate_hash()
        return self.hash

    @classmethod
    def genesis(cls):
        block = cls(
            index=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            transactions=[],
            previous_hash="0",
        )
        block.finalize()
        return block

    def to_dict(self):
        return asdict(self)
