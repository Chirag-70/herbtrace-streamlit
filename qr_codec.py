import base64
import gzip
import hashlib
import json
from pathlib import Path
import qrcode

QR_PREFIX = "HERBTRACE1:"
MAX_QR_PAYLOAD_BYTES = 2900


def canonical_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_payload(snapshot):
    raw = canonical_json(snapshot).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    payload = QR_PREFIX + encoded
    if len(payload.encode("utf-8")) > MAX_QR_PAYLOAD_BYTES:
        raise ValueError(
            "Cumulative batch data is too large for a single standard QR payload. "
            "Reduce verbose free-text fields or use a reference-based QR design."
        )
    return payload


def payload_hash(payload):
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def save_qr(snapshot, batch_id, stage, directory="data/qr_codes"):
    payload = make_payload(snapshot)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{batch_id}_{stage}.png"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    qr.make_image().save(path)
    return str(path), payload, payload_hash(payload)


def decode_payload(payload):
    if not payload.startswith(QR_PREFIX):
        raise ValueError("Not a HerbTrace QR.")
    body = payload[len(QR_PREFIX):]
    body += "=" * (-len(body) % 4)
    raw = gzip.decompress(base64.urlsafe_b64decode(body))
    return json.loads(raw.decode("utf-8"))
