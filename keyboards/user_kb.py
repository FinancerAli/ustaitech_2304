from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from locales import t

# Telegram Premium Custom Emoji IDs
# Replace these with your actual premium emoji IDs from your sticker sets
PREMIUM_EMOJI = {
    "orders": "5368324170671202286",    # 📦
    "cart": "5377637695583979102",       # 🛒
    "profile": "5372981976804190757",    # 👤
    "services": "5373026167722876901",   # 🛍
    "back": "5372926953978341498",       # 🔙
    "buy": "5368324170671202286",       # 💳
    "category": "5373026167722876901",   # 📂
}

STATUS_EMOJI = {
    "pending": "⏳",
    "payment_waiting": "💳",
    "paid_waiting_admin": "🧾",
    "processing": "📦",
    "delivered": "✅",
    "confirmed": "✅",  # legacy compatibility
    "rejected": "❌",
    "cancelled": "🚫",
    "expired": "⌛",
}


ENABLE_TOP_SERVICES = False
ENABLE_SEARCH = False
ENABLE_REVIEWS = False

def main_menu(lang: str = "uz"):
    """
    Generate the main reply keyboard for end users.

    Args:
        lang (str): Two-letter language code ("uz" or "ru"). Defaults to "uz".

    Returns:
        ReplyKeyboardMarkup: A keyboard markup with localized button texts.
    """
    keyboard = [
        [
            KeyboardButton(text=t(lang, "services")),
            KeyboardButton(text=t(lang, "btn_ai_chat")),
        ],
        [
            KeyboardButton(text=t(lang, "cart")),
            KeyboardButton(text=t(lang, "profile")),
        ],
        [
            KeyboardButton(text=t(lang, "language")),
            KeyboardButton(text=t(lang, "contact")),
        ],
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)



def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\U0001f1fa\U0001f1ff O'zbekcha", callback_data="set_lang:uz"),
            InlineKeyboardButton(text="\U0001f1f7\U0001f1fa Русский", callback_data="set_lang:ru"),
        ]
    ])


def categories_keyboard(categories, lang="uz", min_prices=None):
    """Build category list with min price shown per category."""
    cur = t(lang, "currency")
    buttons = []
    for c in categories:
        cat_id = c['id']
        price_tag = ""
        if min_prices and cat_id in min_prices and min_prices[cat_id]:
            price_tag = f" — {min_prices[cat_id]:,.0f} {cur} dan"
        kwargs = {
            "text": f"{c['name']}{price_tag}",
            "callback_data": f"category:{cat_id}",
            "style": "primary",
        }
        cat_icon = dict(c).get("icon_emoji_id") or PREMIUM_EMOJI.get("category")
        if cat_icon:
            kwargs["icon_custom_emoji_id"] = cat_icon
        buttons.append([InlineKeyboardButton(**kwargs)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def services_keyboard(services, lang="uz", page: int = 1, total_count: int = 0, query: str = ""):
    cur = t(lang, "currency")
    buttons = []
    for s in services:
        stock = int(dict(s).get("stock") or -1)
        text_lbl = f"{s['name']} — {s['price']:,} {cur}"
        if dict(s).get("promo_active"):
            text_lbl += f" | {s['cashback_percent']}% cashback"
        btn_style = "success" if stock != 0 else "danger"
        kwargs = {
            "text": text_lbl,
            "callback_data": f"service:{s['id']}:{page}",
            "style": btn_style,
        }
        icon_id = dict(s).get("icon_emoji_id") or PREMIUM_EMOJI.get("services")
        if icon_id:
            kwargs["icon_custom_emoji_id"] = icon_id
        buttons.append([InlineKeyboardButton(**kwargs)])
        
    nav_buttons = []
    q_param = f":{query}" if query else ":"
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page-1}{q_param}"))
    if total_count > page * 10:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page+1}{q_param}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
        
    if query:
        buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_home")])
    else:
        buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_categories")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_detail_keyboard(service_id: int, lang="uz", stock: int = -1, back_page: int = 1):
    buttons = []
    if stock > 0 or stock == -1:
        buttons.append([InlineKeyboardButton(text=t(lang, "btn_order"), callback_data=f"order:{service_id}", style="success", icon_custom_emoji_id=PREMIUM_EMOJI["buy"])])
        buttons.append([InlineKeyboardButton(text=t(lang, "add_to_cart"), callback_data=f"cart_add:{service_id}", icon_custom_emoji_id=PREMIUM_EMOJI["cart"])])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"back_services_list:{back_page}", icon_custom_emoji_id=PREMIUM_EMOJI["back"])])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_keyboard(lang="uz"):
    """Inline keyboard shown under profile message with orders button."""
    orders_text = t(lang, "my_orders")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=orders_text, callback_data="profile_orders", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI["orders"])],
    ])

