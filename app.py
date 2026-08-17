import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from blockchain.blockchain import Blockchain
from blockchain.smart_contract import HerbTraceContract
from blockchain.transaction import Transaction
from blockchain.wallet import load_or_create_participant
from ml.anomaly_detector import detect_anomaly, rate_processing
from utils.gps import extract_exif_gps, normalize_browser_location, capture_timestamp
from utils.qr_codec import save_qr, decode_payload

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

st.set_page_config(page_title="HerbTrace | Ayurvedic Supply Chain", page_icon="🌿", layout="wide")

LEDGER = Blockchain()
CONTRACT = HerbTraceContract()

for key, default in {
    "participant_id": "FARMER-001",
    "role": "Farmer / Collector",
    "live_location": None,
    "location_time": None,
    "capture_time": None,
}.items():
    st.session_state.setdefault(key, default)

st.markdown("""
<style>
.block-container{max-width:1400px;padding-top:1.5rem}
.hero{padding:26px;border-radius:22px;background:linear-gradient(135deg,#0b3d2e,#176b4f);
color:white;margin-bottom:20px}
.card{padding:18px;border:1px solid #dfe7e2;border-radius:16px;background:#ffffff}
.small{color:#66756e;font-size:.88rem}
.metricbox{padding:15px;border-radius:15px;background:#f3f8f5;border:1px solid #dce9e2}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🌿 HerbTrace</h1>
<p>Traceable Ayurvedic Herb Supply Chain • Tamper-Evident Python Blockchain</p>
</div>
""", unsafe_allow_html=True)

roles = ["Farmer / Collector", "Processing Industry", "Laboratory", "Manufacturing Company",
         "Government Verification", "Consumer", "Blockchain Status"]
role = st.sidebar.selectbox("Current Layer", roles, index=roles.index(st.session_state.role))
st.session_state.role = role

role_prefix = {
    "Farmer / Collector": "FARMER",
    "Processing Industry": "PROCESSOR",
    "Laboratory": "LAB",
    "Manufacturing Company": "MANUFACTURER",
    "Government Verification": "GOV",
    "Consumer": "CONSUMER",
}
if role in role_prefix:
    st.session_state.participant_id = st.sidebar.text_input(
        "Participant ID", st.session_state.participant_id
    )
    st.sidebar.caption("Each participant ID has its own ECDSA key pair in the prototype ledger.")

def signed_submit(tx_type, actor_id, data):
    record, wallet = load_or_create_participant(actor_id, role)
    tx = Transaction.create(tx_type, actor_id, data)
    tx.actor_signature = wallet.sign(tx.transaction_hash)
    LEDGER.add_signed_transaction(tx)
    block = LEDGER.mine_block()
    return tx, block

def batch_snapshot(batch_id):
    records = LEDGER.find_batch(batch_id)
    return {
        "format": "HerbTrace-QR-v1",
        "batch_id": batch_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blockchain_valid": LEDGER.verify(),
        "records": records,
        "latest_block": records[-1]["block_index"] if records else None,
        "latest_block_hash": records[-1]["block_hash"] if records else None,
    }

def cumulative_qr(batch_id, stage):
    snapshot = batch_snapshot(batch_id)
    path, payload, phash = save_qr(snapshot, batch_id, stage)
    return path, payload, phash

def show_qr(batch_id, stage):
    try:
        path, payload, phash = cumulative_qr(batch_id, stage)
        st.image(path, caption=f"{stage.upper()} cumulative QR")
        st.caption(f"QR SHA-256: {phash}")
        with st.expander("QR payload"):
            st.code(payload)
    except ValueError as e:
        st.error(str(e))

def process_rating_card(rating):
    st.metric("Process Rating", f"{rating:.2f}/10")

