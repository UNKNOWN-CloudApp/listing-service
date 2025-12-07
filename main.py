from typing import List, Optional
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Query, Path, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import MySQLConnection
from fastapi.encoders import jsonable_encoder

from utils.database import get_db         
from models.listing import ListingCreate, ListingRead, ListingUpdate

app = FastAPI(
    title="Listing Service",
    version="1.0.0",
    description="Listing microservice backed by MySQL",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# helpers
def row_to_listing(row: dict) -> ListingRead:
    """Convert a DB row from `listings` into ListingRead."""
    return ListingRead(
        id=row["id"],
        landlord_email=row["landlord_email"],
        name=row["name"],
        address=row["address"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        description=row.get("description"),
        picture_url=row.get("picture_url"),
    )

@app.post("/listing", response_model=ListingRead, status_code=201)
def create_listing(
    payload: ListingCreate,
    db: MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()

    sql = """
        INSERT INTO listings (
            landlord_email,
            name,
            address,
            start_date,
            end_date,
            description,
            picture_url
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        payload.landlord_email,
        payload.name,
        payload.address,
        payload.start_date,
        payload.end_date,
        payload.description,
        str(payload.picture_url) if payload.picture_url else None,
    )

    cursor.execute(sql, values)
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()

    # Fetch to return ListingRead
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM listings WHERE id = %s", (new_id,))
    row = cursor.fetchone()
    cursor.close()

    return row_to_listing(row)

from typing import List

@app.get("/listing", response_model=List[ListingRead])
async def search_listings(
    # ---- filters (all optional) ----
    landlord_email: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    address: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),

    # ---- pagination ----
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),

    db: MySQLConnection = Depends(get_db),
):
    sql = "SELECT * FROM listings WHERE 1=1"
    params = []

    # ---- dynamic filters ----
    if landlord_email:
        sql += " AND landlord_email = %s"
        params.append(landlord_email)

    if name:
        sql += " AND name LIKE %s"
        params.append(f"%{name}%")

    if address:
        sql += " AND address LIKE %s"
        params.append(f"%{address}%")

    if start_date:
        sql += " AND start_date >= %s"
        params.append(start_date)

    if end_date:
        # if you want open-ended listings to still show, you can drop the IS NULL part
        sql += " AND (end_date IS NULL OR end_date <= %s)"
        params.append(end_date)

    # ---- pagination ----
    offset = (page - 1) * page_size
    sql += " ORDER BY id DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])

    cursor = db.cursor(dictionary=True)
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    cursor.close()

    return [row_to_listing(row) for row in rows]

@app.get("/listing/user/{landlord_email}", response_model=List[ListingRead])
def list_listings_by_landlord(
    landlord_email: str,
    db: MySQLConnection = Depends(get_db),
):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM listings WHERE landlord_email = %s", (landlord_email,)
    )
    rows = cursor.fetchall()
    cursor.close()

    return [row_to_listing(r) for r in rows]

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

@app.put("/listing/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: MySQLConnection = Depends(get_db),
):
    raise HTTPException(status_code=501, detail="PUT not implemented yet")

# -----------------------------------------------------------------------------
# Root
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Listing Service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
