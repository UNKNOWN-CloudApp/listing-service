# Test script for bulk create functionality.

import asyncio
import json
import time
import requests
from datetime import datetime

# Test data
test_listings = [
    {
        "landlord_email": "test@example.com",
        "name": "Test Bulk Listing 1",
        "address": "100 Test Street",
        "start_date": "2025-12-15T10:00:00",
        "end_date": "2026-06-15T10:00:00",
        "description": "First test listing for bulk create"
    },
    {
        "landlord_email": "test@example.com", 
        "name": "Test Bulk Listing 2",
        "address": "200 Test Avenue",
        "start_date": "2026-01-01T09:00:00",
        "end_date": "2026-12-31T09:00:00",
        "description": "Second test listing for bulk create"
    },
    {
        "landlord_email": "test2@example.com",
        "name": "Test Bulk Listing 3", 
        "address": "300 Test Boulevard",
        "start_date": "2025-11-01T14:00:00",
        "description": "Third test listing - no end date"
    }
]

def test_bulk_create():
    """Test the complete bulk create workflow."""
    
    base_url = "http://localhost:8080"
    
    print("Testing Bulk Create Functionality")
    print("=" * 50)
    
    # Step 1: Submit bulk create request
    print(f"Step 1: Submitting bulk create request with {len(test_listings)} listings...")
    
    payload = {"listings": test_listings}
    
    try:
        response = requests.post(
            f"{base_url}/listing/bulk-create",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 202:
            print(f"ERROR: Expected 202, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        task_data = response.json()
        task_id = task_data["task_id"]
        
        print(f"SUCCESS: Got 202 response")
        print(f"   Task ID: {task_id}")
        print(f"   Status: {task_data['status']}")
        print(f"   Message: {task_data['message']}")
        print()
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server. Make sure it's running on localhost:8080")
        print("   Run: uvicorn main:app --host 0.0.0.0 --port 8080")
        return False
    except Exception as e:
        print(f"ERROR: Error submitting request: {e}")
        return False
    
    # Step 2: Track progress
    print("Step 2: Tracking progress...")
    
    max_attempts = 30  # 30 seconds max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{base_url}/bulk-create/task/{task_id}")
            
            if response.status_code != 200:
                print(f"ERROR: Error checking status: {response.status_code}")
                return False
                
            status_data = response.json()
            status = status_data["status"]
            message = status_data["message"]
            
            print(f"   [{attempt + 1:2d}] Status: {status:12s} | {message}")
            
            if status == "completed":
                print()
                print("SUCCESS: Bulk create completed successfully")
                
                # Show results
                results = status_data.get("results", {})
                print(f"   Created: {results.get('created_count', 0)} listings")
                print(f"   Errors:  {results.get('error_count', 0)} errors")
                
                if results.get("created_listings"):
                    print("   Created listing IDs:", [l["id"] for l in results["created_listings"]])
                
                if status_data.get("errors"):
                    print("   Errors:", status_data["errors"])
                
                return True
                
            elif status == "failed":
                print()
                print("ERROR: Bulk create failed")
                print(f"   Message: {message}")
                if status_data.get("errors"):
                    print(f"   Errors: {status_data['errors']}")
                return False
            
            # Wait before next check
            time.sleep(1)
            attempt += 1
            
        except Exception as e:
            print(f"ERROR: Error checking status: {e}")
            return False
    
    print()
    print("TIMEOUT: Waiting for completion")
    return False

def test_direct_processing():
    """Test the processing function directly (without server)."""
    
    print("\nTesting Direct Processing (No Server)")
    print("=" * 50)
    
    try:
        # Import the processing function
        import sys
        sys.path.append('.')
        
        from models.bulk_create import (
            process_bulk_create_listings, 
            BulkCreateTaskStatus,
            store_bulk_create_task,
            get_bulk_create_task
        )
        from models.listing import ListingCreate
        from datetime import datetime
        import uuid
        
        # Create test listings
        listings = [
            ListingCreate(
                landlord_email="direct.test@example.com",
                name="Direct Test Listing 1", 
                address="Direct Test Address 1",
                description="Testing direct processing"
            ),
            ListingCreate(
                landlord_email="direct.test@example.com",
                name="Direct Test Listing 2",
                address="Direct Test Address 2", 
                description="Testing direct processing 2"
            )
        ]
        
        # Create task
        task_id = str(uuid.uuid4())
        task_status = BulkCreateTaskStatus(
            task_id=task_id,
            status="pending",
            message="Direct test",
            created_at=datetime.now()
        )
        
        store_bulk_create_task(task_id, task_status)
        
        print(f"Created task: {task_id}")
        print(f"Processing {len(listings)} listings...")
        
        # Process listings
        process_bulk_create_listings(task_id, listings)
        
        # Check final status
        final_status = get_bulk_create_task(task_id)
        
        print(f"Final status: {final_status.status}")
        print(f"Message: {final_status.message}")
        
        if final_status.results:
            results = final_status.results
            print(f"Created: {results.get('created_count', 0)} listings")
            print(f"Errors: {results.get('error_count', 0)} errors")
        
        if final_status.status == "completed":
            print("SUCCESS: Direct processing test passed")
            return True
        else:
            print("ERROR: Direct processing test failed")
            if final_status.errors:
                print(f"   Errors: {final_status.errors}")
            return False
            
    except Exception as e:
        print(f"ERROR: Direct processing error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Bulk Create Test Suite")
    print("=" * 60)
    
    # Test 1: Direct processing (no server needed)
    direct_success = test_direct_processing()
    
    # Test 2: Full API test (requires server)
    api_success = test_bulk_create()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"   Direct Processing: {'PASS' if direct_success else 'FAIL'}")
    print(f"   API Workflow:      {'PASS' if api_success else 'FAIL'}")
    print()
    
    if direct_success and api_success:
        print("All tests passed")
    elif direct_success:
        print("WARNING: Direct processing works, but API test failed (server not running?)")
    else:
        print("FAILED: Tests failed - check errors above")