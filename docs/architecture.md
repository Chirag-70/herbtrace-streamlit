# HerbTrace flow implemented from the supplied architecture

```text
STEP I
FARMER / COLLECTOR
  ├─ participant ID + ECDSA key
  ├─ live herb camera image
  ├─ browser/device geolocation (no manual lat/long)
  ├─ image SHA-256
  ├─ collection rating /10
  └─ cumulative QR
          ↓
STEP II
PROCESSING INDUSTRY
  ├─ initial + final weight
  ├─ herb + process-specific anomaly detection
  ├─ humidity / temperature
  ├─ process rating /10
  └─ cumulative QR
          ↓
STEP III
LABORATORY
  ├─ GPS (when permission is granted)
  ├─ temperature / humidity
  ├─ soil / harvest moisture
  ├─ harvest, storage, transport information
  ├─ laboratory report
  ├─ lab rating /10
  └─ cumulative QR
          ↓
GOVERNMENT VERIFICATION
  ├─ chain integrity check
  ├─ monitoring record
  └─ cumulative QR
          ↓
STEP IV
MANUFACTURING COMPANY
  ├─ product information
  ├─ average/final overall rating /10
  └─ cumulative QR
          ↓
STEP V
CONSUMER / COMPANY
  ├─ scan/upload latest QR
  ├─ complete cumulative trace
  └─ overall rating /10

All signed events are committed to:
Python Blockchain-style SHA-256 hash chain
        ↓
data/ledger.json
