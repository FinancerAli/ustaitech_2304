import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import logging
import json
import re
import secrets
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
from locales import t, TEXTS
from keyboards.user_kb import (
    main_menu, lang_keyboard, categories_keyboard, services_keyboard,
    service_detail_keyboard, cancel_keyboard, skip_cancel_keyboard, payment_method_keyboard, rating_keyboard,
    coupon_pick_keyboard, referral_order_keyboard, STATUS_EMOJI,
    ref_campaigns_keyboard, ref_campaign_detail_keyboard, profile_keyboard,
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
            "📋 Пожалуйста, отправьте ответ, указанный в инструкции.\n"
            "Допустимо: текст, .txt или .json файл.\n\n"
            "Фото и другие типы файлов не принимаются.\n"
            "Если информация неполная или в неверном формате, бот попросит отправить заново."
        )
    return (
        "📋 Iltimos, qo'llanmada so'ralgan ma'lumotlarni yuboring.\n"
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
        f"📬 <b>Yangi mijoz javobi keldi</b>\n\n"
        f"Buyurtma: #{order_id}\n"
        f"Mijoz: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Xizmat: {service_name}\n"
        f"Manba: {source_label}\n"
        f"Sana: {submitted_at}\n\n"
        f"👁 <b>Preview:</b>\n<code>{preview}</code>"
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
        f"🧾 Buyurtma #{order_id}\n"
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

class CartOrderState(StatesGroup):
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


class ReferralEmailState(StatesGroup):
    email = State()


class CampaignEmailState(StatesGroup):
    email = State()

class AIChatState(StatesGroup):
    chatting = State()


async def get_lang(user_id: int) -> str:
    user = await db.get_user(user_id)
    return (user["language"] or "uz") if user else "uz"


def _build_referral_link(order_id: int, referral_code: str) -> str:
    if BOT_USERNAME and referral_code:
        return f"https://t.me/{BOT_USERNAME}?start=refact_{order_id}_{referral_code}"
    return referral_code or ""


def _is_valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value or ""))


def _referral_service_detail_text(service: dict, lang: str) -> str:
    if not service or service.get("delivery_mode") != "referral_activation":
        return ""
    required = int(service.get("required_referrals") or 0)
    if lang == "ru":
        return (
            f"\n\n🎯 <b>Referral activation</b>\n"
            f"🎯 Чтобы активировать эту услугу, нужно пригласить {required} новых пользователей.\n"
            f"Email необходимо отправить после этого."
        )
    return (
        f"\n\n🎯 <b>Referral activation</b>\n"
        f"Ushbu xizmatni faollashtirish uchun {required} ta yangi foydalanuvchi taklif qilishingiz kerak.\n"
        f"Emailingizni keyin alohida yuborasiz."
    )


async def _evaluate_referral_order(order_id: int):
    order = await db.expire_referral_order_if_needed(order_id)
    if not order:
        return None
    service = normalize_service(await db.get_service(order["service_id"]))
    email_required = bool(service and service.get("requires_email"))
    has_email = bool(order.get("customer_email"))
    target_met = int(order.get("current_referrals") or 0) >= int(order.get("required_referrals") or 0)
    if not target_met:
        return order

    if email_required and not has_email:
        await db.update_order_referral_progress(order_id, order["current_referrals"], "awaiting_email")
        return await db.get_order(order_id)

    if order.get("activation_status") != "ready":
        await db.mark_referral_ready(order_id, "target_met")
    return await db.get_order(order_id)


