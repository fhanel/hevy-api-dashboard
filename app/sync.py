from __future__ import annotations
from typing import Dict

from .hevy_client import list_workouts, get_workout
from .mappers import to_workout_row, to_set_rows
from .repo import upsert_workout, insert_sets_bulk
from .db import get_db
from .exercise_sync import sync_exercise_templates



def sync_first_page(page: int = 1, page_size: int = 10) -> Dict[str, int]:
    """
    Unified sync that handles both adding/updating workouts AND deleting removed ones.
    
    This function:
    1. Fetches workout IDs from Hevy to detect deletions
    2. Removes workouts and sets that no longer exist in Hevy
    3. Syncs the remaining workouts (adds/updates)
    4. Ensures data consistency and accurate statistics
    
    Returns a summary dict with counts of all operations.
    """
    
    # 1) First, fetch all workout IDs from Hevy to detect deletions
    hevy_workout_ids = set()
    current_page = 1
    fetch_page_size = 10  # Hevy API only allows max 10 per page
    
    while True:
        try:
            raw = list_workouts(page=current_page, page_size=fetch_page_size)
            workouts = raw.get("workouts", [])
            
            if not workouts:
                break
                
            # Only extract IDs for deletion detection
            page_ids = {w.get("id") for w in workouts if w.get("id")}
            hevy_workout_ids.update(page_ids)
            
            
            if len(workouts) < fetch_page_size:
                break
                
            current_page += 1
            
        except Exception as e:
            break
    
    
    # 2) Handle deletions first
    workouts_deleted = 0
    with get_db() as db:
        # Get local workout IDs
        local_workouts = db.exec_driver_sql("SELECT id FROM workouts").fetchall()
        local_workout_ids = {row[0] for row in local_workouts}
        # Find workouts to delete (local but not in Hevy)
        workouts_to_delete = local_workout_ids - hevy_workout_ids
        
        if workouts_to_delete:
            
            # Delete sets first (foreign key constraint)
            db.exec_driver_sql(
                "DELETE FROM sets WHERE workout_id = ANY(%s)", 
                (list(workouts_to_delete),)
            )
            
            # Delete workouts
            db.exec_driver_sql(
                "DELETE FROM workouts WHERE id = ANY(%s)", 
                (list(workouts_to_delete),)
            )
            
            workouts_deleted = len(workouts_to_delete)
    
    # 3) Now sync the remaining workouts (adds/updates)
    seen = 0
    upserted = 0
    sets_total = 0
    
    # For unified sync, we want to sync ALL workouts, not just one page
    # This ensures we get all the data after deletions
    current_page = 1
    while True:
        try:
            raw = list_workouts(page=current_page, page_size=10)
            workouts = raw.get("workouts", [])
            
            if not workouts:
                break
                
            
            # Process each workout on this page
            with get_db() as db:
                for w in workouts:
                    seen += 1
                    
                    try:
                        wr = to_workout_row(w)
                    except Exception as e:
                        continue
                    
                    workout_id = wr.get("id")
                    if not workout_id:
                        continue

                    try:
                        upsert_workout(db, wr)
                        upserted += 1
                    except Exception as e:
                        continue

                    # Fetch detail and insert sets
                    try:
                        detail = get_workout(workout_id)
                    except Exception as e:
                        continue

                    try:
                        set_rows = to_set_rows(workout_id, detail)
                        if set_rows:
                            insert_sets_bulk(db, set_rows)
                            sets_total += len(set_rows)
                    except Exception as e:
                        pass
            
            # Move to next page
            current_page += 1
            
        except Exception as e:
            break
    
    # 4) Sync exercise templates (lightweight operation)
    exercise_sync_result = sync_exercise_templates()

    summary = {
        "sync_type": "unified_with_deletion",
        "workouts_seen": seen,
        "workouts_upserted": upserted,
        "sets_inserted": sets_total,
        "workouts_deleted": workouts_deleted,
        "total_hevy_workouts": len(hevy_workout_ids),
        "total_local_before": len(local_workout_ids),
        "exercise_sync": {
            "status": exercise_sync_result["status"],
            "imported_count": exercise_sync_result.get("imported_count", 0),
            "total_templates": exercise_sync_result.get("total_templates", 0),
            "message": exercise_sync_result.get("message", "")
        }
    }
    
    return summary
