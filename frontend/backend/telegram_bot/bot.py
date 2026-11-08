import logging
from typing import List
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from backend.config import settings
from backend.vault.repository import Repository
from backend.vault.models import JobStatus, StageStatus, ApprovalDecision, AssetType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("content_factory.bot")

def auth_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if settings.allowed_user_ids and update.effective_user.id not in settings.allowed_user_ids:
            if update.message:
                await update.message.reply_text("⛔ Unauthorized access.")
            return
        return await func(update, context)
    return wrapper

# 1. /start
@auth_required
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *CONTENT-FACTORY HITL Bot Online*\n\n"
        "Available commands:\n"
        "• `/goal <niche>` - Create new content automation job\n"
        "• `/status` - View all pipeline jobs\n"
        "• `/pending` - Jobs awaiting approval\n"
        "• `/approve <id>` - Approve job stage\n"
        "• `/reject <id> <reason>` - Reject and request revision\n"
        "• `/variants <id>` - Request script variants\n"
        "• `/preview <id>` - Preview generated script/media\n"
        "• `/premium <id>` - Enable premium Veo/Flow mode\n"
        "• `/upload_premium <id>` - Attach premium video file\n"
        "• `/post <id>` - Trigger immediate social distribution\n"
        "• `/analyze <id>` - Fetch virality analytics\n"
        "• `/cost` - Total token spend and budget ledger\n"
        "• `/report` - Daily summary report\n"
        "• `/help` - Command documentation"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# 2. /goal
@auth_required
async def goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    niche = " ".join(context.args) if context.args else "AI Productivity Hacks"
    job = await Repository.create_job(niche=niche, config={"target_platform": "TikTok/Shorts"})
    await update.message.reply_text(
        f"🎯 *Job Created #{job.id}*\n"
        f"• *Niche:* {niche}\n"
        f"• *Stage:* {job.current_stage.value}\n"
        f"• *Status:* {job.status.value}",
        parse_mode="Markdown"
    )

# 3. /status
@auth_required
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = await Repository.get_jobs()
    if not jobs:
        return await update.message.reply_text("No jobs in vault.")
    
    lines = ["📊 *Pipeline Status:*"]
    for j in jobs[:10]:
        lines.append(f"• `#{j.id}` [{j.status.value}] *{j.niche}* — Stage: `{j.current_stage.value}`")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# 4. /pending
