import enum
from datetime import datetime

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AWAITING_PREMIUM = "AWAITING_PREMIUM"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class StageStatus(str, enum.Enum):
    IDEA = "IDEA"
    RESEARCH = "RESEARCH"
    SCRIPT = "SCRIPT"
    QC1 = "QC1"
    STYLE = "STYLE"
    ART = "ART"
    VIDEO = "VIDEO"
    QC2 = "QC2"
    POST = "POST"
    ANALYZE = "ANALYZE"

class ApprovalDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class AssetType(str, enum.Enum):
    SCRIPT = "SCRIPT"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"

try:
    from sqlalchemy.orm import declarative_base, mapped_column, Mapped
    from sqlalchemy import String, Integer, Float, Enum, JSON, DateTime, ForeignKey, Boolean, Text
    Base = declarative_base()
except ImportError:
    class Base:
        pass
    def mapped_column(*args, **kwargs):
        return None
    class _Mapped:
        def __class_getitem__(cls, item):
            return item
    Mapped = _Mapped
    class _ColType:
        def __init__(self, *args, **kwargs):
            pass
    String = Integer = Float = Enum = JSON = DateTime = ForeignKey = Boolean = Text = _ColType

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    niche: Mapped[str] = mapped_column(String(255))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    current_stage: Mapped[StageStatus] = mapped_column(Enum(StageStatus), default=StageStatus.IDEA)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class JobStage(Base):
    __tablename__ = "job_stages"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    stage: Mapped[StageStatus] = mapped_column(Enum(StageStatus))
    output: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    file_path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    stage: Mapped[StageStatus] = mapped_column(Enum(StageStatus))
    decision: Mapped[ApprovalDecision] = mapped_column(Enum(ApprovalDecision))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Analytics(Base):
    __tablename__ = "analytics"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    retention_rate: Mapped[float] = mapped_column(Float, default=0.0)

class Cost(Base):
    __tablename__ = "costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    agent_name: Mapped[str] = mapped_column(String(100))
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    usd_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StyleGuide(Base):
    __tablename__ = "style_guides"
    id: Mapped[int] = mapped_column(primary_key=True)
    niche: Mapped[str] = mapped_column(String(255))
    data: Mapped[dict] = mapped_column(JSON, default=dict)

class CharacterBible(Base):
    __tablename__ = "character_bibles"
    id: Mapped[int] = mapped_column(primary_key=True)
    niche: Mapped[str] = mapped_column(String(255), default="General")
    data: Mapped[dict] = mapped_column(JSON, default=dict)

class HookFormula(Base):
    __tablename__ = "hook_formulas"
    id: Mapped[int] = mapped_column(primary_key=True)
    formula: Mapped[str] = mapped_column(String(512))
    virality_score: Mapped[float] = mapped_column(Float, default=0.0)

class RevenueStream(Base):
    __tablename__ = "revenue_streams"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    channel: Mapped[str] = mapped_column(String(100), default="TikTok Creator Rewards")

class RetentionCurve(Base):
    __tablename__ = "retention_curves"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    curve_data: Mapped[dict] = mapped_column(JSON, default=dict)

class SkillManifest(Base):
    __tablename__ = "skill_manifests"
    id: Mapped[int] = mapped_column(primary_key=True)
    skill: Mapped[str] = mapped_column(String(255))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)

class Log(Base):
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
