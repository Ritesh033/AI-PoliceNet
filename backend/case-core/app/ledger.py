import hashlib
import hmac
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .domain import Actor
from .models import LedgerEntry

GENESIS_HASH = "0" * 64


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def canonical_bytes(
    *, seq: int, ts: str, case_id: str | None, actor_id: str, actor_role: str, actor_kind: str,
    action: str, payload: dict, prev_hash: str,
) -> bytes:
    record = {
        "seq": seq, "ts": ts, "case_id": case_id, "actor_id": actor_id, "actor_role": actor_role,
        "actor_kind": actor_kind, "action": action, "payload": payload, "prev_hash": prev_hash,
    }
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()


def entry_hash(entry: LedgerEntry) -> str:
    return hashlib.sha256(
        canonical_bytes(
            seq=entry.seq, ts=entry.ts, case_id=entry.case_id, actor_id=entry.actor_id,
            actor_role=entry.actor_role, actor_kind=entry.actor_kind, action=entry.action,
            payload=entry.payload, prev_hash=entry.prev_hash,
        )
    ).hexdigest()


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checked: int
    head_hash: str
    first_bad_seq: int | None = None
    reason: str | None = None


class Ledger:
    """Append-only hash chain. Tamper-evident, not tamper-proof: edits are detectable, not impossible."""

    def __init__(self, session: Session, clock: Callable[[], datetime] = utcnow):
        self.session = session
        self.clock = clock

    def _last(self) -> LedgerEntry | None:
        return self.session.execute(
            select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(1).with_for_update()
        ).scalar_one_or_none()

    def append(self, *, case_id: str | None, actor: Actor, action: str, payload: dict | None = None) -> LedgerEntry:
        last = self._last()
        entry = LedgerEntry(
            seq=1 if last is None else last.seq + 1,
            ts=iso(self.clock()),
            case_id=case_id,
            actor_id=actor.id,
            actor_role=actor.role.value,
            actor_kind=actor.kind.value,
            action=action,
            payload=payload or {},
            prev_hash=GENESIS_HASH if last is None else last.hash,
            hash="",
        )
        entry.hash = entry_hash(entry)
        self.session.add(entry)
        self.session.flush()
        return entry

    def entries(self, after_seq: int = 0, limit: int = 100, case_id: str | None = None) -> list[LedgerEntry]:
        query = select(LedgerEntry).where(LedgerEntry.seq > after_seq)
        if case_id is not None:
            query = query.where(LedgerEntry.case_id == case_id)
        return list(self.session.execute(query.order_by(LedgerEntry.seq).limit(limit)).scalars())

    def all_entries(self) -> Iterable[LedgerEntry]:
        yield from self.session.execute(select(LedgerEntry).order_by(LedgerEntry.seq)).scalars()

    def verify(self) -> VerifyResult:
        expected_prev = GENESIS_HASH
        expected_seq = 1
        checked = 0
        for e in self.all_entries():
            if e.seq != expected_seq:
                return VerifyResult(False, checked, expected_prev, e.seq, f"sequence gap: expected {expected_seq}")
            if e.prev_hash != expected_prev:
                return VerifyResult(False, checked, expected_prev, e.seq, "previous-hash link broken")
            if entry_hash(e) != e.hash:
                return VerifyResult(False, checked, expected_prev, e.seq, "entry content does not match its hash")
            expected_prev = e.hash
            expected_seq += 1
            checked += 1
        return VerifyResult(True, checked, expected_prev)

    def checkpoint(self, key: str) -> dict:
        """A signed digest of the chain head. Publish it to independent custodians so history cannot be silently rewritten."""
        if not key:
            raise ValueError("APN_CHECKPOINT_KEY is not configured")
        result = self.verify()
        issued_at = iso(self.clock())
        message = f"{result.checked}:{result.head_hash}:{issued_at}".encode()
        return {
            "entries": result.checked,
            "head_hash": result.head_hash,
            "issued_at": issued_at,
            "chain_valid": result.ok,
            "signature": hmac.new(key.encode(), message, hashlib.sha256).hexdigest(),
        }


def verify_checkpoint(checkpoint: dict, key: str) -> bool:
    message = f"{checkpoint['entries']}:{checkpoint['head_hash']}:{checkpoint['issued_at']}".encode()
    expected = hmac.new(key.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, checkpoint["signature"])
