"""
AI Agent Layer for UstAiTech Bot
─────────────────────────────────
Xavfsiz AI katalog va maslahat yordamchisi.
Read-only: hech qachon order/payment/stock o'zgartirmaydi.
Falls back gracefully if AI is disabled or errors occur.
"""

import logging
import asyncio
from config import AI_ENABLED, AI_API_KEY, AI_MODEL

logger = logging.getLogger("ai_agent")

_client = None

SYSTEM_INSTRUCTION = """SEN UstAiTech botining xavfsiz AI katalog va maslahat yordamchisisan.

SENING ROLING:
- mijozga xizmatlar haqida tushuntirish berish
- narxlarni ko'rsatish (faqat catalog ma'lumotidan)
- aksiya va kuponlarni tushuntirish
- xizmatlarni bir-biri bilan solishtirish
- xizmatdan nima maqsadda foydalanish mumkinligini aytish
- ulash / qo'shish / faollashtirish / foydalanish bo'yicha qo'llanma berish
- foydalanuvchiga mos xizmatlarni tavsiya qilish
- savdoga yordam berish, lekin xavfli operatsiyalarga aralashmaslik

SENING QAT'IY CHEKLOVING:
SEN HECH QACHON:
- buyurtma holatini tekshirmaysan
- paymentni tasdiqlamaysan
- order ID bo'yicha ishlamaysan
- to'lov yetib kelgan-kelmaganini aytmaysan
- mahsulotni yuborishni va'da qilmaysan
- delivery trigger qilmaysan
- stock, order, payment, refund, balance, admin actionlarni o'zgartirmaysan
- boshqa foydalanuvchi ma'lumotini ko'rsatmaysan
- maxfiy ma'lumot, token, login, session, ichki admin ma'lumotlarini bermaysan

AGAR FOYDALANUVCHI order/payment/refund/delivery so'rasa:
"Bu masala buyurtma yoki to'lov bo'yicha hisoblanadi. Bu bo'lim bilan operator yoki admin shug'ullanadi. Men sizga xizmat tanlash, narxlar, aksiya va foydalanish bo'yicha yordam bera olaman."

SEN JAVOB BERADIGAN MAVZULAR:
1. Narxlar (faqat catalog ma'lumotidan)
2. Aksiya va chegirmalar
3. Kupon ishlatish qoidalari
4. Xizmatlarni taqqoslash
5. Qaysi xizmat qaysi maqsadga mosligi
6. ChatGPT / Gemini / Claude / Canva / Midjourney / Grok / CapCut va boshqa xizmatlar haqida tushuntirish
7. Kimga qaysi tarif mosligi
8. Xizmatni ulash, qo'shish, ishlatish bo'yicha yo'riqnoma
9. Umumiy savollar

JAVOB FORMATI:
- Asosiy til: o'zbek. Agar foydalanuvchi ruscha yozsa, ruscha javob ber.
- Javoblar aniq, professional va tushunarli bo'lsin.
- Odatda 2-4 jumla yetarli, keraksiz uzun yozma.
- Solishtirish bo'lsa, punktlar bilan aniq farqlarni ber.
- Bilmasang: "Hozir menda bu bo'yicha aniq ma'lumot yo'q" deb ayt.
- Narx/xizmat o'ylab topma — faqat berilgan catalog ma'lumotiga tayan.
- Hech qachon gapni yarida qoldirma, har doim to'liq jumlalar yoz.
- Agar savolga javob bera olmasang — FAQAT "NEED_HUMAN" yoz, boshqa hech narsa qo'shma.

BOT HAQIDA:
- UstAiTech — premium AI obunalar va raqamli xizmatlar do'koni
- To'lov: bank kartasi yoki Telegram Stars
- Buyurtma: Xizmat tanlash → To'lov → Admin tekshiruvi → Yetkazish (1-24 soat, odatda 1-3 soat)
- Bonus tizimi: har bir xaridda cashback
- Referral: do'stlarni taklif qilsangiz bonus
- Savat tizimi: bir nechta xizmatni birga xarid qilish mumkin
- Admin ish vaqti: 9:00-23:00"""


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not AI_ENABLED or not AI_API_KEY:
        return None
    try:
        from google import genai
        _client = genai.Client(api_key=AI_API_KEY)
        logger.info(f"AI Agent initialized: {AI_MODEL}")
        return _client
    except Exception as e:
        logger.error(f"AI init failed: {e}")
        return None


async def _get_catalog_context() -> str:
    """Load real catalog from DB for AI context."""
    try:
        import database as db
        services = await db.get_services(only_active=True)
        if not services:
            return ""
        lines = ["MAVJUD XIZMATLAR KATALOGI:"]
        for s in services[:30]:
            s = dict(s) if not isinstance(s, dict) else s
            name = s.get("name", "?")
            price = s.get("price", 0)
            desc = (s.get("description_uz") or "")[:100]
            stock = s.get("stock", "∞")
            lines.append(f"- {name}: {price:,} so'm | {desc} | Mavjud: {stock}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Catalog load failed: {e}")
        return ""


