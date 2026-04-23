from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\U0001f4cb Kutilayotgan buyurtmalar"), KeyboardButton(text="\U0001f4ca Statistika")],
            [KeyboardButton(text="\U0001f6e0 Xizmatlarni boshqarish"), KeyboardButton(text="\U0001f4c2 Kategoriyalar")],
            [KeyboardButton(text="\U0001f465 Foydalanuvchilar"), KeyboardButton(text="\U0001f4dc Barcha buyurtmalar")],
            [KeyboardButton(text="\u2705 Tasdiqlangan mijozlar")],
            [KeyboardButton(text="\U0001f4e2 Xabar yuborish"), KeyboardButton(text="\U0001f3f7 Kuponlar")],
            [KeyboardButton(text="? Reviewlar"), KeyboardButton(text="\U0001f4e5 Excel eksport")],
            [KeyboardButton(text="\U0001f4be Backup"), KeyboardButton(text="\U0001f48e Bonus boshqaruv")],
            [KeyboardButton(text="?? Referral aktivatsiyalar")],
            [KeyboardButton(text="\U0001f519 Foydalanuvchi menyusi"), KeyboardButton(text="?? Aksiyalar boshqaruvi")],
            [KeyboardButton(text="?? Analitika"), KeyboardButton(text="?? CRM")],
        ],
        resize_keyboard=True,
    )