def cart_keyboard(cart_items, lang="uz"):
    buttons = []
    for item in cart_items:
        buttons.append([
            InlineKeyboardButton(text="➖", callback_data=f"cart_minus:{item['id']}"),
            InlineKeyboardButton(text=f"{item['service_name']} ({item['quantity']})", callback_data=f"cart_noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_plus:{item['id']}")
        ])
        buttons.append([InlineKeyboardButton(text=f"▫️ {item['service_name']}", callback_data=f"cart_del:{item['id']}")])
    if cart_items:
        buttons.append([InlineKeyboardButton(text=t(lang, "btn_checkout"), callback_data="cart_checkout")])
        buttons.append([InlineKeyboardButton(text=t(lang, "btn_clear_cart"), callback_data="cart_clear")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard(lang="uz"):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "cancel"))]],
        resize_keyboard=True,
    )


def skip_cancel_keyboard(lang="uz"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_skip"))],
            [KeyboardButton(text=t(lang, "cancel"))],
        ],
        resize_keyboard=True,
    )


def payment_method_keyboard(lang="uz", supports_stars=False):
    kb = [[KeyboardButton(text=t(lang, "btn_card_payment"))]]
    if supports_stars:
        kb.append([KeyboardButton(text="⭐️ Telegram Stars")])
    kb.append([KeyboardButton(text=t(lang, "cancel"))])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def confirm_order_keyboard(order_id: int, lang="uz"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_confirm_order"), callback_data=f"confirm_order:{order_id}")],
    ])


def referral_order_keyboard(order_id: int, lang="uz"):
    email_text = "📧 Email yuborish" if lang == "uz" else "📧 Отправить email"
    link_text = "🔗 Havola" if lang == "uz" else "🔗 Ссылка"
    status_text = "📊 Holatni ko'rish" if lang == "uz" else "📊 Статус"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=email_text, callback_data=f"ref_email:{order_id}")],
        [InlineKeyboardButton(text=link_text, callback_data=f"ref_link:{order_id}")],
        [InlineKeyboardButton(text=status_text, callback_data=f"ref_status:{order_id}")],
    ])


def quantity_keyboard(service_id: int, lang="uz"):
    btn_1_text = "1️⃣ 1 dona" if lang == "uz" else "1️⃣ 1 шт."
    btn_3_text = "3️⃣ 3 dona" if lang == "uz" else "3️⃣ 3 шт."
    btn_5_text = "5️⃣ 5 dona" if lang == "uz" else "5️⃣ 5 шт."
    btn_10_text = "▫️ 10 dona" if lang == "uz" else "▫️ 10 ▫️."

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=btn_1_text, callback_data=f"qty:{service_id}:1"),
            InlineKeyboardButton(text=btn_3_text, callback_data=f"qty:{service_id}:3"),
            InlineKeyboardButton(text=btn_5_text, callback_data=f"qty:{service_id}:5"),
        ],
        [
            InlineKeyboardButton(text=btn_10_text, callback_data=f"qty:{service_id}:10"),
            InlineKeyboardButton(text=t(lang, "btn_other_qty"), callback_data=f"qty_custom:{service_id}")
        ],
        [InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel_quantity_prompt")]
    ])


