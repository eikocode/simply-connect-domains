"""
SQLite DataOS for save-my-brain extension.

Mirrors the structure of apps/save-my-brain/backend's Supabase schema,
adapted for local SQLite. Provides proper structured storage for
documents, transactions, medical records, policies, and family members.

Tables follow the AIOS DataOS pattern:
  smb_documents          — master document table with file hash for dedup
  smb_transactions       — receipts, bank statements (amount, merchant, category)
  smb_medical_records    — doctor visits, prescriptions
  smb_policies           — insurance with expiry tracking
  smb_family_members     — household roster
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS smb_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_hash TEXT UNIQUE,
    file_type TEXT,
    doc_type TEXT,
    summary TEXT,
    key_points TEXT,
    important_dates TEXT,
    red_flags TEXT,
    action_items TEXT,
    family_member_id INTEGER,
    currency TEXT,
    extracted_text TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_smb_documents_hash ON smb_documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_smb_documents_type ON smb_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_smb_documents_family ON smb_documents(family_member_id);

CREATE TABLE IF NOT EXISTS smb_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    family_member_id INTEGER,
    date TEXT,
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'HKD',
    merchant TEXT,
    category TEXT,
    description TEXT,
    is_income INTEGER DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES smb_documents(id)
);

CREATE INDEX IF NOT EXISTS idx_smb_transactions_category ON smb_transactions(category);
CREATE INDEX IF NOT EXISTS idx_smb_transactions_date ON smb_transactions(date);
CREATE INDEX IF NOT EXISTS idx_smb_transactions_family ON smb_transactions(family_member_id);

CREATE TABLE IF NOT EXISTS smb_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    family_member_id INTEGER,
    policy_type TEXT,
    insurer TEXT,
    policy_number TEXT,
    sum_insured REAL,
    currency TEXT DEFAULT 'HKD',
    annual_premium REAL,
    start_date TEXT,
    expiry_date TEXT,
    beneficiary TEXT,
    key_exclusions TEXT,
    waiting_period_days INTEGER,
    FOREIGN KEY (document_id) REFERENCES smb_documents(id)
);

CREATE INDEX IF NOT EXISTS idx_smb_policies_expiry ON smb_policies(expiry_date);

CREATE TABLE IF NOT EXISTS smb_medical_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    family_member_id INTEGER,
    date TEXT,
    provider TEXT,
    doctor TEXT,
    diagnosis TEXT,
    medications TEXT,
    follow_up_date TEXT,
    notes TEXT,
    FOREIGN KEY (document_id) REFERENCES smb_documents(id)
);

CREATE INDEX IF NOT EXISTS idx_smb_medical_date ON smb_medical_records(date);

CREATE TABLE IF NOT EXISTS smb_family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    aliases TEXT,
    is_primary INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db_path(cm=None) -> str:
    """Resolve the SQLite DB path. Priority: SC_DATA_DIR env → cm._root → cwd."""
    data_dir = os.getenv("SC_DATA_DIR")
    if not data_dir and cm is not None:
        data_dir = str(cm._root)
    if not data_dir:
        data_dir = "."
    db_path = Path(data_dir) / "data" / "smb.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def init_db(cm=None) -> sqlite3.Connection:
    """Create tables if they don't exist. Safe to call repeatedly."""
    path = get_db_path(cm)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def get_connection(cm=None) -> sqlite3.Connection:
    """Open a connection (initialises schema if needed)."""
    return init_db(cm)


def compute_file_hash(file_bytes: bytes) -> str:
    """SHA-256 hex digest of file bytes — for duplicate detection."""
    return hashlib.sha256(file_bytes).hexdigest()


