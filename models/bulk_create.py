from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import threading
import time
import uuid

from models.listing import ListingCreate

# Models
class BulkListingCreate(BaseModel):
    listings: List[ListingCreate]

class BulkCreateTaskResponse(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    message: str

class BulkCreateTaskStatus(BaseModel):
    task_id: str
    status: str
    message: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

# Task Storage
_bulk_create_tasks: Dict[str, BulkCreateTaskStatus] = {}
_task_lock = threading.Lock()

# Task Management Functions
def store_bulk_create_task(task_id: str, task_status: BulkCreateTaskStatus):
    """Store a bulk create task status safely."""
    with _task_lock:
        _bulk_create_tasks[task_id] = task_status

def get_bulk_create_task(task_id: str) -> Optional[BulkCreateTaskStatus]:
    """Get bulk create task status safely."""
    with _task_lock:
        return _bulk_create_tasks.get(task_id)

def update_bulk_create_task(task_id: str, **updates):
    """Update bulk create task status fields safely."""
    with _task_lock:
        if task_id in _bulk_create_tasks:
            for key, value in updates.items():
                setattr(_bulk_create_tasks[task_id], key, value)

# Background Processing
def process_bulk_create_listings(task_id: str, listings: List[ListingCreate]):
    """
    Process bulk listing creation in the background.
    Updates task status as it progresses.
    """
    try:
        update_bulk_create_task(
            task_id, 
            status="processing",
            message=f"Processing {len(listings)} listings..."
        )
        
        conn = None
        cursor = None
        try:
            from utils.database import db_pool
            conn = db_pool.get_connection()
            cursor = conn.cursor()
            
            created_listings = []
            errors = []
            
            # Process each listing
            for i, listing in enumerate(listings):
                try:
                    time.sleep(0.1)  # Small delay to simulate work
                    
                    sql = """
                        INSERT INTO listings (
                            landlord_email, name, address, start_date, 
                            end_date, description, picture_url
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    values = (
                        listing.landlord_email,
                        listing.name,
                        listing.address,
                        listing.start_date,
                        listing.end_date,
                        listing.description,
                        str(listing.picture_url) if listing.picture_url else None,
                    )
                    
                    cursor.execute(sql, values)
                    new_id = cursor.lastrowid
                    created_listings.append({"id": new_id, "index": i})
                    
                    # Update progress
                    progress = ((i + 1) / len(listings)) * 100
                    update_bulk_create_task(
                        task_id,
                        message=f"Processing {i + 1}/{len(listings)} listings ({progress:.1f}%)"
                    )
                    
                except Exception as e:
                    errors.append(f"Listing {i + 1}: {str(e)}")
                    continue
            
            conn.commit()
            
            update_bulk_create_task(
                task_id,
                status="completed",
                completed_at=datetime.now(),
                message=f"Successfully created {len(created_listings)} listings",
                results={
                    "created_count": len(created_listings),
                    "error_count": len(errors),
                    "created_listings": created_listings
                },
                errors=errors if errors else None
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                
    except Exception as e:
        update_bulk_create_task(
            task_id,
            status="failed",
            completed_at=datetime.now(),
            message=f"Bulk creation failed: {str(e)}",
            errors=[str(e)]
        )