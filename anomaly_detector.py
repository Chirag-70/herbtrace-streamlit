from collections import defaultdict
import math
from pathlib import Path
import json

try:
    from sklearn.ensemble import IsolationForest
except ImportError:
    IsolationForest = None


def _historical_records(ledger, herb_name, process_type):
    rows = []
    for block in ledger.chain:
        for tx in block.transactions:
            d = tx.get("data", {})
            if d.get("event") != "PROCESSING":
                continue
            if d.get("herb_name") != herb_name or d.get("process_type") != process_type:
                continue
            inp = d.get("input_quantity_kg")
            out = d.get("output_quantity_kg")
            if inp and out and inp > 0:
                rows.append([
                    float(inp),
                    float(out),
                    float(inp - out),
                    float(d.get("humidity_percent", 0.0)),
                    float(d.get("temperature_c", 0.0)),
                ])
    return rows


def detect_anomaly(ledger, herb_name, process_type, input_kg, output_kg, humidity=0.0, temperature=0.0):
    if input_kg <= 0:
        return {"anomaly": True, "score": 1.0, "method": "validation", "message": "Invalid input weight."}

    change_pct = (output_kg - input_kg) / input_kg * 100.0
    loss_pct = max(0.0, -change_pct)
    gain_pct = max(0.0, change_pct)
    history = _historical_records(ledger, herb_name, process_type)
    if gain_pct > 0:
        return {
            "anomaly": True,
            "score": round(min(1.0, gain_pct / 10.0), 4),
            "method": "WeightDirectionValidation",
            "history_samples": len(history),
            "change_percent": round(change_pct, 2),
            "loss_percent": 0.0,
            "message": "Final weight increased; investigate added moisture/material or measurement error.",
        }

    if len(history) >= 8 and IsolationForest is not None:
        model = IsolationForest(contamination="auto", random_state=42)
        model.fit(history)
        pred = int(model.predict([[input_kg, output_kg, input_kg - output_kg, humidity, temperature]])[0])
        decision = float(model.decision_function([[input_kg, output_kg, input_kg - output_kg, humidity, temperature]])[0])
        anomaly = pred == -1
        return {
            "anomaly": anomaly,
            "score": round(max(0.0, min(1.0, 0.5 - decision)), 4),
            "method": "IsolationForest",
            "history_samples": len(history),
            "loss_percent": round(loss_pct, 2),
            "change_percent": round(change_pct, 2),
        }

    if history:
        losses = [r[2] / r[0] * 100 for r in history if r[0] > 0]
        mean = sum(losses) / len(losses)
        variance = sum((x - mean) ** 2 for x in losses) / max(1, len(losses) - 1)
        std = math.sqrt(variance)
        threshold = max(5.0, mean + 2 * std)
        anomaly = loss_pct > threshold
        score = min(1.0, max(0.0, (loss_pct - mean) / max(1.0, threshold)))
        return {
            "anomaly": anomaly,
            "score": round(score, 4),
            "method": "HistoricalBaseline",
            "history_samples": len(history),
            "baseline_loss_percent": round(mean, 2),
            "threshold_percent": round(threshold, 2),
            "loss_percent": round(loss_pct, 2),
            "change_percent": round(change_pct, 2),
        }

    # Cold-start rule: no model can learn a herb/process pattern without history.
    anomaly = loss_pct > 20.0
    return {
        "anomaly": anomaly,
        "score": round(min(1.0, loss_pct / 20.0), 4),
        "method": "ColdStartRule",
        "history_samples": 0,
        "loss_percent": round(loss_pct, 2),
        "change_percent": round(change_pct, 2),
        "message": "Insufficient historical data for a learned herb/process baseline.",
    }


def rate_processing(anomaly_result, input_kg, output_kg):
    change_pct = (output_kg - input_kg) / input_kg * 100.0
    loss_pct = max(0.0, -change_pct)
    score = 10.0
    if change_pct > 0:
        score -= min(4.0, change_pct * 0.4)
    if loss_pct > 5:
        score -= min(2.5, (loss_pct - 5) * 0.25)
    if loss_pct > 10:
        score -= 1.5
    if anomaly_result["anomaly"]:
        score -= 3.0
    return round(max(0.0, min(10.0, score)), 2)
