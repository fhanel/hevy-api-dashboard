from fastapi import FastAPI, APIRouter, Query, HTTPException
from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from .db import get_db, create_all_tables
from .sync import sync_first_page
from .models import WeeklyComment

app = FastAPI(title="Hevy Workout Tracker API")

class CreateMuscleGroupRequest(BaseModel):
    name: str

class UpdateExerciseMappingRequest(BaseModel):
    exercise_title: str
    custom_muscle_group_id: Optional[int] = None

class MappingPreferenceRequest(BaseModel):
    mapping_type: str

class WeeklyCommentRequest(BaseModel):
    week_start: str
    comment: Optional[str] = None

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

@app.on_event("startup")
def _startup():
    create_all_tables()

api = APIRouter()

@api.get("/workouts")
def list_workouts(limit: int = Query(200, ge=1, le=1000)):
    with get_db() as db:
        rows = db.exec_driver_sql(
            "SELECT * FROM workouts ORDER BY COALESCE(started_at, '1970-01-01') DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


@api.get("/workouts/{workout_id}")
def get_workout(workout_id: str):
    """Get a specific workout by ID with its sets"""
    with get_db() as db:
        # Get the workout
        workout_row = db.exec_driver_sql(
            "SELECT * FROM workouts WHERE id = %s",
            (workout_id,),
        ).fetchone()
        
        if not workout_row:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        # Check user's mapping preference
        preference_result = db.exec_driver_sql(
            "SELECT mapping_type FROM mapping_preferences WHERE user_id = %s",
            ("default_user",)
        ).fetchone()
        
        mapping_type = preference_result[0] if preference_result else "hevy"
        
        if mapping_type == "custom":
            # Use custom muscle group mappings
            sets_rows = db.exec_driver_sql(
                """SELECT s.*, 
                          COALESCE(cmg.name, e.primary_muscle_group, 'Other') AS muscle_group
                   FROM sets s
                   LEFT JOIN exercises e ON e.exercise_title = s.exercise_title
                   LEFT JOIN exercise_custom_mappings ecm ON ecm.exercise_title = s.exercise_title AND ecm.user_id = 'default_user'
                   LEFT JOIN custom_muscle_groups cmg ON cmg.id = ecm.custom_muscle_group_id
                   WHERE s.workout_id = %s 
                   ORDER BY s.exercise_index, s.set_index""",
                (workout_id,),
            ).fetchall()
        else:
            # Use Hevy's primary muscle groups (default)
            sets_rows = db.exec_driver_sql(
                """SELECT s.*, 
                          COALESCE(e.primary_muscle_group, 'Other') AS muscle_group
                   FROM sets s
                   LEFT JOIN exercises e ON e.exercise_title = s.exercise_title
                   WHERE s.workout_id = %s 
                   ORDER BY s.exercise_index, s.set_index""",
                (workout_id,),
            ).fetchall()
        
        workout = _row_to_dict(workout_row)
        workout["sets"] = [_row_to_dict(r) for r in sets_rows]
        
        return workout


def _row_to_dict(row) -> Dict[str, Any]:
    if isinstance(row, dict): return row
    if hasattr(row, "_mapping"): return dict(row._mapping)
    try: return dict(row)
    except Exception: return {"_": repr(row)}


@api.get("/_counts")
def counts():
    with get_db() as db:
        wc = db.exec_driver_sql("SELECT COUNT(*) FROM workouts").fetchone()[0]
        sc = db.exec_driver_sql("SELECT COUNT(*) FROM sets").fetchone()[0]
    return {"workouts": wc, "sets": sc}

@api.get("/exercises/titles")
def list_exercise_titles(limit: int = Query(200, ge=1, le=5000)):
    """
    Returns distinct exercise_title values seen in sets, ordered by frequency (most common first).
    """
    sql = """
        SELECT exercise_title, COUNT(*) AS cnt
        FROM sets
        WHERE exercise_title IS NOT NULL AND exercise_title <> ''
        GROUP BY exercise_title
        ORDER BY cnt DESC, exercise_title ASC
        LIMIT %s
    """
    with get_db() as db:
        rows = db.exec_driver_sql(sql, (limit,)).fetchall()
    return [{"exercise_title": r[0], "count": int(r[1] or 0)} for r in rows]





@api.get("/exercises/used")
def list_used_exercises():
    """
    List only exercises that are actually used in workouts (have sets).
    """
    sql = """
        WITH exercise_sets AS (
            SELECT 
                s.exercise_title,
                COUNT(*) as usage_count
            FROM sets s
            GROUP BY s.exercise_title
        ),
        mapped_exercises AS (
            SELECT 
                es.exercise_title,
                e.type,
                e.primary_muscle_group,
                e.secondary_muscle_group,
                es.usage_count
            FROM exercise_sets es
            INNER JOIN exercises e ON e.exercise_title = es.exercise_title
        ),
        unmapped_exercises AS (
            SELECT 
                es.exercise_title,
                NULL as type,
                'Other' as primary_muscle_group,
                NULL as secondary_muscle_group,
                es.usage_count
            FROM exercise_sets es
            LEFT JOIN exercises e ON e.exercise_title = es.exercise_title
            WHERE e.exercise_title IS NULL
        )
        SELECT * FROM mapped_exercises
        UNION ALL
        SELECT * FROM unmapped_exercises
        ORDER BY exercise_title
    """
    with get_db() as db:
        results = db.exec_driver_sql(sql).fetchall()

        return [
            {
                "exercise_title": row[0],
                "type": row[1],
                "primary_muscle_group": row[2],
                "secondary_muscle_group": row[3],
                "usage_count": int(row[4])
            }
            for row in results
        ]


@api.get("/exercises/by-muscle-group")
def list_exercises_by_muscle_group():
    """
    List exercises grouped by muscle group for easier selection.
    Returns a dictionary with muscle groups as keys and lists of exercises as values.
    """
    sql = """
        WITH exercise_sets AS (
            SELECT 
                s.exercise_title,
                COUNT(*) as usage_count
            FROM sets s
            GROUP BY s.exercise_title
        ),
        mapped_exercises AS (
            SELECT 
                es.exercise_title,
                e.type,
                e.primary_muscle_group,
                e.secondary_muscle_group,
                es.usage_count
            FROM exercise_sets es
            INNER JOIN exercises e ON e.exercise_title = es.exercise_title
        ),
        unmapped_exercises AS (
            SELECT 
                es.exercise_title,
                NULL as type,
                'Other' as primary_muscle_group,
                NULL as secondary_muscle_group,
                es.usage_count
            FROM exercise_sets es
            LEFT JOIN exercises e ON e.exercise_title = es.exercise_title
            WHERE e.exercise_title IS NULL
        )
        SELECT * FROM mapped_exercises
        UNION ALL
        SELECT * FROM unmapped_exercises
        ORDER BY primary_muscle_group, exercise_title
    """
    with get_db() as db:
        results = db.exec_driver_sql(sql).fetchall()
        
        # Group exercises by muscle group
        muscle_groups = {}
        for row in results:
            muscle_group = row[2] or 'Other'
            if muscle_group not in muscle_groups:
                muscle_groups[muscle_group] = []
            
            muscle_groups[muscle_group].append({
                "exercise_title": row[0],
                "type": row[1],
                "primary_muscle_group": row[2],
                "secondary_muscle_group": row[3],
                "usage_count": int(row[4])
            })
        
        return muscle_groups


# Custom Muscle Group Management
@api.get("/custom-muscle-groups")
def list_custom_muscle_groups():
    """List all custom muscle groups"""
    with get_db() as db:
        results = db.exec_driver_sql(
            "SELECT id, name, created_at FROM custom_muscle_groups ORDER BY name"
        ).fetchall()
        return [
            {"id": row[0], "name": row[1], "created_at": row[2].isoformat()}
            for row in results
        ]


@api.post("/custom-muscle-groups")
def create_custom_muscle_group(request: CreateMuscleGroupRequest):
    """Create a new custom muscle group"""
    name = request.name
    with get_db() as db:
        # Check if name already exists
        existing = db.exec_driver_sql(
            "SELECT id FROM custom_muscle_groups WHERE name = %s",
            (name,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Muscle group name already exists")
        
        # Insert new muscle group
        result = db.exec_driver_sql(
            "INSERT INTO custom_muscle_groups (name, user_id) VALUES (%s, %s) RETURNING id",
            (name, "default_user")  # Using default_user for now
        ).fetchone()
        
        return {"id": result[0], "name": name, "message": "Custom muscle group created"}


@api.delete("/custom-muscle-groups/{group_id}")
def delete_custom_muscle_group(group_id: int):
    """Delete a custom muscle group and its mappings"""
    with get_db() as db:
        # Delete mappings first
        db.exec_driver_sql(
            "DELETE FROM exercise_custom_mappings WHERE custom_muscle_group_id = %s",
            (group_id,)
        )
        
        # Delete the muscle group
        result = db.exec_driver_sql(
            "DELETE FROM custom_muscle_groups WHERE id = %s",
            (group_id,)
        )
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Muscle group not found")
        
        return {"message": "Custom muscle group deleted"}


@api.get("/exercise-mappings")
def list_exercise_mappings():
    """List all exercises with their custom muscle group mappings"""
    sql = """
        WITH exercise_sets AS (
            SELECT 
                s.exercise_title,
                COUNT(*) as usage_count
            FROM sets s
            GROUP BY s.exercise_title
        ),
        all_exercises AS (
            SELECT 
                es.exercise_title,
                e.type,
                e.primary_muscle_group,
                e.secondary_muscle_group,
                es.usage_count
            FROM exercise_sets es
            LEFT JOIN exercises e ON e.exercise_title = es.exercise_title
        )
        SELECT 
            ae.exercise_title,
            ae.type,
            ae.primary_muscle_group,
            ae.secondary_muscle_group,
            ae.usage_count,
            cmg.id as custom_muscle_group_id,
            cmg.name as custom_muscle_group_name
        FROM all_exercises ae
        LEFT JOIN exercise_custom_mappings ecm ON ecm.exercise_title = ae.exercise_title
        LEFT JOIN custom_muscle_groups cmg ON cmg.id = ecm.custom_muscle_group_id
        ORDER BY ae.exercise_title
    """
    with get_db() as db:
        results = db.exec_driver_sql(sql).fetchall()
        return [
            {
                "exercise_title": row[0],
                "type": row[1],
                "primary_muscle_group": row[2],
                "secondary_muscle_group": row[3],
                "usage_count": int(row[4]),
                "custom_muscle_group_id": row[5],
                "custom_muscle_group_name": row[6]
            }
            for row in results
        ]


@api.post("/exercise-mappings")
def update_exercise_mapping(request: UpdateExerciseMappingRequest):
    """Update or create an exercise mapping"""
    exercise_title = request.exercise_title
    custom_muscle_group_id = request.custom_muscle_group_id
    with get_db() as db:
        if custom_muscle_group_id is None:
            # Remove mapping
            db.exec_driver_sql(
                "DELETE FROM exercise_custom_mappings WHERE exercise_title = %s",
                (exercise_title,)
            )
            return {"message": "Exercise mapping removed"}
        else:
            # Verify custom muscle group exists
            group = db.exec_driver_sql(
                "SELECT id FROM custom_muscle_groups WHERE id = %s",
                (custom_muscle_group_id,)
            ).fetchone()
            if not group:
                raise HTTPException(status_code=404, detail="Custom muscle group not found")
            
            # Upsert mapping
            db.exec_driver_sql(
                """INSERT INTO exercise_custom_mappings (exercise_title, custom_muscle_group_id, user_id)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (exercise_title, user_id)
                   DO UPDATE SET custom_muscle_group_id = EXCLUDED.custom_muscle_group_id""",
                (exercise_title, custom_muscle_group_id, "default_user")
            )
            return {"message": "Exercise mapping updated"}


# Mapping Preference Management
@api.get("/mapping-preference")
def get_mapping_preference():
    """Get the current mapping preference"""
    with get_db() as db:
        result = db.exec_driver_sql(
            "SELECT mapping_type FROM mapping_preferences WHERE user_id = %s",
            ("default_user",)
        ).fetchone()
        
        if result:
            return {"mapping_type": result[0]}
        else:
            return {"mapping_type": "hevy"}  # Default to Hevy mapping


@api.post("/mapping-preference")
def save_mapping_preference(request: MappingPreferenceRequest):
    """Save the mapping preference"""
    mapping_type = request.mapping_type
    
    if mapping_type not in ["hevy", "custom"]:
        raise HTTPException(status_code=400, detail="mapping_type must be 'hevy' or 'custom'")
    
    with get_db() as db:
        db.exec_driver_sql(
            """INSERT INTO mapping_preferences (user_id, mapping_type)
               VALUES (%s, %s)
               ON CONFLICT (user_id)
               DO UPDATE SET mapping_type = EXCLUDED.mapping_type, updated_at = NOW()""",
            ("default_user", mapping_type)
        )
        
        return {"message": f"Mapping preference saved: {mapping_type}"}

@api.get("/weekly-comments")
def get_weekly_comments():
    """Get all weekly comments for the default user."""
    with get_db() as db:
        rows = db.exec_driver_sql(
            "SELECT week_start, comment FROM weekly_comments WHERE user_id = %s ORDER BY week_start DESC",
            ("default_user",)
        ).fetchall()
    return {row[0]: row[1] for row in rows}

@api.post("/weekly-comments")
def save_weekly_comment(request: WeeklyCommentRequest):
    """Save or update a weekly comment for the default user."""
    with get_db() as db:
        db.exec_driver_sql(
            """INSERT INTO weekly_comments (user_id, week_start, comment, created_at, updated_at)
               VALUES (%s, %s, %s, NOW(), NOW())
               ON CONFLICT (user_id, week_start)
               DO UPDATE SET comment = EXCLUDED.comment, updated_at = NOW()""",
            ("default_user", request.week_start, request.comment)
        )
        return {"message": f"Weekly comment saved for {request.week_start}"}

stats = APIRouter()

@stats.get("/stats/weekly_volume")
def weekly_volume(weeks: int = Query(8, ge=1, le=52)):
    """
    Sum(weight_kg * reps) per ISO week for the specified number of weeks.
    Returns week_start (UTC, Monday 00:00) + total volume (kg·reps).
    Ascending by week_start.
    """
    sql = """
        WITH first_workout AS (
            SELECT date_trunc('week', MIN(w.started_at))::date AS first_week
            FROM workouts w
            WHERE w.started_at IS NOT NULL
        ),
        current_week AS (
            SELECT date_trunc('week', NOW())::date AS current_week
        ),
        week_series AS (
            SELECT (current_week - (generate_series(0, %s-1) * interval '1 week'))::date AS week_start
            FROM current_week
        ),
        filtered_weeks AS (
            SELECT week_start
            FROM week_series
            WHERE week_start >= (SELECT first_week FROM first_workout)
        ),
        volume_data AS (
            SELECT
                date_trunc('week', w.started_at)::date AS week_start,
                SUM(COALESCE(s.weight_kg, 0) * COALESCE(s.reps, 0))::bigint AS volume
            FROM sets s
            JOIN workouts w ON w.id = s.workout_id
            WHERE w.started_at IS NOT NULL
            GROUP BY 1
        )
        SELECT
            fw.week_start,
            COALESCE(vd.volume, 0)::bigint AS volume
        FROM filtered_weeks fw
        LEFT JOIN volume_data vd ON vd.week_start = fw.week_start
        ORDER BY fw.week_start ASC
    """
    with get_db() as db:
        rows = db.exec_driver_sql(sql, (weeks,)).fetchall()
    return [
        {"week_start": r[0].isoformat(), "volume": int(r[1] or 0)}
        for r in rows
    ]


@stats.get("/stats/best_prs")
def best_prs(min_reps: int = Query(5, ge=1, le=100)):
    """
    Per exercise_title, return:
      - best_epley_1rm: max(weight * (1 + reps/30))
      - best_tonnage:   max(weight * reps)
      - best_weight_ge_min_reps: max(weight) among sets with reps >= min_reps
    """
    sql = """
        SELECT
            s.exercise_title,
            MAX(COALESCE(s.weight_kg, 0) * (1 + COALESCE(s.reps, 0) / 30.0))         AS best_epley_1rm,
            MAX(COALESCE(s.weight_kg, 0) * COALESCE(s.reps, 0))                       AS best_tonnage,
            MAX(CASE WHEN COALESCE(s.reps,0) >= %s THEN COALESCE(s.weight_kg, 0) END) AS best_weight_ge_min_reps
        FROM sets s
        WHERE s.exercise_title IS NOT NULL
        GROUP BY s.exercise_title
        ORDER BY s.exercise_title ASC
    """
    with get_db() as db:
        rows = db.exec_driver_sql(sql, (min_reps,)).fetchall()
    out = []
    for r in rows:
        exercise = r[0]
        best_epley = float(r[1] or 0)
        best_ton = float(r[2] or 0)
        best_w_ge = r[3]
        out.append({
            "exercise_title": exercise,
            "best_epley_1rm": round(best_epley, 2),
            "best_tonnage": round(best_ton, 2),
            "best_weight_ge_min_reps": (round(float(best_w_ge), 2) if best_w_ge is not None else None),
            "min_reps_threshold": min_reps,
        })
    return out

@stats.get("/stats/progression")
def progression(
    exercises: str = Query(..., description="Comma-separated exercise titles"),
    weeks: int = Query(12, ge=1, le=104),
    metric: str = Query("epley_1rm", pattern="^(epley_1rm|best_weight|tonnage)$"),
    min_reps: int = Query(5, ge=1, le=50, description="Only used when metric=best_weight")
):
    """
    Per-week progression for one or more exercises. Metrics:
      - epley_1rm (default): weight * (1 + reps/30)
      - best_weight: max weight with reps >= min_reps
      - tonnage: weight * reps (single-set)
    """
    # Parse exercise list
    exercise_list = [ex.strip() for ex in exercises.split(',') if ex.strip()]
    if not exercise_list:
        return {"error": "No exercises provided"}
    
    # Build metric SQL expression
    if metric == "epley_1rm":
        metric_sql = "COALESCE(s.weight_kg,0) * (1 + COALESCE(s.reps,0) / 30.0)"
        params_metric = []
    elif metric == "tonnage":
        metric_sql = "COALESCE(s.weight_kg,0) * COALESCE(s.reps,0)"
        params_metric = []
    else:  # best_weight
        metric_sql = "CASE WHEN COALESCE(s.reps,0) >= %s THEN COALESCE(s.weight_kg,0) END"
        params_metric = [min_reps]

    # Build exercise filter
    exercise_conditions = " OR ".join(["s.exercise_title = %s"] * len(exercise_list))
    
    sql = f"""
        SELECT
            w.started_at::date AS workout_date,
            s.exercise_title,
            MAX({metric_sql}) AS value
        FROM sets s
        JOIN workouts w ON w.id = s.workout_id
        WHERE w.started_at IS NOT NULL
          AND w.started_at >= NOW() - (%s || ' weeks')::interval
          AND ({exercise_conditions})
        GROUP BY 1, 2
        ORDER BY 1 ASC, 2 ASC
    """

    # parameters: [min_reps?] + weeks + exercise_list
    params = [*params_metric, weeks, *exercise_list]
    with get_db() as db:
        rows = db.exec_driver_sql(sql, tuple(params)).fetchall()

    # Group data by exercise
    exercise_data = {}
    for row in rows:
        workout_date = row[0].isoformat() if row[0] else None
        exercise_title = row[1]
        value = float(row[2]) if row[2] is not None else None
        
        if exercise_title not in exercise_data:
            exercise_data[exercise_title] = []
        
        exercise_data[exercise_title].append({
            "workout_date": workout_date,
            "value": value
        })
    
    return {
        "exercises": exercise_list,
        "metric": metric,
        "min_reps": min_reps if metric == "best_weight" else None,
        "weeks": weeks,
        "data": exercise_data,
    }

@stats.get("/stats/weekly_summary")
def weekly_summary(weeks: int = Query(16, ge=1, le=104)):
    """
    Weekly rollups:
      - wpw: workouts per week
      - spw: sets per week
      - rpw: reps per week
      - dpw_avg_minutes: average duration per workout (minutes)
    """
    sql = """
        WITH first_workout AS (
            SELECT date_trunc('week', MIN(w.started_at))::date AS first_week
            FROM workouts w
            WHERE w.started_at IS NOT NULL
        ),
        current_week AS (
            SELECT date_trunc('week', NOW())::date AS current_week
        ),
        week_series AS (
            SELECT (current_week - (generate_series(0, %s-1) * interval '1 week'))::date AS week_start
            FROM current_week
        ),
        filtered_weeks AS (
            SELECT week_start
            FROM week_series
            WHERE week_start >= (SELECT first_week FROM first_workout)
        ),
        wk AS (
            SELECT
                date_trunc('week', w.started_at)::date AS week_start,
                w.id AS workout_id,
                EXTRACT(EPOCH FROM (w.ended_at - w.started_at)) / 60.0 AS duration_min
            FROM workouts w
            WHERE w.started_at IS NOT NULL
              AND w.ended_at IS NOT NULL
        ),
        set_agg AS (
            SELECT s.workout_id,
                   COUNT(*)::int AS sets_count,
                   SUM(COALESCE(s.reps,0))::int AS reps_count
            FROM sets s
            GROUP BY s.workout_id
        )
        SELECT
            fw.week_start,
            COUNT(DISTINCT wk.workout_id)::int                            AS wpw,
            COALESCE(SUM(sa.sets_count), 0)::int                          AS spw,
            COALESCE(SUM(sa.reps_count), 0)::int                          AS rpw,
            CASE
              WHEN COUNT(DISTINCT wk.workout_id) > 0
              THEN ROUND(SUM(COALESCE(wk.duration_min,0)) / COUNT(DISTINCT wk.workout_id), 1)
              ELSE 0
            END                                                           AS dpw_avg_minutes
        FROM filtered_weeks fw
        LEFT JOIN wk ON wk.week_start = fw.week_start
        LEFT JOIN set_agg sa ON sa.workout_id = wk.workout_id
        GROUP BY fw.week_start
        ORDER BY fw.week_start ASC;
    """
    with get_db() as db:
        rows = db.exec_driver_sql(sql, (weeks,)).fetchall()
    return [
        {
            "week_start": r[0].isoformat(),
            "wpw": int(r[1] or 0),
            "spw": int(r[2] or 0),
            "rpw": int(r[3] or 0),
            "dpw_avg_minutes": float(r[4] or 0),
        }
        for r in rows
    ]

@stats.get("/stats/weekday_grid")
def weekday_grid(weeks: int = Query(16, ge=1, le=104)):
    """
    Grid data: for each week_start and weekday (1=Mon..7=Sun),
    returns count and the first title of that day (by started_at).
    Uses window functions (row_number) and MOD() to avoid '%' in SQL.
    """
    sql = """
        WITH first_workout AS (
            SELECT date_trunc('week', MIN(w.started_at))::date AS first_week
            FROM workouts w
            WHERE w.started_at IS NOT NULL
        ),
        current_week AS (
            SELECT date_trunc('week', NOW())::date AS current_week
        ),
        week_series AS (
            SELECT (current_week - (generate_series(0, %s-1) * interval '1 week'))::date AS week_start
            FROM current_week
        ),
        filtered_weeks AS (
            SELECT week_start
            FROM week_series
            WHERE week_start >= (SELECT first_week FROM first_workout)
        ),
        week_day_combinations AS (
            SELECT fw.week_start, d.weekday
            FROM filtered_weeks fw
            CROSS JOIN (SELECT generate_series(1, 7) AS weekday) d
        ),
        base AS (
            SELECT
                date_trunc('week', w.started_at)::date AS week_start,
                MOD((EXTRACT(DOW FROM w.started_at)::int + 6), 7) + 1 AS weekday, -- 1..7 (Mon..Sun)
                w.started_at,
                w.id,
                COALESCE(NULLIF(TRIM(w.title), ''), 'Workout') AS title
            FROM workouts w
            WHERE w.started_at IS NOT NULL
        ),
        firsts AS (
            SELECT
                week_start,
                weekday,
                title,
                id,
                ROW_NUMBER() OVER (PARTITION BY week_start, weekday ORDER BY started_at ASC) AS rn
            FROM base
        ),
        counts AS (
            SELECT
                week_start,
                weekday,
                COUNT(*)::int AS count
            FROM base
            GROUP BY week_start, weekday
        )
        SELECT
            wdc.week_start,
            wdc.weekday,
            COALESCE(c.count, 0)::int AS count,
            COALESCE(f.title, '') AS title,
            f.id AS workout_id
        FROM week_day_combinations wdc
        LEFT JOIN counts c ON c.week_start = wdc.week_start AND c.weekday = wdc.weekday
        LEFT JOIN firsts f ON f.week_start = wdc.week_start AND f.weekday = wdc.weekday AND f.rn = 1
        ORDER BY wdc.week_start ASC, wdc.weekday ASC;
    """
    with get_db() as db:
        rows = db.exec_driver_sql(sql, (weeks,)).fetchall()
    return [
        {
            "week_start": r[0].isoformat(),
            "weekday": int(r[1]),
            "count": int(r[2]),
            "title": r[3],
            "workout_id": r[4],
        }
        for r in rows
    ]




@stats.get("/stats/muscle_sets_weekly")
def muscle_sets_weekly(weeks: int = Query(16, ge=1, le=104)):
    """
    Returns total SETS per muscle group per week.
    Uses custom muscle groups if user preference is set to 'custom', otherwise uses Hevy's primary muscle groups.
    """
    with get_db() as db:
        # Check user's mapping preference
        preference_result = db.exec_driver_sql(
            "SELECT mapping_type FROM mapping_preferences WHERE user_id = %s",
            ("default_user",)
        ).fetchone()
        
        mapping_type = preference_result[0] if preference_result else "hevy"
        
        if mapping_type == "custom":
            # Use custom muscle group mappings
            sql = """
                WITH first_workout AS (
                    SELECT date_trunc('week', MIN(w.started_at))::date AS first_week
                    FROM workouts w
                    WHERE w.started_at IS NOT NULL
                ),
                current_week AS (
                    SELECT date_trunc('week', NOW())::date AS current_week
                ),
                week_series AS (
                    SELECT (current_week - (generate_series(0, %s-1) * interval '1 week'))::date AS week_start
                    FROM current_week
                ),
                filtered_weeks AS (
                    SELECT week_start
                    FROM week_series
                    WHERE week_start >= (SELECT first_week FROM first_workout)
                ),
                labeled AS (
                    SELECT
                        date_trunc('week', w.started_at)::date AS week_start,
                        INITCAP(COALESCE(cmg.name, e.primary_muscle_group, 'Other')) AS muscle
                    FROM sets s
                    JOIN workouts w ON w.id = s.workout_id
                    LEFT JOIN exercises e ON e.exercise_title = s.exercise_title
                    LEFT JOIN exercise_custom_mappings ecm ON ecm.exercise_title = s.exercise_title AND ecm.user_id = 'default_user'
                    LEFT JOIN custom_muscle_groups cmg ON cmg.id = ecm.custom_muscle_group_id
                    WHERE w.started_at IS NOT NULL
                )
                SELECT
                    fw.week_start,
                    COALESCE(l.muscle, 'Other') AS muscle,
                    COUNT(l.muscle)::int AS sets
                FROM filtered_weeks fw
                LEFT JOIN labeled l ON l.week_start = fw.week_start
                GROUP BY fw.week_start, l.muscle
                ORDER BY fw.week_start ASC, l.muscle ASC;
            """
        else:
            # Use Hevy's primary muscle groups (default)
            sql = """
                WITH first_workout AS (
                    SELECT date_trunc('week', MIN(w.started_at))::date AS first_week
                    FROM workouts w
                    WHERE w.started_at IS NOT NULL
                ),
                current_week AS (
                    SELECT date_trunc('week', NOW())::date AS current_week
                ),
                week_series AS (
                    SELECT (current_week - (generate_series(0, %s-1) * interval '1 week'))::date AS week_start
                    FROM current_week
                ),
                filtered_weeks AS (
                    SELECT week_start
                    FROM week_series
                    WHERE week_start >= (SELECT first_week FROM first_workout)
                ),
                labeled AS (
                    SELECT
                        date_trunc('week', w.started_at)::date AS week_start,
                        INITCAP(COALESCE(e.primary_muscle_group, 'Other')) AS muscle
                    FROM sets s
                    JOIN workouts w ON w.id = s.workout_id
                    LEFT JOIN exercises e ON e.exercise_title = s.exercise_title
                    WHERE w.started_at IS NOT NULL
                )
                SELECT
                    fw.week_start,
                    COALESCE(l.muscle, 'Other') AS muscle,
                    COUNT(l.muscle)::int AS sets
                FROM filtered_weeks fw
                LEFT JOIN labeled l ON l.week_start = fw.week_start
                GROUP BY fw.week_start, l.muscle
                ORDER BY fw.week_start ASC, l.muscle ASC;
            """
        
        rows = db.exec_driver_sql(sql, (weeks,)).fetchall()
        return [
            {"week_start": r[0].isoformat(), "muscle": r[1], "sets": int(r[2] or 0)}
            for r in rows
        ]







sync_router = APIRouter()


@sync_router.post("/sync/hevy")
def sync_hevy(page: int = 1, page_size: int = 10):
    try:
        result = sync_first_page(page=page, page_size=page_size)
        return result
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Mount routers
app.include_router(api)
app.include_router(stats)
app.include_router(sync_router)

@app.get("/")
def root():
    return {"service": "hevy-tracker-api", "ok": True}

