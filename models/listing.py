from __future__ import annotations

from typing import Optional, Literal, List
from datetime import date, datetime
from pydantic import BaseModel, Field, AnyHttpUrl


RoomType = Literal["STUDIO", "PRIVATE_ROOM", "SHARED_ROOM", "APARTMENT", "OTHER"]


class ListingBase(BaseModel):
    """Shared fields for a housing listing (request/response)."""

    address: str = Field(
        ...,
        description="Full street address for the listing.",
        json_schema_extra={"example": "123 College Ave, New York, NY"},
    )
    distance_from_campus_km: Optional[float] = Field(
        None,
        ge=0,
        description="Distance from campus in kilometers.",
        json_schema_extra={"example": 1.2},
    )
    public_transportation: Optional[List[str]] = Field(
        default_factory=list,
        description="Transit options near the listing.",
        json_schema_extra={"example": ["Subway 1", "Bus M4"]},
    )
    price_per_month: float = Field(
        ...,
        ge=0,
        description="Monthly rent price.",
        json_schema_extra={"example": 1500},
    )
    available_from: date = Field(
        ...,
        description="Start date the listing is available (UTC).",
        json_schema_extra={"example": "2025-11-01"},
    )
    available_to: Optional[date] = Field(
        None,
        description="End date the listing is available (UTC).",
        json_schema_extra={"example": "2026-05-31"},
    )
    room_type: RoomType = Field(
        ...,
        description="Type of room offered.",
        json_schema_extra={"example": "STUDIO"},
    )
    gender_neutral: bool = Field(
        True,
        description="Whether the listing is gender-neutral.",
        json_schema_extra={"example": True},
    )
    utilities_included: bool = Field(
        False,
        description="True if utilities are included in the price.",
        json_schema_extra={"example": True},
    )
    ac_heater_included: bool = Field(
        False,
        description="True if AC/heating is included.",
        json_schema_extra={"example": True},
    )
    furnished: bool = Field(
        False,
        description="True if the unit is furnished.",
        json_schema_extra={"example": True},
    )
    pet_allowed: bool = Field(
        False,
        description="True if pets are allowed.",
        json_schema_extra={"example": False},
    )
    kitchen: bool = Field(
        False,
        description="True if the unit has a kitchen.",
        json_schema_extra={"example": True},
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "address": "123 College Ave, New York, NY",
                    "distance_from_campus_km": 1.2,
                    "public_transportation": ["Subway A", "Bus M5"],
                    "price_per_month": 1500,
                    "available_from": "2025-11-01",
                    "available_to": "2026-05-31",
                    "room_type": "STUDIO",
                    "gender_neutral": True,
                    "utilities_included": True,
                    "ac_heater_included": True,
                    "furnished": True,
                    "pet_allowed": False,
                    "kitchen": True,
                }
            ]
        }
    }


