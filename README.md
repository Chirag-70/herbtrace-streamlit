# HerbTrace — Python Blockchain Prototype

This version follows the supplied handwritten flow while intentionally using **only Python + Streamlit + a local JSON ledger**.

## Architecture

Farmer / Collector
→ live browser geolocation + live camera image
→ collection transaction + QR

Processing Industry
→ initial/final weight + humidity/temperature
→ herb/process-specific anomaly detection
→ process rating /10
→ cumulative QR

Laboratory
→ GPS (optional), temperature, humidity, soil/harvest moisture, harvest/storage/transport data, lab report
→ laboratory rating /10
→ cumulative QR

Government Verification
→ blockchain integrity verification + monitoring transaction
→ cumulative QR

Manufacturing Company
→ product creation
→ final overall rating /10
→ cumulative QR

Consumer
→ scan/upload the latest cumulative QR or enter Batch ID
→ see the complete recorded chain

## Important technical facts

- This is **not Hyperledger Fabric** and is not a decentralized production blockchain.
- The ledger is a Python tamper-evident hash chain stored in `data/ledger.json`.
- SHA-256 is used for transaction and block hashes.
- ECDSA P-256 participant keys are used to sign transactions.
- Participant private keys are stored locally in `data/participants.json` for this prototype. Do not use this storage design for production secrets.
- A QR stores a compressed cumulative JSON snapshot of the batch. QR capacity is finite; the app rejects an oversized cumulative payload rather than silently omitting data.
- Browser geolocation is obtained with `navigator.geolocation` through `streamlit-geolocation`. It requires user permission and is not cryptographic proof of physical presence.
- The camera image is hashed with SHA-256. EXIF GPS, if present, is retained as secondary evidence.
- The herb CNN was intentionally not included because the earlier requirement was to remove the CNN herb classifier. A real model can be plugged into the collection layer later without changing the blockchain/QR design.
- The anomaly detector uses Isolation Forest after enough history exists for the same herb + processing stage. Before that it uses a historical baseline or a cold-start validation rule. It does not invent a learned model when there is no training history.

## Local run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

Push the repository to GitHub and set the main file to `app.py`.

The JSON ledger is file-based. Streamlit Cloud instances are not a suitable production database, so this project is intended as a prototype/demo unless persistent external storage is added later.

## Browser GPS

The farmer must:
1. open the app in a browser that supports geolocation;
2. allow location permission;
3. obtain live location;
4. capture the herb image;
5. submit the batch.

No latitude/longitude input field is provided.

## QR stages

QR images are written under:

`data/qr_codes/`

Stages include:
- collection
- processing
- laboratory
- government
- manufacturing

Every later QR contains the cumulative transaction history available at that point.
