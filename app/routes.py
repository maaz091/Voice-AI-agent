"""
REST API endpoints for Patient CRUD operations.

All responses use the strict envelope: { "data": ..., "error": ... }
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    APIResponse,
    Patient,
    PatientCreate,
    PatientRead,
    PatientUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: Convert Patient DB model to PatientRead dict
# ---------------------------------------------------------------------------

def _patient_to_read(patient: Patient) -> dict:
    """Convert a Patient ORM object to a PatientRead-serialized dict."""
    read = PatientRead.model_validate(patient)
    return read.model_dump(mode="json")


# ---------------------------------------------------------------------------
# GET /patients — List all (with optional filters)
# ---------------------------------------------------------------------------

@router.get("/patients", response_model=APIResponse)
def list_patients(
    last_name: Optional[str] = Query(None, description="Filter by last name"),
    date_of_birth: Optional[str] = Query(None, description="Filter by DOB (MM/DD/YYYY)"),
    phone_number: Optional[str] = Query(None, description="Filter by phone (10 digits)"),
    session: Session = Depends(get_session),
):
    """List all non-deleted patients. Supports optional query filters."""
    statement = select(Patient).where(Patient.deleted_at == None)  # noqa: E711

    if last_name:
        statement = statement.where(Patient.last_name == last_name)
    if date_of_birth:
        # Parse the filter date from MM/DD/YYYY string
        try:
            from datetime import datetime as dt
            filter_date = dt.strptime(date_of_birth, "%m/%d/%Y").date()
            statement = statement.where(Patient.date_of_birth == filter_date)
        except ValueError:
            return JSONResponse(
                status_code=422,
                content={"data": None, "error": "date_of_birth filter must be in MM/DD/YYYY format"},
            )
    if phone_number:
        statement = statement.where(Patient.phone_number == phone_number)

    patients = session.exec(statement).all()
    return {"data": [_patient_to_read(p) for p in patients], "error": None}


# ---------------------------------------------------------------------------
# GET /patients/{id} — Get by UUID
# ---------------------------------------------------------------------------

@router.get("/patients/{patient_id}", response_model=APIResponse)
def get_patient(
    patient_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    """Retrieve a single patient by UUID. Returns 404 if not found or soft-deleted."""
    patient = session.get(Patient, patient_id)

    if patient is None or patient.deleted_at is not None:
        return JSONResponse(
            status_code=404,
            content={"data": None, "error": f"Patient with id '{patient_id}' not found"},
        )

    return {"data": _patient_to_read(patient), "error": None}


# ---------------------------------------------------------------------------
# POST /patients — Create
# ---------------------------------------------------------------------------

@router.post("/patients", response_model=APIResponse, status_code=201)
def create_patient(
    patient_data: PatientCreate,
    session: Session = Depends(get_session),
):
    """
    Create a new patient record.
    Logs the incoming data payload to stdout for observability.
    """
    # Observability: Log incoming payload
    logger.info(f"CREATE PATIENT - Incoming payload: {patient_data.model_dump()}")

    # Create the Patient ORM object from validated data
    patient = Patient(
        **patient_data.model_dump(),
        patient_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session.add(patient)
    session.commit()
    session.refresh(patient)

    logger.info(f"Patient created: {patient.patient_id} - {patient.first_name} {patient.last_name}")

    return JSONResponse(
        status_code=201,
        content={"data": _patient_to_read(patient), "error": None},
    )


# ---------------------------------------------------------------------------
# PUT /patients/{id} — Partial Update
# ---------------------------------------------------------------------------

@router.put("/patients/{patient_id}", response_model=APIResponse)
def update_patient(
    patient_id: uuid.UUID,
    patient_data: PatientUpdate,
    session: Session = Depends(get_session),
):
    """Update an existing patient record. Partial updates allowed."""
    patient = session.get(Patient, patient_id)

    if patient is None or patient.deleted_at is not None:
        return JSONResponse(
            status_code=404,
            content={"data": None, "error": f"Patient with id '{patient_id}' not found"},
        )

    # Only update fields that were actually provided and are not None
    update_data = patient_data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        return {"data": _patient_to_read(patient), "error": None}

    for key, value in update_data.items():
        setattr(patient, key, value)

    # Always update the timestamp on modification
    patient.updated_at = datetime.now(timezone.utc)

    session.add(patient)
    session.commit()
    session.refresh(patient)

    logger.info(f"Patient updated: {patient.patient_id} - fields: {list(update_data.keys())}")

    return {"data": _patient_to_read(patient), "error": None}


# ---------------------------------------------------------------------------
# DELETE /patients/{id} — Soft Delete
# ---------------------------------------------------------------------------

@router.delete("/patients/{patient_id}", response_model=APIResponse)
def delete_patient(
    patient_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    """Soft-delete a patient record by setting deleted_at timestamp."""
    patient = session.get(Patient, patient_id)

    if patient is None or patient.deleted_at is not None:
        return JSONResponse(
            status_code=404,
            content={"data": None, "error": f"Patient with id '{patient_id}' not found"},
        )

    patient.deleted_at = datetime.now(timezone.utc)
    patient.updated_at = datetime.now(timezone.utc)

    session.add(patient)
    session.commit()

    logger.info(f"Patient soft-deleted: {patient_id}")

    return {"data": None, "error": None}