async def _notify_referral_email_saved(bot: Bot, order: dict):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                (
                    f"📧 <b>Referral order email saqlandi</b>\n\n"
                    f"Buyurtma: #{order['id']}\n"
                    f"User: <code>{order['user_id']}</code>\n"
                    f"Xizmat: {order['service_name']}\n"
                    f"Email: <code>{order.get('customer_email') or '-'}</code>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass


async def _notify_referral_threshold(bot: Bot, order: dict, awaiting_email: bool = False, storage=None):
    buyer = await db.get_user(order["user_id"])
    buyer_lang = (buyer["language"] or "uz") if buyer else "uz"
    
    markup = None
    if awaiting_email:
        user_text = (
            "✅ Kerakli referral soni to'plandi.\n\n📧 Iltimos, xizmatni aktivlashtirish uchun emailingizni (yoki akkaunt ma'lumotingizni) yuboring:"
            if buyer_lang == "uz" else
            "✅ Необходимое число рефералов достигнуто.\n\n📧 Пожалуйста, отправьте ваш email (или данные аккаунта) для активации услуги:"
        )
        from keyboards.user_kb import cancel_keyboard
        markup = cancel_keyboard(buyer_lang)
        
        if storage:
            from aiogram.fsm.context import FSMContext
            from aiogram.fsm.storage.base import StorageKey
            inviter_state = FSMContext(
                storage=storage,
                key=StorageKey(bot_id=bot.id, chat_id=order["user_id"], user_id=order["user_id"])
            )
            await inviter_state.update_data(referral_email_order_id=order["id"], referral_email_lang=buyer_lang)
            await inviter_state.set_state(ReferralEmailState.email)
    else:
        user_text = (
            "✅ Kerakli referral soni to'plandi.\n\nBuyurtmangiz aktivlashtirishga tayyor. Admin tez orada xizmatni tayyorlaydi."
            if buyer_lang == "uz" else
            "✅ Необходимое число рефералов достигнуто.\n\n🎯 Ваш заказ передан админу. Скоро услуга будет активирована."
        )
    try:
        await bot.send_message(order["user_id"], user_text, reply_markup=markup)
    except Exception:
        pass

    admin_text = (
        f"🎉 <b>Referral threshold reached</b>\n\n"
        f"Buyurtma: #{order['id']}\n"
        f"User: <code>{order['user_id']}</code>\n"
        f"Xizmat: {order['service_name']}\n"
        f"Progress: {order.get('current_referrals', 0)} / {order.get('required_referrals', 0)}\n"
        f"Email: <code>{order.get('customer_email') or '-'}</code>\n"
        f"Holat: {order.get('referral_status')} | {order.get('activation_status')}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass


async def _process_pending_referral(state: FSMContext, bot: Bot, invited_user_id: int):
    data = await state.get_data()
    pending = data.get("pending_referral_source")
    if not pending:
        return

    await state.update_data(pending_referral_source=None)
    pending_type = pending.get("type", "order")

    if pending_type == "campaign":
        campaign_id = int(pending.get("campaign_id") or 0)
        inviter_id = int(pending.get("inviter_id") or 0)
        was_existing = bool(pending.get("was_existing_user"))
        # Antifraud: block self referral, block existing users, block invalid IDs
        if not campaign_id or not inviter_id or was_existing or inviter_id == invited_user_id:
            return
            
        # Antifraud: duplicate check — one user can only be invited once to this campaign
        is_new_invite = await db.record_campaign_invite(campaign_id, inviter_id, invited_user_id)
        if not is_new_invite:
            return

        camp = await db.get_referral_campaign(campaign_id)
        if not camp or not camp["is_active"]:
            return
        participant = await db.get_campaign_participant(campaign_id, inviter_id)
        if not participant or participant["reward_given"]:
            return
            
        new_count = await db.increment_campaign_referral(campaign_id, inviter_id)
        inviter = await db.get_user(inviter_id)
        inviter_lang = (inviter["language"] or "uz") if inviter else "uz"
        required = int(camp["required_referrals"])
        try:
            prog_filled = min(10, round(new_count / max(required, 1) * 10)) if required else 10
            prog_bar = "🟩" * prog_filled + "⬜" * (10 - prog_filled)
            msg = f"🎯 <b>{camp['name']}</b>\n{prog_bar} {new_count}/{required}"
            await bot.send_message(inviter_id, msg, parse_mode="HTML")
        except Exception:
            pass
        if new_count >= required:
            await db.mark_campaign_reward_given(campaign_id, inviter_id)
            reward_type = camp.get("reward_type", "bonus")
            reward_value = int(camp.get("reward_value") or 0)
            if reward_type == "bonus" and reward_value > 0:
                await db.add_bonus(inviter_id, reward_value)
                try:
                    reward_msg = (
                        f"🏆 <b>{camp['name']}</b> kampaniyasini bajardingiz!\nMukofot: {reward_value} bonus berildi."
                        if inviter_lang == "uz" else
                        f"🏆 Вы выполнили кампанию <b>{camp['name']}</b>!\nНаграда: {reward_value} бонусов начислено."
                    )
                    await bot.send_message(inviter_id, reward_msg, parse_mode="HTML")
                except Exception:
                    pass
            else:
                # Service activation — ask for email safely via FSMContext
                await db.set_campaign_participant_activation_status(campaign_id, inviter_id, "ready")
                from keyboards.user_kb import cancel_keyboard
                try:
                    email_msg = (
                        f"🏆 <b>{camp['name']}</b> kampaniyasini bajardingiz!\n\n"
                        f"📧 Iltimos, xizmatni aktivlashtirish uchun emailingizni (yoki akkaunt ma'lumotingizni) yuboring:"
                        if inviter_lang == "uz" else
                        f"🏆 Вы выполнили кампанию <b>{camp['name']}</b>!\n\n"
                        f"📧 Пожалуйста, отправьте ваш email (или данные аккаунта) для активации:"
                    )
                    await bot.send_message(inviter_id, email_msg, parse_mode="HTML", reply_markup=cancel_keyboard(inviter_lang))
                except Exception:
                    pass
                # Set FSM state for email collection if possible without overwriting critical states
                if state.storage:
                    from aiogram.fsm.context import FSMContext
                    from aiogram.fsm.storage.base import StorageKey
                    inviter_fsm = FSMContext(
                        storage=state.storage,
                        key=StorageKey(bot_id=bot.id, chat_id=inviter_id, user_id=inviter_id)
                    )
                    current_inviter_state = await inviter_fsm.get_state()
                    # Only override if the inviter is not currently doing something important
                    if not current_inviter_state or "Order" not in str(current_inviter_state) and "Admin" not in str(current_inviter_state):
                        await inviter_fsm.update_data(campaign_email_campaign_id=campaign_id, campaign_email_lang=inviter_lang)
                        await inviter_fsm.set_state(CampaignEmailState.email)
                # Notify admins
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"🏆 <b>Kampaniya target bajarildi!</b>\n\n"
                            f"Kampaniya: {camp['name']}\n"
                            f"User: @{inviter.get('username', 'nomalum')} (<code>{inviter_id}</code>)\n"
                            f"Progress: {new_count}/{required}\n"
                            f"Email kutilmoqda...",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
        return

    order_id = int(pending.get("order_id") or 0)
    referral_code = pending.get("referral_code")
    owner_user_id = int(pending.get("owner_user_id") or 0)
    was_existing_user = bool(pending.get("was_existing_user"))
    order = await db.get_order_by_referral(order_id, referral_code)
    if not order:
        return
    order = await db.expire_referral_order_if_needed(order_id) or order
    if order.get("referral_status") == "expired":
        return

    status = "qualified"
    if was_existing_user:
        status = "rejected_existing_user"
    elif owner_user_id == invited_user_id:
        status = "rejected_self_ref"
    elif await db.get_referral_invite_for_order_user(order_id, invited_user_id):
        status = "duplicate"

    await db.create_referral_invite(
        order_id=order_id,
        service_id=order["service_id"],
        owner_user_id=owner_user_id,
        invited_user_id=invited_user_id,
        referral_code=referral_code,
        status=status,
    )

    if status != "qualified":
        return

    new_count = int(order.get("current_referrals") or 0) + 1
    await db.update_order_referral_progress(order_id, new_count)
    updated = await _evaluate_referral_order(order_id)
    owner = await db.get_user(owner_user_id)
    owner_lang = (owner["language"] or "uz") if owner else "uz"
    try:
        await bot.send_message(
            owner_user_id,
            (
                f"🎯 Yangi referral qabul qilindi.\nNatijangiz: {updated.get('current_referrals', new_count)} / {updated.get('required_referrals', 0)}"
                if owner_lang == "uz" else
                f"🎯 Новый реферал получен.\nВаш прогресс: {updated.get('current_referrals', new_count)} / {updated.get('required_referrals', 0)}"
            ),
        )
    except Exception:
        pass

    target_met = int(updated.get("current_referrals") or 0) >= int(updated.get("required_referrals") or 0)
    if target_met and updated.get("activation_status") == "ready":
        await _notify_referral_threshold(bot, updated, awaiting_email=False)
    elif target_met and updated.get("referral_status") == "awaiting_email":
        await _notify_referral_threshold(bot, updated, awaiting_email=True, storage=state.storage)


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


@router.message(F.text.in_(["🎯 Referral dasturi", "🎯 Реферальная программа"]))
async def show_ref_campaigns(message: Message):
    lang = await get_lang(message.from_user.id)
    campaigns = await db.get_active_referral_campaigns()
    if not campaigns:
        await message.answer(t(lang, "ref_campaign_no_active"), parse_mode="HTML")
        return
    completed_ids = await db.get_user_completed_campaign_ids(message.from_user.id)
    await message.answer(
        t(lang, "ref_campaign_title"),
        reply_markup=ref_campaigns_keyboard(campaigns, completed_ids, lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "ref_camp_list")
async def ref_camp_list_callback(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    campaigns = await db.get_active_referral_campaigns()
    if not campaigns:
        await call.answer(t(lang, "ref_campaign_no_active"), show_alert=True)
        return
    completed_ids = await db.get_user_completed_campaign_ids(call.from_user.id)
    await call.message.edit_text(
        t(lang, "ref_campaign_title"),
        reply_markup=ref_campaigns_keyboard(campaigns, completed_ids, lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ref_camp:"))
async def ref_camp_detail(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    campaign_id = int(call.data.split(":")[1])
    camp = await db.get_referral_campaign(campaign_id)
    if not camp:
        await call.answer("Kampaniya topilmadi.", show_alert=True)
        return

    reward_type = camp["reward_type"]
    reward_val = camp["reward_value"]
    if reward_type == "bonus":
        reward_text = f"{reward_val:,} so'm bonus" if lang == "uz" else f"{reward_val:,} сум бонуса"
    elif reward_type == "discount":
        reward_text = f"{reward_val}% chegirma" if lang == "uz" else f"{reward_val}% скидка"
    else:
        reward_text = camp.get("reward_description") or ("🎁 Xizmat" if lang == "uz" else "🎁 Услуга")

    participant = await db.get_campaign_participant(campaign_id, call.from_user.id)
    joined = participant is not None

    text = t(lang, "ref_campaign_item",
             name=camp["name"],
             desc=camp["description"] or "",
             required=camp["required_referrals"],
             reward=reward_text)

    if camp.get("deadline") and camp["deadline"].lower() not in ("yo'q", "yoq", "net", "no", "skip", "/skip"):
        deadline_text = "⏳ Muddat: " if lang == "uz" else "⏳ Дедлайн: "
        text += f"\n\n{deadline_text}<b>{html.escape(camp['deadline'])}</b>"

    link = None
    if joined:
        ref_code = str(call.from_user.id)
        link = f"https://t.me/{BOT_USERNAME}?start=refcamp_{campaign_id}_{ref_code}"
        
        current = participant["current_referrals"]
        required = camp["required_referrals"]
        bar_filled = min(10, int(current / max(required, 1) * 10))
        bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)
        text += t(lang, "ref_campaign_progress", current=current, required=required, bar=bar)
        
        if participant.get("reward_given"):
            act_st = participant.get("activation_status") or "pending"
            email = participant.get("customer_email")
            st_text = ""
            if act_st == "pending":
                st_text = "⏳ Kutilmoqda (Email yuboring)" if lang == "uz" else "⏳ Ожидание (Отправьте Email)"
            elif act_st == "ready":
                st_text = "🟢 Adminga yuborildi (Jarayonda)" if lang == "uz" else "🟢 Отправлено админу (В процессе)"
            elif act_st == "activated":
                st_text = "✅ Aktivlashtirildi" if lang == "uz" else "✅ Активировано"
            
            text += f"\n\n📧 Email: <code>{email or '-'}</code>\n📊 Holat: <b>{st_text}</b>"

    await call.answer()
    await call.message.edit_text(
        text,
        reply_markup=ref_campaign_detail_keyboard(campaign_id, participant, lang, link=link, camp_name=camp["name"]),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("ref_camp_ask_email:"))
async def ref_camp_ask_email(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    campaign_id = int(call.data.split(":")[1])
    await state.update_data(campaign_email_campaign_id=campaign_id, campaign_email_lang=lang)
    await state.set_state(CampaignEmailState.email)
    from keyboards.user_kb import cancel_keyboard
    msg = (
        "📧 Iltimos, xizmatni aktivlashtirish uchun emailingizni (yoki akkaunt ma'lumotingizni) yuboring:"
        if lang == "uz" else
        "📧 Пожалуйста, отправьте ваш email (или данные аккаунта) для активации:"
    )
    await call.message.answer(msg, reply_markup=cancel_keyboard(lang))
    await call.answer()


@router.callback_query(F.data.startswith("ref_camp_join:"))
async def ref_camp_join(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    campaign_id = int(call.data.split(":")[1])
    camp = await db.get_referral_campaign(campaign_id)
    if not camp or not camp["is_active"]:
        await call.answer("Kampaniya mavjud emas yoki yopilgan.", show_alert=True)
        return

    existing = await db.get_campaign_participant(campaign_id, call.from_user.id)
    if existing:
        ref_code = str(call.from_user.id)
        link = f"https://t.me/{BOT_USERNAME}?start=refcamp_{campaign_id}_{ref_code}"
        await call.answer()
        await call.message.edit_text(
            t(lang, "ref_campaign_already_joined",
              current=existing["current_referrals"],
              required=camp["required_referrals"],
              link=link),
            reply_markup=ref_campaign_detail_keyboard(campaign_id, existing, lang, link=link, camp_name=camp["name"]),
            parse_mode="HTML"
        )
        return

    await db.join_campaign(campaign_id, call.from_user.id)
    ref_code = str(call.from_user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=refcamp_{campaign_id}_{ref_code}"
    await call.answer()
    await call.message.edit_text(
        t(lang, "ref_campaign_joined", link=link),
        reply_markup=ref_campaign_detail_keyboard(campaign_id, {"reward_given": 0, "current_referrals": 0, "activation_status": "pending"}, lang, link=link, camp_name=camp["name"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ref_camp_link:"))
async def ref_camp_link(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    campaign_id = int(call.data.split(":")[1])
    camp = await db.get_referral_campaign(campaign_id)
    if not camp:
        await call.answer("Kampaniya topilmadi.", show_alert=True)
        return

    participant = await db.get_campaign_participant(campaign_id, call.from_user.id)
    if not participant:
        await call.answer("Avval kampaniyaga qo'shiling.", show_alert=True)
        return

    ref_code = str(call.from_user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=refcamp_{campaign_id}_{ref_code}"
    current = participant["current_referrals"]
    required = camp["required_referrals"]
    await call.answer()
    await call.message.edit_text(
        t(lang, "ref_campaign_invite_text",
          name=camp["name"], link=link,
          current=current, required=required),
        reply_markup=ref_campaign_detail_keyboard(campaign_id, participant, lang, link=link, camp_name=camp["name"]),
        parse_mode="HTML"
    )


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
            "📋 Пожалуйста, отправьте ответ по форме.\n"
            "Принимается: обычный текст, .txt или .json файл.\n\n"
            "Фото, видео, аудио и другие файлы не принимаются."
        )
    return (
        "📋 Iltimos, forma bo'yicha javobingizni yuboring.\n"
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
        f"👁 <b>Preview:</b>\n<code>{preview}</code>"
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
        f"🧾 Buyurtma #{order_id}\n"
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
    pending_referral_source = None
    existing_user = await db.get_user(message.from_user.id)
    was_existing_user = existing_user is not None
    # --- Referral logic disabled ---
    # if len(args) > 1 and args[1].startswith("ref_"):
    #     ref_code = args[1][4:]
    #     ref_user = await db.get_user_by_referral(ref_code)
    #     if ref_user and ref_user["id"] != message.from_user.id:
    #         referred_by = ref_user["id"]
    # elif len(args) > 1 and args[1].startswith("refcamp_"):
    #     payload = args[1][8:]
    #     parts = payload.split("_", 1)
    #     if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
    #         campaign_id = int(parts[0])
    #         inviter_id = int(parts[1])
    #         if inviter_id != message.from_user.id:
    #             pending_referral_source = {
    #                 "type": "campaign",
    #                 "campaign_id": campaign_id,
    #                 "inviter_id": inviter_id,
    #                 "was_existing_user": was_existing_user,
    #             }
    # elif len(args) > 1 and args[1].startswith("refact_"):
    #     payload = args[1][7:]
    #     parts = payload.split("_", 1)
    #     if len(parts) == 2 and parts[0].isdigit():
    #         order = await db.get_order_by_referral(int(parts[0]), parts[1])
    #         if order and int(order.get("required_referrals") or 0) > 0:
    #             pending_referral_source = {
    #                 "type": "order",
    #                 "order_id": order["id"],
    #                 "referral_code": parts[1],
    #                 "owner_user_id": order["user_id"],
    #                 "was_existing_user": was_existing_user,
    #             }

    user = existing_user
    is_new = user is None
    await db.save_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name, referred_by)
    # if pending_referral_source:
    #     await state.update_data(pending_referral_source=pending_referral_source)

    # --- Referral bonus logic disabled ---
    # if referred_by and is_new:
    #     ...

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
    # if pending_referral_source:
    #     await _process_pending_referral(state, message.bot, message.from_user.id)


def _is_expirable_order(order: dict | None) -> bool:
    """True only while the order is still genuinely waiting for payment."""
    if not order:
        return False
    if order.get("receipt_file_id"):
        return False
    if (order.get("payment_status") or "pending") in {"submitted", "paid"}:
        return False
    return (order.get("status") or "pending") in {"pending", "payment_waiting"}


async def abandoned_cart_job(user_id: int, order_id: int, bot: Bot, lang: str):
    # ==== Stage 1: Soft reminder — 15 minutes ====
    await asyncio.sleep(900)
    try:
        order = await db.get_order(order_id)
        if not _is_expirable_order(order):
            return
        # Try AI personalized message
        try:
            import ai_agent
            ai_msg = await ai_agent.personalize_remarketing(
                name=order.get("service_name", ""),
                product=order.get("service_name", ""),
                price=order.get("final_price", order.get("price", 0)),
                lang=lang,
            )
            if ai_msg:
                await bot.send_message(user_id, f"🤖 {ai_msg}", parse_mode="HTML")
            else:
                await bot.send_message(user_id, t(lang, "remarketing_text"), parse_mode="HTML")
        except Exception:
            await bot.send_message(user_id, t(lang, "remarketing_text"), parse_mode="HTML")
    except Exception:
        pass

    # ==== Stage 2: Urgency reminder — 1 hour (45 min more) ====
    await asyncio.sleep(2700)
    try:
        order = await db.get_order(order_id)
        if not _is_expirable_order(order):
            return
        if lang == "uz":
            text2 = (
                f"⏳ <b>Buyurtma #{order_id} hali kutmoqda!</b>\n\n"
                f"🛍 {order['service_name']}\n"
                f"💰 {order.get('final_price', order['price']):,} so'm\n\n"
                f"To'lov qilmasangiz, buyurtma 3 soat ichida bekor qilinadi."
            )
        else:
            text2 = (
                f"⏰ <b>Заказ #{order_id} ещё ждёт!</b>\n\n"
                f"🛍 {order['service_name']}\n"
                f"💰 {order.get('final_price', order['price']):,} сум\n\n"
                f"Если вы не оплатите, заказ будет отменён через 3 часа."
            )
        await bot.send_message(user_id, text2, parse_mode="HTML")
    except Exception:
        pass

    # ==== Stage 3: Final warning + auto-expire — 4 hours (3h more) ====
    await asyncio.sleep(10800)
    try:
        order = await db.get_order(order_id)
        if not _is_expirable_order(order):
            return
        # Expire the order
        await db.update_order_status(order_id, "expired")
        qty = order.get("quantity", 1)
        await db.increase_stock(order["service_id"], amount=qty)
        bonus_used = order.get("bonus_used") or 0
        if bonus_used > 0:
            await db.add_bonus(user_id, bonus_used, f"Buyurtma #{order_id} vaqti tugadi")

        if lang == "uz":
            expire_text = (
                f"🧾 <b>Buyurtma #{order_id} bekor qilindi.</b>\n\n"
                f"🛍 {order['service_name']}\n"
                f"4 soat ichida to'lov tasdiqlanmaganligi sababli buyurtma avtomatik bekor qilindi.\n\n"
                f"Qayta buyurtma berish uchun /start bosing."
            )
        else:
            expire_text = (
                f"❌ <b>Заказ #{order_id} отменён.</b>\n\n"
                f"🛍 {order['service_name']}\n"
                f"Заказ автоматически отменён, так как оплата не была произведена в течение 4 часов.\n\n"
                f"Для нового заказа нажмите /start."
            )
        if bonus_used > 0:
            expire_text += f"\n🎁 Bonus ({bonus_used:,} so'm) qaytarildi." if lang == "uz" else f"\n🎁 Бонус ({bonus_used:,} сум) возвращён."
        try:
            await bot.send_message(user_id, expire_text, parse_mode="HTML")
        except Exception:
            pass
    except Exception:
        pass


# LANGUAGE

async def send_referral_intro(message: Message, user_id: int, lang: str):
    user = await db.get_user(user_id)
    ref_code = user["referral_code"] if user else ""
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}"
    
    if lang == "ru":
        text = (
            "🎁 <b>Приглашайте друзей и получайте бонусы!</b>\n\n"
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
            "🎁 <b>Do'stlaringizni taklif qiling va bonuslar oling!</b>\n\n"
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
async def set_language(call: CallbackQuery, state: FSMContext):
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
    await _process_pending_referral(state, call.bot, call.from_user.id)


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

    # 🤖 AI FAQ Auto-Answer ▫️
    try:
        import ai_agent
        faq_answer = await ai_agent.answer_faq(message.text)
        if faq_answer:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            await message.answer(
                f"🤖 <b>AI yordamchi:</b>\n\n{faq_answer}\n\n"
                f"<i>Bu avtomatik javob. Operator kerakmi?</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Rahmat, yetarli", callback_data="faq_ok")],
                    [InlineKeyboardButton(text="💬 Operatorga yozish", callback_data=f"faq_human:{message.from_user.id}")],
                ])
            )
            await state.update_data(faq_original_msg=message.text)
            return
    except Exception:
        pass

    # 🤖 Create support ticket (fallback) ▫️
    await _create_support_ticket(message, state, lang)


async def _create_support_ticket(message: Message, state: FSMContext, lang: str):
    """Create ticket and notify admins."""
    ticket_id = await db.create_ticket(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
        message_text=message.text,
    )

    # 🤖 AI Triage ▫️
    triage_tag = ""
    try:
        import ai_agent
        triage = await ai_agent.triage_support(
            message.text,
            f"{message.from_user.full_name} (@{message.from_user.username})"
        )
        if triage:
            urgency_map = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            u_icon = urgency_map.get(triage.get("urgency", ""), "❓")
            cat = triage.get("category", "other")
            summary = triage.get("summary", "")
            triage_tag = f"\n\n🏷 {u_icon} {triage.get('urgency','').upper()} | {cat}\n🏷 {summary}"
    except Exception:
        pass

    from keyboards.admin_kb import support_ticket_keyboard
    admin_text = (
        f"🎫 <b>Yangi murojaat — Ticket #{ticket_id}</b>\n"
        f"👤 {message.from_user.full_name}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"📱 @{message.from_user.username or 'nomalum'}\n\n"
        f"💬 <b>Xabar:</b>\n{message.text}"
        f"{triage_tag}"
    )

    # ✍️ AI Draft Reply ✍️
    draft_text = ""
    try:
        import ai_agent
        draft = await ai_agent.draft_admin_reply(message.text, message.from_user.full_name)
        if draft:
            draft_text = f"\n\n✍️ <b>AI draft:</b>\n<i>{draft}</i>"
    except Exception:
        pass

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                int(admin_id),
                admin_text + draft_text,
                reply_markup=support_ticket_keyboard(ticket_id),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await state.clear()
    if lang == "uz":
        await message.answer(
            f"✅ <b>Murojaatingiz qabul qilindi!</b>\n\n"
            f"🎫 Ticket raqami: <b>#{ticket_id}</b>\n"
            f"Operator tez orada javob beradi.",
            reply_markup=main_menu(lang), parse_mode="HTML"
        )
    else:
        await message.answer(
            f"✅ <b>Ваше обращение принято!</b>\n\n"
            f"🎫 Номер обращения: <b>#{ticket_id}</b>\n"
            f"Оператор ответит в ближайшее время.",
            reply_markup=main_menu(lang), parse_mode="HTML"
        )


@router.callback_query(F.data == "faq_ok")
async def faq_ok(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(call.from_user.id)
    await call.answer("✅")
    await call.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("faq_human:"))
async def faq_escalate_to_human(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    original_msg = data.get("faq_original_msg", "")
    if original_msg:
        # Create a fake-ish message wrapper ? reuse call.message for bot ref
        ticket_id = await db.create_ticket(
            user_id=call.from_user.id,
            username=call.from_user.username or "",
            full_name=call.from_user.full_name or "",
            message_text=original_msg,
        )
        from keyboards.admin_kb import support_ticket_keyboard
        admin_text = (
            f"🎫 <b>Yangi murojaat — Ticket #{ticket_id}</b>\n"
            f"👤 {call.from_user.full_name}\n"
            f"🆔 ID: <code>{call.from_user.id}</code>\n\n"
            f"💬 <b>Xabar:</b>\n{original_msg}\n\n"
            f"<i>🤖 AI javob bermadi, operator kerak</i>"
        )
        for admin_id in ADMIN_IDS:
            try:
                await call.message.bot.send_message(
                    int(admin_id), admin_text,
                    reply_markup=support_ticket_keyboard(ticket_id),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await state.clear()
        if lang == "uz":
            await call.message.answer(
                f"✅ <b>Ticket #{ticket_id} yaratildi.</b>\nOperator tez orada javob beradi.",
                reply_markup=main_menu(lang), parse_mode="HTML"
            )
        else:
            await call.message.answer(
                f"✅ <b>Тикет #{ticket_id} создан.</b>\nОператор ответит в ближайшее время.",
                reply_markup=main_menu(lang), parse_mode="HTML"
            )
    else:
        await state.clear()
        await call.message.answer(
            "💬 Iltimos, operatorga yozish tugmasini bosing.",
            reply_markup=main_menu(lang)
        )


# CATEGORIES / SERVICES

@router.message(F.text.in_([t("uz", "services"), t("ru", "services")]))
async def show_categories(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await get_lang(user_id)

    await _delete_tracked_ui_messages(message.bot, message.chat.id, user_id)

    # categories = await db.get_categories()  # Kategoriya o'chirilgan
    stats = await db.get_stats()
    confirmed = stats["confirmed"]

    if True:  # Har doim servislarni ko'rsatamiz (kategoriya o'chirilgan)
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
        reply_markup=categories_keyboard(categories, lang, min_prices=min_prices),
        parse_mode="HTML"
    )
    _track_ui_message(user_id, sent.message_id)


@router.callback_query(F.data == "back_categories")
async def back_to_categories(call: CallbackQuery):
    await call.answer()
    lang = await get_lang(call.from_user.id)
    categories = await db.get_categories()
    min_prices = await db.get_category_min_prices()
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
    markup = categories_keyboard(categories, lang, min_prices=min_prices)
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
    min_prices = await db.get_category_min_prices()
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
        reply_markup=categories_keyboard(categories, lang, min_prices=min_prices),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("service:"))
async def service_detail(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)

    parts = call.data.split(":")
    service_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1

    s = normalize_service(await db.get_public_service(service_id))
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
        
    # Detect subscription duration from service name
    name_lower = s["name"].lower()
    if any(w in name_lower for w in ("yillik", "annual", "1 yil", "12 oy", "yearly")):
        onetime_suffix = " (yillik obuna)" if lang == "uz" else " (годовая подписка)"
    elif any(w in name_lower for w in ("haftalik", "weekly", "1 hafta", "7 kun")):
        onetime_suffix = " (haftalik)" if lang == "uz" else " (еженедельно)"
    else:
        onetime_suffix = " (oylik obuna)" if lang == "uz" else " (ежемесячно)"
    
    # Flash Sale Calculation
    from datetime import datetime
    has_flash_sale = False
    if s.get("flash_discount") and s.get("flash_expire_at"):
        try:
            expire_dt = datetime.strptime(s["flash_expire_at"], "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.now()
            if now_dt < expire_dt:
                has_flash_sale = True
                hours_left = max(1, int((expire_dt - now_dt).total_seconds() / 3600))
                
                flash_text = f"⚡ {s['flash_discount']}% (qoldi: {hours_left} soat)" if lang == "uz" else f"⚡ {s['flash_discount']}% (осталось: {hours_left} ч.)"
                badge = f"{flash_text} | " + badge
                
                old_price = s['price']
                s['price'] = int(old_price * (100 - s['flash_discount']) / 100)
                
                narx_lbl = "Narxi" if lang == "uz" else "Цена"
                price_text = f"💰 {narx_lbl}: <s>{old_price:,}</s> <b>{s['price']:,} so'm</b>{onetime_suffix}\n"
        except Exception:
            pass
            
    if not has_flash_sale:
        price_text = f"{t(lang, 'service_price', price=s['price'])}{onetime_suffix}\n"
    if s['stock'] == 0:
        stock_txt = f"\n{t(lang, 'stock_empty')}\n"
    else:
        stock_txt = ""
    urgency = f"\n{t(lang, 'urgency')}"

    text = (
        f"<b>1️⃣ {t(lang, 'services')} \u2192</b>\n\n"
        f"\U0001f4e6 <b>{badge}{s['name']}</b>\n\n"
        f"{desc}{_referral_service_detail_text(s, lang)}\n\n"
        f"{price_text}"
        f"{cb_text}"
        f"{bulk_text}"
        f"{stock_txt}"
        f"{rating_text}"
        f"{urgency}"
    )
    if s["image_file_id"]:
        try:
            sent = await call.message.answer_photo(
                s["image_file_id"],
                caption=text,
                reply_markup=service_detail_keyboard(service_id, lang, s["stock"], back_page=page),
                parse_mode="HTML",
            )
            _track_ui_message(call.from_user.id, sent.message_id)
        except Exception:
            # Fallback for invalid file_id
            sent = await call.message.answer(
                text,
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
    # Skip note step — go directly to order creation
    await _create_order_and_show_payment(target_message, state, lang, note="", user_id_override=user_id)


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


# CART FLOW

@router.message(F.text.in_([TEXTS["uz"]["cart"], TEXTS["ru"]["cart"]]))
async def view_cart(message: Message):
    lang = await get_lang(message.from_user.id)
    cart_items = await db.get_cart(message.from_user.id)
    if not cart_items:
        await message.answer(t(lang, "cart_empty"), reply_markup=main_menu(lang))
        return
        
    total = sum(i["price"] * i["quantity"] for i in cart_items)
    items_txt = "\n".join(t(lang, "cart_item", name=i["service_name"], qty=i["quantity"], price=i["price"]*i["quantity"]) for i in cart_items)
    
    from keyboards.user_kb import cart_keyboard
    text = t(lang, "cart_content", items=items_txt, total=total)
    
    await message.answer(text, reply_markup=cart_keyboard(cart_items, lang), parse_mode="HTML")

async def _refresh_cart(call: CallbackQuery, lang: str):
    cart_items = await db.get_cart(call.from_user.id)
    if not cart_items:
        await call.message.edit_text(t(lang, "cart_empty"))
        return
        
    total = sum(i["price"] * i["quantity"] for i in cart_items)
    items_txt = "\n".join(t(lang, "cart_item", name=i["service_name"], qty=i["quantity"], price=i["price"]*i["quantity"]) for i in cart_items)
    
    from keyboards.user_kb import cart_keyboard
    text = t(lang, "cart_content", items=items_txt, total=total)
    await call.message.edit_text(text, reply_markup=cart_keyboard(cart_items, lang), parse_mode="HTML")

@router.callback_query(F.data == "cart_noop")
async def cart_noop(call: CallbackQuery):
    await call.answer()

@router.callback_query(F.data.startswith("cart_add:"))
async def add_to_cart(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    service_id = int(call.data.split(":")[1])
    s = normalize_service(await db.get_public_service(service_id))
    if not s:
        await call.answer(t(lang, "service_not_found"), show_alert=True)
        return
    if s.get("delivery_mode") == "referral_activation":
        text = (
            "🎯 Referral activation xizmati savatga qo'shilmaydi. Iltimos, xizmat kartasidan to'g'ridan-to'g'ri buyurtma bering."
            if lang == "uz"
            else "🎯 Услуга с активацией по рефералам не добавляется в корзину. Пожалуйста, закажите напрямую с карточки услуги."
        )
        await call.answer(text, show_alert=True)
        return
    if s["stock"] == 0:
        await call.answer(t(lang, "out_of_stock"), show_alert=True)
        return
        
    s_price = s["price"]
    from datetime import datetime
    if s.get("flash_discount") and s.get("flash_expire_at"):
        try:
            expire_dt = datetime.strptime(s["flash_expire_at"], "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.now()
            if now_dt < expire_dt:
                s_price = int(s_price * (100 - s['flash_discount']) / 100)
        except Exception:
            pass
            
    await db.add_to_cart(call.from_user.id, service_id, s_price, 1)
    await call.answer(t(lang, "add_to_cart") + " ✅", show_alert=True)

@router.callback_query(F.data.startswith("cart_plus:"))
async def cart_plus(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    cart_id = int(call.data.split(":")[1])
    # check stock logic could be added here, assuming simple +1 for now
    cart_items = await db.get_cart(call.from_user.id)
    item = next((i for i in cart_items if i["id"] == cart_id), None)
    if item:
        service = normalize_service(await db.get_public_service(item["service_id"]))
        if not service:
            await call.answer(t(lang, "service_not_found"), show_alert=True)
            return
        new_qty = item["quantity"] + 1
        if service["stock"] != -1 and new_qty > service["stock"]:
            await call.answer(t(lang, "stock_error", stock=service["stock"]), show_alert=True)
            return
        await db.update_cart_quantity(cart_id, call.from_user.id, new_qty)
        await _refresh_cart(call, lang)
    await call.answer()

@router.callback_query(F.data.startswith("cart_minus:"))
async def cart_minus(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    cart_id = int(call.data.split(":")[1])
    cart_items = await db.get_cart(call.from_user.id)
    item = next((i for i in cart_items if i["id"] == cart_id), None)
    if item:
        if item["quantity"] <= 1:
            await db.remove_from_cart(cart_id, call.from_user.id)
        else:
            await db.update_cart_quantity(cart_id, call.from_user.id, item["quantity"] - 1)
        await _refresh_cart(call, lang)
    await call.answer()

@router.callback_query(F.data.startswith("cart_del:"))
async def cart_del(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    cart_id = int(call.data.split(":")[1])
    await db.remove_from_cart(cart_id, call.from_user.id)
    await _refresh_cart(call, lang)
    await call.answer()

@router.callback_query(F.data == "cart_clear")
async def cart_clear(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    await db.clear_cart(call.from_user.id)
    await call.message.edit_text(t(lang, "cart_empty"))
    await call.answer()


async def _validate_cart_items_for_checkout(user_id: int, lang: str):
    cart_items = await db.get_cart(user_id)
    if not cart_items:
        return False, t(lang, "cart_empty"), []
    for item in cart_items:
        service = normalize_service(await db.get_public_service(item["service_id"]))
        if not service:
            return False, t(lang, "service_not_found"), []
        if service["stock"] != -1 and item["quantity"] > service["stock"]:
            return False, t(lang, "stock_error", stock=service["stock"]), []
    return True, None, cart_items


@router.callback_query(F.data == "cart_checkout")
async def cart_checkout(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    ok, error_text, cart_items = await _validate_cart_items_for_checkout(call.from_user.id, lang)
    if not ok:
        await call.answer(error_text, show_alert=True)
        return
    for item in cart_items:
        service = normalize_service(await db.get_public_service(item["service_id"]))
        if service and service.get("delivery_mode") == "referral_activation":
            text = (
                "🎯 Referral activation xizmatlari uchun savat checkout o'chirilgan. Iltimos, shu xizmatni alohida buyurtma qiling."
                if lang == "uz"
                else "🎯 Для услуг с активацией по рефералам checkout через корзину отключён. Пожалуйста, закажите эту услугу отдельно."
            )
            await call.answer(text, show_alert=True)
            return
    
    total = sum(i["price"] * i["quantity"] for i in cart_items)
    await state.update_data(cart_total=total, lang=lang, payment_method="manual")
    await state.set_state(CartOrderState.waiting_note)
    
    note_text = f"<b>{t(lang, 'step_1')} ✅</b>\n\nSavatdagi barcha buyurtmalar uchun qo'shimcha izoh yoki talablaringizni yozing (yoki o'tkazib yuboring):"
    await call.message.answer(note_text, reply_markup=skip_cancel_keyboard(lang), parse_mode="HTML")
    await call.answer()

@router.message(CartOrderState.waiting_note)
async def cart_receive_note(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    note = "" if _is_skip(message.text, lang) else message.text
    await state.update_data(note=note)
    
    total = data["cart_total"]
    
    # Check if all cart items support Stars
    cart_items = await db.get_cart(message.from_user.id)
    all_support_stars = bool(cart_items)
    if all_support_stars:
        for ci in cart_items:
            svc = await db.get_service(ci["service_id"])
            if not svc or not normalize_service(svc).get("supports_stars"):
                all_support_stars = False
                break
    
    if all_support_stars:
        await state.update_data(cart_supports_stars=True)
        await state.set_state(CartOrderState.waiting_payment_method)
        from keyboards.user_kb import payment_method_keyboard
        text = f"<b>{t(lang, 'step_2')} 💳</b>\n\nQanday usulda to'lov qilasiz? / Выберите способ оплаты:"
        await message.answer(text, reply_markup=payment_method_keyboard(lang, supports_stars=True), parse_mode="HTML")
    else:
        await state.set_state(CartOrderState.waiting_receipt)
        payment_text = t(lang, "payment_info", price=total, card=CARD_NUMBER, owner=CARD_OWNER)
        await message.answer(payment_text, reply_markup=cancel_keyboard(lang), parse_mode="HTML")


@router.message(CartOrderState.waiting_payment_method)
async def cart_receive_payment_method(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    total = data.get("cart_total", 0)
    
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    
    from keyboards.user_kb import payment_method_keyboard
    
    if message.text in [t("uz", "btn_card_payment"), t("ru", "btn_card_payment")]:
        await state.update_data(payment_method="manual")
        await state.set_state(CartOrderState.waiting_receipt)
        payment_text = t(lang, "payment_info", price=total, card=CARD_NUMBER, owner=CARD_OWNER)
        await message.answer(payment_text, reply_markup=cancel_keyboard(lang), parse_mode="HTML")
    elif "Telegram Stars" in (message.text or ""):
        await state.update_data(payment_method="stars")
        user_id = message.from_user.id
        note = data.get("note", "")
        ok, error_text, cart_items = await _validate_cart_items_for_checkout(user_id, lang)
        if not ok:
            await state.clear()
            await message.answer(error_text, reply_markup=main_menu(lang))
            return
        
        import uuid
        import keyboards.admin_kb as adm_kb
        
        for item in cart_items:
            service = normalize_service(await db.get_public_service(item["service_id"]))
            stars_price = service.get("stars_price", 0) * item["quantity"]
            final_price = item["price"] * item["quantity"]
            
            order_id = await db.create_order(
                user_id=user_id,
                service_id=item["service_id"],
                service_name=item["service_name"],
                price=item["price"],
                note=note,
                discount=0,
                final_price=final_price,
                coupon_code=None,
                bonus_used=0,
                quantity=item["quantity"]
            )
            await db.decrease_stock(item["service_id"], amount=item["quantity"])
            
            payload = f"stars_order:{order_id}:{uuid.uuid4().hex[:8]}"
            service_name = item["service_name"][:32].strip()
            await message.answer_invoice(
                title=service_name,
                description=f"Buyurtma #{order_id} to'lovi ({item['quantity']} dona)",
                payload=payload,
                currency="XTR",
                prices=[LabeledPrice(label=service_name, amount=stars_price)]
            )
            asyncio.create_task(abandoned_cart_job(user_id, order_id, bot, lang))
        
        await db.clear_cart(user_id)
        await state.clear()
    else:
        await message.answer("Iltimos, pastdagi tugmalardan birini tanlang.", reply_markup=payment_method_keyboard(lang, True))


@router.message(CartOrderState.waiting_receipt, F.photo)
async def cart_receive_receipt(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or "nomalum"
    data = await state.get_data()
    lang = data.get("lang", "uz")
    note = data.get("note", "")
    
    ok, error_text, cart_items = await _validate_cart_items_for_checkout(user_id, lang)
    if not ok:
        await state.clear()
        await message.answer(error_text, reply_markup=main_menu(lang))
        return
        
    file_id = message.photo[-1].file_id
    import keyboards.admin_kb as adm_kb
    
    for item in cart_items:
        final_price = item["price"] * item["quantity"]
        order_id = await db.create_order(
            user_id=user_id,
            service_id=item["service_id"],
            service_name=item["service_name"],
            price=item["price"],
            note=note,
            discount=0,
            final_price=final_price,
            coupon_code=None,
            bonus_used=0,
            quantity=item["quantity"]
        )
        await db.set_order_receipt(order_id, file_id)
        await db.create_payment(
            order_id=order_id, user_id=user_id, method="manual",
            amount=final_price, receipt_file_id=file_id, status="submitted",
        )
        await db.decrease_stock(item["service_id"], amount=item["quantity"])
        
        # Notify admin with receipt photo per item
        for admin_id in ADMIN_IDS:
            try:
                text = (
                    f"\U0001f514 <b>Yangi buyurtma #{order_id} (Savatdan)</b>\n\n"
                    f"\U0001f464 @{username} (<code>{user_id}</code>)\n"
                    f"\U0001f6cd {item['service_name']}\n"
                    f"\U0001f4b0 {final_price:,} so'm ({item['quantity']} dona)\n"
                    f"\U0001f4dd {note or '—'}"
                )
                await bot.send_photo(
                    admin_id, file_id,
                    caption=text,
                    reply_markup=adm_kb.order_action_keyboard(order_id),
                    parse_mode="HTML",
                )
            except Exception:
                pass
        asyncio.create_task(abandoned_cart_job(user_id, order_id, message.bot, lang))
        
    await db.clear_cart(user_id)
    await state.clear()
    
    await message.answer(
        "✅ <b>Savatdagi buyurtmalar qabul qilindi!</b>\n\nAdmin tez orada ko'rib chiqadi.", 
        reply_markup=main_menu(lang), parse_mode="HTML"
    )

@router.message(CartOrderState.waiting_receipt)
async def cart_receipt_invalid(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    await message.answer(t(lang, "send_photo_receipt"))


# ORDER FLOW

@router.callback_query(F.data.startswith("order:"))
async def start_order(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    service_id = int(call.data.split(":")[1])
    s = normalize_service(await db.get_public_service(service_id))
    if not s:
        await call.answer(t(lang, "service_not_found"), show_alert=True)
        return
    if s["stock"] == 0:
        await call.answer(t(lang, "out_of_stock"), show_alert=True)
        return
    await call.answer()
    
    # Flash Sale Calculation for Order
    from datetime import datetime
    if s.get("flash_discount") and s.get("flash_expire_at"):
        try:
            expire_dt = datetime.strptime(s["flash_expire_at"], "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.now()
            if now_dt < expire_dt:
                s['price'] = int(s['price'] * (100 - s['flash_discount']) / 100)
        except Exception:
            pass
            
    await state.update_data(
        service_id=service_id,
        service_name=s["name"],
        base_price=s["price"],
        lang=lang,
        delivery_mode=s.get("delivery_mode", "manual"),
        required_referrals=int(s.get("required_referrals") or 0),
        requires_email=int(s.get("requires_email") or 0),
        referral_deadline_days=int(s.get("referral_deadline_days") or 0),
    )
    
    await state.update_data(supports_stars=bool(s["supports_stars"]), stars_price=s["stars_price"])
    
    await state.update_data(payment_method="manual")

    # Auto-skip quantity step when stock is unlimited (most services)
    if s["stock"] == -1:
        unit_price = await db.get_price_for_quantity(service_id, 1, s["price"])
        await state.update_data(quantity=1, price=unit_price, unit_price=unit_price)
        await _show_coupon_picker_or_continue(call.message, call.from_user.id, state, lang)
        return

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
    
    s = normalize_service(await db.get_public_service(int(service_id_str)))
    if not s:
        await call.answer(t(lang, "service_not_found"), show_alert=True)
        return
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
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
        
    try:
        qty = int(message.text)
        if qty <= 0: raise ValueError
    except ValueError:
        await message.answer(t(lang, "invalid_quantity"))
        return
        
    s = normalize_service(await db.get_public_service(data["service_id"]))
    if not s:
        await message.answer(t(lang, "service_not_found"))
        return
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

    # Per-user limit check
    if coupon.get("max_per_user", 0) > 0:
        can_use = await db.check_coupon_user_limit(coupon["id"], call.from_user.id, coupon["max_per_user"])
        if not can_use:
            limit_text = (
                "⚠️ Siz bu kuponni allaqachon ishlatgansiz."
                if lang == "uz"
                else "❌ У вас есть незавершённый заказ."
            )
            await call.answer(limit_text, show_alert=True)
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
    await state.update_data(coupon_id=coupon["id"])
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
            # Per-user limit check
            if coupon.get("max_per_user", 0) > 0:
                can_use = await db.check_coupon_user_limit(coupon["id"], message.from_user.id, coupon["max_per_user"])
                if not can_use:
                    limit_text = (
                        "⚠️ Siz bu kuponni allaqachon ishlatgansiz."
                        if lang == "uz"
                        else "❌ У вас есть незавершённый заказ."
                    )
                    await message.answer(limit_text, parse_mode="HTML")
                    return
            discount = coupon["discount_percent"]
            coupon_code = coupon["code"]
            price = data["price"]
            final = price - (price * discount // 100)
            await message.answer(t(lang, "coupon_applied", discount=discount, final=final), parse_mode="HTML")
            await state.update_data(coupon_id=coupon["id"])
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
    """Kept for backward compat — if user somehow reaches this state, handle it."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    note = "" if _is_skip(message.text, lang) else (message.text or "")
    await _create_order_and_show_payment(message, state, lang, note=note)


async def _create_order_and_show_payment(message, state: FSMContext, lang: str, note: str = "", user_id_override: int = None):
    """Core order creation + payment flow. Called directly (no note step)."""
    data = await state.get_data()
    user_id = user_id_override or message.from_user.id
    discount = data.get("discount", 0)
    coupon_code = data.get("coupon_code")
    bonus_used = data.get("bonus_used", 0) or 0
    price = data["price"]
    final_price = max(0, price - (price * discount // 100) - bonus_used)
    is_referral_activation = data.get("delivery_mode") == "referral_activation"
    referral_code = secrets.token_hex(4) if is_referral_activation else None
    referral_link = _build_referral_link(0, referral_code) if is_referral_activation else None
    referral_status = "not_required"
    referral_deadline_at = None
    required_referrals = 0
    if is_referral_activation:
        required_referrals = int(data.get("required_referrals") or 0)
        referral_status = "awaiting_email" if int(data.get("requires_email") or 0) else "awaiting_referrals"
        referral_deadline_at = db.build_referral_deadline(int(data.get("referral_deadline_days") or 0))
    latest_service = normalize_service(await db.get_public_service(data["service_id"]))
    if not latest_service:
        await state.clear()
        await message.answer(t(lang, "service_not_found"), reply_markup=main_menu(lang))
        return
    qty_for_order = data.get("quantity", 1)
    if latest_service["stock"] != -1 and qty_for_order > latest_service["stock"]:
        await message.answer(t(lang, "stock_error", stock=latest_service["stock"]))
        return

    order_id = await db.create_order(
        user_id=user_id,
        service_id=data["service_id"],
        service_name=data["service_name"],
        price=price,
        note=note,
        discount=discount,
        final_price=final_price,
        coupon_code=coupon_code,
        bonus_used=bonus_used,
        quantity=data.get("quantity", 1),
        required_referrals=required_referrals,
        current_referrals=0 if is_referral_activation else 0,
        referral_status=referral_status,
        referral_code=referral_code,
        referral_link=referral_link,
        referral_deadline_at=referral_deadline_at,
        activation_status="pending",
    )
    try:
        await db.decrease_stock(data["service_id"], amount=data.get("quantity", 1))
        if coupon_code:
            await db.use_coupon(coupon_code)
            coupon_id = data.get("coupon_id")
            if coupon_id:
                await db.record_coupon_use(coupon_id, user_id)
        if bonus_used > 0:
            await db.use_bonus(user_id, bonus_used, f"Buyurtma #{order_id}")
    except Exception as pipeline_err:
        logging.error(f"Order #{order_id} pipeline xatosi, rollback: {pipeline_err}")
        await db.update_order_status(order_id, "cancelled")
        await db.increase_stock(data["service_id"], amount=data.get("quantity", 1))
        if bonus_used > 0:
            await db.add_bonus(user_id, bonus_used, f"Rollback: pipeline xatosi #{order_id}")
        await state.clear()
        await message.answer(
            "❌ Buyurtma yaratishda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.",
            reply_markup=main_menu(lang),
        )
        return

    import keyboards.admin_kb as adm_kb
    usr = await db.get_user(user_id)
    username = (usr.get("username") if usr else None) or (getattr(getattr(message, 'from_user', None), 'username', None)) or "nomalum"
    discount_text = f"\nChegirma: {discount}% | Yakuniy: {final_price:,} so'm" if discount else ""
    bonus_text = f"\n\U0001f381 Bonus: {bonus_used:,} so'm" if bonus_used else ""
    if is_referral_activation and referral_code:
        referral_link = _build_referral_link(order_id, referral_code)
        await db.set_order_referral_link(order_id, referral_link)
        init_bar = "⬜" * 10
        intro_text = (
            f"✅ <b>Buyurtmangiz yaratildi!</b>\n\n"
            f"Ushbu xizmatni faollashtirish uchun <b>{required_referrals}</b> ta yangi foydalanuvchi taklif qilishingiz kerak.\n\n"
            f"📊 <b>Progress:</b> 0 / {required_referrals}\n"
            f"{init_bar}\n\n"
            f"🔗 Taklif havolangiz:\n<code>{referral_link}</code>\n\n"
            f"📧 Emailingizni keyin alohida yuborasiz."
            if lang == "uz"
            else
            f"✅ <b>Заказ принят!</b>\n\n"
            f"🎯 Чтобы активировать услугу, пригласите <b>{required_referrals}</b> новых пользователей.\n\n"
            f"📊 <b>Прогресс:</b> 0 / {required_referrals}\n"
            f"{init_bar}\n\n"
            f"🔗 Ваша ссылка:\n<code>{referral_link}</code>\n\n"
            f"📧 Email необходимо отправить позже."
        )
        await message.answer(intro_text, reply_markup=referral_order_keyboard(order_id, lang), parse_mode="HTML")

    if final_price == 0:
        # Bonus covers full price — no payment needed
        await state.clear()
        await message.answer(t(lang, "order_accepted_free", order_id=order_id), reply_markup=main_menu(lang), parse_mode="HTML")
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"\U0001f514 <b>Yangi buyurtma #{order_id}</b> (Bonus bilan to'liq to'langan)\n\n"
                    f"\U0001f464 @{username} (<code>{user_id}</code>)\n"
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
            text = f"💳 <b>To'lov</b>\n\n📦 {data['service_name']}\n💰 Narx: <b>{final_price:,} so'm</b>\n\nTo'lov usulini tanlang:"
            sent = await message.answer(text, reply_markup=payment_method_keyboard(lang, supports_stars=True), parse_mode="HTML")
            _track_ui_message(user_id, sent.message_id)
        else:
            await state.set_state(OrderState.waiting_receipt)
            from keyboards.user_kb import cancel_keyboard
            text = f"💳 <b>To'lov</b>\n\n📦 {data['service_name']}\n💰 Narx: <b>{final_price:,} so'm</b>\n\n{t(lang, 'payment_info', price=final_price, card=CARD_NUMBER, owner=CARD_OWNER)}"
            await message.answer(
                text,
                reply_markup=cancel_keyboard(lang),
                parse_mode="HTML",
            )
        asyncio.create_task(abandoned_cart_job(user_id, order_id, message.bot, lang))


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
                await db.increase_stock(order["service_id"], amount=order.get("quantity", 1))
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
    await db.create_payment(
        order_id=order_id, user_id=message.from_user.id,
        method="manual", amount=data.get("final_price", data.get("price", 0)),
        receipt_file_id=file_id,
        status="submitted",
    )
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
                await db.increase_stock(order["service_id"], amount=order.get("quantity", 1))
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
        
        # Record payment
        order = await db.get_order(order_id)
        await db.create_payment(
            order_id=order_id, user_id=message.from_user.id,
            method="stars", amount=message.successful_payment.total_amount,
            charge_id=charge_id, payload=payload,
            status="paid", paid_at="CURRENT_TIMESTAMP",
        )
        
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
        if int(o.get("required_referrals") or 0) > 0:
            o = await db.expire_referral_order_if_needed(o["id"]) or o
        emoji = STATUS_EMOJI.get(o["status"], "❓")
        fp = o["final_price"] or o["price"]
        text += f"{emoji} <b>#{o['id']}</b> — {o['service_name']}\n   {fp:,} so'm | {o['created_at'][:10]}\n"
        if int(o.get("required_referrals") or 0) > 0:
            cur = int(o.get("current_referrals") or 0)
            req = int(o.get("required_referrals") or 0)
            bar_f = min(10, round(cur / max(req, 1) * 10)) if req else 0
            bar = "🟩" * bar_f + "⬜" * (10 - bar_f)
            text += f"   {bar} {cur}/{req}\n"
            if o.get("customer_email"):
                text += f"   📧 {o.get('customer_email')}\n"
        text += "\n"
    await message.answer(text, parse_mode="HTML")
    for o in orders:
        if int(o.get("required_referrals") or 0) <= 0:
            continue
        order = await db.expire_referral_order_if_needed(o["id"]) or o
        cur = int(order.get("current_referrals") or 0)
        req = int(order.get("required_referrals") or 0)
        bar_f = min(10, round(cur / max(req, 1) * 10)) if req else 0
        bar = "🟩" * bar_f + "⬜" * (10 - bar_f)
        ref_st = order.get("referral_status", "not_required")
        act_st = order.get("activation_status", "pending")
        if lang == "uz":
            ref_label = {"awaiting_referrals": "⏳ Kutilmoqda", "awaiting_email": "📧 Email kerak",
                         "target_met": "✅ Bajarildi", "expired": "⏰ Tugagan", "cancelled": "❌ Bekor"}.get(ref_st, ref_st)
            act_label = {"pending": "⏳", "ready": "🟢 Tayyor", "activated": "✅ Aktiv", "failed": "❌"}.get(act_st, act_st)
            summary = (
                f"🧾 <b>Buyurtma #{order['id']}</b>\n"
                f"{bar} {cur}/{req}\n"
                f"📋 {ref_label} | {act_label}"
            )
        else:
            ref_label = {"awaiting_referrals": "⏳ Ожидание", "awaiting_email": "📧 Нужен email",
                         "target_met": "✅ Достигнуто", "expired": "⏰ Истёк", "cancelled": "❌ Отменён"}.get(ref_st, ref_st)
            act_label = {"pending": "⏳", "ready": "🟢 Готово", "activated": "✅ Активир.", "failed": "❌"}.get(act_st, act_st)
            summary = (
                f"🧾 <b>Заказ #{order['id']}</b>\n"
                f"{bar} {cur}/{req}\n"
                f"📋 {ref_label} | {act_label}"
            )
        await message.answer(summary, reply_markup=referral_order_keyboard(order["id"], lang), parse_mode="HTML")


@router.callback_query(F.data == "profile_orders")
async def profile_orders_cb(call: CallbackQuery, state: FSMContext):
    """Show orders list from profile inline button."""
    await call.answer()
    lang = await get_lang(call.from_user.id)
    orders = await db.get_user_orders(call.from_user.id)
    if not orders:
        await call.message.answer(t(lang, "no_orders"))
        return
    text = t(lang, "orders_list")
    for o in orders:
        if int(o.get("required_referrals") or 0) > 0:
            o = await db.expire_referral_order_if_needed(o["id"]) or o
        emoji = STATUS_EMOJI.get(o["status"], "\u2753")
        fp = o["final_price"] or o["price"]
        text += f"{emoji} <b>#{o['id']}</b> \u2014 {o['service_name']}\n   {fp:,} so'm | {o['created_at'][:10]}\n"
        if int(o.get("required_referrals") or 0) > 0:
            cur = int(o.get("current_referrals") or 0)
            req = int(o.get("required_referrals") or 0)
            bar_f = min(10, round(cur / max(req, 1) * 10)) if req else 0
            bar = "\U0001f7e9" * bar_f + "\u2b1c" * (10 - bar_f)
            text += f"   {bar} {cur}/{req}\n"
        text += "\n"
    await call.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("ref_link:"))
async def referral_order_link(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    order_id = int(call.data.split(":")[1])
    order = await db.get_order(order_id)
    if not order or order["user_id"] != call.from_user.id or int(order.get("required_referrals") or 0) <= 0:
        await call.answer(t(lang, "order_not_found"), show_alert=True)
        return
    link = order.get("referral_link") or _build_referral_link(order_id, order.get("referral_code"))
    await call.answer()
    await call.message.answer(
        f"🔗 Taklif havolangiz:\n{link}" if lang == "uz" else f"🔗 Ваша ссылка:\n{link}"
    )


@router.callback_query(F.data.startswith("ref_status:"))
async def referral_order_status(call: CallbackQuery):
    """Show user full referral order progress with progress bar."""
    lang = await get_lang(call.from_user.id)
    order_id = int(call.data.split(":")[1])
    order = await db.expire_referral_order_if_needed(order_id) or await db.get_order(order_id)
    if not order or order["user_id"] != call.from_user.id or int(order.get("required_referrals") or 0) <= 0:
        await call.answer(t(lang, "order_not_found"), show_alert=True)
        return

    current = int(order.get("current_referrals") or 0)
    required = int(order.get("required_referrals") or 0)
    bar_filled = min(10, round(current / max(required, 1) * 10)) if required else 0
    bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)

    ref_status = order.get("referral_status", "not_required")
    act_status = order.get("activation_status", "pending")

    status_labels_uz = {
        "awaiting_referrals": "⏳ Referallar kutilmoqda",
        "awaiting_email": "📧 Email kutilmoqda",
        "target_met": "✅ Target bajarildi",
        "expired": "⏰ Muddati tugagan",
        "cancelled": "❌ Bekor qilingan",
    }
    status_labels_ru = {
        "awaiting_referrals": "⏳ Ожидаются рефералы",
        "awaiting_email": "📧 Ожидается email",
        "target_met": "✅ Цель достигнута",
        "expired": "⏰ Срок истёк",
        "cancelled": "❌ Отменён",
    }
    act_labels_uz = {
        "pending": "⏳ Kutilmoqda",
        "ready": "🟢 Tayyor",
        "activated": "✅ Aktivlashtirildi",
        "failed": "❌ Muvaffaqiyatsiz",
    }
    act_labels_ru = {
        "pending": "⏳ Ожидает",
        "ready": "🟢 Готово",
        "activated": "✅ Активировано",
        "failed": "❌ Не удалось",
    }

    labels = status_labels_uz if lang == "uz" else status_labels_ru
    act_lbl = act_labels_uz if lang == "uz" else act_labels_ru

    deadline_raw = order.get("referral_deadline_at")
    if deadline_raw:
        deadline_text = str(deadline_raw)[:16]
        if ref_status == "expired":
            deadline_text = f"⚠️ {deadline_text} (tugagan)" if lang == "uz" else f"⚠️ {deadline_text} (истёк)"
    else:
        deadline_text = "belgilanmagan" if lang == "uz" else "не установлен"

    email_text = order.get("customer_email") or ("-" if lang == "uz" else "не указан")

    if lang == "uz":
        text = (
            f"📊 <b>Buyurtma #{order_id} — Referral holati</b>\n\n"
            f"🛒 Xizmat: {order['service_name']}\n\n"
            f"<b>Progress:</b> {current} / {required}\n"
            f"{bar}\n\n"
            f"📋 Holat: {labels.get(ref_status, ref_status)}\n"
            f"⚡ Aktivatsiya: {act_lbl.get(act_status, act_status)}\n"
            f"📧 Email: <code>{email_text}</code>\n"
            f"📅 Deadline: {deadline_text}"
        )
    else:
        text = (
            f"📊 <b>Заказ #{order_id} — Статус реферала</b>\n\n"
            f"🛒 Услуга: {order['service_name']}\n\n"
            f"<b>Прогресс:</b> {current} / {required}\n"
            f"{bar}\n\n"
            f"📋 Статус: {labels.get(ref_status, ref_status)}\n"
            f"⚡ Активация: {act_lbl.get(act_status, act_status)}\n"
            f"📧 Email: <code>{email_text}</code>\n"
            f"📅 Дедлайн: {deadline_text}"
        )

    await call.answer()
    await call.message.answer(text, parse_mode="HTML", reply_markup=referral_order_keyboard(order_id, lang))


@router.callback_query(F.data.startswith("ref_email:"))
async def referral_order_email_start(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    order_id = int(call.data.split(":")[1])
    order = await db.get_order(order_id)
    if not order or order["user_id"] != call.from_user.id or int(order.get("required_referrals") or 0) <= 0:
        await call.answer(t(lang, "order_not_found"), show_alert=True)
        return
    await state.update_data(referral_email_order_id=order_id, referral_email_lang=lang)
    await state.set_state(ReferralEmailState.email)
    await call.answer()
    await call.message.answer(
        "📧 Email manzilingizni yuboring:" if lang == "uz" else "📧 Отправьте ваш email:",
        reply_markup=cancel_keyboard(lang),
    )


@router.message(ReferralEmailState.email)
async def referral_order_email_save(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("referral_email_lang", "uz")
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    email = (message.text or "").strip()
    if not _is_valid_email(email):
        await message.answer(
            "❌ Email format noto'g'ri. Qaytadan yuboring." if lang == "uz" else "❌ Неверный формат email. Отправьте снова."
        )
        return
    order_id = int(data["referral_email_order_id"])
    order = await db.get_order(order_id)
    if not order or order["user_id"] != message.from_user.id:
        await state.clear()
        await message.answer(t(lang, "order_not_found"), reply_markup=main_menu(lang))
        return
    await db.set_order_referral_email(order_id, email)
    updated = await _evaluate_referral_order(order_id)
    await _notify_referral_email_saved(message.bot, updated or order)
    await state.clear()
    if updated and updated.get("activation_status") == "ready":
        text = (
            "✅ Email saqlandi. Buyurtmangiz aktivlashtirishga tayyor."
            if lang == "uz" else
            "✅ Email сохранён. Ваш заказ передан админу."
        )
    else:
        text = (
            "✅ Email saqlandi. Referral to'lgach admin tayyorlaydi."
            if lang == "uz" else
            "✅ Email сохранён. После завершения реферала админ активирует услугу."
        )
    await message.answer(text, reply_markup=main_menu(lang))


@router.message(CampaignEmailState.email)
async def campaign_email_save(message: Message, state: FSMContext):
    """Collect email from campaign participant after they completed referral target."""
    data = await state.get_data()
    lang = data.get("campaign_email_lang", "uz")
    if _is_cancel(message.text, lang):
        await state.clear()
        await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
        return
    email = (message.text or "").strip()
    if not _is_valid_email(email):
        await message.answer(
            "❌ Email format noto'g'ri. Qaytadan yuboring." if lang == "uz" else "❌ Неверный формат email. Отправьте снова."
        )
        return
    campaign_id = int(data.get("campaign_email_campaign_id", 0))
    if not campaign_id:
        await state.clear()
        await message.answer("❌ Xatolik.", reply_markup=main_menu(lang))
        return
    await db.set_campaign_participant_email(campaign_id, message.from_user.id, email)
    camp = await db.get_referral_campaign(campaign_id)
    camp_name = camp["name"] if camp else f"#{campaign_id}"
    await state.clear()
    await message.answer(
        f"✅ Email saqlandi! Admin tez orada xizmatni aktivlashtiradi.\n\n📧 {email}"
        if lang == "uz" else
        f"✅ Email сохранён! Админ скоро активирует услугу.\n\n📧 {email}",
        reply_markup=main_menu(lang),
    )
    # Notify admins
    user = await db.get_user(message.from_user.id)
    username = f"@{user['username']}" if user and user.get("username") else "nomalum"
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"📧 <b>Kampaniya email saqlandi!</b>\n\n"
                f"Kampaniya: {camp_name}\n"
                f"User: {username} (<code>{message.from_user.id}</code>)\n"
                f"Email: <code>{email}</code>\n\n"
                f"Aktivlashtirishga tayyor.",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    order_id = int(call.data.split(":")[1])
    order = await db.get_order(order_id)
    if order and order["user_id"] == call.from_user.id and order["status"] == "pending":
        await db.update_order_status(order_id, "cancelled")
        await db.increase_stock(order["service_id"], amount=order.get("quantity", 1))
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
        reply_markup=profile_keyboard(lang),
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
        text += "🎉 <b>Maxsus takliflar:</b>\n"
        for p in regular_promos[:10]:
            title = p["title"] or "Aksiya"
            body = p["text"] or ""
            text += f"• <b>{title}</b>"
            if body:
                text += f"\n{body}"
            text += "\n\n"

    if service_promos:
        text += "🎊 <b>Xizmat aksiyalari:</b>\n"
        for p in service_promos:
            bonus = int(p["price"] * p["cashback_percent"] / 100)
            promo_title = p["title"] or "Cashback aksiya"
            text += (
                f"• <b>{p['service_name']}</b>\n"
                f"🎁 {promo_title} ({p['cashback_percent']}% cashback)\n"
                f"💰 Kutilayotgan bonus: {bonus:,} so'm\n\n"
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


# --- AI Chat ---
@router.message(F.text.in_(["🤖 AI yordamchi", "🤖 ИИ Помощник"]))
async def ai_chat_start(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await state.set_state(AIChatState.chatting)
    await state.update_data(chat_history=[])
    from keyboards.user_kb import cancel_keyboard
    text = "🤖 Men sizning sun'iy intellekt yordamchingizman!\n\nBizning xizmatlar, narxlar va chegirmalar haqida istalgan savolingizni bering. Sizga yordam berishdan xursand bo'laman.\n\nChiqish uchun bekor qilish tugmasini bosing." if lang == "uz" else "🤖 Я ваш помощник с искусственным интеллектом!\n\nЗадайте любой вопрос о наших услугах, ценах и скидках. Буду рад помочь вам.\n\nНажмите кнопку отмены для выхода."
    await message.answer(text, reply_markup=cancel_keyboard(lang))

@router.message(AIChatState.chatting)
async def ai_chat_process(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    if message.text in ["❌ Bekor qilish", "❌ Отмена", "/cancel", "/start", "🏠 Asosiy menyu", "🏠 Главное меню"]:
        await state.clear()
        from keyboards.user_kb import main_menu
        await message.answer(t(lang, "main_menu"), reply_markup=main_menu(lang))
        return
    wait_msg = await message.answer("⏳ O'ylanmoqda..." if lang == "uz" else "⏳ Думаю...")
    import ai_agent
    
    data = await state.get_data()
    chat_history = data.get("chat_history", [])
    
    answer = await ai_agent._ask(message.text, with_catalog=True, history=chat_history)
    if answer:
        chat_history.append({"role": "user", "content": message.text})
        chat_history.append({"role": "assistant", "content": answer})
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]
        await state.update_data(chat_history=chat_history)
        await wait_msg.edit_text(answer)
    else:
        await wait_msg.edit_text("❌ Uzr, savolga javob topa olmadim." if lang == "uz" else "❌ Извините, не смог найти ответ на вопрос.")
