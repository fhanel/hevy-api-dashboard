from typing import Any, Dict, List

def to_workout_row(w: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Hevy workout (list or detail) into our DB row shape.
    Hevy keys seen so far: id, title, description, start_time, end_time,
    created_at, updated_at, exercises, ...
    """
    title = w.get("title") or "Workout"
    notes = w.get("description") or w.get("notes") or ""

    return {
        "id": str(w.get("id")) if w.get("id") is not None else None,
        "title": title,
        "notes": notes,
        "started_at": w.get("start_time"),
        "ended_at": w.get("end_time"),
        "created_at": w.get("created_at"),
        "updated_at": w.get("updated_at"),
    }

def to_set_rows(workout_id: str, workout_detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten the workout detail's exercises/sets into DB rows.
    """
    rows: List[Dict[str, Any]] = []
    for ex in (workout_detail.get("exercises") or []):
        ex_idx = ex.get("index")
        ex_title = ex.get("title") or ""
        for s in (ex.get("sets") or []):
            s_idx = s.get("index")
            rows.append({
                # Make a stable text id so ON CONFLICT DO NOTHING
                "id": f"{workout_id}:{ex_idx}:{s_idx}",
                "workout_id": workout_id,
                "exercise_index": ex_idx,
                "set_index": s_idx,
                "exercise_title": ex_title,
                "type": s.get("type"),
                "weight_kg": s.get("weight_kg"),
                "reps": s.get("reps"),
                "distance_meters": s.get("distance_meters"),
                "duration_seconds": s.get("duration_seconds"),
                "rpe": s.get("rpe"),
                "custom_metric": s.get("custom_metric"),
            })
    return rows
