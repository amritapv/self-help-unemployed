"""
Telegram bot for UNMAPPED — same flow as the web ChatView, in Telegram.

Architecture:
  Telegram <-> long-poll <-> this process <-> HTTP <-> FastAPI on localhost
                                              ^
                                              |
                                  same /chat, /assess-skills,
                                  /match-opportunities the web app uses

Session state (per-chat conversation history, collected data, profile_id) lives
in SQLite via api.repository. Survives restarts; no in-memory state.

Run with:
    python -m api.telegram_bot

Environment variables (in .env):
    TELEGRAM_BOT_TOKEN    - from @BotFather (required)
    UNMAPPED_API_URL      - defaults to http://localhost:8000
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from api import repository
from api.transcribe import transcribe

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

API_URL = os.environ.get("UNMAPPED_API_URL", "http://localhost:8000")
DEFAULT_COUNTRY = "GH"
DEFAULT_LANGUAGE = "en"

GREETING = (
    "Hi! I'm UNMAPPED — I help you understand your skills and find work that fits.\n\n"
    "Tell me about your educational background — formal schooling, certifications, "
    "or any training you've done."
)

HELP = (
    "Commands:\n"
    "/start — start (or restart) the assessment\n"
    "/reset — wipe my memory of you and start fresh\n"
    "/country GH | IN — set your country (default: GH)\n"
    "/help — this message"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("unmapped.telegram")


# ── Session helpers ───────────────────────────────────────────────────────────

def load_session(chat_id: int) -> dict:
    sess = repository.get_telegram_session(chat_id)
    if sess is None:
        sess = {
            "chat_id": chat_id,
            "messages": [],
            "collected_data": None,
            "profile_id": None,
            "country_code": DEFAULT_COUNTRY,
            "language": DEFAULT_LANGUAGE,
        }
    return sess


def save_session(sess: dict) -> None:
    repository.upsert_telegram_session(
        chat_id=sess["chat_id"],
        messages=sess["messages"],
        collected_data=sess["collected_data"],
        profile_id=sess["profile_id"],
        country_code=sess["country_code"],
        language=sess["language"],
    )


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    repository.delete_telegram_session(chat_id)
    sess = load_session(chat_id)
    sess["messages"] = [{"role": "assistant", "content": GREETING}]
    save_session(sess)
    await update.message.reply_text(GREETING)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repository.delete_telegram_session(update.effective_chat.id)
    await update.message.reply_text("Cleared. Run /start when you're ready.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP)


async def cmd_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    code = (args[0].upper() if args else "")
    if code not in ("GH", "IN"):
        await update.message.reply_text("Usage: /country GH or /country IN")
        return
    sess = load_session(update.effective_chat.id)
    sess["country_code"] = code
    save_session(sess)
    await update.message.reply_text(f"Country set to {code}.")


# ── Message handler (the conversation engine) ─────────────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = (update.message.text or "").strip()
    if not user_text:
        return
    sess = load_session(update.effective_chat.id)
    await _process_user_text(update, context, sess, user_text)


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Voice note or uploaded audio -> Whisper -> same flow as a typed message."""
    chat_id = update.effective_chat.id
    media = update.message.voice or update.message.audio
    if media is None:
        return

    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

    try:
        tg_file = await media.get_file()
        audio_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception as exc:
        log.exception("voice download failed: %s", exc)
        await update.message.reply_text("Couldn't download that audio. Mind retrying?")
        return

    try:
        # Transcription is blocking — run off the event loop so other handlers stay responsive.
        text, detected_lang, lang_prob = await asyncio.to_thread(transcribe, audio_bytes)
    except Exception as exc:
        log.exception("transcription failed: %s", exc)
        await update.message.reply_text("Sorry, I couldn't transcribe that. Try typing instead?")
        return

    if not text:
        await update.message.reply_text("I didn't catch anything in that audio. Try again?")
        return

    # Echo what we heard so the user can correct typos quickly
    await update.message.reply_text(f'🎙️ "{text}"')

    sess = load_session(chat_id)

    # Auto-detect language: if Whisper is confident and text is long enough,
    # update the session so Claude responds in the right language.
    if detected_lang and lang_prob >= 0.85 and len(text) >= 10 and detected_lang != sess["language"]:
        log.info("chat %s language: %s -> %s (prob %.2f)", chat_id, sess["language"], detected_lang, lang_prob)
        sess["language"] = detected_lang

    await _process_user_text(update, context, sess, text)


