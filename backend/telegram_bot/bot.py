from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from backend.config import get_settings
from backend.vault import get_pending_approvals, get_job, get_jobs, log_event

settings = get_settings()

logger = logging.getLogger(__name__)

application: Optional[Application] = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    text = (
        "🎬 <b>CONTENT-FACTORY Bot</b>\n\n"
        "Commands:\n"
        "/goal <niche> <freq> <platforms> - Set content goal\n"
        "/status - Pipeline overview\n"
        "/pending - Pending approvals\n"
        "/approve <job_id> - Approve current stage\n"
        "/reject <job_id> <reason> - Reject with reason\n"
        "/variants <job_id> [n] - Request N new variants\n"
        "/preview <job_id> - Preview script/video\n"
        "/premium <job_id> - Get Flow/Veo prompt pack\n"
        "/upload_premium <job_id> - Upload premium video (reply with video)\n"
        "/post <job_id> - Manually trigger posting\n"
        "/analyze <job_id> - Run analytics on completed job\n"
        "/cost - Cost summary\n"
        "/report - Weekly analytics report\n"
        "/help - Show this help"
    )
    await update.message.reply_html(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: /goal <niche> <frequency_per_week> <platforms>\n"
            "Example: /goal finance 3 tiktok,youtube,instagram"
        )
        return

    niche = args[0]
    try:
        freq = int(args[1])
    except ValueError:
        await update.message.reply_text("Frequency must be a number")
        return

    platforms = [p.strip() for p in args[2].split(",")]
    valid_platforms = {"tiktok", "youtube", "instagram", "x", "linkedin", "facebook"}
    platforms = [p for p in platforms if p in valid_platforms]

    if not platforms:
        await update.message.reply_text("No valid platforms. Use: tiktok, youtube, instagram, x, linkedin, facebook")
        return

    # Create goal via Manager (would integrate with actual agent)
    from backend.vault import create_job
    job = await create_job(
        niche=niche,
        config={
            "frequency": freq,
            "platforms": platforms,
            "approval_mode": settings.default_approval_mode,
        },
    )

    await update.message.reply_html(
        f"✅ <b>Goal Set</b>\n"
        f"Niche: <b>{niche}</b>\n"
        f"Frequency: <b>{freq}/week</b>\n"
        f"Platforms: <b>{', '.join(platforms)}</b>\n"
        f"Job ID: <code>{job.id}</code>\n\n"
        f"Research will start at {settings.daily_research_hour}:00 daily."
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    from backend.vault import get_jobs
    from backend.vault.models import JobStatus

    jobs = await get_jobs(limit=10)
    if not jobs:
        await update.message.reply_text("No jobs yet. Use /goal to create one.")
        return

    lines = ["📊 <b>Pipeline Status</b>\n"]
    for job in jobs:
        status_emoji = {
            JobStatus.PENDING: "⏳",
            JobStatus.RUNNING: "🔄",
            JobStatus.PAUSED: "⏸",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
            JobStatus.CANCELLED: "🚫",
        }.get(job.status, "❓")

        lines.append(
            f"{status_emoji} Job <code>{job.id}</code> | {job.niche} | "
            f"Stage: <b>{job.current_stage}</b> | {job.status.value}"
        )

    await update.message.reply_html("\n".join(lines))


async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    approvals = await get_pending_approvals()
    if not approvals:
        await update.message.reply_text("✅ No pending approvals")
        return

    lines = ["⏳ <b>Pending Approvals</b>\n"]
    for a in approvals:
        job = await get_job(a.job_id)
        lines.append(
            f"Job <code>{a.job_id}</code> ({job.niche if job else '?'}) | "
            f"Stage: <b>{a.stage}</b> | Since: {a.requested_at.strftime('%H:%M')}"
        )

    await update.message.reply_html("\n".join(lines))


async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve <job_id>")
        return

    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be a number")
        return

    from backend.vault import get_pending_approvals, resolve_approval
    from backend.vault.models import ApprovalDecision

    approvals = await get_pending_approvals()
    approval = next((a for a in approvals if a.job_id == job_id), None)

    if not approval:
        await update.message.reply_text(f"No pending approval for job {job_id}")
        return

    await resolve_approval(approval.id, ApprovalDecision.APPROVED, str(user_id), "Approved via Telegram")
    await update.message.reply_text(f"✅ Job {job_id} approved. Pipeline will continue.")


async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reject <job_id> <reason>")
        return

    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be a number")
        return

    reason = " ".join(context.args[1:])

    from backend.vault import get_pending_approvals, resolve_approval
    from backend.vault.models import ApprovalDecision

    approvals = await get_pending_approvals()
    approval = next((a for a in approvals if a.job_id == job_id), None)

    if not approval:
        await update.message.reply_text(f"No pending approval for job {job_id}")
        return

    await resolve_approval(approval.id, ApprovalDecision.REJECTED, str(user_id), reason)
    await update.message.reply_text(f"❌ Job {job_id} rejected: {reason}")


async def variants_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /variants <job_id> [count]")
        return

    try:
        job_id = int(context.args[0])
        count = int(context.args[1]) if len(context.args) > 1 else 3
    except ValueError:
        await update.message.reply_text("Job ID and count must be numbers")
        return

    from backend.vault import log_event
    await log_event("INFO", "telegram", f"Variants requested: {count} for job {job_id}", {"job_id": job_id, "user_id": user_id})

    await update.message.reply_text(f"🔄 Requested {count} new variants for job {job_id}. Scriptwriter will generate them.")


async def preview_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /preview <job_id>")
        return

    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be a number")
        return

    from backend.vault import get_job_assets
    scripts = await get_job_assets(job_id, asset_type="script")
    videos = await get_job_assets(job_id, asset_type="video")

    if scripts:
        latest = scripts[-1]
        meta = latest.metadata_json
        text = (
            f"📝 <b>Script Preview - Job {job_id}</b>\n\n"
            f"<b>Title:</b> {meta.get('title', 'N/A')}\n"
            f"<b>Hook:</b> {meta.get('hook', 'N/A')[:200]}...\n"
            f"<b>CTA:</b> {meta.get('cta', 'N/A')}\n"
            f"<b>Hashtags:</b> {' '.join(meta.get('hashtags', []))}\n"
        )
        await update.message.reply_html(text)
    elif videos:
        await update.message.reply_text(f"Video available at: {videos[-1].path}")
    else:
        await update.message.reply_text("No script or video found for this job")


async def cost_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    from backend.vault import get_total_costs
    from datetime import datetime, timedelta

    daily = await get_total_costs(since=datetime.utcnow() - timedelta(days=1))
    weekly = await get_total_costs(since=datetime.utcnow() - timedelta(days=7))
    monthly = await get_total_costs(since=datetime.utcnow() - timedelta(days=30))

    await update.message.reply_html(
        f"💰 <b>Cost Summary</b>\n\n"
        f"Today: <b>${daily:.4f}</b>\n"
        f"Week: <b>${weekly:.4f}</b>\n"
        f"Month: <b>${monthly:.4f}</b>\n\n"
        f"Budget: ${settings.daily_budget_usd}/day, ${settings.monthly_budget_usd}/month"
    )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    await update.message.reply_text("📊 Weekly report generation not yet implemented")


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /premium <job_id>")
        return

    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be a number")
        return

    await update.message.reply_text(
        f"🎬 <b>Premium Prompt Pack for Job {job_id}</b>\n\n"
        f"Feature not yet implemented. Will generate:\n"
        f"• Flow character reference prompts\n"
        f"• Veo scene-by-scene prompts\n"
        f"• Style guide for Nano Banana",
        parse_mode="HTML"
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Unknown command. Use /help")


async def upload_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /upload_premium <job_id> (then reply with video)")
        return

    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be a number")
        return

    from backend.vault import get_job
    job = await get_job(job_id)
    if not job:
        await update.message.reply_text(f"Job {job_id} not found")
        return

    if job.current_stage != "AWAITING_PREMIUM":
        await update.message.reply_text(f"Job {job_id} is not awaiting premium upload (stage: {job.current_stage})")
        return

    from backend.vault.repository import get_session
    async with get_session() as session:
        session.add(job)
        if not job.config_json:
            job.config_json = {}
        job.config_json.update({"awaiting_premium_upload": True, "premium_uploader_id": user_id})
        await session.commit()
    await update.message.reply_text(
        f"📥 Ready for premium upload for Job {job_id}.\n"
        f"Reply to this message with the video file (MP4/MOV)."
    )


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        return

    from backend.vault import get_job, add_asset
    import os
    import shutil

    jobs = await get_jobs()
    target_job = None
    for job in jobs:
        if job.config_json and job.config_json.get("awaiting_premium_upload") and job.config_json.get("premium_uploader_id") == user_id:
            target_job = job
            break

    if not target_job:
        return

    video = update.message.video or update.message.document
    if not video:
        return

    file = await context.bot.get_file(video.file_id)
    upload_dir = f"backend/vault/uploads/premium/{target_job.id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"premium_{video.file_id}.mp4")

    await file.download_to_drive(file_path)

    await add_asset(
        job_id=target_job.id,
        asset_type="video",
        path=file_path,
        metadata={"source": "premium_upload", "uploader_id": user_id}
    )

    from backend.vault.repository import get_session
    async with get_session() as session:
        session.add(target_job)
        if not target_job.config_json:
            target_job.config_json = {}
        target_job.config_json.update({
            "awaiting_premium_upload": False,
            "premium_uploader_id": None,
        })
        await session.commit()

    await update.message.reply_text(
        f"✅ Premium video uploaded for Job {target_job.id}.\n"
        f"Pipeline will continue to QC2."
    )


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /post <job_id>")
        return

    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be a number")
        return

    from backend.vault import get_job
    from backend.agents import PosterAgent

    job = await get_job(job_id)
    if not job:
        await update.message.reply_text(f"Job {job_id} not found")
        return

    from backend.scheduler import _db_job_to_agent_job
    agent_job = _db_job_to_agent_job(job)

    await update.message.reply_text(f"📤 Posting Job {job_id}...")
    result = await PosterAgent().run(agent_job)

    if result.success:
        await update.message.reply_text(
            f"✅ Posted successfully!\n"
            f"Platforms: {result.output.get('posted', 0)} posted, {result.output.get('failed', 0)} failed"
        )
    else:
        await update.message.reply_text(f"❌ Posting failed: {result.error}")


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in settings.allowed_user_ids:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /analyze <job_id>")
        return

    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be a number")
        return

    from backend.vault import get_job
    from backend.agents import AnalystAgent

    job = await get_job(job_id)
    if not job:
        await update.message.reply_text(f"Job {job_id} not found")
        return

    from backend.scheduler import _db_job_to_agent_job
    agent_job = _db_job_to_agent_job(job)

    await update.message.reply_text(f"📊 Analyzing Job {job_id}...")
    result = await AnalystAgent().run(agent_job)

    if result.success:
        out = result.output
        await update.message.reply_html(
            f"✅ Analysis complete!\n\n"
            f"Jobs analyzed: <b>{out.get('analyzed_jobs', 0)}</b>\n"
            f"Insights: <b>{len(out.get('insights', []))}</b>\n"
            f"Recommendations: <b>{len(out.get('recommendations', []))}</b>\n\n"
            f"Top insight: {out.get('insights', ['None'])[0] if out.get('insights') else 'None'}"
        )
    else:
        await update.message.reply_text(f"❌ Analysis failed: {result.error}")


def create_application() -> Application:
    global application
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

    application = Application.builder().token(settings.telegram_bot_token).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("goal", goal_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("reject", reject_command))
    application.add_handler(CommandHandler("variants", variants_command))
    application.add_handler(CommandHandler("preview", preview_command))
    application.add_handler(CommandHandler("cost", cost_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("upload_premium", upload_premium_command))
    application.add_handler(CommandHandler("post", post_command))
    application.add_handler(CommandHandler("analyze", analyze_command))

    # Video handler for premium uploads
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.MimeType("video/mp4"), handle_video_upload))

    # Fallback
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    return application


async def start_bot() -> None:
    global application
    if application is None:
        application = create_application()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Telegram bot started")


async def stop_bot() -> None:
    global application
    if application:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Telegram bot stopped")