async def _ask(prompt: str, system: str = None, with_catalog: bool = False) -> str | None:
    """Core LLM call with safety wrapper."""
    client = _get_client()
    if not client:
        return None
    try:
        from google.genai import types
        sys_instruction = system or SYSTEM_INSTRUCTION

        # Append real catalog if requested
        if with_catalog:
            catalog = await _get_catalog_context()
            if catalog:
                sys_instruction += f"\n\n{catalog}"

        config_kwargs = {
            "system_instruction": sys_instruction,
            "max_output_tokens": 1024,
            "temperature": 0.3,
        }
        # Only add thinking_config for 2.5+ models
        if "2.5" in AI_MODEL:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        config = types.GenerateContentConfig(**config_kwargs)

        for attempt in range(2):
            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=AI_MODEL,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    text = response.text.strip()
                    text = text.replace("**", "").replace("*", "")
                    logger.info(f"AI response ({len(text)} chars): {text[:80]}...")
                    return text
                else:
                    logger.warning(f"AI empty response for: {prompt[:50]}")
                    return None
            except Exception as e:
                if "429" in str(e) and attempt == 0:
                    logger.warning(f"AI rate limited, waiting 5s...")
                    await asyncio.sleep(5)
                    continue
                raise
    except Exception as e:
        logger.warning(f"AI call failed: {e}")
    return None


# ──── 1. SMART PRODUCT RECOMMENDATION ────

async def recommend_products(user_history: list[dict], catalog: list[dict]) -> str | None:
    if not AI_ENABLED:
        return None
    history_text = "\n".join(
        f"- {h.get('service_name', '?')} ({h.get('final_price', 0):,} so'm)"
        for h in user_history[:10]
    ) or "Hali xarid qilmagan"

    prompt = f"Foydalanuvchi xarid tarixi:\n{history_text}\n\nShu foydalanuvchiga katalogdan 2-3 ta eng mos xizmatni tavsiya qil."
    return await _ask(prompt, with_catalog=True)


# ──── 2. FAQ AUTO-ANSWER (WITH CATALOG) ────

async def answer_faq(question: str) -> str | None:
    """Try to answer FAQ with real catalog context. Returns None if can't."""
    if not AI_ENABLED:
        return None
    q = question.strip()
    if len(q) < 3 or q.isdigit():
        return None
    result = await _ask(f"Mijoz savoli: {q}", with_catalog=True)
    if result and "NEED_HUMAN" in result:
        return None
    return result


# ──── 3. SUPPORT TRIAGE ────

TRIAGE_SYSTEM = """Sen support ticket triage tizimisan. Murojaatlarni tahlil qilasan.
Javobni FAQAT quyidagi JSON formatda ber, boshqa hech narsa yozma:
{"urgency": "high/medium/low", "category": "payment/technical/question/complaint/other", "summary": "1 jumla qisqa xulosa"}

Qoidalar:
- high: to'lov muammosi, xizmat ishlamayapti, shoshilinch
- medium: savol, tushunmovchilik
- low: umumiy savol, takroriy"""


async def triage_support(message: str, user_info: str = "") -> dict | None:
    if not AI_ENABLED:
        return None
    prompt = f"Murojaat: {message}\nFoydalanuvchi: {user_info}"
    result = await _ask(prompt, system=TRIAGE_SYSTEM)
    if not result:
        return None
    try:
        import json
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except Exception:
        pass
    return None


# ──── 4. ORDER STATUS EXPLANATION ────

async def explain_order_status(order: dict, lang: str = "uz") -> str | None:
    if not AI_ENABLED:
        return None
    lang_instruction = "O'zbek tilida yoz." if lang == "uz" else "Ruscha yoz."
    prompt = f"""Buyurtma holatini mijozga tushunarli tilda izohla.
Buyurtma: #{order.get('id', '?')} — {order.get('service_name', '?')}
Holat: {order.get('status', '?')}
Yaratilgan: {str(order.get('created_at', '?'))[:16]}
Yetkazish: {order.get('fulfillment_status', 'pending')}
{lang_instruction}"""
    return await _ask(prompt)


# ──── 5. ADMIN DRAFT REPLY ────

ADMIN_DRAFT_SYSTEM = """Sen admin yordamchisisam. Mijozning murojaatiga professional javob draft qil.
Qoidalar:
- O'zbek tilida yoz
- Professional va do'stona ton
- Muammoni hal qilish yo'lini taklif qil
- 2-4 jumla, to'liq gaplar
- Admin buni tahrirlashi mumkin"""


async def draft_admin_reply(message: str, user_name: str = "Mijoz") -> str | None:
    if not AI_ENABLED:
        return None
    prompt = f"Mijoz ismi: {user_name}\nMijoz xabari: {message}"
    return await _ask(prompt, system=ADMIN_DRAFT_SYSTEM)


# ──── 6. PERSONALIZED REMARKETING ────

REMARKETING_SYSTEM = """Mijozga sotib olinmagan savatdagi mahsulot uchun shaxsiy xabar yoz.
Qoidalar:
- Juda qisqa (2-3 jumla)
- Do'stona va motivatsion ton
- Emojidan mos foydalanishing mumkin
- Hech qachon "oxirgi imkoniyat" yoki bosim qo'yma
- Mahsulotning foydasini ta'kidla
- To'liq, tugallangan jumlalar bilan yoz"""


async def personalize_remarketing(
    name: str, product: str, price: int, lang: str = "uz"
) -> str | None:
    if not AI_ENABLED:
        return None
    lang_instruction = "O'zbek tilida yoz" if lang == "uz" else "Ruscha yoz"
    prompt = f"Mahsulot: {product}\nNarxi: {price:,} so'm\n{lang_instruction}"
    return await _ask(prompt, system=REMARKETING_SYSTEM)
