from typing import Any, Dict, Iterable, Mapping
from sqlalchemy.sql import text

def _normalize_workout_params(wr: Mapping[str, Any]) -> Dict[str, Any]:
    # Ensure every key exists so SQLAlchemy always has a value to bind.
    return {
        "id": wr.get("id"),
        "title": wr.get("title") or "Workout",
        "notes": wr.get("notes") or "",
        "started_at": wr.get("started_at"),
        "ended_at": wr.get("ended_at"),
        "created_at": wr.get("created_at"),
        "updated_at": wr.get("updated_at"),
    }

UPSERT_WORKOUT_SQL = text("""
    INSERT INTO workouts (
        id, title, notes, started_at, ended_at, created_at, updated_at
    ) VALUES (
        :id, :title, :notes, :started_at, :ended_at, :created_at, :updated_at
    )
    ON CONFLICT (id) DO UPDATE SET
        title      = EXCLUDED.title,
        notes      = EXCLUDED.notes,
        started_at = EXCLUDED.started_at,
        ended_at   = EXCLUDED.ended_at,
        created_at = EXCLUDED.created_at,
        updated_at = EXCLUDED.updated_at
""")

def upsert_workout(conn, wr: Mapping[str, Any]) -> None:
    params = _normalize_workout_params(wr)
    conn.execute(UPSERT_WORKOUT_SQL, params)

INSERT_SETS_SQL = text("""
    INSERT INTO sets (
        id, workout_id, exercise_index, set_index, exercise_title, type,
        weight_kg, reps, distance_meters, duration_seconds, rpe, custom_metric
    ) VALUES (
        :id, :workout_id, :exercise_index, :set_index, :exercise_title, :type,
        :weight_kg, :reps, :distance_meters, :duration_seconds, :rpe, :custom_metric
    )
    ON CONFLICT (id) DO NOTHING
""")

def insert_sets_bulk(conn, rows: Iterable[Mapping[str, Any]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    conn.execute(INSERT_SETS_SQL, rows)
    return len(rows)
