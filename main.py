import hashlib
import json
from typing import List, Optional
from datetime import date, datetime
from fastapi import (
    BackgroundTasks,
    FastAPI,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import MySQLConnection
import uuid

from pydantic import BaseModel

from utils.database import get_db         
from models.listing import ListingCreate, ListingRead, ListingUpdate
from models.bulk_create import (
    BulkListingCreate, 
    BulkCreateTaskResponse, 
    BulkCreateTaskStatus,
    store_bulk_create_task, 
    get_bulk_create_task,
    process_bulk_create_listings
)

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

# -----------------------------------------------------------------------------
# Hypermedia / Linked-data models
# -----------------------------------------------------------------------------

class ListingLinks(BaseModel):
    self: str
    landlord_listings: str


class ListingWithLinks(BaseModel):
    data: ListingRead
    _links: ListingLinks


class PaginatedLinks(BaseModel):
    self: str
    next: Optional[str] = None
    prev: Optional[str] = None


class PaginatedListingResponse(BaseModel):
    items: List[ListingWithLinks]
    page: int
    page_size: int
    _links: PaginatedLinks

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
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

def compute_etag_from_row(row: dict) -> str:
    """
    Compute a weak ETag from the DB row contents.

    If you have an `updated_at` column you can simplify this to:
        f'W/"{row["id"]}-{row["updated_at"].timestamp()}"'
    """
    # Only hash relevant fields to keep it stable and deterministic
    payload = json.dumps(
        {
            "id": row["id"],
            "landlord_email": row["landlord_email"],
            "name": row["name"],
            "address": row["address"],
            "start_date": str(row["start_date"]) if row.get("start_date") else None,
            "end_date": str(row["end_date"]) if row.get("end_date") else None,
            "description": row.get("description"),
            "picture_url": row.get("picture_url"),
        },
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    md5_hex = hashlib.md5(payload).hexdigest()
    return f'W/"{md5_hex}"'


def listing_with_links(row: dict) -> ListingWithLinks:
    """Wrap a DB row into ListingWithLinks with relative paths."""
    listing = row_to_listing(row)
    lid = listing.id
    landlord = listing.landlord_email
    return ListingWithLinks(
        data=listing,
        _links=ListingLinks(
            self=f"/listing/{lid}",
            landlord_listings=f"/listing/user/{landlord}",
        ),
    )

# -----------------------------------------------------------------------------
# POST /listing  (201 Created + Location)
# -----------------------------------------------------------------------------
@app.post("/listing", response_model=ListingRead, status_code=201)
def create_listing(
    payload: ListingCreate,
    response: Response,
    db: MySQLConnection = Depends(get_db),
):
    if payload.start_date >= payload.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )

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

    # Set Location header to the new resource's relative URL
    response.headers["Location"] = f"/listing/{new_id}"

    # Also set ETag for the created resource
    response.headers["ETag"] = compute_etag_from_row(row)

    return row_to_listing(row)


# -----------------------------------------------------------------------------
# GET /listing  (collection with filters, pagination, linked data)
# -----------------------------------------------------------------------------

@app.get("/listing", response_model=PaginatedListingResponse)
async def search_listings(
    # ---- filters (all optional) ----
    landlord_email: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    address: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),

    # ---- pagination ----
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),

    request: Request = None,
    db: MySQLConnection = Depends(get_db),
):
    sql = "SELECT * FROM listings WHERE 1=1"
    params: List[object] = []

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
    
    if description:
        sql += " AND description LIKE %s"
        params.append(f"%{description}%")

    # ---- date filters (range containment) ----
    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date must be <= end_date")

        sql += " AND start_date <= %s"
        params.append(start_date)

        sql += " AND (end_date IS NULL OR end_date >= %s)"
        params.append(end_date)

    elif start_date:
        # any listing that hasn't started after the requested start
        sql += " AND start_date <= %s"
        params.append(start_date)

    elif end_date:
        # any listing that doesn't end before the requested end
        sql += " AND (end_date IS NULL OR end_date >= %s)"
        params.append(end_date)

    # ---- pagination ----
    offset = (page - 1) * page_size
    sql += " ORDER BY id DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])

    cursor = db.cursor(dictionary=True)
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    cursor.close()

    items = [listing_with_links(row) for row in rows]

    base_path = str(request.url.path)  # e.g. "/listing"
    self_link = f"{base_path}?page={page}&page_size={page_size}"
    next_link = (
        f"{base_path}?page={page + 1}&page_size={page_size}"
        if len(rows) == page_size
        else None
    )
    prev_link = (
        f"{base_path}?page={page - 1}&page_size={page_size}"
        if page > 1
        else None
    )

    return PaginatedListingResponse(
        items=items,
        page=page,
        page_size=page_size,
        _links=PaginatedLinks(
            self=self_link,
            next=next_link,
            prev=prev_link,
        ),
    )