async def _process_user_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    sess: dict,
    user_text: str,
) -> None:
    """Shared core: append the user turn, call /chat, and either continue the
    conversation or run the full assessment when Claude flags ready."""
    chat_id = update.effective_chat.id

    if not sess["messages"]:
        # User started chatting without /start — seed the greeting silently
        sess["messages"] = [{"role": "assistant", "content": GREETING}]

    sess["messages"].append({"role": "user", "content": user_text})

    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

    async with httpx.AsyncClient(timeout=120.0) as client:
        chat_data = await _post_chat(client, sess)
        if chat_data is None:
            await update.message.reply_text(
                "I'm having trouble reaching the assessment service. Try /reset and try again."
            )
            return

        assistant_msg = (chat_data.get("message") or "").replace("[READY_FOR_ASSESSMENT]", "").strip()
        sess["messages"].append({"role": "assistant", "content": assistant_msg})

        if chat_data.get("ready_for_assessment") and chat_data.get("collected_data"):
            sess["collected_data"] = chat_data["collected_data"]
            save_session(sess)

            if assistant_msg:
                await update.message.reply_text(assistant_msg)
            await update.message.reply_text("Analyzing your profile…")
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

            profile = await _post_assess(client, sess)
            if profile is None:
                await update.message.reply_text(
                    "Couldn't build your skills profile. Try /reset and walk through again."
                )
                return
            sess["profile_id"] = profile.get("profile_id")
            save_session(sess)

            opps_data = await _post_match(client, sess, profile)
            if opps_data is None:
                await update.message.reply_text(
                    "Skills profile is built, but I couldn't fetch opportunities. "
                    "Try /reset to retry."
                )
                return

            await update.message.reply_text(
                _format_results(profile, opps_data),
                parse_mode=None,  # plain text — safest with arbitrary Claude output
            )
            return

        save_session(sess)
        if assistant_msg:
            await update.message.reply_text(assistant_msg)


# ── HTTP wrappers ─────────────────────────────────────────────────────────────

async def _post_chat(client: httpx.AsyncClient, sess: dict) -> dict | None:
    try:
        r = await client.post(
            f"{API_URL}/chat",
            json={
                "messages": sess["messages"],
                "country_code": sess["country_code"],
                "language": sess["language"],
            },
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.exception("/chat failed: %s", exc)
        return None


async def _post_assess(client: httpx.AsyncClient, sess: dict) -> dict | None:
    try:
        r = await client.post(
            f"{API_URL}/assess-skills",
            json={
                **(sess["collected_data"] or {}),
                "country_code": sess["country_code"],
                "language": sess["language"],
            },
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.exception("/assess-skills failed: %s", exc)
        return None


async def _post_match(client: httpx.AsyncClient, sess: dict, profile: dict) -> dict | None:
    try:
        r = await client.post(
            f"{API_URL}/match-opportunities",
            json={
                "skills_profile": profile,
                "country_code": sess["country_code"],
                "language": sess["language"],
            },
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.exception("/match-opportunities failed: %s", exc)
        return None


# ── Output formatting ─────────────────────────────────────────────────────────

def _format_results(profile: dict, opps_data: dict) -> str:
    """Plain-text Telegram message: portable summary + top 5 opportunities."""
    lines: list[str] = []
    summary = (profile.get("portable_summary") or "").strip()
    if summary:
        lines.append("YOUR PROFILE")
        lines.append(summary)
        lines.append("")

    risk = profile.get("automation_risk") or {}
    risk_summary = (risk.get("plain_language_summary") or "").strip()
    if risk_summary:
        lines.append("AUTOMATION OUTLOOK")
        lines.append(risk_summary)
        lines.append("")

    opportunities = opps_data.get("opportunities") or []
    if not opportunities:
        note = opps_data.get("note") or "No opportunities matched yet."
        lines.append(note)
        return "\n".join(lines)

    lines.append(f"TOP {min(5, len(opportunities))} OPPORTUNITIES")
    for i, opp in enumerate(opportunities[:5], 1):
        lines.append("")
        lines.append(f"{i}. {opp.get('title', '?')}")
        if path := opp.get("employer_or_path"):
            lines.append(f"   {path}")
        if fit := opp.get("fit_explanation"):
            lines.append(f"   • Why it fits: {fit}")
        if wage := opp.get("wage_range"):
            lines.append(f"   • Wage: {wage}")
        if growth := opp.get("sector_growth_signal"):
            lines.append(f"   • Outlook: {growth}")
        if gap := opp.get("skill_gap"):
            lines.append(f"   • Gap: {gap}")
        if step := opp.get("next_step"):
            lines.append(f"   • Next step: {step}")

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN not set. Get one from @BotFather and add to .env."
        )

    repository.init_db()  # ensure telegram_sessions table exists

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("country", cmd_country))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))

    log.info("Bot polling against %s — Ctrl-C to stop.", API_URL)
    app.run_polling()


if __name__ == "__main__":
    main()
