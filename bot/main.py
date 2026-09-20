"""Telegram-бот, який друкує записки на Citizen CT-E351."""
from __future__ import annotations

import io
import logging
import re
import time
from datetime import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ChatAction, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import texts as T
from .config import Config, load_config
from .dt import now_in, parse_datetime
from .printing import PrinterError, check_printer, print_image
from .render import Receipt, preview_frame, render_receipt

log = logging.getLogger("printer-bot")

CHOOSING_TYPE, ENTER_DATETIME, ENTER_NAME, ASK_MORE, ENTER_COPIES, CONFIRM = range(6)

KEY_PROCEDURE = "procedure_key"
KEY_WHEN = "when"
KEY_NAMES = "names"
KEY_COPIES = "copies"
KEY_SHEET = "sheet"

PREVIEW_NAMES = 15

ACTIVE_MEMBER_STATUSES = frozenset({
    ChatMemberStatus.OWNER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
})
ACCESS_TTL = 300.0
ACCESS_DENY_TTL = 60.0


# Клавіатури
def kb(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def kb_types() -> ReplyKeyboardMarkup:
    return kb([[p.button] for p in T.PROCEDURES])


def kb_datetime() -> ReplyKeyboardMarkup:
    return kb([[T.BTN_NOW], [T.BTN_CANCEL]])


def kb_more() -> ReplyKeyboardMarkup:
    return kb([[T.BTN_MORE, T.BTN_DONE], [T.BTN_CANCEL]])


def kb_copies() -> ReplyKeyboardMarkup:
    return kb([list(T.COPY_PRESETS), [T.BTN_CANCEL]])


def kb_confirm() -> ReplyKeyboardMarkup:
    return kb([[T.BTN_PRINT], [T.BTN_CANCEL]])


# Допоміжне
def cfg_of(context: ContextTypes.DEFAULT_TYPE) -> Config:
    return context.application.bot_data["cfg"]


async def allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Доступ мають учасники дозволеного чату та явно вказані id."""
    user = update.effective_user
    if user is None:
        return False
    cfg = cfg_of(context)
    if not cfg.restricted:
        return True
    if user.id in cfg.allowed_user_ids:
        return True
    if not cfg.allowed_chat_id:
        return False

    cache: dict[int, tuple[bool, float]] = context.application.bot_data.setdefault(
        "access_cache", {}
    )
    now = time.monotonic()
    cached = cache.get(user.id)
    if cached and cached[1] > now:
        return cached[0]

    try:
        member = await context.bot.get_chat_member(cfg.allowed_chat_id, user.id)
        if member.status == ChatMemberStatus.RESTRICTED:
            ok = bool(getattr(member, "is_member", False))
        else:
            ok = member.status in ACTIVE_MEMBER_STATUSES
    except TelegramError as exc:
        log.warning("Перевірка чату %s для %s не вдалася: %s",
                    cfg.allowed_chat_id, user.id, exc)
        ok = False

    cache[user.id] = (ok, now + (ACCESS_TTL if ok else ACCESS_DENY_TTL))
    return ok


def build_receipt(context: ContextTypes.DEFAULT_TYPE) -> Receipt:
    data = context.user_data
    procedure = T.PROCEDURE_BY_KEY[data[KEY_PROCEDURE]]
    when: datetime = data[KEY_WHEN]
    return Receipt(procedure_title=procedure.title, when=when,
                   names=list(data.get(KEY_NAMES, [])))


def summary(context: ContextTypes.DEFAULT_TYPE, sheet_height: int,
            cfg: Config) -> str:
    data = context.user_data
    procedure = T.PROCEDURE_BY_KEY[data[KEY_PROCEDURE]]
    when: datetime = data[KEY_WHEN]
    listed = data.get(KEY_NAMES, [])
    # підпис до фото в Telegram обмежений 1024 символами
    shown = listed[:PREVIEW_NAMES]
    names = "\n".join(f"  • {n}" for n in shown)
    if len(listed) > PREVIEW_NAMES:
        names += f"\n  … і ще {len(listed) - PREVIEW_NAMES}"
    return (
        f"*Перевірте перед друком*\n\n"
        f"Тип: {procedure.button}\n"
        f"Дата: {when.strftime('%d.%m.%Y')}\n"
        f"Час: {when.strftime('%H:%M')}\n"
        f"Імена:\n{names}\n"
        f"Копій: {data[KEY_COPIES]}\n"
        f"Листок: {cfg.print_width // cfg.dots_per_mm}×"
        f"{sheet_height // cfg.dots_per_mm} мм"
    )


async def send_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = cfg_of(context)
    sheet = render_receipt(cfg, build_receipt(context))
    context.user_data[KEY_SHEET] = sheet
    image = preview_frame(sheet)
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
    await update.message.reply_photo(
        photo=buffer,
        caption=summary(context, sheet.height, cfg),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_confirm(),
    )


# Кроки діалогу
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await allowed(update, context):
        await update.message.reply_text(T.NOT_ALLOWED,
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(T.GREETING, reply_markup=kb_types())
    return CHOOSING_TYPE


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    procedure = T.PROCEDURE_BY_BUTTON.get(update.message.text.strip())
    if procedure is None:
        await update.message.reply_text(T.ASK_TYPE, reply_markup=kb_types())
        return CHOOSING_TYPE
    context.user_data[KEY_PROCEDURE] = procedure.key
    await update.message.reply_text(T.ASK_DATETIME,
                                    parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=kb_datetime())
    return ENTER_DATETIME


async def enter_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cfg = cfg_of(context)
    raw = update.message.text.strip()
    if raw == T.BTN_NOW:
        when = now_in(cfg.timezone).replace(tzinfo=None)
    else:
        when = parse_datetime(raw, cfg.timezone)
    if when is None:
        await update.message.reply_text(T.BAD_DATETIME,
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=kb_datetime())
        return ENTER_DATETIME
    context.user_data[KEY_WHEN] = when
    context.user_data[KEY_NAMES] = []
    await update.message.reply_text(
        f"Дата й час: *{when.strftime('%d.%m.%Y %H:%M')}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(T.ASK_FIRST_NAME, parse_mode=ParseMode.MARKDOWN)
    return ENTER_NAME


async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # можна надіслати одразу список — по імені в рядку
    added = [" ".join(line.split()) for line in update.message.text.splitlines()]
    added = [name for name in added if len(name) >= 2]
    if not added:
        await update.message.reply_text(T.BAD_NAME)
        return ENTER_NAME
    context.user_data.setdefault(KEY_NAMES, []).extend(added)
    listed = "\n".join(f"{i}. {n}" for i, n in
                       enumerate(context.user_data[KEY_NAMES], start=1))
    await update.message.reply_text(f"Додано:\n{listed}\n\n{T.ASK_MORE}",
                                    reply_markup=kb_more())
    return ASK_MORE


async def ask_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    if choice == T.BTN_MORE:
        await update.message.reply_text(T.ASK_NEXT_NAME,
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=ReplyKeyboardRemove())
        return ENTER_NAME
    if choice == T.BTN_DONE:
        await update.message.reply_text(T.ASK_COPIES, reply_markup=kb_copies())
        return ENTER_COPIES
    await update.message.reply_text(T.ASK_MORE, reply_markup=kb_more())
    return ASK_MORE


async def enter_copies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cfg = cfg_of(context)
    raw = update.message.text.strip()
    try:
        copies = int(raw)
    except ValueError:
        copies = 0
    if not 1 <= copies <= cfg.max_copies:
        await update.message.reply_text(
            T.BAD_COPIES.format(max_copies=cfg.max_copies),
            reply_markup=kb_copies(),
        )
        return ENTER_COPIES
    context.user_data[KEY_COPIES] = copies
    await send_preview(update, context)
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.strip() != T.BTN_PRINT:
        await update.message.reply_text("Оберіть дію 👇", reply_markup=kb_confirm())
        return CONFIRM

    cfg = cfg_of(context)
    copies = context.user_data[KEY_COPIES]
    notice = await update.message.reply_text(T.PRINTING,
                                             reply_markup=ReplyKeyboardRemove())
    sheet = context.user_data.get(KEY_SHEET) or render_receipt(cfg, build_receipt(context))
    try:
        await print_image(cfg, sheet, copies)
    except PrinterError as exc:
        log.exception("Друк не вдався")
        await notice.edit_text(
            f"❌ Не вдалося надрукувати.\n\n`{exc}`\n\n"
            f"Принтер: `{cfg.describe_printer()}`\n"
            f"Натисніть /start, щоб спробувати ще раз.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    await notice.edit_text(f"✅ Готово. Надруковано копій: {copies}.\n/start — нова записка")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(T.CANCELLED, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Команди
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    await update.message.reply_text(T.HELP, parse_mode=ParseMode.MARKDOWN)


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    cfg = cfg_of(context)
    try:
        detail = await check_printer(cfg)
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(
            f"❌ Принтер недоступний\n`{cfg.describe_printer()}`\n\n`{exc}`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    await update.message.reply_text(f"✅ Принтер на зв'язку\n`{detail}`",
                                    parse_mode=ParseMode.MARKDOWN)


async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(f"Ваш Telegram id: `{user.id}`",
                                    parse_mode=ParseMode.MARKDOWN)


async def chatid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує id чату — потрібне для налаштування ALLOWED_CHAT_ID."""
    chat = update.effective_chat
    await update.message.reply_text(
        f"id цього чату: `{chat.id}`\nтип: {chat.type}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        await update.message.reply_text(T.NOT_ALLOWED)
        return
    await update.message.reply_text(T.UNKNOWN)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Необроблена помилка", exc_info=context.error)


async def post_init(application: Application) -> None:
    cfg: Config = application.bot_data["cfg"]
    log.info("Принтер: %s", cfg.describe_printer())
    log.info("Листок: %s", cfg.paper_size)
    log.info("Доступ: %s", cfg.describe_access())


def build_application(cfg: Config) -> Application:
    application = (
        Application.builder()
        .token(cfg.bot_token)
        .post_init(post_init)
        .build()
    )
    application.bot_data["cfg"] = cfg

    private = filters.ChatType.PRIVATE
    text = filters.TEXT & ~filters.COMMAND & private
    # «Скасувати» має ловитися на будь-якому кроці, тому йде першою
    cancel_button = MessageHandler(
        filters.Regex(f"^{re.escape(T.BTN_CANCEL)}$"), cancel
    )

    def state(handler) -> list:
        return [cancel_button, MessageHandler(text, handler)]

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start, filters=private)],
        states={
            CHOOSING_TYPE: state(choose_type),
            ENTER_DATETIME: state(enter_datetime),
            ENTER_NAME: state(enter_name),
            ASK_MORE: state(ask_more),
            ENTER_COPIES: state(enter_copies),
            CONFIRM: state(confirm),
        },
        fallbacks=[
            CommandHandler("cancel", cancel, filters=private),
            CommandHandler("start", start, filters=private),
            cancel_button,
        ],
        allow_reentry=True,
    )

    application.add_handler(conversation)
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("whoami", whoami_cmd))
    application.add_handler(CommandHandler("chatid", chatid_cmd))
    application.add_handler(MessageHandler(filters.ALL & private, fallback))
    application.add_error_handler(on_error)
    return application


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    cfg = load_config()
    if not cfg.bot_token:
        raise SystemExit("BOT_TOKEN не заданий. Скопіюйте .env.example у .env.")

    application = build_application(cfg)
    log.info("Бот запускається…")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
