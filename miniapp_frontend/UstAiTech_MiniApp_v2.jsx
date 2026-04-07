import { useState, useEffect, useRef } from “react”;

// ─── BRAND COLORS ────────────────────────────────────────────────────────────
// UstAiTech: dark navy #0d1117, cyan #00d4d8, white script logo
const B = {
bg: “#0a0e17”,
card: “rgba(13,18,30,0.95)”,
border: “rgba(0,212,216,0.12)”,
cyan: “#00d4d8”,
cyanDim: “rgba(0,212,216,0.15)”,
cyanGlow: “rgba(0,212,216,0.3)”,
white: “#f0f4f8”,
muted: “rgba(240,244,248,0.45)”,
faint: “rgba(240,244,248,0.08)”,
danger: “#ff4757”,
success: “#00e676”,
warn: “#ffa502”,
};

// ─── REAL PRODUCTS FROM BOT ──────────────────────────────────────────────────
const PRODUCTS = [
{
id: 1, name: “ChatGPT Plus”, subtitle: “Oylik shaxsiy premium”,
desc: “GPT-4o, DALL·E 3, Advanced Data Analysis. Shaxsiy foydalanish. Kafolat bilan.”,
price: 48000, oldPrice: 79900, stock: 14, cat: “chatgpt”,
badge: “🔥 TOP”, badgeColor: “#ff6b35”,
icon: “✦”, grad: [”#10b981”, “#06b6d4”],
perks: [“⚡ 1 soatda”, “✅ 30 kun”, “🎁 Kupon”],
},
{
id: 2, name: “ChatGPT Plus Yillik”, subtitle: “12 oylik eng tejamkor”,
desc: “Yillik obuna — 12 oy uzluksiz premium. GPT-4o, DALL·E 3, Codex. VIP xizmat.”,
price: 429000, oldPrice: 576000, stock: 5, cat: “chatgpt”,
badge: “💎 VIP”, badgeColor: “#8b5cf6”,
icon: “◈”, grad: [”#8b5cf6”, “#ec4899”],
perks: [“📅 12 oy”, “💰 25% tejash”, “👑 VIP”],
},
{
id: 3, name: “ChatGPT Business”, subtitle: “Korporativ 1 slot”,
desc: “ChatGPT Team plan. Jamoa boshqaruvi, admin panel, kengaytirilgan API. Biznes uchun.”,
price: 49000, oldPrice: 79900, stock: 8, cat: “chatgpt”,
badge: “🏢 BIZ”, badgeColor: “#3b82f6”,
icon: “▣”, grad: [”#3b82f6”, “#06b6d4”],
perks: [“👥 Team”, “🔧 Admin”, “📊 Stats”],
},
{
id: 4, name: “ChatGPT Business Admin 8”, subtitle: “8 slotli admin paket”,
desc: “8 ta foydalanuvchi uchun admin boshqaruvi. Korporativ darajada xizmat.”,
price: 149000, oldPrice: 199000, stock: 3, cat: “chatgpt”,
badge: “⚡ HOT”, badgeColor: “#f59e0b”,
icon: “⊞”, grad: [”#f59e0b”, “#ef4444”],
perks: [“8 slot”, “🛡 Admin”, “🔒 Xavfsiz”],
},
{
id: 5, name: “SuperGrok”, subtitle: “xAI premium oylik”,
desc: “Grok-3 modeli. Real-time internet, X platformasi integratsiyasi. Kuchli AI.”,
price: 66000, oldPrice: 99900, stock: 9, cat: “grok”,
badge: “🚀 NEW”, badgeColor: “#00d4d8”,
icon: “⬡”, grad: [”#00d4d8”, “#6366f1”],
perks: [“🌐 Real-time”, “🧠 Grok-3”, “📡 X API”],
},
{
id: 6, name: “Super Grok 1 Yillik”, subtitle: “6 oy kafolat bilan”,
desc: “Yillik SuperGrok — 6 oy ishlamasa qaytaramiz. Eng ishonchli paket.”,
price: 370000, oldPrice: 499000, stock: 4, cat: “grok”,
badge: “🛡 KAFOLAT”, badgeColor: “#00e676”,
icon: “◉”, grad: [”#00e676”, “#00d4d8”],
perks: [“📅 1 yil”, “🛡 6 oy kafolat”, “⭐ Premium”],
},
{
id: 7, name: “Grok Heavy 1M”, subtitle: “1 million token paket”,
desc: “Grok Heavy modeli — 1 million token. Katta loyihalar, keng kontekst oynasi.”,
price: 77000, oldPrice: 110000, stock: 6, cat: “grok”,
badge: “💪 HEAVY”, badgeColor: “#a855f7”,
icon: “◐”, grad: [”#a855f7”, “#ec4899”],
perks: [“1M token”, “📝 Katta kontekst”, “🔥 Heavy”],
},
{
id: 8, name: “Gemini Pro Oylik”, subtitle: “Google AI premium”,
desc: “Gemini 1.5 Pro. Rasm, audio, video tahlil. Google Search integratsiyasi.”,
price: 45000, oldPrice: 69900, stock: 11, cat: “google”,
badge: “✨ STAR”, badgeColor: “#fbbf24”,
icon: “✧”, grad: [”#fbbf24”, “#f97316”],
perks: [“🖼 Multimodal”, “🔍 Google”, “🎵 Audio”],
},
{
id: 9, name: “Gemini Pro 1 Yillik”, subtitle: “To’liq kafolat bilan”,
desc: “Yillik Gemini Pro — to’liq kafolat. 2TB+ storage, Antigravity bonus.”,
price: 179000, oldPrice: 259000, stock: 5, cat: “google”,
badge: “🌟 BEST”, badgeColor: “#34d399”,
icon: “❋”, grad: [”#34d399”, “#06b6d4”],
perks: [“📅 1 yil”, “2TB storage”, “🛡 Kafolat”],
},
{
id: 10, name: “Veo3 Ultra + Antigravity”, subtitle: “25K credit video AI”,
desc: “Google Veo3 — video generatsiya. 25,000 Antigravity kredit. Kontent yaratish uchun.”,
price: 65000, oldPrice: 99900, stock: 7, cat: “google”,
badge: “🎬 VIDEO”, badgeColor: “#f43f5e”,
icon: “▶”, grad: [”#f43f5e”, “#f97316”],
perks: [“🎬 Video AI”, “25K kredit”, “🤖 Antigravity”],
},
{
id: 11, name: “Capcut Pro 35 kun”, subtitle: “Avtomatik uzaytiriladi”,
desc: “CapCut Pro premium — 35 kunlik. Video tahrirlash, AI effektlar, avtomatik uzaytirish.”,
price: 29000, oldPrice: 45000, stock: 20, cat: “creative”,
badge: “🎥 PRO”, badgeColor: “#ec4899”,
icon: “✂”, grad: [”#ec4899”, “#8b5cf6”],
perks: [“🎥 Pro tools”, “🔄 Avtomatik”, “✨ AI effects”],
},
];

const CATS = [
{ id: “all”, label: “Barchasi”, icon: “⊞” },
{ id: “chatgpt”, label: “ChatGPT”, icon: “✦” },
{ id: “grok”, label: “Grok”, icon: “⬡” },
{ id: “google”, label: “Google AI”, icon: “✧” },
{ id: “creative”, label: “Creative”, icon: “✂” },
];

const PAYMENT_METHODS = [
{ id: “click”, label: “Click”, icon: “💳”, color: “#00bcd4” },
{ id: “payme”, label: “Payme”, icon: “💜”, color: “#9c27b0” },
{ id: “uzum”, label: “Uzum Bank”, icon: “🟠”, color: “#ff6d00” },
{ id: “card”, label: “Karta raqami”, icon: “🏦”, color: “#607d8b” },
];

// ─── HELPERS ──────────────────────────────────────────────────────────────────
const fmt = (n) => Number(n).toLocaleString(“uz-UZ”) + “ so’m”;
const disc = (o, c) => Math.round(((o - c) / o) * 100);
const uid = () => Math.random().toString(36).slice(2, 9).toUpperCase();

// ─── TINY COMPONENTS ──────────────────────────────────────────────────────────

function Logo({ size = 22 }) {
return (
<div style={{ display: “flex”, alignItems: “center”, gap: 0 }}>
<span style={{
fontFamily: “‘Dancing Script’, cursive, serif”,
fontSize: size, fontWeight: 700, color: B.white,
letterSpacing: -0.5, lineHeight: 1,
}}>Ust</span>
<span style={{
fontFamily: “‘Dancing Script’, cursive, serif”,
fontSize: size, fontWeight: 700,
background: `linear-gradient(135deg, ${B.cyan}, #00fff7)`,
WebkitBackgroundClip: “text”, WebkitTextFillColor: “transparent”,
lineHeight: 1,
}}>Ai</span>
<span style={{
fontFamily: “‘Orbitron’, monospace, sans-serif”,
fontSize: size * 0.55, fontWeight: 700, color: B.white,
letterSpacing: 1, alignSelf: “flex-end”, paddingBottom: 2, marginLeft: 1,
}}>.TECH</span>
</div>
);
}

function Badge({ text, color }) {
return (
<span style={{
display: “inline-flex”, alignItems: “center”,
padding: “3px 9px”, borderRadius: 20,
fontSize: 10, fontWeight: 800, letterSpacing: 0.5,
background: color + “22”, color, border: `1px solid ${color}40`,
}}>{text}</span>
);
}

function Pill({ children, active, onClick }) {
return (
<button onClick={onClick} style={{
flexShrink: 0, padding: “7px 14px”, borderRadius: 20,
fontSize: 12, fontWeight: 600, cursor: “pointer”,
whiteSpace: “nowrap”,
background: active ? `linear-gradient(135deg, ${B.cyan}cc, #00a8ac)` : B.faint,
border: `1px solid ${active ? B.cyan + "60" : "rgba(255,255,255,0.07)"}`,
color: active ? “#0a0e17” : B.muted,
boxShadow: active ? `0 4px 14px ${B.cyanGlow}` : “none”,
transition: “all 0.2s ease”,
}}>{children}</button>
);
}

function Divider() {
return <div style={{ height: 1, background: “rgba(0,212,216,0.08)”, margin: “4px 0” }} />;
}

// ─── PRODUCT CARD ──────────────────────────────────────────────────────────────
function ProductCard({ p, onOpen, cartCount, onAddCart, delay = 0 }) {
const [hov, setHov] = useState(false);
const d = disc(p.oldPrice, p.price);
const low = p.stock <= 5;

return (
<div
onMouseEnter={() => setHov(true)}
onMouseLeave={() => setHov(false)}
style={{
background: B.card,
border: `1px solid ${hov ? B.cyan + "30" : B.border}`,
borderRadius: 18, overflow: “hidden”, cursor: “pointer”,
transform: hov ? “translateY(-2px) scale(1.005)” : “none”,
transition: “all 0.25s cubic-bezier(0.34,1.56,0.64,1)”,
boxShadow: hov ? `0 16px 48px rgba(0,0,0,0.5), 0 0 0 1px ${B.cyan}20` : “0 2px 12px rgba(0,0,0,0.4)”,
animation: `fadeUp 0.45s ease ${delay}s both`,
}}
>
{/* Colored strip */}
<div style={{
height: 3,
background: `linear-gradient(90deg, ${p.grad[0]}, ${p.grad[1]})`,
}} />

```
  <div style={{ padding: "16px 16px 14px" }}>
    {/* Top row */}
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: `linear-gradient(135deg, ${p.grad[0]}, ${p.grad[1]})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 18, flexShrink: 0,
          boxShadow: `0 4px 16px ${p.grad[0]}55`,
        }}>{p.icon}</div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 800, color: B.white, lineHeight: 1.2, letterSpacing: -0.2 }}>
            {p.name}
          </div>
          <div style={{ fontSize: 11, color: B.muted, marginTop: 2 }}>{p.subtitle}</div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
        <Badge text={p.badge} color={p.badgeColor} />
        <span style={{
          fontSize: 10, fontWeight: 700, color: B.success,
          background: "#00e67618", border: "1px solid #00e67630",
          borderRadius: 8, padding: "2px 7px",
        }}>-{d}%</span>
      </div>
    </div>

    {/* Perks */}
    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 12 }}>
      {p.perks.map((pk) => (
        <span key={pk} style={{
          fontSize: 10, color: B.muted,
          background: B.faint, border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 7, padding: "3px 8px",
        }}>{pk}</span>
      ))}
      {low && (
        <span style={{
          fontSize: 10, fontWeight: 700, color: B.warn,
          background: "#ffa50218", border: `1px solid ${B.warn}35`,
          borderRadius: 7, padding: "3px 8px",
        }}>⚠ {p.stock} ta qoldi</span>
      )}
    </div>

    {/* Price + actions */}
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div>
        <div style={{ fontSize: 18, fontWeight: 900, color: B.white, letterSpacing: -0.4, lineHeight: 1 }}>
          {fmt(p.price)}
        </div>
        <div style={{ fontSize: 11, color: "rgba(255,255,255,0.25)", textDecoration: "line-through", marginTop: 1 }}>
          {fmt(p.oldPrice)}
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={(e) => { e.stopPropagation(); onAddCart(p); }}
          style={{
            width: 36, height: 36, borderRadius: 10, border: "none",
            background: cartCount > 0 ? `linear-gradient(135deg, ${B.cyan}cc, #00a8ac)` : B.faint,
            color: cartCount > 0 ? "#0a0e17" : B.cyan,
            cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center",
            position: "relative", transition: "all 0.2s",
            boxShadow: cartCount > 0 ? `0 4px 12px ${B.cyanGlow}` : "none",
          }}
        >
          🛒
          {cartCount > 0 && (
            <span style={{
              position: "absolute", top: -5, right: -5,
              width: 16, height: 16, borderRadius: 8,
              background: B.danger, color: "#fff",
              fontSize: 9, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center",
            }}>{cartCount}</span>
          )}
        </button>
        <button
          onClick={() => onOpen(p)}
          style={{
            width: 36, height: 36, borderRadius: 10, border: `1px solid ${B.cyan}40`,
            background: B.cyanDim, color: B.cyan,
            cursor: "pointer", fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center",
            transition: "all 0.2s",
          }}
        >→</button>
      </div>
    </div>
  </div>
</div>
```

);
}

// ─── CART ITEM ────────────────────────────────────────────────────────────────
function CartItem({ item, onQty, onRemove }) {
return (
<div style={{
background: B.card, border: `1px solid ${B.border}`,
borderRadius: 14, padding: “12px 14px”,
display: “flex”, alignItems: “center”, gap: 12,
}}>
<div style={{
width: 36, height: 36, borderRadius: 10, flexShrink: 0,
background: `linear-gradient(135deg, ${item.grad[0]}, ${item.grad[1]})`,
display: “flex”, alignItems: “center”, justifyContent: “center”, fontSize: 16,
}}>{item.icon}</div>
<div style={{ flex: 1, minWidth: 0 }}>
<div style={{ fontSize: 13, fontWeight: 700, color: B.white, overflow: “hidden”, textOverflow: “ellipsis”, whiteSpace: “nowrap” }}>
{item.name}
</div>
<div style={{ fontSize: 12, color: B.cyan, fontWeight: 700, marginTop: 2 }}>
{fmt(item.price * item.qty)}
</div>
</div>
<div style={{ display: “flex”, alignItems: “center”, gap: 8 }}>
<button onClick={() => onQty(item.id, -1)} style={{
width: 26, height: 26, borderRadius: 7, border: `1px solid ${B.border}`,
background: B.faint, color: B.white, cursor: “pointer”, fontSize: 14,
display: “flex”, alignItems: “center”, justifyContent: “center”,
}}>−</button>
<span style={{ color: B.white, fontWeight: 800, fontSize: 14, minWidth: 16, textAlign: “center” }}>{item.qty}</span>
<button onClick={() => onQty(item.id, 1)} style={{
width: 26, height: 26, borderRadius: 7, border: `1px solid ${B.cyan}40`,
background: B.cyanDim, color: B.cyan, cursor: “pointer”, fontSize: 14,
display: “flex”, alignItems: “center”, justifyContent: “center”,
}}>+</button>
<button onClick={() => onRemove(item.id)} style={{
width: 26, height: 26, borderRadius: 7, border: “1px solid rgba(255,71,87,0.3)”,
background: “rgba(255,71,87,0.1)”, color: B.danger, cursor: “pointer”, fontSize: 12,
display: “flex”, alignItems: “center”, justifyContent: “center”,
}}>✕</button>
</div>
</div>
);
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function App() {
const [view, setView] = useState(“home”);
const [cat, setCat] = useState(“all”);
const [cart, setCart] = useState([]);
const [selected, setSelected] = useState(null);
const [payMethod, setPayMethod] = useState(“click”);
const [coupon, setCoupon] = useState(””);
const [couponApplied, setCouponApplied] = useState(null);
const [orderNote, setOrderNote] = useState(””);
const [orderDone, setOrderDone] = useState(null);
const [cartOpen, setCartOpen] = useState(false);
const [animKey, setAnimKey] = useState(0);
const tapRef = useRef(0);

const filtered = cat === “all” ? PRODUCTS : PRODUCTS.filter((p) => p.cat === cat);
const cartTotal = cart.reduce((s, i) => s + i.price * i.qty, 0);
const cartCount = cart.reduce((s, i) => s + i.qty, 0);
const discount10 = couponApplied ? Math.round(cartTotal * 0.1) : 0;
const finalTotal = cartTotal - discount10;

const VALID_COUPONS = [“USTAI10”, “TECH10”, “VIP10”];

const addCart = (p) => {
setCart((c) => {
const ex = c.find((x) => x.id === p.id);
if (ex) return c.map((x) => x.id === p.id ? { …x, qty: Math.min(x.qty + 1, p.stock) } : x);
return […c, { …p, qty: 1 }];
});
};

const updateQty = (id, delta) => {
setCart((c) => c.map((x) => x.id === id
? { …x, qty: Math.max(0, x.qty + delta) }
: x
).filter((x) => x.qty > 0));
};

const removeFromCart = (id) => setCart((c) => c.filter((x) => x.id !== id));

const handleCoupon = () => {
if (VALID_COUPONS.includes(coupon.trim().toUpperCase())) {
setCouponApplied(coupon.trim().toUpperCase());
} else {
alert(“❌ Kupon topilmadi yoki muddati tugagan.”);
}
};

const placeOrder = () => {
const id = “UST-” + uid();
setOrderDone({ id, items: […cart], total: finalTotal, method: payMethod });
setCart([]);
setCoupon(””); setCouponApplied(null); setOrderNote(””);
setView(“success”);
setCartOpen(false);
};

const changeCat = (id) => {
setAnimKey((k) => k + 1);
setCat(id);
};

const openDetail = (p) => { setSelected(p); setView(“detail”); };

const handleLogoTap = () => {
tapRef.current += 1;
if (tapRef.current >= 5) { alert(“👑 Admin mode — kelajakda qo’shiladi!”); tapRef.current = 0; }
};

const getCartCount = (id) => cart.find((x) => x.id === id)?.qty || 0;

return (
<>
<style>{`@import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Orbitron:wght@700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap'); *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; } html, body { background: ${B.bg}; font-family: 'Plus Jakarta Sans', sans-serif; overflow-x: hidden; } ::-webkit-scrollbar { width: 3px; } ::-webkit-scrollbar-thumb { background: ${B.cyan}40; border-radius: 2px; } @keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } } @keyframes slideUp { from { transform:translateY(100%); opacity:0; } to { transform:translateY(0); opacity:1; } } @keyframes pop { 0%{transform:scale(0.5);opacity:0} 70%{transform:scale(1.12)} 100%{transform:scale(1);opacity:1} } @keyframes glow { 0%,100%{box-shadow:0 0 20px ${B.cyanGlow}} 50%{box-shadow:0 0 40px ${B.cyan}60} } @keyframes shimmer { to{background-position:200% center} } select option { background:#0a0e17; color:#fff; } input::placeholder, textarea::placeholder { color: rgba(240,244,248,0.25); }`}</style>

```
  <div style={{ minHeight: "100vh", background: B.bg, display: "flex", justifyContent: "center" }}>
    <div style={{ width: "100%", maxWidth: 430, minHeight: "100vh", position: "relative", overflow: "hidden" }}>

      {/* BG ambient */}
      {[
        { top: -100, left: -80, size: 300, color: B.cyan },
        { top: 300, right: -100, size: 250, color: "#6366f1" },
        { bottom: 50, left: 0, size: 200, color: "#00d4d8" },
      ].map((o, i) => (
        <div key={i} style={{
          position: "fixed", borderRadius: "50%", pointerEvents: "none",
          width: o.size, height: o.size,
          top: o.top, bottom: o.bottom, left: o.left, right: o.right,
          background: `radial-gradient(circle, ${o.color}18, transparent 70%)`,
          filter: "blur(40px)",
        }} />
      ))}

      {/* ── HEADER ── */}
      <header style={{
        padding: "14px 16px 12px",
        borderBottom: `1px solid ${B.border}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        position: "sticky", top: 0, zIndex: 200,
        background: "rgba(10,14,23,0.92)", backdropFilter: "blur(24px)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {view !== "home" && (
            <button onClick={() => setView("home")} style={{
              width: 32, height: 32, borderRadius: 9, border: `1px solid ${B.border}`,
              background: B.faint, color: B.white, cursor: "pointer", fontSize: 15,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>←</button>
          )}
          <div onClick={handleLogoTap} style={{ cursor: "default" }}>
            <Logo size={20} />
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Cart button */}
          <button onClick={() => setCartOpen(true)} style={{
            position: "relative", width: 36, height: 36, borderRadius: 10,
            border: `1px solid ${cart.length > 0 ? B.cyan + "50" : B.border}`,
            background: cart.length > 0 ? B.cyanDim : B.faint,
            color: cart.length > 0 ? B.cyan : B.muted,
            cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: cart.length > 0 ? `0 0 16px ${B.cyanGlow}` : "none",
            transition: "all 0.25s",
          }}>
            🛒
            {cartCount > 0 && (
              <span style={{
                position: "absolute", top: -6, right: -6,
                minWidth: 18, height: 18, borderRadius: 9, padding: "0 4px",
                background: B.danger, color: "#fff",
                fontSize: 10, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center",
                border: `2px solid ${B.bg}`,
              }}>{cartCount}</span>
            )}
          </button>

          {/* Avatar */}
          <div style={{
            width: 32, height: 32, borderRadius: 9,
            background: `linear-gradient(135deg, ${B.cyan}, #006668)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 13, color: "#0a0e17", fontWeight: 900,
            border: `1px solid ${B.cyan}40`,
          }}>U</div>
        </div>
      </header>

      {/* ── PAGE CONTENT ── */}
      <div style={{ padding: "16px 14px 96px", position: "relative", zIndex: 1 }}>

        {/* HOME */}
        {view === "home" && (
          <>
            {/* Hero Banner */}
            <div style={{
              background: `linear-gradient(135deg, rgba(0,212,216,0.12), rgba(99,102,241,0.08))`,
              border: `1px solid ${B.cyan}25`,
              borderRadius: 20, padding: "20px 18px 18px", marginBottom: 18,
              position: "relative", overflow: "hidden",
              animation: "fadeUp 0.5s ease",
            }}>
              <div style={{
                position: "absolute", top: -30, right: -30, width: 120, height: 120,
                borderRadius: "50%",
                background: `radial-gradient(circle, ${B.cyan}25, transparent)`,
              }} />
              <div style={{
                fontSize: 10, letterSpacing: 2, textTransform: "uppercase",
                color: B.cyan, fontWeight: 800, marginBottom: 8,
              }}>✦ Premium Digital Store</div>
              <h1 style={{
                fontFamily: "'Dancing Script', cursive",
                fontSize: 30, fontWeight: 700, color: B.white,
                lineHeight: 1.15, letterSpacing: -0.5, marginBottom: 8,
              }}>
                AI abonementlar<br />
                <span style={{
                  background: `linear-gradient(90deg, ${B.cyan}, #00fff7, ${B.cyan})`,
                  backgroundSize: "200% auto",
                  WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                  animation: "shimmer 3s linear infinite",
                }}>tez va ishonchli</span>
              </h1>
              <p style={{ fontSize: 12, color: B.muted, lineHeight: 1.65, marginBottom: 16 }}>
                ChatGPT, Grok, Gemini va boshqa premium AI<br />
                xizmatlariga kafolat bilan arzon narxda kirish.
              </p>
              <div style={{ display: "flex", gap: 8 }}>
                {[["⚡","Tezkor"], ["🛡","Kafolat"], ["🎁","Bonus"]].map(([ic, tx]) => (
                  <div key={tx} style={{
                    flex: 1, textAlign: "center",
                    background: "rgba(255,255,255,0.04)", border: `1px solid ${B.border}`,
                    borderRadius: 11, padding: "9px 4px",
                  }}>
                    <div style={{ fontSize: 16, marginBottom: 2 }}>{ic}</div>
                    <div style={{ fontSize: 10, color: B.muted, fontWeight: 600 }}>{tx}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Category pills */}
            <div style={{
              display: "flex", gap: 7, overflowX: "auto", paddingBottom: 4, marginBottom: 16,
            }}>
              {CATS.map((c) => (
                <Pill key={c.id} active={cat === c.id} onClick={() => changeCat(c.id)}>
                  {c.icon} {c.label}
                </Pill>
              ))}
            </div>

            {/* Count */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 12, color: B.muted }}>
                {filtered.length} ta xizmat
              </span>
              <span style={{ fontSize: 11, color: B.cyan, fontWeight: 700 }}>
                🔥 Eng yaxshi narxlar
              </span>
            </div>

            {/* Cards */}
            <div key={animKey} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {filtered.map((p, i) => (
                <ProductCard
                  key={p.id} p={p}
                  onOpen={openDetail}
                  cartCount={getCartCount(p.id)}
                  onAddCart={addCart}
                  delay={i * 0.05}
                />
              ))}
            </div>

            {/* Trust bar */}
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
              gap: 8, marginTop: 18,
            }}>
              {[["1000+","Mijozlar"], ["24/7","Xizmat"], ["100%","Kafolat"]].map(([v, l]) => (
                <div key={l} style={{
                  textAlign: "center", background: B.faint,
                  border: `1px solid ${B.border}`, borderRadius: 13, padding: "14px 6px",
                }}>
                  <div style={{
                    fontFamily: "'Orbitron', monospace",
                    fontSize: 16, fontWeight: 700, color: B.cyan, marginBottom: 3,
                  }}>{v}</div>
                  <div style={{ fontSize: 10, color: B.muted }}>{l}</div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* DETAIL VIEW */}
        {view === "detail" && selected && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            {/* Hero */}
            <div style={{
              background: `linear-gradient(145deg, ${selected.grad[0]}20, ${selected.grad[1]}12)`,
              border: `1px solid rgba(255,255,255,0.08)`,
              borderRadius: 20, padding: "22px 18px", marginBottom: 14,
              position: "relative", overflow: "hidden",
            }}>
              <div style={{
                position: "absolute", top: -40, right: -40, width: 160, height: 160,
                borderRadius: "50%", background: `radial-gradient(circle, ${selected.grad[0]}30, transparent)`,
              }} />
              <div style={{
                width: 56, height: 56, borderRadius: 16,
                background: `linear-gradient(135deg, ${selected.grad[0]}, ${selected.grad[1]})`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 26, marginBottom: 16,
                boxShadow: `0 6px 24px ${selected.grad[0]}55`,
              }}>{selected.icon}</div>
              <div style={{ display: "flex", gap: 7, marginBottom: 12, flexWrap: "wrap" }}>
                <Badge text={selected.badge} color={selected.badgeColor} />
                <Badge text={`-${disc(selected.oldPrice, selected.price)}%`} color={B.success} />
                <Badge text={`📦 ${selected.stock} ta`} color={B.muted} />
              </div>
              <h2 style={{ fontSize: 22, fontWeight: 900, color: B.white, letterSpacing: -0.5, marginBottom: 8 }}>
                {selected.name}
              </h2>
              <p style={{ fontSize: 13, color: B.muted, lineHeight: 1.65 }}>{selected.desc}</p>
            </div>

            {/* Perks */}
            <div style={{
              background: B.card, border: `1px solid ${B.border}`,
              borderRadius: 16, padding: 16, marginBottom: 12,
            }}>
              <div style={{ fontSize: 11, color: B.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>
                Nimalar kiradi
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {selected.perks.map((pk) => (
                  <div key={pk} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{
                      width: 5, height: 5, borderRadius: 3, flexShrink: 0,
                      background: `linear-gradient(135deg, ${selected.grad[0]}, ${selected.grad[1]})`,
                    }} />
                    <span style={{ fontSize: 13, color: "rgba(255,255,255,0.75)" }}>{pk}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Price + Add to cart */}
            <div style={{
              background: B.card, border: `1px solid ${B.border}`,
              borderRadius: 16, padding: 16,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 11, color: B.muted, marginBottom: 3, textTransform: "uppercase", letterSpacing: 1 }}>Narx</div>
                  <div style={{ fontSize: 28, fontWeight: 900, color: B.white, letterSpacing: -0.8 }}>{fmt(selected.price)}</div>
                  <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", textDecoration: "line-through" }}>{fmt(selected.oldPrice)}</div>
                </div>
                <div style={{
                  background: "#00e67618", border: `1px solid ${B.success}35`,
                  borderRadius: 12, padding: "10px 14px", textAlign: "center",
                }}>
                  <div style={{ fontSize: 16, fontWeight: 900, color: B.success }}>
                    {fmt(selected.oldPrice - selected.price)}
                  </div>
                  <div style={{ fontSize: 10, color: B.success + "99" }}>tejash</div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={() => { addCart(selected); setCartOpen(true); }} style={{
                  flex: 1, padding: "13px 0", borderRadius: 13, fontSize: 14, fontWeight: 800,
                  background: `linear-gradient(135deg, ${B.cyan}cc, #008c90)`,
                  border: "none", color: "#0a0e17", cursor: "pointer",
                  boxShadow: `0 6px 20px ${B.cyanGlow}`,
                }}>🛒 Savatga qo'sh</button>
                <button onClick={() => { addCart(selected); setView("home"); }} style={{
                  flex: 1, padding: "13px 0", borderRadius: 13, fontSize: 14, fontWeight: 700,
                  background: B.faint, border: `1px solid ${B.border}`,
                  color: B.white, cursor: "pointer",
                }}>💳 Hozir sotib ol</button>
              </div>
            </div>
          </div>
        )}

        {/* SUCCESS VIEW */}
        {view === "success" && orderDone && (
          <div style={{ textAlign: "center", padding: "48px 16px", animation: "fadeUp 0.5s ease" }}>
            <div style={{
              width: 80, height: 80, borderRadius: "50%", margin: "0 auto 24px",
              background: `linear-gradient(135deg, ${B.success}, #00b84d)`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 36, animation: "pop 0.6s cubic-bezier(0.34,1.56,0.64,1)",
              boxShadow: `0 0 40px rgba(0,230,118,0.4)`,
            }}>✓</div>
            <h2 style={{
              fontFamily: "'Dancing Script', cursive",
              fontSize: 28, color: B.white, marginBottom: 8,
            }}>Buyurtma qabul qilindi!</h2>
            <div style={{
              display: "inline-block", background: B.cyanDim, border: `1px solid ${B.cyan}40`,
              borderRadius: 10, padding: "4px 14px", fontSize: 12, color: B.cyan,
              fontWeight: 700, marginBottom: 16,
            }}>#{orderDone.id}</div>
            <p style={{ fontSize: 13, color: B.muted, lineHeight: 1.65, marginBottom: 8 }}>
              {orderDone.items.length} ta xizmat • {fmt(orderDone.total)}
            </p>
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.3)", marginBottom: 32 }}>
              To'lov usuli: <b style={{ color: B.muted }}>{PAYMENT_METHODS.find(m => m.id === orderDone.method)?.label}</b>
              <br />Admin tez orada siz bilan bog'lanadi.
            </p>
            <button onClick={() => setView("home")} style={{
              padding: "13px 40px", borderRadius: 14, fontSize: 14, fontWeight: 800,
              background: `linear-gradient(135deg, ${B.cyan}cc, #008c90)`,
              border: "none", color: "#0a0e17", cursor: "pointer",
              boxShadow: `0 6px 20px ${B.cyanGlow}`,
            }}>← Asosiy sahifa</button>
          </div>
        )}
      </div>

      {/* ── CART DRAWER ── */}
      {cartOpen && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 500,
          background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)",
        }} onClick={() => setCartOpen(false)}>
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: "absolute", bottom: 0, left: "50%",
              transform: "translateX(-50%)",
              width: "100%", maxWidth: 430,
              background: "rgba(10,14,23,0.98)",
              border: `1px solid ${B.border}`,
              borderRadius: "22px 22px 0 0",
              padding: "20px 14px 32px",
              maxHeight: "88vh", overflowY: "auto",
              animation: "slideUp 0.35s cubic-bezier(0.34,1.56,0.64,1)",
            }}
          >
            {/* Handle */}
            <div style={{
              width: 36, height: 4, borderRadius: 2,
              background: "rgba(255,255,255,0.15)", margin: "0 auto 18px",
            }} />

            {/* Title */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 900, color: B.white }}>
                🛒 Savat <span style={{ color: B.cyan, fontSize: 14 }}>{cartCount > 0 ? `(${cartCount})` : ""}</span>
              </h2>
              <button onClick={() => setCartOpen(false)} style={{
                background: B.faint, border: `1px solid ${B.border}`,
                borderRadius: 9, width: 30, height: 30,
                color: B.muted, cursor: "pointer", fontSize: 14,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>✕</button>
            </div>

            {cart.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 0", color: B.muted }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>🛒</div>
                <div style={{ fontSize: 14 }}>Savat bo'sh</div>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.2)", marginTop: 4 }}>
                  Mahsulot qo'shish uchun "🛒" tugmasini bosing
                </div>
              </div>
            ) : (
              <>
                {/* Cart items */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
                  {cart.map((item) => (
                    <CartItem key={item.id} item={item} onQty={updateQty} onRemove={removeFromCart} />
                  ))}
                </div>

                <Divider />

                {/* Coupon */}
                <div style={{ padding: "14px 0" }}>
                  <div style={{ fontSize: 12, color: B.muted, marginBottom: 8, fontWeight: 600 }}>
                    🎁 Kupon kodi
                  </div>
                  {couponApplied ? (
                    <div style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      background: "#00e67612", border: `1px solid ${B.success}35`,
                      borderRadius: 11, padding: "10px 14px",
                    }}>
                      <span style={{ color: B.success, fontWeight: 700, fontSize: 13 }}>
                        ✅ {couponApplied} — 10% chegirma!
                      </span>
                      <button onClick={() => { setCouponApplied(null); setCoupon(""); }} style={{
                        background: "none", border: "none", color: B.danger, cursor: "pointer", fontSize: 13,
                      }}>✕</button>
                    </div>
                  ) : (
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        value={coupon}
                        onChange={(e) => setCoupon(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleCoupon()}
                        placeholder="USTAI10"
                        style={{
                          flex: 1, padding: "10px 13px", borderRadius: 11,
                          background: B.faint, border: `1px solid ${B.border}`,
                          color: B.white, fontSize: 13, outline: "none",
                          fontFamily: "inherit",
                        }}
                      />
                      <button onClick={handleCoupon} style={{
                        padding: "0 16px", borderRadius: 11,
                        background: B.cyanDim, border: `1px solid ${B.cyan}40`,
                        color: B.cyan, cursor: "pointer", fontSize: 13, fontWeight: 700,
                      }}>Qo'lla</button>
                    </div>
                  )}
                </div>

                <Divider />

                {/* Payment method */}
                <div style={{ padding: "14px 0" }}>
                  <div style={{ fontSize: 12, color: B.muted, marginBottom: 10, fontWeight: 600 }}>
                    💳 To'lov usuli
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    {PAYMENT_METHODS.map((m) => (
                      <button key={m.id} onClick={() => setPayMethod(m.id)} style={{
                        padding: "10px 10px", borderRadius: 11, cursor: "pointer",
                        background: payMethod === m.id ? m.color + "20" : B.faint,
                        border: `1px solid ${payMethod === m.id ? m.color + "60" : B.border}`,
                        color: payMethod === m.id ? m.color : B.muted,
                        fontSize: 12, fontWeight: 700, textAlign: "center",
                        transition: "all 0.2s",
                      }}>
                        <div style={{ fontSize: 18, marginBottom: 3 }}>{m.icon}</div>
                        {m.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Note */}
                <div style={{ paddingBottom: 14 }}>
                  <div style={{ fontSize: 12, color: B.muted, marginBottom: 8, fontWeight: 600 }}>
                    📝 Izoh (ixtiyoriy)
                  </div>
                  <textarea
                    value={orderNote}
                    onChange={(e) => setOrderNote(e.target.value)}
                    placeholder="Qo'shimcha talablar yoki savollar..."
                    rows={2}
                    style={{
                      width: "100%", padding: "10px 13px", borderRadius: 11,
                      background: B.faint, border: `1px solid ${B.border}`,
                      color: B.white, fontSize: 13, outline: "none", resize: "none",
                      fontFamily: "inherit",
                    }}
                  />
                </div>

                <Divider />

                {/* Summary */}
                <div style={{ padding: "12px 0 16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, color: B.muted }}>Jami</span>
                    <span style={{ fontSize: 13, color: B.white, fontWeight: 700 }}>{fmt(cartTotal)}</span>
                  </div>
                  {couponApplied && (
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontSize: 13, color: B.success }}>Chegirma ({couponApplied})</span>
                      <span style={{ fontSize: 13, color: B.success, fontWeight: 700 }}>-{fmt(discount10)}</span>
                    </div>
                  )}
                  <div style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "10px 0", borderTop: `1px solid ${B.border}`,
                  }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: B.white }}>To'lov summasi</span>
                    <span style={{ fontSize: 18, fontWeight: 900, color: B.cyan }}>{fmt(finalTotal)}</span>
                  </div>
                </div>

                {/* Place order */}
                <button onClick={placeOrder} style={{
                  width: "100%", padding: "15px 0", borderRadius: 14,
                  fontSize: 15, fontWeight: 900,
                  background: `linear-gradient(135deg, ${B.cyan}cc, #008c90)`,
                  border: "none", color: "#0a0e17", cursor: "pointer",
                  boxShadow: `0 6px 24px ${B.cyanGlow}`,
                  letterSpacing: 0.3,
                  animation: "glow 2s infinite",
                }}>
                  ✓ Buyurtma berish — {fmt(finalTotal)}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── BOTTOM NAV ── */}
      <div style={{
        position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)",
        width: "100%", maxWidth: 430, zIndex: 100,
        background: "rgba(10,14,23,0.96)", backdropFilter: "blur(20px)",
        borderTop: `1px solid ${B.border}`,
        display: "flex", padding: "10px 0 16px",
      }}>
        {[
          { id: "home", icon: "⊞", label: "Bosh sahifa" },
          { id: "cart", icon: "🛒", label: "Savat", count: cartCount },
          { id: "orders", icon: "📦", label: "Buyurtmalar" },
        ].map((tab) => (
          <button key={tab.id} onClick={() => tab.id === "cart" ? setCartOpen(true) : setView(tab.id === "home" ? "home" : "home")} style={{
            flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
            background: "none", border: "none", cursor: "pointer",
            color: (view === tab.id || (tab.id === "cart" && cartOpen)) ? B.cyan : B.muted,
            position: "relative",
          }}>
            <span style={{ fontSize: 20 }}>{tab.icon}</span>
            <span style={{ fontSize: 10, fontWeight: 600 }}>{tab.label}</span>
            {tab.count > 0 && (
              <span style={{
                position: "absolute", top: 0, right: "calc(50% - 18px)",
                minWidth: 16, height: 16, borderRadius: 8, padding: "0 3px",
                background: B.danger, color: "#fff",
                fontSize: 9, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center",
              }}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  </div>
</>
```

);
}