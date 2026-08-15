"""
Patient data model (SQLModel table) and Pydantic schemas.

- Patient: SQLModel table for the database
- PatientCreate: Input schema for POST /patients
- PatientUpdate: Input schema for PUT /patients/{id} (all fields optional)
- PatientRead: Output schema for API responses
- APIResponse: Strict envelope wrapper for every response
"""

import re
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional, TypeVar

from pydantic import EmailStr, field_serializer, field_validator
from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Valid 2-letter US state abbreviations
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

# Regex patterns
NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z'-]{0,49}$")
PHONE_PATTERN = re.compile(r"^\d{10}$")
ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SexEnum(str, Enum):
    """Sex enum with exact casing as required by the assessment PDF."""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE = "Decline to Answer"


# ---------------------------------------------------------------------------
# Database Model
# ---------------------------------------------------------------------------


class Patient(SQLModel, table=True):
    """Patient table in the database."""
    __tablename__ = "patients"

    patient_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    date_of_birth: date  # Proper DATE column in PostgreSQL
    sex: str = Field(max_length=25)
    phone_number: str = Field(max_length=10)
    email: Optional[str] = Field(default=None, max_length=255)
    address_line_1: str = Field(max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(max_length=100)
    state: str = Field(max_length=2, sa_column=Column(String(2)))
    zip_code: str = Field(max_length=10)
    insurance_provider: Optional[str] = Field(default=None, max_length=255)
    insurance_member_id: Optional[str] = Field(default=None, max_length=255)
    preferred_language: str = Field(default="English", max_length=50)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=10)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Optional[datetime] = Field(default=None)


US_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}

# ---------------------------------------------------------------------------
# Shared Validation Helpers
# ---------------------------------------------------------------------------

def _validate_name(value: str, field_name: str) -> str:
    """Validate a name field: 1-50 chars, alphabetic + hyphens/apostrophes."""
    clean = value.strip() if isinstance(value, str) else ""
    if not NAME_PATTERN.match(clean):
        raise ValueError(
            f"{field_name} must be 1-50 characters and contain only "
            f"letters, hyphens, and apostrophes"
        )
    return clean


def _validate_phone(value: str) -> str:
    """Validate phone number: strips formatting down to exactly 10 digits."""
    if not value or not isinstance(value, str):
        raise ValueError("Phone number is required")
    # Clean out spaces, dashes, parens, plus signs
    cleaned = re.sub(r"[^\d]", "", value)
    if len(cleaned) == 11 and cleaned.startswith("1"):
        cleaned = cleaned[1:]
    if not PHONE_PATTERN.match(cleaned):
        raise ValueError("Phone number must be exactly 10 digits (e.g. 5551234567)")
    return cleaned


