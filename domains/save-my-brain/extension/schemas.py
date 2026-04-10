"""
Extraction schemas — copied from apps/save-my-brain/backend/services/claude_processor.py

Phase A: Classification (doc_type, language, names)
Phase B: Type-specific structured extraction

Categories that matter for smart folder queries:
- dining, groceries, transport, medical, dental, education, entertainment,
  shopping, utilities, rent, insurance_premium, subscription, income, fees, other
"""

from __future__ import annotations

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-5"

# Doc types that use Sonnet (need reasoning for red flags, exclusions, etc.)
COMPLEX_DOC_TYPES = {"insurance", "medical", "legal", "contract", "mortgage", "tax"}

# ---------------------------------------------------------------------------
# Phase A — Classification schema
# ---------------------------------------------------------------------------

CLASSIFY_SCHEMA = """{
  "doc_type": "bank_statement|credit_card|insurance|medical|legal|contract|receipt|school|mortgage|utility|id_document|tax|travel|hotel|event|other",
  "detected_names": ["John Lee", "李美玲"],
  "document_language": "en|zh|ja|other",
  "complexity": "simple|complex",
  "brief_description": "One-line description of what this document is",
  "currency": "HKD|USD|RMB|GBP|JPY|EUR|null"
}
Return ONLY the JSON, no markdown fences, no explanation."""

