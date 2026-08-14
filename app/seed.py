"""
Seed data injection.
Inserts 2 realistic patient records on startup if the patients table is empty.
"""

import uuid
from datetime import date, datetime, timezone

from sqlmodel import Session, select

from app.database import engine
from app.models import Patient


def seed_patients():
    """Insert seed records only if the patients table is empty."""
    with Session(engine) as session:
        count = session.exec(select(Patient)).first()
        if count is not None:
            # Table already has data, skip seeding
            return

        seed_records = [
            Patient(
                patient_id=uuid.uuid4(),
                first_name="Jane",
                last_name="Doe",
                date_of_birth=date(1985, 3, 15),
                sex="Female",
                phone_number="5550100000",
                email="jane.doe@example.com",
                address_line_1="123 Main St",
                address_line_2="Apt 4B",
                city="New York",
                state="NY",
                zip_code="10001",
                insurance_provider="Blue Cross Blue Shield",
                insurance_member_id="BCBS123456",
                preferred_language="English",
                emergency_contact_name="John Doe",
                emergency_contact_phone="5550100001",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Patient(
                patient_id=uuid.uuid4(),
                first_name="John",
                last_name="Smith",
                date_of_birth=date(1990, 7, 22),
                sex="Male",
                phone_number="5550200000",
                email="john.smith@example.com",
                address_line_1="456 Oak Ave",
                address_line_2=None,
                city="Los Angeles",
                state="CA",
                zip_code="90001",
                insurance_provider="Aetna",
                insurance_member_id="AET789012",
                preferred_language="English",
                emergency_contact_name="Mary Smith",
                emergency_contact_phone="5550200001",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        for patient in seed_records:
            session.add(patient)
        session.commit()
        print("[OK] Seeded 2 patient records into database.")
