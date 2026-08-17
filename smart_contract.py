from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class HerbTraceContract:
    """Rule engine for the prototype ledger. It is not a Hyperledger smart contract."""

    def create_batch(self, batch_id, herb_name, collector_id, quantity, geo, image_meta, rating):
        return {
            "batch_id": batch_id,
            "herb_name": herb_name,
            "collector_id": collector_id,
            "quantity_kg": float(quantity),
            "collection": {
                "captured_at": image_meta["captured_at"],
                "gps": geo,
                "image": image_meta,
            },
            "ratings": {"collection": rating},
            "processing_history": [],
            "laboratory": None,
            "manufacturing": None,
            "status": "COLLECTED",
            "created_at": now(),
            "updated_at": now(),
        }

    def add_processing(self, batch, record):
        if batch["status"] not in {"COLLECTED", "PROCESSED"}:
            raise ValueError("Batch is not eligible for processing.")
        batch["processing_history"].append(record)
        batch["ratings"]["processing"] = record["process_rating"]
        batch["current_quantity_kg"] = record["output_quantity_kg"]
        batch["status"] = "PROCESSED"
        batch["updated_at"] = now()
        return batch

    def add_laboratory(self, batch, record):
        if batch["status"] != "PROCESSED":
            raise ValueError("Laboratory assessment requires processed batch data.")
        batch["laboratory"] = record
        batch["ratings"]["laboratory"] = record["lab_rating"]
        batch["status"] = record["lab_status"]
        batch["updated_at"] = now()
        return batch

    def add_manufacturing(self, batch, record):
        if batch["status"] != "COMPLIANT":
            raise ValueError("Only COMPLIANT batches can be manufactured.")
        batch["manufacturing"] = record
        batch["ratings"]["manufacturing"] = record["manufacturing_rating"]
        batch["status"] = "MANUFACTURED"
        batch["updated_at"] = now()
        return batch
