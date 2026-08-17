import json
from pathlib import Path
from .block import Block
from .transaction import Transaction


class Blockchain:
    def __init__(self, storage_path="data/ledger.json"):
        self.storage_path = Path(storage_path)
        self.chain = []
        self.pending_transactions = []
        self.load()

    def create_genesis(self):
        if not self.chain:
            self.chain.append(Block.genesis())
            self.save()

    def add_signed_transaction(self, transaction: Transaction):
        if not transaction.actor_signature:
            raise ValueError("Transaction must be signed before submission.")
        if transaction.transaction_hash != transaction.calculate_hash():
            raise ValueError("Transaction hash mismatch.")
        self.pending_transactions.append(transaction.to_dict())

    def mine_block(self):
        if not self.pending_transactions:
            return None
        previous_hash = self.chain[-1].hash if self.chain else "0"
        block = Block(
            index=len(self.chain),
            timestamp=Block.genesis().timestamp,
            transactions=list(self.pending_transactions),
            previous_hash=previous_hash,
        )
        block.finalize()
        self.chain.append(block)
        self.pending_transactions.clear()
        self.save()
        return block

    def verify(self):
        if not self.chain:
            return False
        for i, block in enumerate(self.chain):
            if block.hash != block.calculate_hash():
                return False
            if i and block.previous_hash != self.chain[i - 1].hash:
                return False
            for tx in block.transactions:
                if tx.get("transaction_hash") != Transaction(
                    transaction_id=tx["transaction_id"],
                    transaction_type=tx["transaction_type"],
                    actor_id=tx["actor_id"],
                    data=tx["data"],
                    timestamp=tx["timestamp"],
                    actor_signature=tx.get("actor_signature", ""),
                    transaction_hash=tx.get("transaction_hash", ""),
                ).calculate_hash():
                    return False
        return True

    def find_batch(self, batch_id):
        history = []
        for block in self.chain:
            for tx in block.transactions:
                data = tx.get("data", {})
                if data.get("batch_id") == batch_id:
                    history.append({
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "transaction": tx,
                    })
        return history

    def get_batch_events(self, batch_id):
        return [x["transaction"] for x in self.find_batch(batch_id)]

    def save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps([b.to_dict() for b in self.chain], indent=2),
            encoding="utf-8",
        )

    def load(self):
        if not self.storage_path.exists():
            self.create_genesis()
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self.chain = [
                Block(
                    index=x["index"],
                    timestamp=x["timestamp"],
                    transactions=x["transactions"],
                    previous_hash=x["previous_hash"],
                    nonce=x.get("nonce", 0),
                    hash=x.get("hash", ""),
                )
                for x in data
            ]
            if not self.chain:
                self.create_genesis()
        except (json.JSONDecodeError, KeyError, TypeError, OSError):
            self.chain = []
            self.create_genesis()