def _validate_dob(value: Any) -> date:
    """
    Parse date_of_birth from multiple string formats to datetime.date.
    Rejects future dates.
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        val_clean = value.strip()
        parsed = None
        # Try common formats that LLMs might output
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                parsed = datetime.strptime(val_clean, fmt).date()
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError(
                "date_of_birth must be a valid date in MM/DD/YYYY format"
            )
    else:
        raise ValueError(
            "date_of_birth must be a string in MM/DD/YYYY format"
        )

    if parsed > date.today():
        raise ValueError("date_of_birth cannot be in the future")
    return parsed


def _validate_sex(value: str) -> str:
    """Validate and normalize sex against exact enum values."""
    if not value or not isinstance(value, str):
        raise ValueError("sex is required")
    val_lower = value.strip().lower()
    for e in SexEnum:
        if e.value.lower() == val_lower:
            return e.value
    if "decline" in val_lower or "prefer not" in val_lower:
        return SexEnum.DECLINE.value
    valid = [e.value for e in SexEnum]
    raise ValueError(f"sex must be one of: {', '.join(valid)}")


def _validate_state(value: str) -> str:
    """Validate and normalize US state to 2-letter uppercase abbreviation."""
    if not value or not isinstance(value, str):
        raise ValueError("state is required")
    val_clean = value.strip().lower()
    if val_clean.upper() in US_STATES:
        return val_clean.upper()
    if val_clean in US_STATE_NAMES:
        return US_STATE_NAMES[val_clean]
    raise ValueError("state must be a valid 2-letter US state abbreviation (e.g. CA, NY, TX)")


def _validate_zip(value: str) -> str:
    """Validate ZIP code: 5-digit or ZIP+4 format."""
    clean = value.strip() if isinstance(value, str) else ""
    if not ZIP_PATTERN.match(clean):
        raise ValueError("zip_code must be 5-digit (12345) or ZIP+4 (12345-6789) format")
    return clean


# ---------------------------------------------------------------------------
# Input Schema: Create
# ---------------------------------------------------------------------------


class PatientCreate(SQLModel):
    """Schema for POST /patients — all required fields enforced."""

    first_name: str
    last_name: str
    date_of_birth: date  # Accepts MM/DD/YYYY string, converts to date
    sex: str
    phone_number: str
    email: Optional[EmailStr] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: str = "English"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    # --- Validators ---

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        return _validate_name(v, "first_name")

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: str) -> str:
        return _validate_name(v, "last_name")

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: Any) -> date:
        return _validate_dob(v)

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: str) -> str:
        return _validate_sex(v)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)

    @field_validator("address_line_1")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("address_line_1 is required and cannot be empty")
        return v.strip()

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("city is required and cannot be empty")
        if len(v.strip()) > 100:
            raise ValueError("city must be 1-100 characters")
        return v.strip()

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        return _validate_state(v)

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: str) -> str:
        return _validate_zip(v)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: Any) -> Optional[str]:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("emergency_contact_phone", mode="before")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str) and v.strip():
            return _validate_phone(v)
        return None


# ---------------------------------------------------------------------------
# Input Schema: Update (Partial)
# ---------------------------------------------------------------------------


class PatientUpdate(SQLModel):
    """Schema for PUT /patients/{id} — all fields optional for partial updates."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    # --- Validators (same rules, only applied when field is provided) ---

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_name(v, "first_name")
        return v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_name(v, "last_name")
        return v

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: Any) -> Optional[date]:
        if v is not None:
            return _validate_dob(v)
        return v

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_sex(v)
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_phone(v)
        return v

    @field_validator("address_line_1")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("address_line_1 cannot be empty")
            return v.strip()
        return v

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("city cannot be empty")
            if len(v.strip()) > 100:
                raise ValueError("city must be 1-100 characters")
            return v.strip()
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_state(v)
        return v

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_zip(v)
        return v

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: Any) -> Optional[str]:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("emergency_contact_phone", mode="before")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str) and v.strip():
            return _validate_phone(v)
        return None


# ---------------------------------------------------------------------------
# Output Schema: Read
# ---------------------------------------------------------------------------


class PatientRead(SQLModel):
    """Schema for API responses — serializes date_of_birth as MM/DD/YYYY."""

    patient_id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    phone_number: str
    email: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: str
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    @field_serializer("date_of_birth")
    def serialize_dob(self, v: date, _info: Any) -> str:
        """Serialize date_of_birth back to MM/DD/YYYY for API responses."""
        return v.strftime("%m/%d/%Y")

    @field_serializer("patient_id")
    def serialize_id(self, v: uuid.UUID, _info: Any) -> str:
        """Serialize UUID to string."""
        return str(v)


# ---------------------------------------------------------------------------
# API Response Envelope
# ---------------------------------------------------------------------------

T = TypeVar("T")


class APIResponse(SQLModel):
    """
    Strict response envelope used for EVERY API response.
    { "data": <payload or null>, "error": <string or null> }
    """

    data: Optional[Any] = None
    error: Optional[str] = None
