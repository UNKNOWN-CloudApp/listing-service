from typing import List, Optional
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Query, Path, UploadFile, File
from mysql.connector import MySQLConnection
from fastapi.encoders import jsonable_encoder

from utils.database import get_db         
from models.listing import ListingCreate, ListingRead  

app = FastAPI(
    title="Listing Service",
    version="1.0.0",
    description="Listing microservice backed by MySQL",
)

# helpers
def row_to_listing(row: dict) -> ListingRead:
    """Convert a DB row dict from `listings` into a ListingRead Pydantic object."""
    public_transport = (
        row["public_transport_info"].split(",")
        if row.get("public_transport_info")
        else []
    )

    return ListingRead(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        address=row["address"],
        city=row["city"],
        state=row["state"],
        zipcode=row["zipcode"],
        distance_from_campus_km=float(row["distance_from_campus_km"]),
        public_transportation=public_transport,
        price_per_month=float(row["price_monthly"]),
        available_from=row["available_from"],
        available_to=row["available_to"],
        room_type=row["room_type"],  # adjust if your enum uses different values
        gender_neutral=bool(row["gender_neutral"]),
        utilities_included=bool(row["utilities_included"]),
        ac_heater_included=bool(row["ac_included"] or row["heater_included"]),
        furnished=bool(row["furnished"]),
        pet_allowed=bool(row["pets_allowed"]),
        kitchen=bool(row["kitchen_available"]),
        availability_status=row["availability_status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        image_urls=[],  
    )

@app.post("/listing", response_model=ListingRead, status_code=201)
def create_listing(
    payload: ListingCreate,
    db: MySQLConnection = Depends(get_db),
):
    raise HTTPException(status_code=501, detail="Not implemented yet")


@app.get("/listing/{listing_id}")
def get_listing_debug(
    listing_id: int = Path(..., ge=1),
    db: MySQLConnection = Depends(get_db),
):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            raise HTTPException(status_code=404, detail="Listing not found")

        # Convert Decimal/date to JSON-friendly types
        return jsonable_encoder(row)
    except Exception as e:
        print("ERROR in get_listing:", repr(e))
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.put("/listing/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: int,
    payload: ListingCreate,  # or a separate ListingUpdate model if you have one
    db: MySQLConnection = Depends(get_db),
):
    # Ensure it exists
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    existing = cursor.fetchone()
    cursor.close()

    if not existing:
        raise HTTPException(status_code=404, detail="Listing not found")

    cursor = db.cursor()

    sql = """
        UPDATE listings
        SET
            title = %s,
            description = %s,
            address = %s,
            city = %s,
            state = %s,
            zipcode = %s,
            distance_from_campus_km = %s,
            public_transport_info = %s,
            price_monthly = %s,
            available_from = %s,
            available_to = %s,
            room_type = %s,
            gender_neutral = %s,
            utilities_included = %s,
            ac_included = %s,
            heater_included = %s,
            furnished = %s,
            pets_allowed = %s,
            kitchen_available = %s
        WHERE id = %s
    """

    public_transport_info = ",".join(payload.public_transportation or [])

    values = (
        payload.title,
        payload.description,
        payload.address,
        payload.city,
        payload.state,
        payload.zipcode,
        payload.distance_from_campus_km,
        public_transport_info,
        payload.price_per_month,
        payload.available_from,
        payload.available_to,
        payload.room_type,
        payload.gender_neutral,
        payload.utilities_included,
        payload.ac_heater_included,
        False,
        payload.furnished,
        payload.pet_allowed,
        payload.kitchen,
        listing_id,
    )

    cursor.execute(sql, values)
    db.commit()
    cursor.close()

    return get_listing(listing_id, db)


@app.delete("/listing/{listing_id}")
def delete_listing(
    listing_id: int,
    db: MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute("DELETE FROM listings WHERE id = %s", (listing_id,))
    db.commit()
    deleted = cursor.rowcount
    cursor.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Listing not found")

    return {"message": "Listing deleted successfully"}

@app.get("/listing")
def search_listings(db: MySQLConnection = Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM listings")
        rows = cursor.fetchall()
        cursor.close()

        return rows

    except Exception as e:
        print("ERROR IN /listing:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/listing/{listing_id}/a", response_model=ListingRead)
def update_availability(
    listing_id: int,
    available_from: Optional[date] = Query(None),
    available_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: MySQLConnection = Depends(get_db),
):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    existing = cursor.fetchone()
    cursor.close()

    if not existing:
        raise HTTPException(status_code=404, detail="Listing not found")

    fields = []
    params: list = []

    if available_from is not None:
        fields.append("available_from = %s")
        params.append(available_from)
    if available_to is not None:
        fields.append("available_to = %s")
        params.append(available_to)
    if status is not None:
        fields.append("availability_status = %s")
        params.append(status)

    if fields:
        sql = "UPDATE listings SET " + ", ".join(fields) + " WHERE id = %s"
        params.append(listing_id)
        cursor = db.cursor()
        cursor.execute(sql, tuple(params))
        db.commit()
        cursor.close()

    return get_listing(listing_id, db)


@app.post("/listing/{listing_id}/images")
def upload_images(
    listing_id: int,
    files: List[UploadFile] = File(...),
    db: MySQLConnection = Depends(get_db),
):
    fake_urls = [f"https://example.com/images/{listing_id}/{f.filename}" for f in files]
    return {"listing_id": listing_id, "uploaded": fake_urls}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
