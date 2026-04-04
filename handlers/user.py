from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import json
from datetime import datetime
from io import BytesIO

import database as db
from database import normalize_service
from config import (
    ADMIN_IDS,
    CARD_NUMBER,
    CARD_OWNER,
    BOT_USERNAME,
    BONUS_JOIN,
    BONUS_ORDER_PCT,
    get_tier,
    TIER_LABELS,
    TIER_THRESHOLDS,
)
from locales import t
from keyboards.user_kb import (
    main_menu, lang_keyboard, categories_keyboard, services_keyboard,
    service_detail_keyboard, cancel_keyboard, skip_cancel_keyboard, payment_method_keyboard, rating_keyboard,
    coupon_pick_keyboard, STATUS_EMOJI,
)

# Locale-driven skip/cancel matching — avoids apostrophe/emoji variation-selector mismatches
def _norm(s: str) -> str:
    """Lowercase + collapse whitespace + strip variation selectors for robust matching."""
    import unicodedata
    s = unicodedata.normalize("NFC", s or "")
    return " ".join(s.casefold().split())

def _is_skip(text: str, lang: str = "uz") -> bool:
    n = _norm(text)
    return n in (_norm(t(lang, "btn_skip")), _norm(t("uz", "btn_skip")), _norm(t("ru", "btn_skip")), "skip", "-",
                 _norm(t(lang, "skip")), _norm(t("uz", "skip")), _norm(t("ru", "skip")))

def _is_cancel(text: str, lang: str = "uz") -> bool:
    n = _norm(text)
    return n in (_norm(t(lang, "cancel")), _norm(t("uz", "cancel")), _norm(t("ru", "cancel")))

# Keep for any third-party or legacy references (not used internally anymore)
SKIP_TEXTS: list = []
CANCEL_TEXTS: list = []

router = Router()


GUIDE_REPLY_ALLOWED_EXTENSIONS = (".txt", ".json")
GUIDE_REPLY_MAX_BYTES = 512 * 1024
GUIDE_REPLY_MIN_CHARS = 12


def _delivery_reply_prompt_text(lang: str) -> str:
    if lang == "ru":
        return (
            "📌 Пожалуйста, отправьте данные, запрошенные в инструкции.\n"
            "Допустимо: текст, .txt или .json файл.\n\n"
            "Фото и другие типы файлов не принимаются.\n"
            "Если информация неполная или в неверном формате, бот попросит отправить заново."
        )
    return (
        "📌 Iltimos, qo‘llanmada so‘ralgan ma’lumotlarni yuboring.\n"
        "Qabul qilinadi: matn, .txt yoki .json fayl.\n\n"
        "Rasm va boshqa fayl turlari qabul qilinmaydi.\n"
        "Ma’lumot noto‘liq yoki noto‘g‘ri formatda yuborilsa, qayta yuborish so‘raladi."
    )


def _delivery_reply_invalid_text(lang: str) -> str:
    if lang == "ru":
        return (
            "❌ Сообщение слишком короткое или пустое.\n\n"
            "Пожалуйста, отправьте именно те данные, которые запрошены в инструкции."
        )
    return (
        "❌ Xabar juda qisqa yoki bo‘sh.\n\n"
        "Iltimos, qo‘llanmada so‘ralgan ma’lumotlarni yuboring."
    )


def _delivery_reply_invalid_file_text(lang: str) -> str:
    if lang == "ru":
        return "❌ Файл пустой, слишком большой или не читается. Пожалуйста, отправьте заново."
    return "❌ Fayl bo‘sh, juda katta yoki o‘qib bo‘lmadi. Iltimos, qayta yuboring."


def _delivery_reply_unsupported_file_text(lang: str) -> str:
    if lang == "ru":
        return "❌ Принимаются только .txt и .json файлы."
    return "❌ Faqat .txt va .json fayllar qabul qilinadi."


def _delivery_reply_session_expired_text(lang: str) -> str:
    if lang == "ru":
        return "❌ Сессия ответа истекла. Пожалуйста, свяжитесь с оператором."
    return "❌ Javob sessiyasi tugagan. Iltimos, operator bilan bog‘laning."


def _delivery_reply_success_text(lang: str) -> str:
    if lang == "ru":
        return "✅ Данные приняты. Скоро они будут проверены."
    return "✅ Ma’lumot qabul qilindi. Tez orada tekshiriladi."


def _delivery_reply_reject_other_text(lang: str) -> str:
    if lang == "ru":
        return (
            "❌ Фото и другие типы файлов не принимаются.\n\n"
            "Отправьте данные текстом, .txt или .json файлом."
        )
    return (
        "❌ Rasm va boshqa fayl turlari qabul qilinmaydi.\n\n"
        "Ma’lumotni matn, .txt yoki .json fayl ko‘rinishida yuboring."
    )


def _delivery_reply_invalid_json_text(lang: str) -> str:
    if lang == "ru":
        return "❌ Неверный формат JSON файла. Пожалуйста, исправьте ошибки и отправьте заново."
    return "❌ JSON fayl formati noto'g'ri. Iltimos, xatoliklarni to'g'rilab qayta yuboring."


def _validate_delivery_reply_text(raw_text: str, lang: str):
    text = (raw_text or "").strip()
    if not text or len(text) < GUIDE_REPLY_MIN_CHARS:
        return False, _delivery_reply_invalid_text(lang)
    
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, ensure_ascii=False, indent=2)
            return True, text
        except Exception:
            pass
            
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return True, text


async def _extract_delivery_reply_document_text(bot: Bot, document, lang: str):
    filename = (document.file_name or "").lower()

    if not filename.endswith(GUIDE_REPLY_ALLOWED_EXTENSIONS):
        return False, "", _delivery_reply_unsupported_file_text(lang)

    if document.file_size and document.file_size > GUIDE_REPLY_MAX_BYTES:
        return False, "", _delivery_reply_invalid_file_text(lang)

    buffer = BytesIO()
    await bot.download(document, destination=buffer)
    raw = buffer.getvalue()

    if not raw:
        return False, "", _delivery_reply_invalid_file_text(lang)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8-sig", errors="ignore")

    if filename.endswith(".json"):
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            return False, "", _delivery_reply_invalid_json_text(lang)

    ok, normalized = _validate_delivery_reply_text(text, lang)
    if not ok:
        return False, "", normalized

    return True, normalized, ""


async def _send_delivery_reply_as_txt_to_admin(
    bot: Bot,
    admin_id: int,
    order_id: int,
    service_name: str,
    user,
    payload_text: str,
    source_label: str,
):
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"@{user.username}" if user.username else "-"
    
    preview = payload_text[:1000] + ("\n... (qolgani faylda)" if len(payload_text) > 1000 else "")

    admin_text = (
        f"📩 <b>Yangi mijoz javobi keldi</b>\n\n"
        f"Buyurtma: #{order_id}\n"
        f"Mijoz: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Xizmat: {service_name}\n"
        f"Manba: {source_label}\n"
        f"Sana: {submitted_at}\n\n"
        f"🔎 <b>Preview:</b>\n<code>{preview}</code>"
    )

    txt_body = (
        f"Buyurtma: #{order_id}\n"
        f"Mijoz: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Xizmat: {service_name}\n"
        f"Manba: {source_label}\n"
        f"Sana: {submitted_at}\n\n"
        f"=== MIJOZ JAVOBI ===\n"
        f"{payload_text.strip()}\n"
    )

    # Convert to in-memory file to avoid temp file IO / leaks entirely
    txt_file = BufferedInputFile(
        file=txt_body.encode("utf-8"),
        filename=f"order_{order_id}_customer_reply.txt",
    )
    
    doc_caption = (
        f"📄 Buyurtma #{order_id}\n"
        f"🛍 Xizmat: {service_name}\n"
        f"👤 Mijoz: {user.full_name} ({user.id})"
    )

    await bot.send_message(admin_id, admin_text, disable_web_page_preview=True, parse_mode="HTML")
    await bot.send_document(
        admin_id,
        document=txt_file,
        caption=doc_caption,
    )