# ---------------------------------------------------------------------------
# Phase B — Type-specific extraction schemas
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMAS = {
    "bank_statement": """{
  "summary": "2-3 sentence summary in the user's language",
  "key_points": ["point 1", "point 2"],
  "important_dates": [{"label": "Statement period", "date": "2026-03-31", "days_until": 0}],
  "red_flags": [],
  "action_items": [],
  "transactions": [
    {"date": "2026-03-01", "amount": -125.50, "merchant": "Restaurant ABC", "category": "dining", "description": "Original line text"},
    {"date": "2026-03-02", "amount": 5000.00, "merchant": "Salary", "category": "income", "description": "Monthly salary"}
  ],
  "statement_total": -12340.50,
  "payment_due_date": "2026-04-15"
}
Categories: dining, groceries, transport, medical, education, entertainment, shopping, utilities, rent, insurance_premium, subscription, transfer, income, fees, other.
Use NEGATIVE amounts for spending, POSITIVE for income/credits.
Extract ALL transactions visible in the document.""",

    "credit_card": """{
  "summary": "2-3 sentence summary in the user's language",
  "key_points": ["point 1", "point 2"],
  "important_dates": [{"label": "Payment due", "date": "2026-04-15", "days_until": 12}],
  "red_flags": [],
  "action_items": ["Pay minimum $X by date"],
  "transactions": [
    {"date": "2026-03-01", "amount": -125.50, "merchant": "Restaurant ABC", "category": "dining", "description": "Original line text"}
  ],
  "statement_total": -12340.50,
  "minimum_payment": 500.00,
  "payment_due_date": "2026-04-15"
}
Categories: dining, groceries, transport, medical, education, entertainment, shopping, utilities, rent, insurance_premium, subscription, transfer, fees, other.
All spending amounts should be NEGATIVE. Extract ALL transactions.""",

    "receipt": """{
  "summary": "Brief description in user's language",
  "key_points": [],
  "important_dates": [],
  "red_flags": [],
  "action_items": [],
  "transactions": [
    {"date": "2026-03-15", "amount": -487.00, "merchant": "Wellcome", "category": "groceries", "description": "Groceries"}
  ]
}
Categories: dining, groceries, transport, medical, dental, pharmacy, education, entertainment, shopping, utilities, beauty, fitness, pets, other.
IMPORTANT category rules:
- Dental clinic receipt → "dental"
- Hospital/doctor visit receipt → "medical"
- Pharmacy/drug store receipt → "pharmacy"
- Restaurant/cafe receipt → "dining"
- Supermarket receipt → "groceries"
Do NOT classify a receipt as "insurance" — receipts are expenses, not policies.""",

    "insurance": """{
  "summary": "2-3 paragraph summary in the user's language",
  "key_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "important_dates": [{"label": "Policy renewal", "date": "2027-03-15", "days_until": 350}],
  "red_flags": [{"clause": "Description", "severity": "high|medium|low", "detail": "explanation"}],
  "action_items": ["Pay premium by...", "Review clause X"],
  "policy": {
    "policy_type": "life|medical|critical_illness|income_protection|property|vehicle|travel|other",
    "insurer": "AIA",
    "policy_number": "HK-12345",
    "sum_insured": 2000000,
    "currency": "HKD",
    "annual_premium": 18000,
    "start_date": "2024-03-15",
    "expiry_date": "2027-03-15",
    "beneficiary": "Mary Lee",
    "key_exclusions": ["Pre-existing conditions", "Adventure sports"],
    "waiting_period_days": 90
  }
}
RED FLAG criteria: liability limitation <60 days, auto-renewal without opt-out, penalty >10%, unusual termination terms, non-compete >12mo, unilateral amendment rights, liability cap below reasonable.""",

    "medical": """{
  "summary": "2-3 paragraph summary in the user's language",
  "key_points": ["point 1", "point 2", "point 3"],
  "important_dates": [{"label": "Follow-up appointment", "date": "2026-05-01", "days_until": 28}],
  "red_flags": [{"clause": "Urgent finding", "severity": "high", "detail": "explanation"}],
  "action_items": ["Schedule follow-up", "Take medication X"],
  "medical_record": {
    "date": "2026-04-01",
    "provider": "Queen Mary Hospital",
    "doctor": "Dr. Chan",
    "diagnosis": "Type 2 diabetes — well controlled",
    "medications": ["Metformin 500mg", "Vitamin D"],
    "follow_up_date": "2026-05-01",
    "notes": "Blood sugar levels improving"
  }
}""",

    "mortgage": """{
  "summary": "2-3 paragraph summary in the user's language",
  "key_points": ["point 1", "point 2", "point 3"],
  "important_dates": [{"label": "First payment", "date": "2026-05-01", "days_until": 28}],
  "red_flags": [{"clause": "Description", "severity": "high|medium|low", "detail": "explanation"}],
  "action_items": [],
  "loan": {
    "loan_type": "mortgage",
    "lender": "HSBC",
    "principal": 5000000,
    "currency": "HKD",
    "interest_rate": 3.5,
    "monthly_payment": 22000,
    "start_date": "2026-04-01",
    "end_date": "2056-04-01",
    "property_address": "Unit 1234, Tower 1, Harbour View"
  }
}""",

    "legal": """{
  "summary": "2-3 paragraph summary in the user's language",
  "key_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "important_dates": [{"label": "Deadline", "date": "2026-05-01", "days_until": 28}],
  "red_flags": [{"clause": "Description", "severity": "high|medium|low", "detail": "explanation"}],
  "action_items": ["Sign by...", "Return to..."]
}
RED FLAG criteria: liability limitation <60 days, auto-renewal without opt-out, penalty >10%, unusual termination terms, non-compete >12mo, unilateral amendment rights, liability cap below reasonable.""",

    "contract": """{
  "summary": "2-3 paragraph summary in the user's language",
  "key_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "important_dates": [{"label": "Contract end", "date": "2027-03-15", "days_until": 350}],
  "red_flags": [{"clause": "Description", "severity": "high|medium|low", "detail": "explanation"}],
  "action_items": ["Review clause X", "Sign by..."]
}
RED FLAG criteria: liability limitation <60 days, auto-renewal without opt-out, penalty >10%, unusual termination terms, non-compete >12mo, unilateral amendment rights, liability cap below reasonable.""",

    "id_document": """{
  "summary": "Brief description in user's language",
  "key_points": ["Document holder: Name", "Document type: Passport/HKID/Visa/Driving License"],
  "important_dates": [{"label": "Expiry date", "date": "2030-01-01", "days_until": 1368}],
  "red_flags": [],
  "action_items": ["Renew before expiry"],
  "id_details": {
    "document_type": "passport|hkid|visa|driving_license|other",
    "holder_name": "John Lee",
    "document_number": "H12345678",
    "nationality": "Hong Kong SAR",
    "issue_date": "2020-01-01",
    "expiry_date": "2030-01-01"
  }
}""",

    "utility": """{
  "summary": "Brief description in user's language",
  "key_points": [],
  "important_dates": [{"label": "Payment due", "date": "2026-04-30", "days_until": 27}],
  "red_flags": [],
  "action_items": ["Pay $X by date"],
  "transactions": [
    {"date": "2026-04-01", "amount": -350.00, "merchant": "CLP Power", "category": "utilities", "description": "Electricity bill Mar 2026"}
  ]
}""",

    "tax": """{
  "summary": "2-3 paragraph summary in the user's language",
  "key_points": ["point 1", "point 2", "point 3"],
  "important_dates": [{"label": "Filing deadline", "date": "2026-06-30", "days_until": 88}],
  "red_flags": [],
  "action_items": ["File by deadline", "Pay tax of $X"],
  "tax_details": {
    "tax_year": "2025-26",
    "total_income": 500000,
    "total_deductions": 50000,
    "tax_payable": 30000,
    "currency": "HKD",
    "filing_deadline": "2026-06-30"
  }
}""",

    "school": """{
  "summary": "Brief description in user's language",
  "key_points": ["point 1", "point 2"],
  "important_dates": [{"label": "Sports Day", "date": "2026-08-11", "days_until": 130}],
  "red_flags": [],
  "action_items": ["Prepare white T-shirt and blue shorts", "Bring water bottle"],
  "event": {
    "event_name": "Sports Day",
    "date": "2026-08-11",
    "time": "14:00",
    "end_time": null,
    "location": "School playground",
    "organizer": "ABC Primary School",
    "student_name": "Tommy Lee",
    "what_to_bring": ["White T-shirt", "Blue shorts", "Water bottle", "Sunscreen"],
    "what_to_wear": "White T-shirt and blue shorts",
    "rsvp_required": false,
    "rsvp_deadline": null,
    "fee": null,
    "notes": "Parents welcome to attend. Arrive 15 min early."
  }
}
Extract ALL actionable details: what to wear, what to bring, where to go, what time, any fees, RSVP deadlines. These will be sent as reminders.""",

    "travel": """{
  "summary": "Brief description in user's language",
  "key_points": ["Flight details", "Booking reference"],
  "important_dates": [{"label": "Departure", "date": "2026-07-15", "days_until": 103}],
  "red_flags": [],
  "action_items": ["Check in online 24h before", "Arrive at airport by 10:00"],
  "travel": {
    "travel_type": "flight|train|bus|ferry|other",
    "booking_reference": "ABC123",
    "provider": "Cathay Pacific",
    "route": "Hong Kong → Tokyo Narita",
    "departure_date": "2026-07-15",
    "departure_time": "12:30",
    "arrival_date": "2026-07-15",
    "arrival_time": "17:45",
    "departure_terminal": "Terminal 1",
    "seat": "23A",
    "class": "Economy",
    "passengers": ["John Lee", "Mary Lee"],
    "baggage_allowance": "30kg checked + 7kg cabin",
    "check_in_deadline": "2026-07-14T12:30",
    "cancellation_policy": "Non-refundable",
    "notes": "Meal included. Online check-in opens 48h before."
  }
}
Extract ALL travel details: times, terminals, seats, baggage, passengers, booking ref.""",

    "hotel": """{
  "summary": "Brief description in user's language",
  "key_points": ["Hotel name", "Check-in/out dates", "Confirmation number"],
  "important_dates": [
    {"label": "Check-in", "date": "2026-07-15", "days_until": 103},
    {"label": "Check-out", "date": "2026-07-20", "days_until": 108},
    {"label": "Free cancellation deadline", "date": "2026-07-10", "days_until": 98}
  ],
  "red_flags": [{"clause": "Non-refundable after Jul 10", "severity": "medium", "detail": "Cancellation after this date = full charge"}],
  "action_items": ["Cancel before Jul 10 for free cancellation"],
  "hotel": {
    "hotel_name": "Hilton Tokyo",
    "address": "6-6-2 Nishi-Shinjuku, Tokyo",
    "confirmation_number": "CONF-789456",
    "check_in_date": "2026-07-15",
    "check_in_time": "15:00",
    "check_out_date": "2026-07-20",
    "check_out_time": "11:00",
    "room_type": "Twin Room",
    "guests": ["John Lee", "Mary Lee"],
    "total_cost": 150000,
    "currency": "JPY",
    "payment_status": "Paid in full",
    "cancellation_deadline": "2026-07-10",
    "cancellation_policy": "Free cancellation before Jul 10. Full charge after.",
    "breakfast_included": true,
    "notes": "Late check-out available on request."
  }
}
Extract ALL hotel details: confirmation number, cancellation deadline & policy, costs, breakfast, room type.""",

    "event": """{
  "summary": "Brief description in user's language",
  "key_points": ["Event name", "Date and time", "Location"],
  "important_dates": [{"label": "Event date", "date": "2026-06-15", "days_until": 73}],
  "red_flags": [],
  "action_items": ["RSVP by deadline", "Prepare items to bring"],
  "event": {
    "event_name": "Annual Dinner",
    "date": "2026-06-15",
    "time": "19:00",
    "end_time": "22:00",
    "location": "Grand Ballroom, JW Marriott",
    "organizer": "ABC Company",
    "what_to_bring": [],
    "what_to_wear": "Smart casual / Business attire",
    "rsvp_required": true,
    "rsvp_deadline": "2026-06-01",
    "fee": 500,
    "currency": "HKD",
    "notes": "Parking available. Vegetarian options available on request."
  }
}
Extract ALL event details: time, location, dress code, what to bring, RSVP deadline, fees.""",
}

# Default schema for doc types without a specific one
DEFAULT_EXTRACTION_SCHEMA = """{
  "summary": "2-3 paragraph summary in the user's language",
  "key_points": ["point 1", "point 2", "point 3"],
  "important_dates": [{"label": "Event", "date": "2026-05-01", "days_until": 28}],
  "red_flags": [],
  "action_items": []
}"""

