from __future__ import annotations

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, AnyHttpUrl


class ListingBase(BaseModel):
    """Shared fields for listing request/response."""

    name: Optional[str] = Field(
        None,
        description="Name/title of the listing.",
        json_schema_extra={"example": "Cozy studio near campus"},
    )
    address: Optional[str] = Field(
        None,
        description="Street address of the listing.",
        json_schema_extra={"example": "123 College Ave"},
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Availability start date (UTC).",
        json_schema_extra={"example": "2025-09-01"},
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Availability end date (UTC).",
        json_schema_extra={"example": "2026-05-31"},
    )
    description: Optional[str] = Field(
        None,
        description="Free-text description of the listing.",
        json_schema_extra={"example": "Quiet neighborhood, 5 min walk to campus."},
    )
    picture_url: Optional[AnyHttpUrl] = Field(
        None,
        description="URL to listing picture (optional).",
        json_schema_extra={"example": "https://example.com/listings/1.jpg"},
    )


class ListingCreate(ListingBase):
    """Payload for creating a listing."""

    landlord_email: EmailStr = Field(
        ...,
        description="Email of the landlord (foreign key to users).",
        json_schema_extra={"example": "owner@example.com"},
    )


class ListingUpdate(BaseModel):
    """
    Payload for PUT /listing/{listing_id}.
    You said PUT is not implemented yet (501), but when you do implement it,
    this model lets you do full or partial updates.
    """

    landlord_email: Optional[EmailStr] = None
    name: Optional[str] = None
    address: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    description: Optional[str] = None
    picture_url: Optional[AnyHttpUrl] = None


class ListingRead(ListingBase):
    """Representation returned to clients."""

    id: int = Field(
        ...,
        description="Primary key of the listing.",
        json_schema_extra={"example": 1},
    )
    landlord_email: EmailStr = Field(
        ...,
        description="Email of the landlord who owns this listing.",
        json_schema_extra={"example": "owner@example.com"},
    )
