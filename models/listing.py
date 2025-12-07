from __future__ import annotations

from typing import Optional
from datetime import date
from pydantic import BaseModel, Field, AnyHttpUrl, EmailStr


class ListingBase(BaseModel):
    """Shared fields for Listing (request/response)."""

    name: str = Field(..., description="Listing name.")
    address: str = Field(..., description="Listing address.")
    start_date: date = Field(..., description="Start date of availability.")
    end_date: Optional[date] = Field(
        None, description="End date of availability (nullable)."
    )
    description: Optional[str] = Field(
        None, description="Free-text description of the listing."
    )
    picture_url: Optional[AnyHttpUrl] = Field(
        None, description="URL to picture for this listing (optional)."
    )


class ListingCreate(ListingBase):
    """Payload for creating a listing."""

    landlord_email: EmailStr = Field(
        ..., description="Email of the landlord (FK to users)."
    )


class ListingUpdate(BaseModel):
    """
    Full/partial update for PUT /listing/{id}.
    All fields optional; id comes from path.
    """

    landlord_email: Optional[EmailStr] = None
    name: Optional[str] = None
    address: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    picture_url: Optional[AnyHttpUrl] = None


class ListingRead(ListingBase):
    """Representation returned to clients."""

    id: int = Field(..., description="Listing primary key.")
    landlord_email: EmailStr = Field(
        ..., description="Email of the landlord who owns this listing."
    )