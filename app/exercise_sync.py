from typing import Dict, Any
from .db import get_db
from .hevy_client import list_exercise_templates


def sync_exercise_templates() -> Dict[str, Any]:
    """
    Fetch all exercise templates from Hevy API and populate the exercises table.
    
    Returns:
        Dict with sync statistics
    """
    try:
        # Fetch all exercise templates from Hevy API
        all_templates = []
        page = 1
        page_size = 100
        
        while True:
            try:
                response = list_exercise_templates(page=page, page_size=page_size)
                templates = response.get('exercise_templates', [])
                
                if not templates:
                    break
                    
                all_templates.extend(templates)
                page += 1
                
                # Prevent infinite loops
                if page > 100:  # Max 10,000 exercises
                    break
                    
            except Exception as e:
                break
        
        if not all_templates:
            return {
                "status": "error",
                "message": "No exercise templates found in Hevy API",
                "imported_count": 0,
                "total_templates": 0
            }
        
        # Import to database
        with get_db() as db:
            # Clear existing exercises
            db.exec_driver_sql("DELETE FROM exercises")
            
            # Insert new exercises from Hevy API
            imported_count = 0
            for template in all_templates:
                # Map Hevy API fields to our database fields
                exercise_title = template.get('title', '').strip()
                if not exercise_title:
                    continue
                
                # Secondary muscle groups
                secondary_muscle_groups = template.get('secondary_muscle_groups', [])
                if isinstance(secondary_muscle_groups, list):
                    secondary_muscle_group = ', '.join(secondary_muscle_groups)
                else:
                    secondary_muscle_group = str(secondary_muscle_groups) if secondary_muscle_groups else None
                
                # Primary muscle group directly from Hevy API
                primary_muscle = template.get('primary_muscle_group', '')
                
                db.exec_driver_sql(
                    """INSERT INTO exercises (exercise_title, type, primary_muscle_group, secondary_muscle_group, created_at)
                       VALUES (%s, %s, %s, %s, NOW())
                       ON CONFLICT (exercise_title) 
                       DO UPDATE SET 
                           type = EXCLUDED.type,
                           primary_muscle_group = EXCLUDED.primary_muscle_group,
                           secondary_muscle_group = EXCLUDED.secondary_muscle_group""",
                    (
                        exercise_title,
                        template.get('type'),
                        primary_muscle,
                        secondary_muscle_group,
                    )
                )
                imported_count += 1
        
        return {
            "status": "success",
            "imported_count": imported_count,
            "total_templates": len(all_templates),
            "message": f"Successfully imported {imported_count} exercise templates from Hevy API"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sync failed: {str(e)}",
            "imported_count": 0,
            "total_templates": 0
        }




