from __future__ import annotations

import enum
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_APPROVAL = "awaiting_approval"


class ApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    VARIANTS_REQUESTED = "variants_requested"
    PREMIUM_REQUESTED = "premium_requested"


class AssetType(str, enum.Enum):
    RESEARCH_BRIEF = "research_brief"
    STYLE_GUIDE = "style_guide"
    SCRIPT = "script"
    CHARACTER_BIBLE = "character_bible"
    SHOT_LIST = "shot_list"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FLOW_PROMPT_PACK = "flow_prompt_pack"
    RETENTION_CURVE = "retention_curve"
    ANALYTICS = "analytics"
    REVENUE = "revenue"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    niche: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True
    )
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="IDEA")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    stages: Mapped[List["JobStage"]] = relationship(
        "JobStage", back_populates="job", cascade="all, delete-orphan", order_by="JobStage.started_at"
    )
    assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="job", cascade="all, delete-orphan"
    )
    analytics: Mapped[List["Analytics"]] = relationship(
        "Analytics", back_populates="job", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="job", cascade="all, delete-orphan"
    )
    costs: Mapped[List["Cost"]] = relationship(
        "Cost", back_populates="job", cascade="all, delete-orphan"
    )
    revenue_streams: Mapped[List["RevenueStream"]] = relationship(
        "RevenueStream", back_populates="job", cascade="all, delete-orphan"
    )
    retention_curves: Mapped[List["RetentionCurve"]] = relationship(
        "RetentionCurve", back_populates="job", cascade="all, delete-orphan"
    )


class JobStage(Base):
    __tablename__ = "job_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus), default=StageStatus.PENDING, nullable=False, index=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    output_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="stages")

    __table_args__ = (Index("ix_job_stages_job_stage", "job_id", "stage_name", unique=True),)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="assets")


class Analytics(Base):
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    video_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    views: Mapped[int] = mapped_column(BigInteger, default=0)
    watch_time_seconds: Mapped[int] = mapped_column(BigInteger, default=0)
    retention_pct: Mapped[Optional[float]] = mapped_column(nullable=True)
    ctr: Mapped[Optional[float]] = mapped_column(nullable=True)
    revenue_usd: Mapped[Optional[float]] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    raw_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    job: Mapped["Job"] = relationship("Job", back_populates="analytics")


class StyleGuide(Base):
    __tablename__ = "style_guides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    source_video_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extracted_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    visual_dna_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    hook_formulas_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    character_bible_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    insights_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class CharacterBible(Base):
    __tablename__ = "character_bible"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    reference_images_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    style_guide_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("style_guides.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decision: Mapped[Optional[ApprovalDecision]] = mapped_column(Enum(ApprovalDecision), nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="approvals")


class Cost(Base):
    __tablename__ = "costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    usd_estimate: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="costs")


class SkillManifest(Base):
    __tablename__ = "skill_manifests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    yaml_content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class HookFormula(Base):
    __tablename__ = "hook_formulas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    retention_data_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(default=0.0)
    avg_retention_3s: Mapped[float] = mapped_column(default=0.0)
    last_used: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class RevenueStream(Base):
    __tablename__ = "revenue_streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    job: Mapped["Job"] = relationship("Job", back_populates="revenue_streams")


class RetentionCurve(Base):
    __tablename__ = "retention_curves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    time_points_json: Mapped[List[float]] = mapped_column(JSON, default=list)
    retention_values_json: Mapped[List[float]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="retention_curves")


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    agent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, index=True)