async def _finalize_delivery_reply(message: Message, state: FSMContext, payload_text: str, source_label: str):
    lang = await get_lang(message.from_user.id)
    data = await state.get_data()

    admin_id = data.get("delivery_reply_admin_id")
    order_id = data.get("delivery_reply_order_id")
    service_name = data.get("delivery_reply_service_name", "-")

    if not admin_id or not order_id:
        await state.clear()
        await message.answer(_delivery_reply_session_expired_text(lang))
        return

    await _send_delivery_reply_as_txt_to_admin(
        bot=message.bot,
        admin_id=admin_id,
        order_id=order_id,
        service_name=service_name,
        user=message.from_user,
        payload_text=payload_text,
        source_label=source_label,
    )

    await message.answer(_delivery_reply_success_text(lang))
    await state.clear()


ACTIVE_UI_MESSAGES: dict[int, set[int]] = {}


async def _delete_tracked_ui_messages(bot: Bot, chat_id: int, user_id: int):
    message_ids = list(ACTIVE_UI_MESSAGES.get(user_id, set()))
    if not message_ids:
        return

    for message_id in sorted(message_ids):
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass

    ACTIVE_UI_MESSAGES.pop(user_id, None)


def _track_ui_message(user_id: int, message_id: int):
    ACTIVE_UI_MESSAGES.setdefault(user_id, set()).add(message_id)



class OrderState(StatesGroup):
    waiting_quantity = State()
    waiting_coupon = State()
    waiting_note = State()
    waiting_payment_method = State()
    waiting_receipt = State()


class ReviewState(StatesGroup):
    waiting_comment = State()


class DeliveryGuideReplyState(StatesGroup):
    payload = State()


class DeliveryFormReplyState(StatesGroup):
    """FSM state for collecting free-form customer input after admin sends form instruction."""
    payload = State()


class SupportState(StatesGroup):
    message = State()


class SearchState(StatesGroup):
    query = State()


async def get_lang(user_id: int) -> str:
    user = await db.get_user(user_id)
    return (user["language"] or "uz") if user else "uz"


# -----------------------------------------------------------------------------
# NEW FEATURE: Referral status and Top Services handlers
# -----------------------------------------------------------------------------

@router.message(F.text.in_(["🎖 Referral", "🎖 Рефералы"]))
async def show_referral_status(message: Message):
    lang = await get_lang(message.from_user.id)
    user_id = message.from_user.id
    refs = await db.get_referral_count(user_id)
    tier_key = get_tier(refs)
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

    if tier_key == "bronze":
        remaining = TIER_THRESHOLDS["silver"] - refs
        text = t(lang, "ref_status_bronze", remaining=remaining, current_bonus=BONUS_JOIN["bronze"], next_bonus=BONUS_JOIN["silver"], ref_link=ref_link)
    elif tier_key == "silver":
        remaining = TIER_THRESHOLDS["gold"] - refs
        text = t(lang, "ref_status_silver", remaining=remaining, current_bonus=BONUS_JOIN["silver"], next_bonus=BONUS_JOIN["gold"], ref_link=ref_link)
    else:
        text = t(lang, "ref_status_gold", current_bonus=BONUS_JOIN["gold"], ref_link=ref_link)

    await message.answer(text, parse_mode="HTML")


@router.message(F.text.in_(["💡 Yordam / FAQ", "💡 Помощь / FAQ"]))
async def show_faq(message: Message):
    lang = await get_lang(message.from_user.id)
    await message.answer(t(lang, "faq_text"), parse_mode="HTML")

@router.message(F.text.in_(["⭐ Top xizmatlar", "⭐ Топ услуги", "⭐ Топ услуг"]))
async def show_top_services(message: Message):
    """
    Display a list of the most ordered services. If there are no orders,
    inform the user accordingly.
    """
    lang = await get_lang(message.from_user.id)
    # Fetch the top services from the database
    services = await db.get_top_services(limit=3)
    # If there are no orders or the highest order count is zero, show empty state
    if not services or services[0]["order_count"] == 0:
        await message.answer(t(lang, "no_top_services"))
        return
    # Construct the message header
    text = t(lang, "top_services_title")
    suffix = t(lang, "orders_suffix")
    for idx, svc in enumerate(services, start=1):
        # For each service, include its ranking, name and number of orders
        cnt = svc["order_count"]
        # Skip services with zero orders if they appear lower in the list
        if cnt == 0:
            continue
        text += f"{idx}. <b>{svc['name']}</b> — {cnt} {suffix}\n"
    await message.answer(text, parse_mode="HTML")


# START