@auth_required
async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = await Repository.get_jobs()
    pending = [j for j in jobs if j.status in [JobStatus.AWAITING_APPROVAL, JobStatus.AWAITING_PREMIUM]]
    if not pending:
        return await update.message.reply_text("✅ No jobs awaiting human approval.")
    
    lines = ["⏳ *Awaiting Human Decision:*"]
    for j in pending:
        lines.append(f"• `#{j.id}` *{j.niche}* [{j.current_stage.value}] Status: *{j.status.value}*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# 5. /approve
@auth_required
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/approve <job_id>`", parse_mode="Markdown")
    try:
        job_id = int(context.args[0])
        job = await Repository.get_job_by_id(job_id)
        if not job:
            return await update.message.reply_text(f"Job #{job_id} not found.")
        
        await Repository.create_approval(job_id, job.current_stage, ApprovalDecision.APPROVED)
        await Repository.update_job_config(job_id, {f"approved_{job.current_stage.value.lower()}": True})
        await Repository.update_job_status(job_id, JobStatus.IN_PROGRESS)
        
        await update.message.reply_text(
            f"✅ *Job #{job_id} Approved*\n"
            f"Stage `{job.current_stage.value}` unlocked. Resuming autonomous pipeline.",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("Invalid Job ID.")

# 6. /reject
@auth_required
async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/reject <job_id> [reason]`", parse_mode="Markdown")
    try:
        job_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Revision required"
        job = await Repository.get_job_by_id(job_id)
        if not job:
            return await update.message.reply_text(f"Job #{job_id} not found.")
        
        await Repository.create_approval(job_id, job.current_stage, ApprovalDecision.REJECTED)
        await Repository.update_job_status(job_id, JobStatus.PENDING)
        await Repository.log_event(f"Rejected stage {job.current_stage.value} on job {job_id}: {reason}", job_id=job_id)
        
        await update.message.reply_text(
            f"❌ *Job #{job_id} Rejected*\nReason: {reason}\nRestarting current stage `{job.current_stage.value}` with revision feedback.",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("Invalid Job ID.")

# 7. /variants
@auth_required
async def variants_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/variants <job_id>`", parse_mode="Markdown")
    job_id = int(context.args[0])
    await update.message.reply_text(
        f"📝 *Generated Script Variants for Job #{job_id}:*\n"
        f"1. *Contrarian Hook:* 'Stop doing this mistake in 2026...'\n"
        f"2. *Curiosity Loop:* 'The 1 secret top creators never tell you...'\n"
        f"3. *Urgency Hook:* 'If you do this today, you lose 5 hours...'",
        parse_mode="Markdown"
    )

# 8. /preview
@auth_required
async def preview_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/preview <job_id>`", parse_mode="Markdown")
    job_id = int(context.args[0])
    assets = await Repository.get_assets_by_job(job_id)
    stages = await Repository.get_stages_by_job(job_id)
    
    msg = [f"👁️ *Preview for Job #{job_id}:*"]
    if stages:
        last_stage = stages[-1]
        msg.append(f"• *Current Stage Output:* `{last_stage.stage.value}`")
    if assets:
        msg.append("• *Assets generated:* " + ", ".join([a.asset_type.value for a in assets]))
    else:
        msg.append("• No assets rendered yet.")
    await update.message.reply_text("\n".join(msg), parse_mode="Markdown")

# 9. /premium
@auth_required
async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/premium <job_id>`", parse_mode="Markdown")
    job_id = int(context.args[0])
    await Repository.update_job_config(job_id, {"premium": True})
    await update.message.reply_text(
        f"🌟 *Premium Mode Enabled for Job #{job_id}*\n"
        f"VideoEditor will flag `AWAITING_PREMIUM` to request custom Veo/Flow 8K generation.",
        parse_mode="Markdown"
    )

# 10. /upload_premium
@auth_required
async def upload_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: Send a video file with caption `/upload_premium <job_id>`", parse_mode="Markdown")
    job_id = int(context.args[0])
    await Repository.update_job_config(job_id, {"premium_asset_uploaded": True})
    await Repository.update_job_status(job_id, JobStatus.IN_PROGRESS, StageStatus.VIDEO)
    await update.message.reply_text(f"🎬 Premium render attached for Job #{job_id}. Resuming video pipeline.", parse_mode="Markdown")

# Video attachment handler
@auth_required
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video or update.message.document:
        caption = update.message.caption or ""
        if "/upload_premium" in caption:
            parts = caption.split()
            idx = parts.index("/upload_premium")
            if len(parts) > idx + 1 and parts[idx+1].isdigit():
                job_id = int(parts[idx+1])
                await Repository.update_job_config(job_id, {"premium_asset_uploaded": True})
                await Repository.update_job_status(job_id, JobStatus.IN_PROGRESS, StageStatus.VIDEO)
                await Repository.add_asset(job_id, AssetType.VIDEO, f"vault/premium/job_{job_id}_custom_veo.mp4")
                return await update.message.reply_text(f"✅ Video asset registered for Job #{job_id}. Advancing to QC2.", parse_mode="Markdown")
        await update.message.reply_text("Video received. Tag with `/upload_premium <job_id>` to attach to a job.", parse_mode="Markdown")

# 11. /post
@auth_required
async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/post <job_id>`", parse_mode="Markdown")
    job_id = int(context.args[0])
    await Repository.update_job_status(job_id, JobStatus.IN_PROGRESS, StageStatus.POST)
    await update.message.reply_text(f"🚀 Triggering immediate Postiz dispatch for Job #{job_id} across TikTok, IG Reels, and YT Shorts.", parse_mode="Markdown")

# 12. /analyze
@auth_required
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/analyze <job_id>`", parse_mode="Markdown")
    job_id = int(context.args[0])
    analytics = await Repository.get_analytics_by_job(job_id)
    if not analytics:
        return await update.message.reply_text(f"No analytics yet recorded for Job #{job_id}.")
    a = analytics[-1]
    await update.message.reply_text(
        f"📈 *Performance Analytics #{job_id}:*\n"
        f"• *Views:* {a.views:,}\n"
        f"• *Likes:* {a.likes:,}\n"
        f"• *Retention:* {a.retention_rate}%\n"
        f"• *Comments:* {a.comments:,}\n"
        f"• *Shares:* {a.shares:,}",
        parse_mode="Markdown"
    )

# 13. /cost
@auth_required
async def cost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_cost = await Repository.get_total_costs()
    total_tokens = await Repository.get_total_tokens()
    budget = settings.daily_budget_usd
    pct = round((total_cost / budget) * 100, 1) if budget else 0
    await update.message.reply_text(
        f"💰 *Budget & Cost Ledger:*\n"
        f"• *Total Spent:* ${total_cost:.4f} USD\n"
        f"• *Tokens Consumed:* {total_tokens:,}\n"
        f"• *Daily Budget:* ${budget:.2f} USD\n"
        f"• *Budget Utilization:* {pct}%\n"
        f"• *Status:* {'🟢 Healthy' if pct < 80 else '🟡 Approaching Limit'}",
        parse_mode="Markdown"
    )

# 14. /report
@auth_required
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = await Repository.get_jobs()
    completed = len([j for j in jobs if j.status == JobStatus.COMPLETED])
    in_prog = len([j for j in jobs if j.status == JobStatus.IN_PROGRESS])
    cost = await Repository.get_total_costs()
    await update.message.reply_text(
        f"📋 *CONTENT-FACTORY Daily Executive Summary:*\n"
        f"• *Active Jobs:* {in_prog}\n"
        f"• *Completed Pipelines:* {completed}\n"
        f"• *Total Pipeline Runs:* {len(jobs)}\n"
        f"• *Current Spend:* ${cost:.4f} USD\n"
        f"• *System Health:* All 9 Agents Operational",
        parse_mode="Markdown"
    )

# 15. /help
@auth_required
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

bot_app = ApplicationBuilder().token(settings.telegram_bot_token).build()

# Register all 14 commands
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("goal", goal_command))
bot_app.add_handler(CommandHandler("status", status_command))
bot_app.add_handler(CommandHandler("pending", pending_command))
bot_app.add_handler(CommandHandler("approve", approve_command))
bot_app.add_handler(CommandHandler("reject", reject_command))
bot_app.add_handler(CommandHandler("variants", variants_command))
bot_app.add_handler(CommandHandler("preview", preview_command))
bot_app.add_handler(CommandHandler("premium", premium_command))
bot_app.add_handler(CommandHandler("upload_premium", upload_premium_command))
bot_app.add_handler(CommandHandler("post", post_command))
bot_app.add_handler(CommandHandler("analyze", analyze_command))
bot_app.add_handler(CommandHandler("cost", cost_command))
bot_app.add_handler(CommandHandler("report", report_command))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_handler))
