from pathlib import Path
import base64
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature


class Wallet:
    def __init__(self, private_key=None):
        if private_key:
            self.private_key = serialization.load_pem_private_key(
                private_key.encode(), password=None
            )
        else:
            self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()

    def sign(self, message: str) -> str:
        return self.private_key.sign(
            message.encode(), ec.ECDSA(hashes.SHA256())
        ).hex()

    def verify(self, message: str, signature: str) -> bool:
        try:
            self.public_key.verify(
                bytes.fromhex(signature),
                message.encode(),
                ec.ECDSA(hashes.SHA256()),
            )
            return True
        except (InvalidSignature, ValueError):
            return False

    def private_key_pem(self) -> str:
        return self.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

    def public_key_pem(self) -> str:
        return self.public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()


def load_or_create_participant(participant_id: str, role: str, path="data/participants.json"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    records = {}
    if p.exists():
        try:
            records = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            records = {}

    if participant_id in records:
        return records[participant_id], Wallet(records[participant_id]["private_key_pem"])

    wallet = Wallet()
    record = {
        "participant_id": participant_id,
        "role": role,
        "private_key_pem": wallet.private_key_pem(),
        "public_key_pem": wallet.public_key_pem(),
    }
    records[participant_id] = record
    p.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return record, wallet
