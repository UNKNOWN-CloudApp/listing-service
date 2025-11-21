from __future__ import annotations

import os
import socket
from datetime import datetime
from typing import Optional, List

from fastapi import (
    FastAPI,
    HTTPException,
    Path,
    Query,
    UploadFile,
    File,
)
import uvicorn

from models.listing import ListingCreate, ListingRead, ListingUpdate, AvailabilityPatch


port = int(os.environ.get("FASTAPIPORT", 8000))

app = FastAPI(
    title="Listing Service",
    description="Student housing listing microservice (simple in-memory implementation).",
    version="1.0.0",
)

# -----------------------------------------------------------------------------
# In-memory storage (for demo / assignment)
# -----------------------------------------------------------------------------
LISTINGS_DB: dict[int, ListingRead] = {}
NEXT_ID: int = 1


def next_listing_id() -> int:
    global NEXT_ID
    nid = NEXT_ID
    NEXT_ID += 1
    return nid


# -----------------------------------------------------------------------------
# Listing endpoints
#   - Create / read / update / delete listings
#   - Search with filters
#   - Upload images
#   - Patch availability window
# -----------------------------------------------------------------------------
@app.post("/listing", response_model=ListingRead, status_code=201)
def create_listing(payload: ListingCreate):
    """
    Create a new listing.
    """
    listing_id = next_listing_id()
    now = datetime.utcnow()

    listing = ListingRead(
        id=listing_id,
        created_at=now,
        updated_at=now,
        image_urls=[],
        **payload.model_dump(),
    )
    LISTINGS_DB[listing_id] = listing
    return listing


@app.get("/listing")
def search_listings(
    address: Optional[str] = Query(
        None,
        description="Full or partial address match.",
    ),
    min_distance_km: Optional[float] = Query(
        None,
        ge=0,
        alias="minDistanceKm",
        description="Minimum distance from campus (km).",
    ),
    max_distance_km: Optional[float] = Query(
        None,
        ge=0,
        alias="maxDistanceKm",
        description="Maximum distance from campus (km).",
    ),
    public_transportation: Optional[List[str]] = Query(
        None,
        alias="publicTransportation",
        description="One or more transit options (e.g., Subway A, Bus M5).",
    ),
    min_price: Optional[float] = Query(
        None,
        ge=0,
        alias="minPrice",
        description="Minimum monthly price.",
    ),
    max_price: Optional[float] = Query(
        None,
        ge=0,
        alias="maxPrice",
        description="Maximum monthly price.",
    ),
    room_type: Optional[str] = Query(
        None,
        alias="roomType",
        description="Room type filter.",
    ),
    gender_neutral: Optional[bool] = Query(
        None,
        alias="genderNeutral",
        description="Filter by gender-neutral flag.",
    ),
    utilities_included: Optional[bool] = Query(
        None,
        alias="utilitiesIncluded",
        description="Filter by utilities-included flag.",
    ),
    ac_heater_included: Optional[bool] = Query(
        None,
        alias="acHeaterIncluded",
        description="Filter by AC/heater-included flag.",
    ),
    furnished: Optional[bool] = Query(
        None,
        alias="furnished",
        description="Filter by furnished flag.",
    ),
    pet_allowed: Optional[bool] = Query(
        None,
        alias="petAllowed",
        description="Filter by pet-allowed flag.",
    ),
    kitchen: Optional[bool] = Query(
        None,
        alias="kitchen",
        description="Filter by kitchen flag.",
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-based).",
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        alias="pageSize",
        description="Page size.",
    ),
    sort: str = Query(
        "pricePerMonth",
        description=(
            "Sort field, e.g. pricePerMonth, -pricePerMonth, "
            "distanceFromCampusKm, -distanceFromCampusKm"
        ),
    ),
):
    """
    Search listings with basic filtering & pagination.
    """
    results: List[ListingRead] = list(LISTINGS_DB.values())

    # Filtering
    def matches(l: ListingRead) -> bool:
        if address and address.lower() not in l.address.lower():
            return False

        if min_distance_km is not None and l.distance_from_campus_km is not None:
            if l.distance_from_campus_km < min_distance_km:
                return False
        if max_distance_km is not None and l.distance_from_campus_km is not None:
            if l.distance_from_campus_km > max_distance_km:
                return False

        if public_transportation:
            if not set(public_transportation).intersection(
                set(l.public_transportation or [])
            ):
                return False

        if min_price is not None and l.price_per_month < min_price:
            return False
        if max_price is not None and l.price_per_month > max_price:
            return False

        if room_type and l.room_type != room_type:
            return False

        if gender_neutral is not None and l.gender_neutral != gender_neutral:
            return False
        if utilities_included is not None and l.utilities_included != utilities_included:
            return False
        if ac_heater_included is not None and l.ac_heater_included != ac_heater_included:
            return False
        if furnished is not None and l.furnished != furnished:
            return False
        if pet_allowed is not None and l.pet_allowed != pet_allowed:
            return False
        if kitchen is not None and l.kitchen != kitchen:
            return False

        return True

    results = [l for l in results if matches(l)]

    # Sorting
    sort_reverse = sort.startswith("-")
    sort_field = sort[1:] if sort_reverse else sort

    def sort_key(l: ListingRead):
        # Map sort_field names from OpenAPI to Pydantic attributes
        mapping = {
            "pricePerMonth": "price_per_month",
            "distanceFromCampusKm": "distance_from_campus_km",
            "availableFrom": "available_from",
            "availableTo": "available_to",
        }
        attr = mapping.get(sort_field, None)
        if not attr:
            return 0
        val = getattr(l, attr)
        return (val is None, val)

    if sort_field in {
        "pricePerMonth",
        "distanceFromCampusKm",
        "availableFrom",
        "availableTo",
    }:
        results.sort(key=sort_key, reverse=sort_reverse)

    # Pagination
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    paged = results[start:end]

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": paged,
    }