# ---------------- FARMER ----------------
if role == "Farmer / Collector":
    st.header("🌱 Step I — Farmer / Collector")
    st.info("No manual latitude/longitude input. Get browser/device location and capture the herb image.")

    herb_name = st.text_input("Herb name", "Ashwagandha")
    quantity = st.number_input("Initial herb quantity (kg)", min_value=0.001, value=50.0, step=0.1)

    st.subheader("📍 Live location")
    if streamlit_geolocation:
        live_location = streamlit_geolocation()
        if live_location and live_location.get("latitude") is not None:
            st.session_state.live_location = live_location
            st.session_state.location_time = capture_timestamp()
        if st.session_state.live_location and st.session_state.live_location.get("latitude") is not None:
            loc = normalize_browser_location(st.session_state.live_location)
            st.success("Live browser/device location received.")
            st.write(f"Latitude: {loc['latitude']}")
            st.write(f"Longitude: {loc['longitude']}")
            st.write(f"Accuracy: {loc['accuracy_m']} m" if loc["accuracy_m"] else "Accuracy unavailable")
        else:
            st.warning("Use the component's location button and allow browser location permission. Do not enter coordinates manually.")
    else:
        st.error("Install streamlit-geolocation from requirements.txt to enable browser GPS.")

    st.subheader("📷 Live herb image")
    image = st.camera_input("Capture herb at the collection site")
    if image:
        capture_time = capture_timestamp()
        st.session_state.capture_time = capture_time
        st.image(image, width=420)
        exif = extract_exif_gps(image)
        if exif:
            st.success("Image contains EXIF GPS. It will be retained as secondary evidence.")
            st.json(exif)
        else:
            st.caption("No EXIF GPS found; browser geolocation is the primary source.")

    if st.button("Create Collection Batch", type="primary"):
        if not image:
            st.error("Capture the herb image first.")
        elif not st.session_state.live_location or st.session_state.live_location.get("latitude") is None:
            st.error("Get live location first. Manual coordinates are not accepted.")
        else:
            loc = normalize_browser_location(st.session_state.live_location)
            batch_id = "HERB-" + uuid.uuid4().hex[:8].upper()
            image_bytes = image.getvalue()
            image_meta = {
                "filename": image.name,
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                "captured_at": st.session_state.capture_time,
                "location_observed_at": st.session_state.location_time,
                "location_image_time_delta_seconds": None,
                "source": "STREAMLIT_CAMERA_INPUT",
            }
            rating = 10.0
            batch = CONTRACT.create_batch(batch_id, herb_name, st.session_state.participant_id,
                                          quantity, loc, image_meta, rating)
            batch["current_quantity_kg"] = quantity
            batch["collection"]["gps"]["exif_secondary"] = extract_exif_gps(image)
            tx, block = signed_submit("COLLECTION", st.session_state.participant_id, {
                "event": "COLLECTION", "batch_id": batch_id, "herb_name": herb_name,
                "quantity_kg": quantity, "collection": batch["collection"],
                "rating": rating
            })
            st.session_state["last_batch"] = batch_id
            st.success(f"Batch created: {batch_id}")
            st.write("Block:", block.index, "• Transaction:", tx.transaction_id)
            show_qr(batch_id, "collection")

# ---------------- PROCESSOR ----------------
elif role == "Processing Industry":
    st.header("⚙️ Step II — Processing Industry")
    batch_id = st.text_input("Batch ID", st.session_state.get("last_batch", ""))
    process_type = st.selectbox("Processing stage", ["Cleaning", "Washing", "Drying", "Sorting", "Grinding", "Cutting", "Storage"])
    input_kg = st.number_input("Initial weight (kg)", min_value=0.001, value=50.0)
    output_kg = st.number_input("Final weight (kg)", min_value=0.001, value=47.0)
    humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=10.0)
    temperature = st.number_input("Temperature (°C)", value=25.0)
    remarks = st.text_area("Process observations")

    if input_kg > 0:
        loss = input_kg - output_kg
        st.metric("Weight change", f"{loss:.2f} kg ({loss/input_kg*100:.2f}%)")

    if st.button("Analyze + Record Processing", type="primary"):
        history = [x["transaction"]["data"] for x in LEDGER.find_batch(batch_id)]
        collection = next((x for x in history if x.get("event") == "COLLECTION"), None)
        if not collection:
            st.error("Batch not found or collection transaction is missing.")
        elif output_kg > input_kg:
            st.error("Final weight cannot exceed initial weight.")
        else:
            herb = collection["herb_name"]
            anomaly = detect_anomaly(LEDGER, herb, process_type, input_kg, output_kg, humidity, temperature)
            rating = rate_processing(anomaly, input_kg, output_kg)
            record = {
                "event": "PROCESSING", "batch_id": batch_id, "herb_name": herb,
                "process_type": process_type, "input_quantity_kg": input_kg,
                "output_quantity_kg": output_kg, "quantity_loss_kg": input_kg-output_kg,
                "humidity_percent": humidity, "temperature_c": temperature,
                "anomaly": anomaly, "process_rating": rating,
                "remarks": remarks, "actor_id": st.session_state.participant_id
            }
            tx, block = signed_submit("PROCESSING", st.session_state.participant_id, record)
            st.success("Processing record committed.")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Rating", f"{rating}/10")
            c2.metric("Anomaly", "DETECTED" if anomaly["anomaly"] else "NORMAL")
            c3.metric("Weight Change", f"{anomaly.get('change_percent', 0):.2f}%")
            c4.metric("Method", anomaly["method"])
            show_qr(batch_id, "processing")

