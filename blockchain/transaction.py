from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import uuid


@dataclass
class Transaction:
    transaction_id: str
    transaction_type: str
    actor_id: str
    data: dict
    timestamp: str
    actor_signature: str = ""
    transaction_hash: str = ""

    @classmethod
    def create(cls, transaction_type, actor_id, data, signature=""):
        tx = cls(
            transaction_id=str(uuid.uuid4()),
            transaction_type=transaction_type,
            actor_id=actor_id,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor_signature=signature,
        )
        tx.transaction_hash = tx.calculate_hash()
        return tx

    def calculate_hash(self) -> str:
        payload = {
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type,
            "actor_id": self.actor_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self):
        return asdict(self)