@app.get("/listing/{listing_id}", response_model=ListingRead)
def get_listing(
    listing_id: int = Path(..., ge=1, description="Listing ID"),
):
    """
    Get listing by ID.
    """
    listing = LISTINGS_DB.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@app.put("/listing/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: int = Path(..., ge=1, description="Listing ID"),
    payload: ListingUpdate = ...,
):
    """
    Full update of a listing (PUT).
    """
    existing = LISTINGS_DB.get(listing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Listing not found")

    data = payload.model_dump(exclude_unset=True)
    updated = existing.model_copy(
        update={
            **data,
            "updated_at": datetime.utcnow(),
        }
    )
    LISTINGS_DB[listing_id] = updated
    return updated


@app.delete("/listing/{listing_id}")
def delete_listing(
    listing_id: int = Path(..., ge=1, description="Listing ID"),
):
    """
    Delete a listing.
    """
    if listing_id not in LISTINGS_DB:
        raise HTTPException(status_code=404, detail="Listing not found")
    del LISTINGS_DB[listing_id]
    return {"message": "Listing deleted."}


@app.post("/listing/{listing_id}/images")
async def upload_images(
    listing_id: int = Path(..., ge=1, description="Listing ID"),
    files: List[UploadFile] = File(..., description="One or more image files."),
):
    """
    Upload one or more images for a listing.
    """
    listing = LISTINGS_DB.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Fake public URLs for demo
    host = socket.gethostname()
    uploaded_urls: List[str] = [
        f"https://cdn.example.com/listings/{listing_id}/{f.filename}"
        for f in files
    ]

    updated = listing.model_copy(
        update={
            "image_urls": list(listing.image_urls) + uploaded_urls,
            "updated_at": datetime.utcnow(),
        }
    )
    LISTINGS_DB[listing_id] = updated

    return {"uploaded": uploaded_urls}


@app.patch("/listing/{listing_id}/a", response_model=ListingRead)
def patch_availability(
    listing_id: int = Path(..., ge=1, description="Listing ID"),
    payload: AvailabilityPatch = ...,
):
    """
    Update the availability window for a listing.
    """
    listing = LISTINGS_DB.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if payload.available_from is None and payload.available_to is None:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of available_from or available_to",
        )

    updated = listing.model_copy(
        update={
            **payload.model_dump(exclude_unset=True),
            "updated_at": datetime.utcnow(),
        }
    )
    LISTINGS_DB[listing_id] = updated
    return updated


# -----------------------------------------------------------------------------
# Root
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Listing Service (in-memory demo)",
        "port": port,
    }


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