def services_manage_keyboard(services):
    buttons = []
    for s in services:
        status = "\u2705" if s["active"] else "\U0001f534"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {s['name']} ? {s['price']:,} so'm",
            callback_data=f"adm_service:{s['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="\u2795 Yangi xizmat", callback_data="adm_add_service")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promos_manage_keyboard(promos):
    buttons = []
    for p in promos:
        buttons.append([InlineKeyboardButton(text=f"?? {p['title']}", callback_data=f"adm_del_promo:{p['id']}")])
    buttons.append([InlineKeyboardButton(text="? Yangi Aksiya", callback_data="adm_add_promo")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cashback_promos_manage_keyboard(promos):
    buttons = []
    for p in promos:
        status = "??" if p["is_active"] else "??"
        title = p["title"] or "Cashback"
        buttons.append([InlineKeyboardButton(text=f"{status} {p['service_name']} - {title} ({p['cashback_percent']}%)", callback_data=f"adm_set_cashback:{p['service_id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_admin_detail(service_id: int, active: int, has_delivery: bool = False, has_form: bool = False, auto_deliver: bool = False):
    toggle_text = "\U0001f534 O'chirish" if active else "\u2705 Yoqish"
    delivery_text = "\U0001f4e6 Yetkazish \u2705" if has_delivery else "\U0001f4e6 Yetkazish qo'shish"
    form_text = "\U0001f9fe Forma \u2705" if has_form else "\U0001f9fe Forma ko'rsatmasi qo'shish"
    auto_text = "?? Auto yetkazish ?" if auto_deliver else "?? Auto yetkazish"
    buttons = [
        [InlineKeyboardButton(text="\u270f\ufe0f Tahrirlash", callback_data=f"adm_edit:{service_id}")],
        [InlineKeyboardButton(text="\U0001f4e6 Qoldiqni o'zgartirish", callback_data=f"adm_edit_stock:{service_id}")],
        [InlineKeyboardButton(text="\U0001f381 Cashback sozlash", callback_data=f"adm_set_cashback:{service_id}")],
        [InlineKeyboardButton(text="\U0001f4e6 Ulgurji narxlar", callback_data=f"adm_bulk:{service_id}")],
        [InlineKeyboardButton(text=delivery_text, callback_data=f"adm_set_delivery:{service_id}")],
        [InlineKeyboardButton(text=form_text, callback_data=f"adm_set_form_instruction:{service_id}")],
    ]
    if has_delivery:
        buttons.append([InlineKeyboardButton(text=auto_text, callback_data=f"adm_toggle_auto_deliver:{service_id}")])
    buttons.append([InlineKeyboardButton(text="\U0001f525 Flash Sale (Chegirma)", callback_data=f"adm_flash:{service_id}")])
    buttons.extend([
        [InlineKeyboardButton(text=toggle_text, callback_data=f"adm_toggle:{service_id}")],
        [InlineKeyboardButton(text="\U0001f5d1 O'chirish", callback_data=f"adm_delete:{service_id}")],
        [InlineKeyboardButton(text="\U0001f519 Orqaga", callback_data="adm_back_services")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_action_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\u2705 Tasdiqlash", callback_data=f"adm_confirm:{order_id}"),
            InlineKeyboardButton(text="\u274c Rad etish", callback_data=f"adm_reject:{order_id}"),
        ],
        [InlineKeyboardButton(text="\u2709\ufe0f Javob", callback_data=f"adm_reply:{order_id}")],
    ])


def referral_filters_keyboard(current_filter: str = "pending"):
    labels = [
        ("pending", "? Pending"),
        ("ready", "? Ready"),
        ("expired", "? Expired"),
        ("activated", "?? Activated"),
    ]
    rows = []
    for key, label in labels:
        text = f"? {label}" if key == current_filter else label
        rows.append([InlineKeyboardButton(text=text, callback_data=f"adm_ref_list:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def referral_order_list_keyboard(orders, current_filter: str = "pending"):
    buttons = []
    for o in orders:
        buttons.append([
            InlineKeyboardButton(
                text=f"#{o['id']} {o['service_name']} ({o.get('current_referrals', 0)}/{o.get('required_referrals', 0)})",
                callback_data=f"adm_ref_view:{o['id']}:{current_filter}",
            )
        ])
    buttons.extend(referral_filters_keyboard(current_filter).inline_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def referral_order_detail_keyboard(order_id: int, current_filter: str = "pending"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="? Aktivlashtirdim", callback_data=f"adm_ref_activate:{order_id}:{current_filter}")],
        [InlineKeyboardButton(text="? Bekor qilish", callback_data=f"adm_ref_cancel:{order_id}:{current_filter}")],
        [InlineKeyboardButton(text="0 kun", callback_data=f"adm_ref_deadline:{order_id}:0:{current_filter}")],
        [InlineKeyboardButton(text="7 kun", callback_data=f"adm_ref_deadline:{order_id}:7:{current_filter}")],
        [InlineKeyboardButton(text="14 kun", callback_data=f"adm_ref_deadline:{order_id}:14:{current_filter}")],
        [InlineKeyboardButton(text="30 kun", callback_data=f"adm_ref_deadline:{order_id}:30:{current_filter}")],
        [InlineKeyboardButton(text="?? Mijozga xabar", callback_data=f"adm_reply:{order_id}")],
        [InlineKeyboardButton(text="?? Orqaga", callback_data=f"adm_ref_list:{current_filter}")],
    ])


def delivery_choose_keyboard(order_id: int, has_preset: bool, has_form: bool = False):
    buttons = []

    if has_preset:
        buttons.append([InlineKeyboardButton(
            text="\U0001f4cb Shablon yuborish",
            callback_data=f"adm_deliver_std:{order_id}",
        )])
        buttons.append([InlineKeyboardButton(
            text="\U0001f511 Key + qo?llanma",
            callback_data=f"adm_deliver_keyguide:{order_id}",
        )])

    buttons.append([InlineKeyboardButton(
        text="\U0001f4e9 Individual xabar yozish",
        callback_data=f"adm_deliver_custom:{order_id}",
    )])

    if has_form:
        buttons.append([InlineKeyboardButton(
            text="\U0001f9fe Forma yuborish",
            callback_data=f"adm_deliver_form:{order_id}",
        )])

    buttons.append([InlineKeyboardButton(
        text="\u23ed O'tkazib yuborish",
        callback_data=f"adm_deliver_skip:{order_id}",
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def form_fulfilled_keyboard(order_id: int, user_id: int):
    """Shown to admin in the form-reply notification. Lets admin mark order complete."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="\u2705 Buyurtma bajarildi",
            callback_data=f"adm_form_fulfilled:{order_id}:{user_id}",
        )]
    ])


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="\u274c Bekor qilish")]],
        resize_keyboard=True,
    )


def confirm_delete_keyboard(service_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\u2705 Ha, o'chir", callback_data=f"adm_confirm_delete:{service_id}"),
            InlineKeyboardButton(text="\U0001f519 Yo'q", callback_data=f"adm_service:{service_id}"),
        ]
    ])


def categories_manage_keyboard(categories):
    buttons = []
    for c in categories:
        buttons.append([
            InlineKeyboardButton(text=c["name"], callback_data=f"adm_cat_view:{c['id']}"),
            InlineKeyboardButton(text="??", callback_data=f"adm_cat_edit:{c['id']}"),
            InlineKeyboardButton(text="\U0001f5d1", callback_data=f"adm_cat_del:{c['id']}"),
        ])
    buttons.append([InlineKeyboardButton(text="\u2795 Kategoriya qo'shish", callback_data="adm_cat_add")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def bonus_manage_keyboard(user_id: int, balance: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\u2795 Bonus qo'shish", callback_data=f"adm_bonus_add:{user_id}"),
            InlineKeyboardButton(text="\u2796 Bonus ayirish", callback_data=f"adm_bonus_sub:{user_id}"),
        ],
        [InlineKeyboardButton(text="\U0001f4cb Tarix", callback_data=f"adm_bonus_log:{user_id}")],
    ])


def coupons_keyboard(coupons):
    buttons = []
    for c in coupons:
        status = "\u2705" if c["is_active"] and c["used_count"] < c["max_uses"] else "\u274c"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {c['code']} -{c['discount_percent']}% ({c['used_count']}/{c['max_uses']})",
                callback_data=f"adm_coupon_view:{c['id']}"
            ),
            InlineKeyboardButton(text="\U0001f5d1", callback_data=f"adm_coupon_del:{c['id']}"),
        ])
    buttons.append([InlineKeyboardButton(text="\u2795 Kupon yaratish", callback_data="adm_coupon_add")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def category_detail_keyboard(cat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2795 Xizmat biriktirish", callback_data=f"adm_cat_attach:{cat_id}")],
        [InlineKeyboardButton(text="\U0001f519 Orqaga", callback_data="adm_cat_back")],
    ])


def category_attach_services_keyboard(services, cat_id: int):
    buttons = []

    for s in services:
        buttons.append([
            InlineKeyboardButton(
                text=f"{s['name']} ? {s['price']:,} so'm",
                callback_data=f"adm_cat_attach_pick:{cat_id}:{s['id']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="\U0001f519 Orqaga", callback_data=f"adm_cat_view:{cat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def support_reply_keyboard(user_id: int, message_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="?? Javob berish", callback_data=f"adm_sup_reply:{user_id}:{message_id}")]
    ])


def support_ticket_keyboard(ticket_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="?? Javob berish", callback_data=f"ticket_reply:{ticket_id}")],
        [InlineKeyboardButton(text="? Yopish", callback_data=f"ticket_close:{ticket_id}")],
    ])
def admin_users_keyboard(users, page: int = 0, per_page: int = 10):
    start = page * per_page
    end = start + per_page
    chunk = users[start:end]

    buttons = []
    for u in chunk:
        blocked = "?? " if u["is_blocked"] else ""
        username = f"@{u['username']}" if u["username"] else f"ID {u['id']}"
        full_name = (u["full_name"] or "").strip()
        label = full_name if full_name else username

        if len(label) > 40:
            label = label[:37] + "..."

        buttons.append([
            InlineKeyboardButton(
                text=f"{blocked}{label}",
                callback_data=f"adm_user:{u['id']}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="??", callback_data=f"adm_users_page:{page-1}"))
    if end < len(users):
        nav.append(InlineKeyboardButton(text="??", callback_data=f"adm_users_page:{page+1}"))

    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="?? Yangilash", callback_data=f"adm_users_page:{page}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_user_detail_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="?? Xabar yuborish", callback_data=f"adm_user_msg:{user_id}")],
        [InlineKeyboardButton(text="?? Orqaga", callback_data="adm_users_page:0")],
    ])


def confirmed_customers_keyboard(customers, page: int = 0, per_page: int = 10):
    start = page * per_page
    end = start + per_page
    chunk = customers[start:end]

    buttons = []
    for c in chunk:
        full_name = (c["full_name"] or "").strip()
        username = f"@{c['username']}" if c["username"] else f"ID {c['id']}"
        label = full_name if full_name and full_name != "." else username

        count = c["confirmed_orders_count"] or 0
        total = c["total_spent"] or 0
        btn_text = f"{label} ? {count} ta | {total:,} so'm"

        if len(btn_text) > 62:
            btn_text = btn_text[:59] + "..."

        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"adm_confirmed_customer:{c['id']}:{page}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="??", callback_data=f"adm_confirmed_customers_page:{page-1}"))
    if end < len(customers):
        nav.append(InlineKeyboardButton(text="??", callback_data=f"adm_confirmed_customers_page:{page+1}"))

    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="?? Yangilash", callback_data=f"adm_confirmed_customers_page:{page}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirmed_customer_detail_keyboard(user_id: int, back_page: int = 0, last_order_id: int = None):
    buttons = [
        [InlineKeyboardButton(text="?? Xabar yuborish", callback_data=f"adm_user_msg:{user_id}")]
    ]

    if last_order_id:
        buttons.append([
            InlineKeyboardButton(text="? Qayta baho so'rash", callback_data=f"adm_reask_review:{user_id}:{last_order_id}")
        ])

    buttons.append([
        InlineKeyboardButton(text="?? Orqaga", callback_data=f"adm_confirmed_customers_page:{back_page}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