class ListingCreate(ListingBase):
    """
    Creation payload for a listing.
    ID, created_at, updated_at, and image_urls are generated server-side.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "address": "456 Campus Rd, New York, NY",
                    "distance_from_campus_km": 0.8,
                    "public_transportation": ["Subway 1", "Bus M4"],
                    "price_per_month": 1800,
                    "available_from": "2025-09-01",
                    "available_to": "2026-05-31",
                    "room_type": "PRIVATE_ROOM",
                    "gender_neutral": True,
                    "utilities_included": True,
                    "ac_heater_included": True,
                    "furnished": True,
                    "pet_allowed": False,
                    "kitchen": True,
                }
            ]
        }
    }


class ListingUpdate(BaseModel):
    """
    Full listing update for PUT /listing/{id}.
    All fields optional; ID taken from path.
    """

    address: Optional[str] = Field(
        None,
        description="Updated address.",
        json_schema_extra={"example": "789 New Address Ave, New York, NY"},
    )
    distance_from_campus_km: Optional[float] = Field(
        None,
        ge=0,
        description="Updated distance from campus (km).",
        json_schema_extra={"example": 1.5},
    )
    public_transportation: Optional[List[str]] = Field(
        None,
        description="Updated transit options.",
        json_schema_extra={"example": ["Subway 1", "Bus M4"]},
    )
    price_per_month: Optional[float] = Field(
        None,
        ge=0,
        description="Updated monthly rent.",
        json_schema_extra={"example": 1600},
    )
    available_from: Optional[date] = Field(
        None,
        description="Updated availability start date.",
        json_schema_extra={"example": "2025-12-01"},
    )
    available_to: Optional[date] = Field(
        None,
        description="Updated availability end date.",
        json_schema_extra={"example": "2026-06-30"},
    )
    room_type: Optional[RoomType] = Field(
        None,
        description="Updated room type.",
        json_schema_extra={"example": "APARTMENT"},
    )
    gender_neutral: Optional[bool] = Field(
        None,
        description="Updated gender-neutral flag.",
        json_schema_extra={"example": True},
    )
    utilities_included: Optional[bool] = Field(
        None,
        description="Updated utilities-included flag.",
        json_schema_extra={"example": True},
    )
    ac_heater_included: Optional[bool] = Field(
        None,
        description="Updated AC/heater-included flag.",
        json_schema_extra={"example": True},
    )
    furnished: Optional[bool] = Field(
        None,
        description="Updated furnished flag.",
        json_schema_extra={"example": True},
    )
    pet_allowed: Optional[bool] = Field(
        None,
        description="Updated pet-allowed flag.",
        json_schema_extra={"example": False},
    )
    kitchen: Optional[bool] = Field(
        None,
        description="Updated kitchen flag.",
        json_schema_extra={"example": True},
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"price_per_month": 1600},
                {"address": "789 New Address Ave, New York, NY"},
                {
                    "available_from": "2025-12-01",
                    "available_to": "2026-06-30",
                },
                {
                    "furnished": True,
                    "pet_allowed": False,
                },
            ]
        }
    }


class ListingRead(ListingBase):
    """Representation returned to clients."""

    id: int = Field(
        ...,
        description="Listing ID (server-assigned).",
        json_schema_extra={"example": 42},
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp (UTC).",
        json_schema_extra={"example": "2025-01-10T12:00:00Z"},
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp (UTC).",
        json_schema_extra={"example": "2025-01-15T09:30:00Z"},
    )
    image_urls: List[AnyHttpUrl] = Field(
        default_factory=list,
        description="List of image URLs for the listing.",
        json_schema_extra={
            "example": [
                "https://cdn.example.com/listings/42/img1.jpg",
                "https://cdn.example.com/listings/42/img2.jpg",
            ]
        },
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 42,
                    "address": "123 College Ave, New York, NY",
                    "distance_from_campus_km": 1.2,
                    "public_transportation": ["Subway A", "Bus M5"],
                    "price_per_month": 1500,
                    "available_from": "2025-11-01",
                    "available_to": "2026-05-31",
                    "room_type": "STUDIO",
                    "gender_neutral": True,
                    "utilities_included": True,
                    "ac_heater_included": True,
                    "furnished": True,
                    "pet_allowed": False,
                    "kitchen": True,
                    "created_at": "2025-01-10T12:00:00Z",
                    "updated_at": "2025-01-15T09:30:00Z",
                    "image_urls": [
                        "https://cdn.example.com/listings/42/img1.jpg",
                        "https://cdn.example.com/listings/42/img2.jpg",
                    ],
                }
            ]
        }
    }


class AvailabilityPatch(BaseModel):
    """Partial update for availability window."""

    available_from: Optional[date] = Field(
        None,
        description="New availability start date.",
        json_schema_extra={"example": "2025-12-01"},
    )
    available_to: Optional[date] = Field(
        None,
        description="New availability end date.",
        json_schema_extra={"example": "2026-05-31"},
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"available_from": "2025-12-01"},
                {"available_to": "2026-05-31"},
                {
                    "available_from": "2025-12-01",
                    "available_to": "2026-05-31",
                },
            ]
        }
    }
