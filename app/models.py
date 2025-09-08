from datetime import datetime
from typing import Optional
from sqlalchemy import (
    DateTime, Integer, Numeric, String, Text, func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_title: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    type: Mapped[Optional[str]] = mapped_column(String(100))
    primary_muscle_group: Mapped[Optional[str]] = mapped_column(String(100))
    secondary_muscle_group: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class Set(Base):
    __tablename__ = "sets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workout_id: Mapped[str] = mapped_column(String(64), nullable=False)
    exercise_index: Mapped[Optional[int]] = mapped_column(Integer)
    set_index: Mapped[Optional[int]] = mapped_column(Integer)
    exercise_title: Mapped[Optional[str]] = mapped_column(String(200))
    type: Mapped[Optional[str]] = mapped_column(String(100))
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(10, 3))
    reps: Mapped[Optional[int]] = mapped_column(Integer)
    distance_meters: Mapped[Optional[float]] = mapped_column(Numeric(10, 3))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    rpe: Mapped[Optional[float]] = mapped_column(Numeric(4, 2))
    custom_metric: Mapped[Optional[str]] = mapped_column(String(200))

class CustomMuscleGroup(Base):
    __tablename__ = "custom_muscle_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)  # If I add multi-user in the future?
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ExerciseCustomMapping(Base):
    __tablename__ = "exercise_custom_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_title: Mapped[str] = mapped_column(String(200), nullable=False)
    custom_muscle_group_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)  # If I add multi-user in the future?
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('exercise_title', 'user_id', name='uq_exercise_custom_mapping'),
    )


class MappingPreference(Base):
    __tablename__ = "mapping_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)  # If I add multi-user in the future?
    mapping_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'hevy' or 'custom'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', name='uq_mapping_preference_user'),
    )

class WeeklyComment(Base):
    __tablename__ = "weekly_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)  # If I add multi-user in the future?
    week_start: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD format
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'week_start', name='uq_weekly_comment_user_week'),
    )