# -----------------------------------------------------------------------------
# GET /listing/{listing_id}  (ETag + If-None-Match => 304)
# -----------------------------------------------------------------------------
@app.get(
    "/listing/{listing_id}",
    response_model=ListingRead,
    responses={304: {"description": "Not Modified"}},
)
def get_listing(
    listing_id: int,
    request: Request,
    response: Response,
    db: MySQLConnection = Depends(get_db),
):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")

    etag = compute_etag_from_row(row)

    # Always send the current ETag (including on 304)
    response.headers["ETag"] = etag

    inm = request.headers.get("if-none-match")
    if inm and inm.strip() == etag:
        # IMPORTANT: return a Response object so FastAPI does NOT try to validate a body
        return Response(status_code=304, headers={"ETag": etag})

    return row_to_listing(row)

@app.post("/listing/bulk-create", response_model=BulkCreateTaskResponse, status_code=202)
async def bulk_create_listings(
    payload: BulkListingCreate,
    background_tasks: BackgroundTasks,
):
    """Create multiple listings asynchronously."""
    task_id = str(uuid.uuid4())
    
    # Initialize and store task
    task_status = BulkCreateTaskStatus(
        task_id=task_id,
        status="pending",
        message=f"Bulk creation of {len(payload.listings)} listings queued",
        created_at=datetime.now()
    )
    store_bulk_create_task(task_id, task_status)
    
    # Queue background processing
    background_tasks.add_task(process_bulk_create_listings, task_id, payload.listings)
    
    return BulkCreateTaskResponse(
        task_id=task_id,
        status="pending",
        message=f"Bulk creation started. Use GET /bulk-create/task/{task_id} to check progress."
    )


@app.get("/bulk-create/task/{task_id}", response_model=BulkCreateTaskStatus)
def get_bulk_create_task_status(task_id: str):
    """Check the status of a bulk create task."""
    task = get_bulk_create_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Bulk create task not found")
    return task


# -----------------------------------------------------------------------------
# DELETE /listing/{listing_id}
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# PUT /listing/{listing_id}
# -----------------------------------------------------------------------------

@app.put("/listing/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: MySQLConnection = Depends(get_db),
):
    cursor = db.cursor(dictionary=True)

    # 1. Fetch existing listing
    cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        raise HTTPException(status_code=404, detail="Listing not found")

    # 2. Use new values if provided, otherwise keep old ones
    name = payload.name if payload.name is not None else row["name"]
    address = payload.address if payload.address is not None else row["address"]
    start_date = payload.start_date if payload.start_date is not None else row["start_date"]
    end_date = payload.end_date if payload.end_date is not None else row["end_date"]
    description = payload.description if payload.description is not None else row["description"]
    picture_url = (
        str(payload.picture_url)
        if payload.picture_url is not None
        else row["picture_url"]
    )

    # 3. Single static UPDATE
    cursor.execute(
        """
        UPDATE listings
        SET
            name = %s,
            address = %s,
            start_date = %s,
            end_date = %s,
            description = %s,
            picture_url = %s
        WHERE id = %s
        """,
        (
            name,
            address,
            start_date,
            end_date,
            description,
            picture_url,
            listing_id,
        ),
    )
    db.commit()

    # 4. Fetch updated row
    cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    updated_row = cursor.fetchone()
    cursor.close()

    return row_to_listing(updated_row)


# -----------------------------------------------------------------------------
# Root
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Listing Service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