# ---------------- LAB ----------------
elif role == "Laboratory":
    st.header("🧪 Step III — Laboratory")
    batch_id = st.text_input("Batch ID", st.session_state.get("last_batch", ""))
    appearance = st.text_area("Organoleptic / macroscopic observations")
    st.subheader("📍 Laboratory location")
    lab_location = None
    if streamlit_geolocation:
        lab_live = streamlit_geolocation()
        if lab_live and lab_live.get("latitude") is not None:
            lab_location = normalize_browser_location(lab_live)
            st.success(f"Lab GPS: {lab_location['latitude']:.6f}, {lab_location['longitude']:.6f}")
        else:
            st.caption("Allow browser location if laboratory GPS is to be recorded.")
    moisture = st.number_input("Moisture / LOD (%)", 0.0, 100.0, 5.0)
    foreign = st.number_input("Foreign matter (%)", 0.0, 100.0, 0.0)
    temperature = st.number_input("Sample/storage temperature (°C)", value=25.0)
    humidity = st.number_input("Sample/storage humidity (%)", 0.0, 100.0, 50.0)
    soil_moisture = st.number_input("Soil moisture / harvest moisture (%)", 0.0, 100.0, 20.0)
    harvest_time = st.text_input("Harvest time / date (if recorded)")
    storage_data = st.text_area("Storage conditions")
    transport_data = st.text_area("Transportation conditions")
    lab_report = st.text_area("Laboratory report / observations")
    safety = st.selectbox("Safety test status", ["Compliant", "Non-compliant", "Retest required"])
    lab_status = st.selectbox("Final laboratory status", ["COMPLIANT", "NON_COMPLIANT", "REQUIRES_RETEST"])

    if st.button("Record Laboratory Assessment", type="primary"):
        if not LEDGER.find_batch(batch_id):
            st.error("Batch not found.")
        else:
            score = 10.0
            if moisture > 15: score -= 2
            if foreign > 2: score -= 2
            if safety != "Compliant": score -= 4
            if lab_status != "COMPLIANT": score -= 3
            score = round(max(0, min(10, score)), 2)
            record = {
                "event": "LABORATORY", "batch_id": batch_id,
                "appearance": appearance, "moisture_percent": moisture,
                "foreign_matter_percent": foreign, "temperature_c": temperature,
                "humidity_percent": humidity, "soil_moisture_percent": soil_moisture,
                "harvest_time": harvest_time, "storage_data": storage_data,
                "transportation_data": transport_data, "laboratory_report": lab_report,
                "lab_location": lab_location, "safety_status": safety,
                "lab_status": lab_status, "lab_rating": score,
                "actor_id": st.session_state.participant_id
            }
            tx, block = signed_submit("LABORATORY", st.session_state.participant_id, record)
            st.metric("Laboratory Rating", f"{score}/10")
            st.success("Laboratory data committed.")
            show_qr(batch_id, "laboratory")

# ---------------- MANUFACTURER ----------------
elif role == "Manufacturing Company":
    st.header("🏭 Step IV — Manufacturing Company")
    batch_id = st.text_input("Approved Batch ID", st.session_state.get("last_batch", ""))
    product_name = st.text_input("Product", "Ashwagandha Capsules")
    manufacturer = st.text_input("Company", "HerbTrace Pharma")
    manufacturing_date = st.date_input("Manufacturing date")
    expiry_date = st.date_input("Expiry date")

    if st.button("Create Product + Final Rating", type="primary"):
        events = [x["transaction"]["data"] for x in LEDGER.find_batch(batch_id)]
        lab = next((x for x in events if x.get("event") == "LABORATORY"), None)
        if not lab or lab.get("lab_status") != "COMPLIANT":
            st.error("Only a COMPLIANT laboratory batch can be manufactured.")
        else:
            ratings = [x.get("rating") for x in events if isinstance(x.get("rating"), (int,float))]
            proc = [x.get("process_rating") for x in events if x.get("process_rating") is not None]
            lab_rating = lab["lab_rating"]
            collection_rating = 10.0
            process_rating = proc[-1] if proc else 10.0
            overall = round((collection_rating + process_rating + lab_rating) / 3, 2)
            manufacturing_rating = overall
            record = {
                "event": "MANUFACTURING", "batch_id": batch_id,
                "product_name": product_name, "manufacturer": manufacturer,
                "manufacturing_date": str(manufacturing_date),
                "expiry_date": str(expiry_date),
                "manufacturing_rating": manufacturing_rating,
                "overall_rating": overall,
                "actor_id": st.session_state.participant_id
            }
            tx, block = signed_submit("MANUFACTURING", st.session_state.participant_id, record)
            st.success("Product created and cumulative traceability finalized.")
            st.metric("Overall Rating", f"{overall}/10")
            show_qr(batch_id, "manufacturing")

