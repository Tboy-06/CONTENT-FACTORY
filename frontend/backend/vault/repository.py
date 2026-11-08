from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, func, update, delete
from backend.config import settings
from backend.vault.models import (
    Base, Job, JobStage, Asset, Approval, Analytics, Cost,
    StyleGuide, CharacterBible, HookFormula, RevenueStream,
    RetentionCurve, SkillManifest, Log,
    JobStatus, StageStatus, ApprovalDecision, AssetType
)

engine = create_async_engine(settings.effective_database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class Repository:
    # 1. Job Operations
    @staticmethod
    async def create_job(niche: str, config: dict = None) -> Job:
        async with AsyncSessionLocal() as session:
            job = Job(niche=niche, config=config or {})
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return job

    @staticmethod
    async def get_jobs():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Job).order_by(Job.id.desc()))
            return res.scalars().all()

    @staticmethod
    async def get_job_by_id(job_id: int):
        async with AsyncSessionLocal() as session:
            return await session.get(Job, job_id)

    @staticmethod
    async def get_completed_jobs_count() -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED))
            return int(res.scalar() or 0)

    @staticmethod
    async def get_active_jobs_count() -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(func.count(Job.id)).where(Job.status != JobStatus.COMPLETED))
            return int(res.scalar() or 0)

    @staticmethod
    async def update_job_status(job_id: int, status: JobStatus, stage: StageStatus = None):
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = status
                if stage:
                    job.current_stage = stage
                await session.commit()
                return job
            return None

    @staticmethod
    async def update_job_config(job_id: int, config: dict):
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            if job:
                job.config = {**(job.config or {}), **config}
                await session.commit()
                return job
            return None

    @staticmethod
    async def delete_job(job_id: int):
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            if job:
                await session.delete(job)
                await session.commit()
                return True
            return False

    # 2. Stage Operations
    @staticmethod
    async def create_stage(job_id: int, stage: StageStatus, output: dict = None):
        async with AsyncSessionLocal() as session:
            st = JobStage(job_id=job_id, stage=stage, output=output or {})
            session.add(st)
            await session.commit()
            await session.refresh(st)
            return st

    @staticmethod
    async def get_stages_by_job(job_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(JobStage).where(JobStage.job_id == job_id).order_by(JobStage.id.asc()))
            return res.scalars().all()

    @staticmethod
    async def update_stage_output(stage_id: int, output: dict):
        async with AsyncSessionLocal() as session:
            st = await session.get(JobStage, stage_id)
            if st:
                st.output = output
                await session.commit()
                return st
            return None

    # 3. Asset Operations
    @staticmethod
    async def add_asset(job_id: int, asset_type: AssetType, file_path: str):
        async with AsyncSessionLocal() as session:
            asset = Asset(job_id=job_id, asset_type=asset_type, file_path=file_path)
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
            return asset

    @staticmethod
    async def get_assets_by_job(job_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Asset).where(Asset.job_id == job_id).order_by(Asset.id.asc()))
            return res.scalars().all()

    @staticmethod
    async def delete_asset(asset_id: int):
        async with AsyncSessionLocal() as session:
            asset = await session.get(Asset, asset_id)
            if asset:
                await session.delete(asset)
                await session.commit()
                return True
            return False

    # 4. Approval Operations
    @staticmethod
    async def create_approval(job_id: int, stage: StageStatus, decision: ApprovalDecision):
        async with AsyncSessionLocal() as session:
            approval = Approval(job_id=job_id, stage=stage, decision=decision)
            session.add(approval)
            await session.commit()
            await session.refresh(approval)
            return approval

    @staticmethod
    async def get_approvals_by_job(job_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Approval).where(Approval.job_id == job_id).order_by(Approval.id.desc()))
            return res.scalars().all()

    # 5. Cost Tracking Operations
    @staticmethod
    async def record_cost(job_id: int, agent_name: str, tokens: int, usd_estimate: float):
        async with AsyncSessionLocal() as session:
            c = Cost(job_id=job_id, agent_name=agent_name, tokens=tokens, usd_estimate=usd_estimate)
            session.add(c)
            await session.commit()
            await session.refresh(c)
            return c

    @staticmethod
    async def get_total_costs() -> float:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(func.sum(Cost.usd_estimate)))
            return res.scalar() or 0.0

    @staticmethod
    async def get_total_tokens() -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(func.sum(Cost.tokens)))
            return res.scalar() or 0

    @staticmethod
    async def get_costs_by_job(job_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Cost).where(Cost.job_id == job_id).order_by(Cost.id.asc()))
            return res.scalars().all()

    @staticmethod
    async def get_costs_by_agent():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Cost.agent_name, func.sum(Cost.usd_estimate), func.sum(Cost.tokens)).group_by(Cost.agent_name))
            return res.all()

    # 6. Analytics Operations
    @staticmethod
    async def record_analytics(job_id: int, views: int, likes: int, comments: int = 0, shares: int = 0, retention_rate: float = 0.0):
        async with AsyncSessionLocal() as session:
            a = Analytics(job_id=job_id, views=views, likes=likes, comments=comments, shares=shares, retention_rate=retention_rate)
            session.add(a)
            await session.commit()
            await session.refresh(a)
            return a

    @staticmethod
    async def get_analytics_by_job(job_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Analytics).where(Analytics.job_id == job_id))
            return res.scalars().all()

    @staticmethod
    async def get_analytics_by_niche(niche: str):
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(Analytics, Job)
                .join(Job, Analytics.job_id == Job.id)
                .where(Job.niche == niche)
            )
            return res.all()

    @staticmethod
    async def get_total_views() -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(func.coalesce(func.sum(Analytics.views), 0)))
            return int(res.scalar() or 0)

    # 7. Style Guides
    @staticmethod
    async def upsert_style_guide(niche: str, data: dict):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(StyleGuide).where(StyleGuide.niche == niche))
            existing = res.scalars().first()
            if existing:
                existing.data = data
                await session.commit()
                return existing
            sg = StyleGuide(niche=niche, data=data)
            session.add(sg)
            await session.commit()
            await session.refresh(sg)
            return sg

    @staticmethod
    async def get_style_guides():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(StyleGuide))
            return res.scalars().all()

    @staticmethod
    async def get_style_guide_by_niche(niche: str):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(StyleGuide).where(StyleGuide.niche == niche))
            return res.scalars().first()

    # 8. Character Bible
    @staticmethod
    async def upsert_character_bible(niche: str, data: dict):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CharacterBible).where(CharacterBible.niche == niche))
            existing = res.scalars().first()
            if existing:
                existing.data = data
                await session.commit()
                return existing
            cb = CharacterBible(niche=niche, data=data)
            session.add(cb)
            await session.commit()
            await session.refresh(cb)
            return cb

    @staticmethod
    async def get_character_bibles():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CharacterBible))
            return res.scalars().all()

    # 9. Hook Formulas
    @staticmethod
    async def upsert_hook_formula(formula: str, virality_score: float = 0.0):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(HookFormula).where(HookFormula.formula == formula))
            existing = res.scalars().first()
            if existing:
                existing.virality_score = virality_score
                await session.commit()
                return existing
            hf = HookFormula(formula=formula, virality_score=virality_score)
            session.add(hf)
            await session.commit()
            await session.refresh(hf)
            return hf

    @staticmethod
    async def get_hook_formulas():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(HookFormula).order_by(HookFormula.virality_score.desc()))
            return res.scalars().all()

    # 10. Revenue Streams
    @staticmethod
    async def record_revenue(job_id: int, amount: float, channel: str = "TikTok Creator Rewards"):
        async with AsyncSessionLocal() as session:
            rev = RevenueStream(job_id=job_id, amount=amount, channel=channel)
            session.add(rev)
            await session.commit()
            await session.refresh(rev)
            return rev

    @staticmethod
    async def get_total_revenue() -> float:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(func.sum(RevenueStream.amount)))
            return res.scalar() or 0.0

    # 11. Retention Curves
    @staticmethod
    async def record_retention_curve(job_id: int, curve_data: dict):
        async with AsyncSessionLocal() as session:
            rc = RetentionCurve(job_id=job_id, curve_data=curve_data)
            session.add(rc)
            await session.commit()
            await session.refresh(rc)
            return rc

    @staticmethod
    async def get_retention_curve(job_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(RetentionCurve).where(RetentionCurve.job_id == job_id).order_by(RetentionCurve.id.desc()))
            return res.scalars().first()

    # 12. Skill Manifests
    @staticmethod
    async def register_skill(skill: str, parameters: dict):
        async with AsyncSessionLocal() as session:
            sm = SkillManifest(skill=skill, parameters=parameters)
            session.add(sm)
            await session.commit()
            await session.refresh(sm)
            return sm

    @staticmethod
    async def get_skills():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(SkillManifest))
            return res.scalars().all()

    # 13. Logging
    @staticmethod
    async def log_event(message: str, job_id: int = None):
        async with AsyncSessionLocal() as session:
            l = Log(message=message, job_id=job_id)
            session.add(l)
            await session.commit()
            return l

    @staticmethod
    async def get_logs(limit: int = 50):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Log).order_by(Log.id.desc()).limit(limit))
            return res.scalars().all()