def coupon_pick_keyboard(coupons, lang="uz"):
    buttons = []

    for c in coupons:
        scope_icon = "\U0001f310" if c["service_id"] is None else "\U0001f3af"
        buttons.append([
            InlineKeyboardButton(
                text=f"{scope_icon} {c['code']} — -{c['discount_percent']}%",
                callback_data=f"use_coupon:{c['code']}"
            )
        ])

    skip_text = "\u23ed O'tkazib yuborish" if lang == "uz" else "\u23ed Пропустить"
    buttons.append([
        InlineKeyboardButton(text=skip_text, callback_data="use_coupon:skip")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

REVIEW_TEMPLATE_TEXTS = {
    "pos_fast": {
        "uz": "✅ Juda tez va qulay bo'ldi",
        "ru": "✅ Всё было быстро и удобно",
    },
    "pos_price": {
        "uz": "▫️ Narxi ham juda yaxshi ekan",
        "ru": "🔥 Цена тоже очень порадовала",
    },
    "pos_recommend": {
        "uz": "▫️ Xizmat zo'r, tavsiya qilaman",
        "ru": "⚡ Быстрая доставка, рекомендую",
    },
    "pos_support": {
        "uz": "▫️ Operator yaxshi yordam berdi",
        "ru": "👨‍💼 Оператор хорошо помог",
    },
    "pos_ok": {
        "uz": "⭐ Hammasi yaxshi ishladi",
        "ru": "⭐ Всё прошло хорошо",
    },
    "neg_delay": {
        "uz": "⏳ Biroz kechikdi",
        "ru": "⏳ Было немного долго",
    },
    "neg_unclear": {
        "uz": "❗ Yana aniqlik kerak bo'ldi",
        "ru": "❗ Понадобилось больше уточнений",
    },
    "neg_expect": {
        "uz": "▫️ Kutganimdan biroz boshqacha bo'ldi",
        "ru": "📞 Буду рекомендовать знакомым",
    },
    "neg_retry": {
        "uz": "▫️ Keyinroq yana urinib ko'raman",
        "ru": "🔄 Попробую ещё раз",
    },
    "neg_mid": {
        "uz": "▫️ O'rtacha tajriba bo'ldi",
        "ru": "💡 Хорошие советы",
    },
}


def review_templates_keyboard(order_id: int, rating: int, lang="uz"):
    buttons = []

    if rating >= 4:
        keys = ["pos_fast", "pos_price", "pos_recommend", "pos_support", "pos_ok"]
    else:
        keys = ["neg_delay", "neg_unclear", "neg_expect", "neg_retry", "neg_mid"]

    for key in keys:
        text_lbl = REVIEW_TEMPLATE_TEXTS[key]["uz" if lang == "uz" else "ru"]
        buttons.append([
            InlineKeyboardButton(
                text=text_lbl,
                callback_data=f"rate_tpl:{order_id}:{rating}:{key}"
            )
        ])

    custom_text = "✍️ O'z fikrimni yozaman" if lang == "uz" else "✍️ Напишу свой отзыв"
    skip_text = "⏭ O'tkazib yuborish" if lang == "uz" else "⏭ Пропустить"

    buttons.append([
        InlineKeyboardButton(text=custom_text, callback_data=f"rate_custom:{order_id}:{rating}")
    ])
    buttons.append([
        InlineKeyboardButton(text=skip_text, callback_data=f"rate_skip:{order_id}:{rating}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def rating_keyboard(order_id: int):
    stars = [InlineKeyboardButton(text="\u2b50" * i, callback_data=f"rate:{order_id}:{i}") for i in range(1, 6)]
    return InlineKeyboardMarkup(inline_keyboard=[stars[:3], stars[3:]])


def bonus_keyboard(lang="uz"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_skip"))],
            [KeyboardButton(text=t(lang, "cancel"))],
        ],
        resize_keyboard=True,
    )


def ref_campaigns_keyboard(campaigns, completed_ids=None, lang="uz"):
    if completed_ids is None:
        completed_ids = []
    buttons = []
    for c in campaigns:
        status_icon = "🏆" if c["id"] in completed_ids else ("✅" if c["is_active"] else "🔴")
        buttons.append([InlineKeyboardButton(
            text=f"{status_icon} {c['name']} ({c['required_referrals']} ta)",
            callback_data=f"ref_camp:{c['id']}"
        )])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ref_campaign_detail_keyboard(campaign_id: int, participant, lang="uz", link: str = None, camp_name: str = ""):
    buttons = []
    if not participant:
        join_text = "🎯 Qo'shilish" if lang == "uz" else "🎯 Вступить"
        buttons.append([InlineKeyboardButton(text=join_text, callback_data=f"ref_camp_join:{campaign_id}")])
    else:
        # Check if reward given
        # participant might be passed as True from old code, handle it safely
        if isinstance(participant, dict) and participant.get("reward_given"):
            act_st = participant.get("activation_status") or "pending"
            if not participant.get("customer_email"):
                # Missing email
                email_btn = "📧 Email yuborish" if lang == "uz" else "📧 Отправить Email"
                buttons.append([InlineKeyboardButton(text=email_btn, callback_data=f"ref_camp_ask_email:{campaign_id}")])
            else:
                # Has email, waiting or activated
                email_btn = "📧 Email o'zgartirish" if lang == "uz" else "📧 Изменить Email"
                buttons.append([InlineKeyboardButton(text=email_btn, callback_data=f"ref_camp_ask_email:{campaign_id}")])
                
        link_text = "🔗 Havolani olish" if lang == "uz" else "🔗 Получить ссылку"
        buttons.append([InlineKeyboardButton(text=link_text, callback_data=f"ref_camp_link:{campaign_id}")])
        
        if link:
            share_text = "↗️ Ulashish (Do'stlarga jo'natish)" if lang == "uz" else "↗️ Поделиться с друзьями"
            import urllib.parse
            share_msg = f"Ajoyib imkoniyat!\n\n{camp_name} dasturida qatnashing va bepul xizmatlarga ega bo'ling!" if lang == "uz" else f"Отличная возможность!\n\nУчаствуйте в {camp_name} и получайте бесплатные услуги!"
            share_url = f"https://t.me/share/url?url={link}&text={urllib.parse.quote(share_msg)}"
            buttons.append([InlineKeyboardButton(text=share_text, url=share_url)])
            
    back_text = t(lang, "btn_back")
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="ref_camp_list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def contact_keyboard(lang="uz"):
    op_text = t(lang, "btn_support")
    ch_text = "📺 Kanalga o'tish" if lang == "uz" else "📺 Перейти в канал"
    back_text = t(lang, "btn_back_arrow")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=op_text, url="https://t.me/UstAiTechsupportbot")],
        [InlineKeyboardButton(text=ch_text, url="https://t.me/UstAiTech")],
        [InlineKeyboardButton(text=back_text, callback_data="back_home")]
    ])