# ---------------- GOV ----------------
elif role == "Government Verification":
    st.header("🏛️ Government Verification & Monitoring")
    batch_id = st.text_input("Batch ID")
    if st.button("Verify Chain"):
        history = LEDGER.find_batch(batch_id)
        if not history:
            st.error("Batch not found.")
        else:
            chain_valid = LEDGER.verify()
            st.success("Blockchain integrity: VALID" if chain_valid else "Blockchain integrity: INVALID")
            st.write("Recorded events:", len(history))
            if chain_valid and st.button("Record Government Verification"):
                gov_record = {
                    "event": "GOVERNMENT_VERIFICATION",
                    "batch_id": batch_id,
                    "verification": "VALID",
                    "monitored_at": datetime.now(timezone.utc).isoformat(),
                    "actor_id": st.session_state.participant_id,
                }
                tx, block = signed_submit("GOVERNMENT_VERIFICATION", st.session_state.participant_id, gov_record)
                st.success("Government verification committed.")
                show_qr(batch_id, "government")
            for item in history:
                with st.expander(f"Block {item['block_index']} • {item['transaction']['transaction_type']}"):
                    st.json(item["transaction"])

# ---------------- CONSUMER ----------------
elif role == "Consumer":
    st.header("🛒 Step V — Consumer / Company")
    st.write("Scan/upload a cumulative QR. Every later-stage QR carries the previous traceability records.")

    uploaded_qr = st.file_uploader("Upload cumulative QR image", type=["png","jpg","jpeg"])
    if uploaded_qr:
        try:
            import cv2
            import numpy as np
            image_array = np.frombuffer(uploaded_qr.getvalue(), dtype=np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            detector = cv2.QRCodeDetector()
            payload, points, _ = detector.detectAndDecode(frame)
            if not payload:
                st.error("No readable HerbTrace QR data detected.")
            else:
                snapshot = decode_payload(payload)
                st.success("HerbTrace cumulative QR verified and decoded.")
                st.json(snapshot)
        except Exception as e:
            st.error(f"QR decode failed: {e}")

    batch_id = st.text_input("Or enter Batch ID")
    if st.button("Show Full Trace"):
        history = LEDGER.find_batch(batch_id)
        if not history:
            st.error("Batch not found.")
        else:
            st.success("Blockchain integrity VALID" if LEDGER.verify() else "Blockchain integrity INVALID")
            for item in history:
                with st.expander(item["transaction"]["transaction_type"]):
                    st.json(item["transaction"])
            proc = [x["transaction"]["data"].get("process_rating") for x in history if x["transaction"]["data"].get("process_rating") is not None]
            lab = next((x["transaction"]["data"] for x in history if x["transaction"]["data"].get("event") == "LABORATORY"), None)
            man = next((x["transaction"]["data"] for x in history if x["transaction"]["data"].get("event") == "MANUFACTURING"), None)
            if man:
                st.metric("Overall Rating", f"{man.get('overall_rating', 0)}/10")
            if proc:
                st.metric("Latest Processing Rating", f"{proc[-1]}/10")
            if lab:
                st.metric("Laboratory Rating", f"{lab.get('lab_rating', 0)}/10")
            st.subheader("📱 Consumer Cumulative QR")
            show_qr(batch_id, "consumer")

# ---------------- STATUS ----------------
else:
    st.header("⛓️ Blockchain Status")
    valid = LEDGER.verify()
    c1,c2,c3 = st.columns(3)
    c1.metric("Blocks", len(LEDGER.chain))
    c2.metric("Integrity", "VALID" if valid else "INVALID")
    c3.metric("Transactions", sum(len(b.transactions) for b in LEDGER.chain))
    st.write("Ledger storage:", str(LEDGER.storage_path))
    if st.button("Re-verify Ledger"):
        st.success("Integrity verified." if LEDGER.verify() else "Integrity failure detected.")