def find_document_by_hash(cm, file_hash: str) -> dict | None:
    """Return existing document row if hash matches, else None."""
    conn = get_connection(cm)
    try:
        row = conn.execute(
            "SELECT * FROM smb_documents WHERE file_hash = ?",
            (file_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def insert_document(cm, doc: dict) -> int:
    """Insert a document row and return its id. Also sync family members."""
    conn = get_connection(cm)
    try:
        cursor = conn.execute(
            """INSERT INTO smb_documents
               (filename, file_hash, file_type, doc_type, summary, key_points,
                important_dates, red_flags, action_items, family_member_id,
                currency, extracted_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc.get("filename", ""),
                doc.get("file_hash"),
                doc.get("file_type"),
                doc.get("doc_type", "other"),
                doc.get("summary", ""),
                json.dumps(doc.get("key_points", []), ensure_ascii=False),
                json.dumps(doc.get("important_dates", []), ensure_ascii=False),
                json.dumps(doc.get("red_flags", []), ensure_ascii=False),
                json.dumps(doc.get("action_items", []), ensure_ascii=False),
                doc.get("family_member_id"),
                doc.get("currency"),
                doc.get("extracted_text"),
            ),
        )
        doc_id = cursor.lastrowid
        conn.commit()
        return doc_id
    finally:
        conn.close()


def insert_transactions(cm, doc_id: int, transactions: list[dict],
                        family_member_id: int | None = None,
                        default_currency: str = "HKD") -> int:
    """Bulk insert transactions linked to a document. Returns count inserted."""
    if not transactions:
        return 0
    conn = get_connection(cm)
    count = 0
    try:
        for txn in transactions:
            amount = float(txn.get("amount", 0) or 0)
            conn.execute(
                """INSERT INTO smb_transactions
                   (document_id, family_member_id, date, amount, currency,
                    merchant, category, description, is_income)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    doc_id,
                    family_member_id,
                    txn.get("date", ""),
                    abs(amount),
                    txn.get("currency", default_currency),
                    txn.get("merchant", ""),
                    txn.get("category", "other"),
                    txn.get("description", ""),
                    1 if amount > 0 else 0,
                ),
            )
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def insert_policy(cm, doc_id: int, policy: dict, family_member_id: int | None = None) -> int:
    conn = get_connection(cm)
    try:
        cursor = conn.execute(
            """INSERT INTO smb_policies
               (document_id, family_member_id, policy_type, insurer, policy_number,
                sum_insured, currency, annual_premium, start_date, expiry_date,
                beneficiary, key_exclusions, waiting_period_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id, family_member_id,
                policy.get("policy_type"),
                policy.get("insurer"),
                policy.get("policy_number"),
                policy.get("sum_insured"),
                policy.get("currency", "HKD"),
                policy.get("annual_premium"),
                policy.get("start_date"),
                policy.get("expiry_date"),
                policy.get("beneficiary"),
                json.dumps(policy.get("key_exclusions", []), ensure_ascii=False),
                policy.get("waiting_period_days"),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_medical(cm, doc_id: int, med: dict, family_member_id: int | None = None) -> int:
    conn = get_connection(cm)
    try:
        cursor = conn.execute(
            """INSERT INTO smb_medical_records
               (document_id, family_member_id, date, provider, doctor,
                diagnosis, medications, follow_up_date, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id, family_member_id,
                med.get("date"),
                med.get("provider"),
                med.get("doctor"),
                med.get("diagnosis"),
                json.dumps(med.get("medications", []), ensure_ascii=False),
                med.get("follow_up_date"),
                med.get("notes"),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def sync_family_member(cm, name: str, is_primary: bool = False) -> int:
    """Insert family member if not exists, return id."""
    conn = get_connection(cm)
    try:
        row = conn.execute(
            "SELECT id FROM smb_family_members WHERE LOWER(name) = LOWER(?)",
            (name,),
        ).fetchone()
        if row:
            return row["id"]
        cursor = conn.execute(
            "INSERT INTO smb_family_members (name, is_primary) VALUES (?, ?)",
            (name, 1 if is_primary else 0),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def find_family_member_id(cm, name: str) -> int | None:
    """Case-insensitive lookup."""
    if not name:
        return None
    conn = get_connection(cm)
    try:
        row = conn.execute(
            "SELECT id FROM smb_family_members WHERE LOWER(name) = LOWER(?)",
            (name,),
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Semantic duplicate detection
# ---------------------------------------------------------------------------

def _norm_merchant(m: str | None) -> str:
    """Normalize merchant name for comparison."""
    if not m:
        return ""
    # Lowercase, collapse whitespace, remove punctuation
    import re
    return re.sub(r"[^\w\s]", "", m.lower()).strip()


def find_semantic_duplicate_transaction(
    cm,
    merchant: str | None,
    date_str: str | None,
    amount: float | None,
    amount_tolerance: float = 0.5,
) -> dict | None:
    """
    Look for an existing transaction with matching (merchant, date, amount).

    Uses normalized merchant name (lowercase, no punctuation) and exact date.
    Amount has a small tolerance (default 0.5) to handle rounding.

    Returns the matching transaction row as a dict, or None.
    """
    if not merchant or not date_str or amount is None:
        return None

    norm_merch = _norm_merchant(merchant)
    if not norm_merch:
        return None

    conn = get_connection(cm)
    try:
        rows = conn.execute(
            """SELECT t.id, t.date, t.amount, t.merchant, t.category, t.currency,
                      t.document_id, d.filename, d.doc_type, d.uploaded_at
               FROM smb_transactions t
               LEFT JOIN smb_documents d ON d.id = t.document_id
               WHERE t.date = ?
                 AND ABS(t.amount - ?) < ?""",
            (date_str, abs(float(amount)), amount_tolerance),
        ).fetchall()

        for row in rows:
            existing_norm = _norm_merchant(row["merchant"])
            # Exact normalized match, or one contains the other
            if existing_norm == norm_merch:
                return dict(row)
            if existing_norm and norm_merch and (
                existing_norm in norm_merch or norm_merch in existing_norm
            ):
                return dict(row)

        return None
    finally:
        conn.close()


def find_semantic_duplicate_policy(
    cm,
    insurer: str | None,
    policy_number: str | None,
) -> dict | None:
    """Match insurance policy by (insurer, policy_number)."""
    if not policy_number:
        return None
    conn = get_connection(cm)
    try:
        rows = conn.execute(
            """SELECT p.id, p.insurer, p.policy_number, p.policy_type,
                      p.document_id, d.filename, d.uploaded_at
               FROM smb_policies p
               LEFT JOIN smb_documents d ON d.id = p.document_id
               WHERE p.policy_number = ?""",
            (policy_number,),
        ).fetchall()
        for row in rows:
            # If insurer also matches (case-insensitive), it's definitely a dup
            if not insurer or (row["insurer"] or "").lower() == insurer.lower():
                return dict(row)
        return None
    finally:
        conn.close()


def find_semantic_duplicate_medical(
    cm,
    doctor: str | None,
    date_str: str | None,
    provider: str | None = None,
) -> dict | None:
    """Match medical record by (doctor, date) or (provider, date)."""
    if not date_str:
        return None
    if not doctor and not provider:
        return None
    conn = get_connection(cm)
    try:
        rows = conn.execute(
            """SELECT m.id, m.doctor, m.provider, m.date,
                      m.document_id, d.filename, d.uploaded_at
               FROM smb_medical_records m
               LEFT JOIN smb_documents d ON d.id = m.document_id
               WHERE m.date = ?""",
            (date_str,),
        ).fetchall()
        for row in rows:
            row_doctor = (row["doctor"] or "").lower()
            row_provider = (row["provider"] or "").lower()
            if doctor and row_doctor == doctor.lower():
                return dict(row)
            if provider and row_provider == provider.lower():
                return dict(row)
        return None
    finally:
        conn.close()


def find_semantic_duplicate(cm, doc_type: str, extraction: dict) -> dict | None:
    """
    Dispatcher: look for a semantic duplicate based on doc_type + extracted fields.

    Returns a dict with:
      {
        "kind": "transaction" | "policy" | "medical",
        "match": {...existing row...},
      }
    ...or None if no duplicate is found.
    """
    # Transactions (receipts, bank statements, credit cards, utility bills)
    if doc_type in ("receipt", "bank_statement", "credit_card", "utility"):
        txns = extraction.get("transactions") or []
        if txns:
            t = txns[0]
            match = find_semantic_duplicate_transaction(
                cm,
                merchant=t.get("merchant"),
                date_str=t.get("date"),
                amount=t.get("amount"),
            )
            if match:
                return {"kind": "transaction", "match": match}

    # Insurance policies
    if doc_type == "insurance":
        policy = extraction.get("policy") or {}
        match = find_semantic_duplicate_policy(
            cm,
            insurer=policy.get("insurer"),
            policy_number=policy.get("policy_number"),
        )
        if match:
            return {"kind": "policy", "match": match}

    # Medical records
    if doc_type == "medical":
        med = extraction.get("medical_record") or {}
        match = find_semantic_duplicate_medical(
            cm,
            doctor=med.get("doctor"),
            date_str=med.get("date"),
            provider=med.get("provider"),
        )
        if match:
            return {"kind": "medical", "match": match}

    return None