@router.message(DeliveryGuideReplyState.payload, F.text)
async def delivery_guide_reply_text(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    ok, normalized = _validate_delivery_reply_text(message.text or "", lang)
    if not ok:
        await message.answer(normalized + "\n\n" + _delivery_reply_prompt_text(lang))
        return

    await _finalize_delivery_reply(
        message=message,
        state=state,
        payload_text=normalized,
        source_label="text",
    )


@router.message(DeliveryGuideReplyState.payload, F.document)
async def delivery_guide_reply_document(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)

    ok, payload_text, error_text = await _extract_delivery_reply_document_text(
        bot=message.bot,
        document=message.document,
        lang=lang,
    )

    if not ok:
        await message.answer(error_text + "\n\n" + _delivery_reply_prompt_text(lang))
        return

    source_label = message.document.file_name or "document"

    await _finalize_delivery_reply(
        message=message,
        state=state,
        payload_text=payload_text,
        source_label=source_label,
    )


@router.message(DeliveryGuideReplyState.payload)
async def delivery_guide_reply_reject_other(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await message.answer(_delivery_reply_reject_other_text(lang) + "\n\n" + _delivery_reply_prompt_text(lang))


# ---------------------------------------------------------------------------
# DeliveryFormReplyState — free-form customer input for service-specific forms
# ---------------------------------------------------------------------------

def _form_reply_accepted_text(lang: str) -> str:
    if lang == "ru":
        return (
            "📌 Пожалуйста, отправьте ответ на форму.\n"
            "Принимается: обычный текст, .txt или .json файл.\n\n"
            "Фото, видео, аудио и другие файлы не принимаются."
        )
    return (
        "📌 Iltimos, forma bo'yicha javobingizni yuboring.\n"
        "Qabul qilinadi: oddiy matn, .txt yoki .json fayl.\n\n"
        "Rasm, video, audio va boshqa fayl turlari qabul qilinmaydi."
    )


def _form_reply_reject_text(lang: str) -> str:
    if lang == "ru":
        return (
            "❌ Этот тип сообщения не принимается.\n\n"
            "Отправьте ответ в виде текста, .txt или .json файла."
        )
    return (
        "❌ Bu turdagi xabar qabul qilinmaydi.\n\n"
        "Javobingizni matn, .txt yoki .json fayl ko'rinishida yuboring."
    )


def _form_reply_success_text(lang: str) -> str:
    if lang == "ru":
        return "✅ Ответ принят. Пожалуйста, ожидайте."
    return "✅ Javobingiz qabul qilindi. Iltimos, kuting."


async def _finalize_form_reply(
    message: Message,
    state: FSMContext,
    payload_text: str,
    source_label: str,
):
    """Forward customer's form response to admin and acknowledge the user. Does NOT complete order."""
    lang = await get_lang(message.from_user.id)
    data = await state.get_data()

    admin_id = data.get("form_reply_admin_id")
    order_id = data.get("form_reply_order_id")
    service_name = data.get("form_reply_service_name", "-")

    if not admin_id or not order_id:
        await state.clear()
        await message.answer(_delivery_reply_session_expired_text(lang))
        return

    from datetime import datetime
    from aiogram.types import BufferedInputFile
    from keyboards.admin_kb import form_fulfilled_keyboard

    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = message.from_user
    username = f"@{user.username}" if user.username else "-"

    preview = payload_text[:800] + ("\n... (davomi faylda)" if len(payload_text) > 800 else "")

    admin_preview_text = (
        f"📋 <b>Forma javobi keldi</b>\n\n"
        f"Buyurtma: #{order_id}\n"
        f"Xizmat: {service_name}\n"
        f"Mijoz: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Manba: {source_label}\n"
        f"Sana: {submitted_at}\n\n"
        f"🔎 <b>Preview:</b>\n<code>{preview}</code>"
    )

    txt_body = (
        f"Buyurtma: #{order_id}\n"
        f"Xizmat: {service_name}\n"
        f"Mijoz: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Manba: {source_label}\n"
        f"Sana: {submitted_at}\n\n"
        f"=== MIJOZ FORMA JAVOBI ===\n"
        f"{payload_text.strip()}\n"
    )

    txt_file = BufferedInputFile(
        file=txt_body.encode("utf-8"),
        filename=f"form_order_{order_id}.txt",
    )
    doc_caption = (
        f"📄 Buyurtma #{order_id}\n"
        f"🛍 Xizmat: {service_name}\n"
        f"👤 Mijoz: {user.full_name} ({user.id})"
    )

    try:
        await message.bot.send_message(
            admin_id,
            admin_preview_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await message.bot.send_document(
            admin_id,
            document=txt_file,
            caption=doc_caption,
            reply_markup=form_fulfilled_keyboard(order_id, user.id),
        )
    except Exception:
        pass

    await state.clear()
    await message.answer(_form_reply_success_text(lang))


@router.message(DeliveryFormReplyState.payload, F.text)
async def delivery_form_reply_text(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    text = (message.text or "").strip()
    if not text:
        await message.answer(_form_reply_reject_text(lang) + "\n\n" + _form_reply_accepted_text(lang))
        return
    await _finalize_form_reply(message, state, text, "text")


@router.message(DeliveryFormReplyState.payload, F.document)
async def delivery_form_reply_document(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    document = message.document

    filename = (document.file_name or "").lower()
    if not filename.endswith((".txt", ".json")):
        await message.answer(_form_reply_reject_text(lang) + "\n\n" + _form_reply_accepted_text(lang))
        return

    if document.file_size and document.file_size > GUIDE_REPLY_MAX_BYTES:
        await message.answer(_delivery_reply_invalid_file_text(lang) + "\n\n" + _form_reply_accepted_text(lang))
        return

    from io import BytesIO
    buffer = BytesIO()
    await message.bot.download(document, destination=buffer)
    raw = buffer.getvalue()
    if not raw:
        await message.answer(_delivery_reply_invalid_file_text(lang) + "\n\n" + _form_reply_accepted_text(lang))
        return

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8-sig", errors="ignore")

    if filename.endswith(".json"):
        try:
            import json as _json
            parsed = _json.loads(text)
            text = _json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            await message.answer(_delivery_reply_invalid_json_text(lang) + "\n\n" + _form_reply_accepted_text(lang))
            return

    source_label = document.file_name or "document"
    await _finalize_form_reply(message, state, text, source_label)


@router.message(DeliveryFormReplyState.payload)
async def delivery_form_reply_reject_other(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await message.answer(_form_reply_reject_text(lang) + "\n\n" + _form_reply_accepted_text(lang))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):

    await state.clear()
    args = message.text.split(maxsplit=1)
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        ref_user = await db.get_user_by_referral(ref_code)
        if ref_user and ref_user["id"] != message.from_user.id:
            referred_by = ref_user["id"]

    user = await db.get_user(message.from_user.id)
    is_new = user is None
    await db.save_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name, referred_by)

    if referred_by and is_new:
        ref_user = await db.get_user(referred_by)
        if ref_user:
            lang_ref = ref_user["language"] or "uz"
            ref_count = await db.get_referral_count(referred_by)
            tier = get_tier(ref_count)
            bonus_amount = BONUS_JOIN[tier]
            await db.add_bonus(referred_by, bonus_amount, f"Yangi a'zo: {message.from_user.full_name}")
            updated_ref = await db.get_user(referred_by)
            new_balance = updated_ref["bonus_balance"] if updated_ref else 0
            tier_label = TIER_LABELS[tier][lang_ref]
            try:
                await message.bot.send_message(
                    referred_by,
                    t(lang_ref, "referral_bonus_notify",
                      name=message.from_user.full_name,
                      amount=bonus_amount,
                      balance=new_balance),
                    parse_mode="HTML",
                )
                
                if ref_count == TIER_THRESHOLDS["silver"]:
                    await message.bot.send_message(
                        referred_by,
                        t(lang_ref, "referral_silver_congrats", count=TIER_THRESHOLDS["silver"]),
                        parse_mode="HTML"
                    )
                elif ref_count == TIER_THRESHOLDS["gold"]:
                    await message.bot.send_message(
                        referred_by,
                        t(lang_ref, "referral_gold_congrats", count=TIER_THRESHOLDS["gold"]),
                        parse_mode="HTML"
                    )
            except Exception:
                pass

    user = await db.get_user(message.from_user.id)
    if is_new or not user or not user["language"]:
        await message.answer(t("uz", "choose_lang"), reply_markup=lang_keyboard())
        return

    lang = user["language"] or "uz"
    await message.answer(
        t(lang, "welcome", name=message.from_user.full_name),
        reply_markup=main_menu(lang),
        parse_mode="HTML",
    )


async def abandoned_cart_job(user_id: int, order_id: int, bot: Bot, lang: str):
    await asyncio.sleep(900)  # 15 minutes trigger
    try:
        from database import get_order
        order = await get_order(order_id)
        if order and order['status'] == 'pending':
            from locales import t
            await bot.send_message(user_id, t(lang, "remarketing_text"), parse_mode="HTML")
    except Exception:
        pass


# LANGUAGE

async def send_referral_intro(message: Message, user_id: int, lang: str):
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    
    if lang == "ru":
        text = (
            "🤝 <b>Приглашайте друзей и получайте бонусы!</b>\n\n"
            "За приглашенных друзей вы получаете стартовый бонус плюс процент от их первых заказов!\n\n"
            f"{TIER_LABELS['bronze']['ru']} (до {TIER_THRESHOLDS['silver']} чел):\n"
            f"• За регистрацию: <b>{BONUS_JOIN['bronze']:,} сум</b>\n"
            f"• Кэшбэк с заказа: <b>{BONUS_ORDER_PCT['bronze']}%</b>\n\n"
            f"{TIER_LABELS['silver']['ru']} (от {TIER_THRESHOLDS['silver']} чел):\n"
            f"• За регистрацию: <b>{BONUS_JOIN['silver']:,} сум</b>\n"
            f"• Кэшбэк с заказа: <b>{BONUS_ORDER_PCT['silver']}%</b>\n\n"
            f"{TIER_LABELS['gold']['ru']} (от {TIER_THRESHOLDS['gold']} чел):\n"
            f"• За регистрацию: <b>{BONUS_JOIN['gold']:,} сум</b>\n"
            f"• Кэшбэк с заказа: <b>{BONUS_ORDER_PCT['gold']}%</b>\n\n"
            f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{link}</code>"
        )
    else:
        text = (
            "🤝 <b>Do'stlaringizni taklif qiling va bonuslar oling!</b>\n\n"
            "Taklif qilingan har bir do'stingiz uchun boshlang'ich bonus hamda ularning birinchi buyurtmasidan foiz olasiz!\n\n"
            f"{TIER_LABELS['bronze']['uz']} ({TIER_THRESHOLDS['silver']} ta gacha):\n"
            f"• Ro'yxatdan o'tish bonusi: <b>{BONUS_JOIN['bronze']:,} so'm</b>\n"
            f"• Buyurtma keshbeki: <b>{BONUS_ORDER_PCT['bronze']}%</b>\n\n"
            f"{TIER_LABELS['silver']['uz']} ({TIER_THRESHOLDS['silver']} +):\n"
            f"• Ro'yxatdan o'tish bonusi: <b>{BONUS_JOIN['silver']:,} so'm</b>\n"
            f"• Buyurtma keshbeki: <b>{BONUS_ORDER_PCT['silver']}%</b>\n\n"
            f"{TIER_LABELS['gold']['uz']} ({TIER_THRESHOLDS['gold']} +):\n"
            f"• Ro'yxatdan o'tish bonusi: <b>{BONUS_JOIN['gold']:,} so'm</b>\n"
            f"• Buyurtma keshbeki: <b>{BONUS_ORDER_PCT['gold']}%</b>\n\n"
            f"🔗 <b>Sizning referal havolangiz:</b>\n<code>{link}</code>"
        )

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data.startswith("set_lang:"))
async def set_language(call: CallbackQuery):
    lang = call.data.split(":")[1]
    await db.set_user_language(call.from_user.id, lang)
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        t(lang, "welcome", name=call.from_user.full_name),
        reply_markup=main_menu(lang),
        parse_mode="HTML",
    )
    await send_referral_intro(call.message, call.from_user.id, lang)


@router.message(F.text.in_(["🌐 Til", "🌐 Язык"]))
async def change_lang(message: Message):
    await message.answer(t("uz", "choose_lang"), reply_markup=lang_keyboard())


@router.message(F.text.in_(["💬 Operatorga yozish", "💬 Написать оператору"]))
async def support_start(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await state.set_state(SupportState.message)
    await message.answer(t(lang, "support_ask"), parse_mode="HTML", reply_markup=cancel_keyboard(lang))


@router.message(SupportState.message)
async def support_message_receive(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "action_canceled"), reply_markup=main_menu(lang))
        return

    from keyboards.admin_kb import support_reply_keyboard
    admin_text = (
        f"📩 <b>Yangi murojaat:</b>\n"
        f"👤 User: {message.from_user.full_name}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
        f"💬 <b>Xabar:</b>\n{message.text}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                int(admin_id),
                admin_text,
                reply_markup=support_reply_keyboard(message.from_user.id, message.message_id),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await state.clear()
    await message.answer(t(lang, "support_sent"), reply_markup=main_menu(lang))


# CATEGORIES / SERVICES

@router.message(F.text.in_([t("uz", "services"), t("ru", "services")]))
async def show_categories(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await get_lang(user_id)

    await _delete_tracked_ui_messages(message.bot, message.chat.id, user_id)

    categories = await db.get_categories()
    stats = await db.get_stats()
    confirmed = stats["confirmed"]

    if not categories:
        services = await db.get_services(only_active=True, limit=10, offset=0)
        total_count = await db.get_services_count(only_active=True)
        if not services:
            await message.answer(t(lang, "no_services"))
            return
        sent = await message.answer(
            t(lang, "services_list", confirmed_orders=confirmed),
            reply_markup=services_keyboard(services, lang, page=1, total_count=total_count),
            parse_mode="HTML"
        )
        _track_ui_message(user_id, sent.message_id)
        return

    sent = await message.answer(
        t(lang, "categories_list", confirmed_orders=confirmed),
        reply_markup=categories_keyboard(categories, lang),
        parse_mode="HTML"
    )
    _track_ui_message(user_id, sent.message_id)


@router.callback_query(F.data == "back_categories")
async def back_to_categories(call: CallbackQuery):
    await call.answer()
    lang = await get_lang(call.from_user.id)
    categories = await db.get_categories()
    stats = await db.get_stats()
    confirmed = stats["confirmed"]

    if not categories:
        services = await db.get_services(only_active=True, limit=10, offset=0)
        total_count = await db.get_services_count(only_active=True)
        text = t(lang, "services_list", confirmed_orders=confirmed)
        markup = services_keyboard(services, lang, page=1, total_count=total_count)
        try:
            await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            try:
                await call.message.delete()
            except Exception:
                pass
            await call.message.answer(text, reply_markup=markup, parse_mode="HTML")
        return

    text = t(lang, "categories_list", confirmed_orders=confirmed)
    markup = categories_keyboard(categories, lang)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer(text, reply_markup=markup, parse_mode="HTML")


@router.message(F.text.in_(["🔍 Qidiruv", "🔍 Поиск"]))
async def search_start(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await state.set_state(SearchState.query)
    await message.answer(t(lang, "search_prompt"), reply_markup=cancel_keyboard(lang))


@router.message(SearchState.query)
async def search_execute(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "action_canceled"), reply_markup=main_menu(lang))
        return
    query = message.text.strip().lower()
    await state.clear()
    services = await db.get_services(only_active=True, query=query, limit=10, offset=0)
    total_count = await db.get_services_count(only_active=True, query=query)
    if not services:
        await message.answer(t(lang, "search_empty"), reply_markup=main_menu(lang))
        return
    await message.answer(
        f"🔍 <b>Qidiruv natijalari:</b> {total_count} ta topildi", 
        reply_markup=services_keyboard(services, lang, page=1, total_count=total_count, query=query), 
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_home")
async def back_home_callback(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    ACTIVE_UI_MESSAGES.pop(call.from_user.id, None)
    await call.message.delete()
    await call.message.answer(
        t(lang, "welcome", name=call.from_user.full_name),
        reply_markup=main_menu(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("page:"))
async def pagination_handler(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    parts = call.data.split(":", 2)
    page = int(parts[1])
    query = parts[2] if len(parts) > 2 else ""
    offset = (page - 1) * 10
    services = await db.get_services(only_active=True, query=query, limit=10, offset=offset)
    total_count = await db.get_services_count(only_active=True, query=query)
    if query:
        text = f"🔍 <b>Qidiruv natijalari:</b> {total_count} ta topildi (Sahifa {page})"
    else:
        text = t(lang, "services_list", confirmed_orders=(await db.get_stats())["confirmed"])

    await call.message.edit_text(
        text, 
        reply_markup=services_keyboard(services, lang, page=page, total_count=total_count, query=query), 
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("category:"))
async def show_category_services(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    cat_id = int(call.data.split(":")[1])
    services = await db.get_services(only_active=True, category_id=cat_id, limit=10, offset=0)
    total_count = await db.get_services_count(only_active=True, category_id=cat_id)
    cat = await db.get_category(cat_id)
    if not services:
        await call.answer(t(lang, "no_services"), show_alert=True)
        return
    await call.answer()
    _track_ui_message(call.from_user.id, call.message.message_id)
    await call.message.edit_text(
        f"<b>{cat['name']}</b>\n\n{t(lang, 'category_services_list')}",
        reply_markup=services_keyboard(services, lang, page=1, total_count=total_count, query=""),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("back_services_list"))
async def back_to_services_list(call: CallbackQuery):
    await call.answer()
    lang = await get_lang(call.from_user.id)

    parts = call.data.split(":")
    page = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

    categories = await db.get_categories()
    stats = await db.get_stats()
    confirmed = stats["confirmed"]

    try:
        await call.message.delete()
    except Exception:
        pass

    if not categories:
        offset = (page - 1) * 10
        services = await db.get_services(only_active=True, limit=10, offset=offset)
        total_count = await db.get_services_count(only_active=True)

        if not services and page > 1:
            page = 1
            offset = 0
            services = await db.get_services(only_active=True, limit=10, offset=offset)

        await call.message.answer(
            t(lang, "services_list", confirmed_orders=confirmed),
            reply_markup=services_keyboard(services, lang, page=page, total_count=total_count),
            parse_mode="HTML",
        )
        return

    await call.message.answer(
        t(lang, "categories_list", confirmed_orders=confirmed),
        reply_markup=categories_keyboard(categories, lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("service:"))
async def service_detail(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)

    parts = call.data.split(":")
    service_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1

    s = normalize_service(await db.get_service(service_id))
    if not s:
        await call.answer(t(lang, "service_not_found"), show_alert=True)
        return
    await call.answer()
    avg, cnt = await db.get_service_avg_rating(service_id)
    rating_text = t(lang, "rating_info", avg=avg, cnt=cnt) if cnt else ""
    if lang == "ru":
        desc = s["description_ru"] or s["description_uz"] or s["description"]
    else:
        desc = s["description_uz"] or s["description"]

    badge = ""
    if avg >= 4.5: badge = f"{t(lang, 'badge_rec')} | "
    elif cnt > 10: badge = f"{t(lang, 'badge_top')} | "

    cb_text = ""
    if s.get("promo_active"):
        perc = s['cashback_percent']
        perc_fmt = int(perc) if perc == int(perc) else perc
        cb_bonus = int(s['price'] * perc / 100)
        cb_text = f"\n{t(lang, 'cb_perc', percent=perc_fmt)}\n{t(lang, 'cb_amount', amount=cb_bonus)}\n"

    tiers = await db.get_bulk_prices(service_id)
    bulk_text = ""
    if tiers:
        bulk_text = f"\n{t(lang, 'bulk_title')}"
        for t_ in tiers:
            bulk_text += t(lang, 'bulk_tier', min=t_['min_quantity'], price=t_['price_per_unit'])
        bulk_text += "\n"
        
    onetime_suffix = " (bir martalik)" if lang == "uz" else " (единоразово)"
    price_text = f"{t(lang, 'service_price', price=s['price'])}{onetime_suffix}\n"
    stock_txt = (t(lang, 'stock_avail', count=s['stock']) + "\n") if s['stock'] > 0 else (f"\n{t(lang, 'stock_empty')}\n")
    urgency = f"\n{t(lang, 'urgency')}"

    text = (
        f"<b>1️⃣ {t(lang, 'services')} \u2192</b>\n\n"
        f"\U0001f4e6 <b>{badge}{s['name']}</b>\n\n"
        f"{desc}\n\n"
        f"{price_text}"
        f"{cb_text}"
        f"{bulk_text}"
        f"{stock_txt}"
        f"{rating_text}"
        f"{urgency}"
    )
    if s["image_file_id"]:
        sent = await call.message.answer_photo(
            s["image_file_id"],
            caption=text,
            reply_markup=service_detail_keyboard(service_id, lang, s["stock"], back_page=page),
            parse_mode="HTML",
        )
        _track_ui_message(call.from_user.id, sent.message_id)
    else:
        await call.message.edit_text(
            text,
            reply_markup=service_detail_keyboard(service_id, lang, s["stock"], back_page=page),
            parse_mode="HTML"
        )


async def _continue_after_coupon_choice(target_message, user_id: int, state: FSMContext, lang: str, discount: int = 0, coupon_code: str = None):
    data = await state.get_data()

    user = await db.get_user(user_id)
    balance = (user["bonus_balance"] or 0) if user else 0
    price = data["price"]
    price_after_coupon = price - (price * discount // 100)
    bonus_used = min(balance, price_after_coupon)
    final_after_bonus = price_after_coupon - bonus_used

    if bonus_used > 0:
        if final_after_bonus == 0:
            await target_message.answer(t(lang, "bonus_full_cover", amount=bonus_used), parse_mode="HTML")
        else:
            await target_message.answer(t(lang, "bonus_applied", amount=bonus_used, final=final_after_bonus), parse_mode="HTML")

    await state.update_data(discount=discount, coupon_code=coupon_code, bonus_used=bonus_used)
    await state.set_state(OrderState.waiting_note)

    note_text = f"<b>{t(lang, 'step_3')} →</b>\n\n{t(lang, 'order_note', name=data.get('service_name', 'Xizmat'))}"
    sent = await target_message.answer(note_text, reply_markup=skip_cancel_keyboard(lang), parse_mode="HTML")
    _track_ui_message(user_id, sent.message_id)


async def _show_coupon_picker_or_continue(target_message, user_id: int, state: FSMContext, lang: str):
    data = await state.get_data()
    quantity = data.get("quantity", 1)
    unit_price = data.get("unit_price", data.get("base_price", 0))
    total_price = data["price"]
    service_id = data["service_id"]

    coupons = await db.get_available_coupons_for_service(service_id)

    if coupons:
        if quantity > 1:
            price_line = f"💰 {quantity} ta x {unit_price:,} so'm = <b>{total_price:,} so'm</b>\n\n"
        else:
            price_line = f"💰 <b>{total_price:,} so'm</b>\n\n"

        picker_text = (
            "\U0001f525 Mavjud kuponlardan birini tanlang yoki o'tkazib yuboring:"
            if lang == "uz"
            else "\U0001f525 Выберите доступный купон или пропустите:"
        )

        await state.set_state(OrderState.waiting_coupon)
        sent = await target_message.answer(
            f"<b>{t(lang, 'step_3')} →</b>\n\n{price_line}{picker_text}",
            reply_markup=coupon_pick_keyboard(coupons, lang),
            parse_mode="HTML",
        )
        _track_ui_message(user_id, sent.message_id)
    else:
        await _continue_after_coupon_choice(target_message, user_id, state, lang, discount=0, coupon_code=None)


# ORDER FLOW

@router.callback_query(F.data.startswith("order:"))
async def start_order(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    service_id = int(call.data.split(":")[1])
    s = normalize_service(await db.get_service(service_id))
    if not s:
        await call.answer(t(lang, "service_not_found"), show_alert=True)
        return
    if s["stock"] == 0:
        await call.answer(t(lang, "out_of_stock"), show_alert=True)
        return
    await call.answer()
    await state.update_data(service_id=service_id, service_name=s["name"], base_price=s["price"], lang=lang)
    
    await state.update_data(supports_stars=bool(s["supports_stars"]), stars_price=s["stars_price"])
    
    await state.update_data(payment_method="manual")
    from keyboards.user_kb import quantity_keyboard
    q_txt = "Iltimos, xarid miqdorini tanlang:" if lang == "uz" else "Пожалуйста, выберите количество покупок:"
    text = f"<b>{t(lang, 'step_1')} \u2192</b>\n\n{q_txt}"
    sent = await call.message.answer(text, reply_markup=quantity_keyboard(service_id, lang), parse_mode="HTML")
    _track_ui_message(call.from_user.id, sent.message_id)

@router.callback_query(F.data.startswith("qty:"))
async def receive_preset_quantity(call: CallbackQuery, state: FSMContext):
    _, service_id_str, qty_str = call.data.split(":")
    qty = int(qty_str)
    
    data = await state.get_data()
    lang = data.get("lang", "uz")
    
    s = normalize_service(await db.get_service(int(service_id_str)))
    if s["stock"] != -1 and qty > s["stock"]:
        await call.answer(t(lang, "stock_error", stock=s["stock"]), show_alert=True)
        return
        
    await call.message.delete()
        
    unit_price = await db.get_price_for_quantity(int(service_id_str), qty, data["base_price"])
    total_price = unit_price * qty
    
    await state.update_data(quantity=qty, price=total_price, unit_price=unit_price)
    await _show_coupon_picker_or_continue(call.message, call.from_user.id, state, lang)

@router.callback_query(F.data.startswith("qty_custom:"))
async def receive_custom_quantity(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await call.message.delete()
    
    await state.set_state(OrderState.waiting_quantity)
    text = t(lang, "ask_custom_quantity")
    from keyboards.user_kb import cancel_keyboard
    await call.message.answer(text, reply_markup=cancel_keyboard(lang), parse_mode="HTML")

@router.callback_query(F.data == "cancel_quantity_prompt")
async def cancel_quantity_prompt(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    await state.clear()
    await call.answer()
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))

@router.message(OrderState.waiting_quantity)
async def receive_quantity(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
        
    try:
        qty = int(message.text)
        if qty <= 0: raise ValueError
    except ValueError:
        await message.answer(t(lang, "invalid_quantity"))
        return
        
    s = normalize_service(await db.get_service(data["service_id"]))
    if s["stock"] != -1 and qty > s["stock"]:
        await message.answer(t(lang, "stock_error", stock=s["stock"]))
        return
        
    unit_price = await db.get_price_for_quantity(data["service_id"], qty, data["base_price"])
    total_price = unit_price * qty
    
    await state.update_data(quantity=qty, price=total_price, unit_price=unit_price)
    await _show_coupon_picker_or_continue(message, message.from_user.id, state, lang)


@router.callback_query(OrderState.waiting_coupon, F.data.startswith("use_coupon:"))
async def receive_coupon_pick(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    raw = call.data.split(":", 1)[1]

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if raw == "skip":
        await call.answer()
        await _continue_after_coupon_choice(call.message, call.from_user.id, state, lang, discount=0, coupon_code=None)
        return

    coupon = await db.get_coupon(raw, service_id=data["service_id"])
    if not coupon:
        invalid_text = (
            "❌ Bu kupon endi mavjud emas yoki bu xizmatga mos emas."
            if lang == "uz"
            else "❌ Этот купон больше недоступен или не подходит для этой услуги."
        )
        await call.answer(invalid_text, show_alert=True)
        return

    discount = coupon["discount_percent"]
    coupon_code = coupon["code"]
    price = data["price"]
    final = price - (price * discount // 100)

    await call.answer()
    await call.message.answer(
        t(lang, "coupon_applied", discount=discount, final=final),
        parse_mode="HTML",
    )
    await _continue_after_coupon_choice(call.message, call.from_user.id, state, lang, discount=discount, coupon_code=coupon_code)


@router.message(OrderState.waiting_coupon)
async def receive_coupon(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    discount = 0
    coupon_code = None
    if not _is_skip(message.text, lang):
        coupon = await db.get_coupon(message.text.strip(), service_id=data["service_id"])
        if coupon:
            discount = coupon["discount_percent"]
            coupon_code = coupon["code"]
            price = data["price"]
            final = price - (price * discount // 100)
            await message.answer(t(lang, "coupon_applied", discount=discount, final=final), parse_mode="HTML")
        else:
            invalid_text = (
                "❌ Kupon noto'g'ri, faol emas yoki bu xizmat uchun mos emas."
                if lang == "uz"
                else "❌ Купон неверный, неактивен или не подходит для этой услуги."
            )
            await message.answer(invalid_text, parse_mode="HTML")
            return
    # Delegate to shared helper — ensures consistent bonus logic, message tracking and state transitions
    await _continue_after_coupon_choice(message, message.from_user.id, state, lang, discount=discount, coupon_code=coupon_code)


@router.message(OrderState.waiting_note)
async def receive_note(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if _is_cancel(message.text, lang):
        bonus_used = data.get("bonus_used", 0) or 0
        if bonus_used > 0:
            await db.add_bonus(message.from_user.id, bonus_used, "Buyurtma bekor qilindi (izoh bosqichi)")
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    note = "" if _is_skip(message.text, lang) else message.text
    discount = data.get("discount", 0)
    coupon_code = data.get("coupon_code")
    bonus_used = data.get("bonus_used", 0) or 0
    price = data["price"]
    final_price = max(0, price - (price * discount // 100) - bonus_used)
    order_id = await db.create_order(
        user_id=message.from_user.id,
        service_id=data["service_id"],
        service_name=data["service_name"],
        price=price,
        note=note,
        discount=discount,
        final_price=final_price,
        coupon_code=coupon_code,
        bonus_used=bonus_used,
        quantity=data.get("quantity", 1),
    )
    await db.decrease_stock(data["service_id"], amount=data.get("quantity", 1))
    if coupon_code:
        await db.use_coupon(coupon_code)
    if bonus_used > 0:
        await db.use_bonus(message.from_user.id, bonus_used, f"Buyurtma #{order_id}")

    import keyboards.admin_kb as adm_kb
    username = message.from_user.username or "nomalum"
    discount_text = f"\nChegirma: {discount}% | Yakuniy: {final_price:,} so'm" if discount else ""
    bonus_text = f"\n\U0001f381 Bonus: {bonus_used:,} so'm" if bonus_used else ""

    if final_price == 0:
        # Bonus covers full price — no payment needed
        await state.clear()
        await message.answer(t(lang, "order_accepted_free", order_id=order_id), reply_markup=main_menu(lang), parse_mode="HTML")
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"\U0001f514 <b>Yangi buyurtma #{order_id}</b> (Bonus bilan to'liq to'langan)\n\n"
                    f"\U0001f464 @{username} (<code>{message.from_user.id}</code>)\n"
                    f"\U0001f6cd {data['service_name']}\n"
                    f"\U0001f4b0 {price:,} so'm{discount_text}{bonus_text}\n"
                    f"\U0001f4dd {note or '—'}",
                    reply_markup=adm_kb.order_action_keyboard(order_id),
                    parse_mode="HTML",
                )
            except Exception:
                pass
    else:
        await state.update_data(order_id=order_id, final_price=final_price)
        supports_stars = data.get("supports_stars", False)
        
        if supports_stars:
            await state.set_state(OrderState.waiting_payment_method)
            from keyboards.user_kb import payment_method_keyboard
            text = f"<b>{t(lang, 'step_4')} \u2192</b>\n\nQanday usulda to'lov qilasiz? / Выберите способ оплаты:"
            sent = await message.answer(text, reply_markup=payment_method_keyboard(lang, supports_stars=True), parse_mode="HTML")
            _track_ui_message(message.from_user.id, sent.message_id)
        else:
            await state.set_state(OrderState.waiting_receipt)
            from keyboards.user_kb import cancel_keyboard
            text = f"<b>{t(lang, 'step_4')} \u2192</b>\n\n{t(lang, 'payment_info', price=final_price, card=CARD_NUMBER, owner=CARD_OWNER)}"
            await message.answer(
                text,
                reply_markup=cancel_keyboard(lang),
                parse_mode="HTML",
            )
        asyncio.create_task(abandoned_cart_job(message.from_user.id, order_id, message.bot, lang))


@router.message(OrderState.waiting_payment_method, ~F.successful_payment)
async def receive_payment_method(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    order_id = data.get("order_id")
    
    if _is_cancel(message.text, lang):
        if order_id:
            await db.update_order_status(order_id, "cancelled")
            order = await db.get_order(order_id)
            if order:
                await db.increase_stock(order["service_id"])
                bonus_used = order["bonus_used"] or 0
                if bonus_used > 0:
                    await db.add_bonus(message.from_user.id, bonus_used, f"Buyurtma #{order_id} bekor qilindi")
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return

    from keyboards.user_kb import payment_method_keyboard, cancel_keyboard
    if message.text in [t("uz", "btn_card_payment"), t("ru", "btn_card_payment")]:
        await state.update_data(payment_method="manual")
        await state.set_state(OrderState.waiting_receipt)
        final_price = data.get("final_price", data.get("price", 0))
        text = f"<b>{t(lang, 'step_4')} (Davomi) \u2192</b>\n\n{t(lang, 'payment_info', price=final_price, card=CARD_NUMBER, owner=CARD_OWNER)}"
        await message.answer(text, reply_markup=cancel_keyboard(lang), parse_mode="HTML")
    elif "Telegram Stars" in message.text and data.get("supports_stars"):
        await state.update_data(payment_method="stars")
        import uuid
        qty = data.get("quantity", 1)
        invoice_amount = data.get("stars_price", 0) * qty
        payload = f"stars_order:{order_id}:{uuid.uuid4().hex[:8]}"
        
        service_name = data.get("service_name", "Xizmat")
        await message.answer_invoice(
            title=service_name[:32].strip(),
            description=f"Buyurtma #{order_id} to'lovi",
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=service_name[:32].strip(), amount=invoice_amount)]
        )
    else:
        await message.answer("Iltimos, pastdagi tugmalardan birini tanlang.", reply_markup=payment_method_keyboard(lang, data.get("supports_stars")))


@router.message(OrderState.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    order_id = data["order_id"]
    file_id = message.photo[-1].file_id
    await db.set_order_receipt(order_id, file_id)
    await state.clear()
    await message.answer(
        t(lang, "order_accepted", order_id=order_id),
        reply_markup=main_menu(lang),
        parse_mode="HTML",
    )
    order = await db.get_order(order_id)
    import keyboards.admin_kb as adm_kb
    for admin_id in ADMIN_IDS:
        try:
            username = message.from_user.username or "nomalum"
            discount_text = f"\nChegirma: {order['discount']}% | Yakuniy: {order['final_price']:,} so'm" if order["discount"] else ""
            bonus_text = f"\n\U0001f381 Bonus: {order['bonus_used']:,} so'm" if (order["bonus_used"] or 0) > 0 else ""
            text = (
                f"\U0001f514 <b>Yangi buyurtma #{order_id}</b>\n\n"
                f"\U0001f464 @{username} (<code>{message.from_user.id}</code>)\n"
                f"\U0001f6cd {order['service_name']}\n"
                f"\U0001f4b0 {order['price']:,} so'm{discount_text}{bonus_text}\n"
                f"\U0001f4dd {order['note'] or '—'}"
            )
            await bot.send_photo(
                admin_id, file_id,
                caption=text,
                reply_markup=adm_kb.order_action_keyboard(order_id),
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.message(OrderState.waiting_receipt, ~F.successful_payment)
async def receipt_not_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if _is_cancel(message.text, lang):
        order_id = data.get("order_id")
        if order_id:
            await db.update_order_status(order_id, "cancelled")
            order = await db.get_order(order_id)
            if order:
                await db.increase_stock(order["service_id"])
                bonus_used = order["bonus_used"] or 0
                if bonus_used > 0:
                    await db.add_bonus(message.from_user.id, bonus_used, f"Buyurtma #{order_id} bekor qilindi")
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    await message.answer(t(lang, "send_photo_receipt"), parse_mode="HTML")


@router.pre_checkout_query(F.invoice_payload.startswith("stars_order:"))
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext, bot: Bot):
    payload = message.successful_payment.invoice_payload
    charge_id = message.successful_payment.telegram_payment_charge_id
    if payload and payload.startswith("stars_order:"):
        order_id = int(payload.split(":")[1])
        
        # Idempotent DB call
        success = await db.mark_order_paid_with_stars(order_id, charge_id, payload)
        if not success:
            return  # Message already processed
        
        lang = await get_lang(message.from_user.id)
        await state.clear()
        
        await message.answer(
            f"⭐️ <b>Telegram Stars orqali to'lov qabul qilindi!</b>\n\n" + t(lang, "order_accepted", order_id=order_id).replace("✅", ""),
            reply_markup=main_menu(lang),
            parse_mode="HTML",
        )
        
        order = await db.get_order(order_id)
        if not order: return
        
        import keyboards.admin_kb as adm_kb
        for admin_id in ADMIN_IDS:
            try:
                username = message.from_user.username or "nomalum"
                discount_text = f"\nChegirma: {order['discount']}% | Yakuniy (So'm ekvivalenti): {order['final_price']:,} so'm" if order["discount"] else ""
                bonus_text = f"\n\U0001f381 Bonus: {order['bonus_used']:,} so'm" if (order["bonus_used"] or 0) > 0 else ""
                text = (
                    f"⭐️ <b>Telegram Stars orqali to'landi</b>\n\n"
                    f"\U0001f514 <b>Yangi buyurtma #{order_id}</b>\n\n"
                    f"\U0001f464 @{username} (<code>{message.from_user.id}</code>)\n"
                    f"\U0001f6cd {order['service_name']}\n"
                    f"⭐️ Narx: {message.successful_payment.total_amount} XTR\n"
                    f"💳 To'lov ID: <code>{charge_id}</code>{discount_text}{bonus_text}\n"
                    f"\U0001f4dd {order['note'] or '—'}"
                )
                await bot.send_message(
                    admin_id,
                    text=text,
                    reply_markup=adm_kb.order_action_keyboard(order_id),
                    parse_mode="HTML",
                )
            except Exception:
                pass


# MY ORDERS

@router.message(F.text.in_(["📦 Buyurtmalarim", "📦 Мои заказы"]))
async def my_orders(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(message.from_user.id)
    orders = await db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer(t(lang, "no_orders"))
        return
    text = t(lang, "orders_list")
    for o in orders:
        emoji = STATUS_EMOJI.get(o["status"], "?")
        fp = o["final_price"] or o["price"]
        text += f"{emoji} <b>#{o['id']}</b> — {o['service_name']}\n   {fp:,} so'm | {o['created_at'][:10]}\n\n"
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    order_id = int(call.data.split(":")[1])
    order = await db.get_order(order_id)
    if order and order["user_id"] == call.from_user.id and order["status"] == "pending":
        await db.update_order_status(order_id, "cancelled")
        await db.increase_stock(order["service_id"])
        bonus_used = order["bonus_used"] or 0
        if bonus_used > 0:
            await db.add_bonus(call.from_user.id, bonus_used, f"Buyurtma #{order_id} bekor qilindi")
        await call.answer(t(lang, "order_cancelled"), show_alert=True)
        await call.message.edit_reply_markup(reply_markup=None)
    else:
        await call.answer(t(lang, "order_cancel_forbidden"), show_alert=True)


# PROFILE

@router.message(F.text.in_(["👤 Profil", "👤 Профиль"]))
async def show_profile(message: Message):
    lang = await get_lang(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    orders = await db.get_user_orders(message.from_user.id)
    spent = await db.get_user_total_spent(message.from_user.id)
    refs = await db.get_referral_count(message.from_user.id)
    ref_code = user["referral_code"] if user else ""
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}" if BOT_USERNAME and ref_code else ref_code
    bonus = (user["bonus_balance"] or 0) if user else 0
    total_cashback = await db.get_user_total_cashback(message.from_user.id)
    tier = get_tier(refs)
    tier_label = TIER_LABELS[tier][lang]
    await message.answer(
        t(lang, "profile_text",
          user_id=message.from_user.id,
          full_name=message.from_user.full_name,
          orders=len(orders),
          spent=spent,
          referrals=refs,
          ref_link=ref_link) +
        t(lang, "profile_bonus", bonus=bonus, tier=tier_label) +
        t(lang, "profile_cashback", total=total_cashback),
        parse_mode="HTML",
    )


# REVIEW

@router.callback_query(F.data.startswith("rate:"))
async def rate_service(call: CallbackQuery, state: FSMContext):
    from keyboards.user_kb import review_templates_keyboard

    parts = call.data.split(":")
    order_id, rating = int(parts[1]), int(parts[2])
    order = await db.get_order(order_id)
    lang = await get_lang(call.from_user.id)

    if not order:
        await call.answer(t(lang, "order_not_found"), show_alert=True)
        return

    if await db.review_exists(order_id):
        await call.answer(t(lang, "already_reviewed"), show_alert=True)
        return

    await call.answer()
    await call.message.edit_text(
        "\u2b50" * rating + f"\n\n{t(lang, 'rate_comment')}",
        reply_markup=review_templates_keyboard(order_id, rating, lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("rate_tpl:"))
async def rate_service_template(call: CallbackQuery):
    from keyboards.user_kb import REVIEW_TEMPLATE_TEXTS

    parts = call.data.split(":")
    order_id = int(parts[1])
    rating = int(parts[2])
    template_key = parts[3]

    order = await db.get_order(order_id)
    lang = await get_lang(call.from_user.id)

    if not order:
        await call.answer(t(lang, "order_not_found"), show_alert=True)
        return

    if await db.review_exists(order_id):
        await call.answer(t(lang, "already_reviewed"), show_alert=True)
        return

    comment = REVIEW_TEMPLATE_TEXTS[template_key]["uz" if lang == "uz" else "ru"]

    await db.add_review(order_id, call.from_user.id, order["service_id"], rating, comment)
    await call.answer()
    await call.message.answer(t(lang, "rate_thanks"), reply_markup=main_menu(lang))


@router.callback_query(F.data.startswith("rate_custom:"))
async def rate_service_custom(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    order_id = int(parts[1])
    rating = int(parts[2])

    order = await db.get_order(order_id)
    lang = await get_lang(call.from_user.id)

    if not order:
        await call.answer(t(lang, "order_not_found"), show_alert=True)
        return

    if await db.review_exists(order_id):
        await call.answer(t(lang, "already_reviewed"), show_alert=True)
        return

    await state.update_data(order_id=order_id, rating=rating, service_id=order["service_id"], lang=lang)
    await state.set_state(ReviewState.waiting_comment)

    await call.answer()
    await call.message.edit_text(
        "\u2b50" * rating + f"\n\n{t(lang, 'rate_comment')}",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("rate_skip:"))
async def rate_service_skip(call: CallbackQuery):
    parts = call.data.split(":")
    order_id = int(parts[1])
    rating = int(parts[2])

    order = await db.get_order(order_id)
    lang = await get_lang(call.from_user.id)

    if not order:
        await call.answer(t(lang, "order_not_found"), show_alert=True)
        return

    if await db.review_exists(order_id):
        await call.answer(t(lang, "already_reviewed"), show_alert=True)
        return

    await db.add_review(order_id, call.from_user.id, order["service_id"], rating, "")
    await call.answer()
    await call.message.answer(t(lang, "rate_thanks"), reply_markup=main_menu(lang))


@router.message(ReviewState.waiting_comment)
async def receive_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    comment = "" if message.text.strip() == "-" else message.text
    await db.add_review(data["order_id"], message.from_user.id, data["service_id"], data["rating"], comment)
    await state.clear()
    await message.answer(t(lang, "rate_thanks"), reply_markup=main_menu(lang))


@router.message(F.text.in_(["🎉 Aksiyalar", "🎉 Акции"]))
async def show_promos(message: Message):
    lang = await get_lang(message.from_user.id)

    regular_promos = await db.get_promos()
    service_promos = await db.get_active_service_promotions()

    if not regular_promos and not service_promos:
        await message.answer("🎉 Hozircha aksiyalar yo'q. / Пока нет активных акций.")
        return

    text = "🎉 <b>Faol Aksiyalar / Активные акции:</b>\n\n"

    if regular_promos:
        text += "📢 <b>Maxsus takliflar:</b>\n"
        for p in regular_promos[:10]:
            title = p["title"] or "Aksiya"
            body = p["text"] or ""
            text += f"• <b>{title}</b>"
            if body:
                text += f"\n{body}"
            text += "\n\n"

    if service_promos:
        text += "🛍 <b>Xizmat aksiyalari:</b>\n"
        for p in service_promos:
            bonus = int(p["price"] * p["cashback_percent"] / 100)
            promo_title = p["title"] or "Cashback aksiya"
            text += (
                f"• <b>{p['service_name']}</b>\n"
                f"🎁 {promo_title} ({p['cashback_percent']}% cashback)\n"
                f"💎 Kutilayotgan bonus: {bonus:,} so'm\n\n"
            )

    await message.answer(text, parse_mode="HTML")


# CONTACT / ABOUT

@router.message(F.text.in_(["📞 Aloqa", "📞 Контакты"]))
async def contact(message: Message):
    lang = await get_lang(message.from_user.id)
    from keyboards.user_kb import contact_keyboard
    await message.answer(t(lang, "contact_text"), reply_markup=contact_keyboard(lang), parse_mode="HTML")


@router.message(F.text.in_(["ℹ️ Haqida", "ℹ️ О боте"]))
async def about(message: Message):
    lang = await get_lang(message.from_user.id)
    await message.answer(t(lang, "about_text"), parse_mode="HTML")
