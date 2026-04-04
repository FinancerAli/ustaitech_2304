import { useEffect, useMemo, useState } from 'react'
import './App.css'
import {
  fetchCatalogServices,
  fetchProfileOrders,
  fetchProfileSummary,
} from './lib/api'

const categories = [
  {
    id: 'chatgpt',
    name: 'ChatGPT',
    subtitle: 'Personal AI subscriptions',
    description: 'Premium personal access including Plus and yearly plans.',
    icon: '◌',
  },
  {
    id: 'business',
    name: 'ChatGPT Business',
    subtitle: 'Team and admin plans',
    description: 'Business subscriptions, shared access, and admin slot offers.',
    icon: '▣',
  },
  {
    id: 'other-ai',
    name: 'Other AI',
    subtitle: 'Gemini, Grok, and more',
    description: 'Alternative premium AI services and advanced tool access.',
    icon: '✦',
  },
]

const featuredServices = [
  {
    name: 'ChatGPT Plus',
    subtitle: 'Premium personal AI access',
    price: 'from $20',
    stock: '12 in stock',
    badge: 'Popular',
  },
  {
    name: 'ChatGPT Business',
    subtitle: 'Team productivity and shared access',
    price: 'from $25',
    stock: '7 in stock',
    badge: 'Business',
  },
  {
    name: 'Gemini Pro',
    subtitle: 'Advanced AI subscription access',
    price: 'from $19',
    stock: '9 in stock',
    badge: 'Featured',
  },
]


function buildFeaturedCardFromApi(item) {
  const rawDescription =
    String(item?.description || item?.description_ru || 'Premium AI subscription access')
      .replace(/\s+/g, ' ')
      .trim()

  const shortDescription =
    rawDescription.length > 88 ? `${rawDescription.slice(0, 88)}…` : rawDescription

  return {
    name: item?.name || 'Service',
    subtitle: shortDescription || 'Premium AI subscription access',
    price: item?.price != null ? `${item.price} so'm` : 'Price on request',
    stock: item?.stock != null ? `${item.stock} in stock` : 'Stock unavailable',
    badge:
      item?.promo_title ||
      (item?.promo_active
        ? 'Promo'
        : item?.review_count
          ? `${item.avg_rating}★`
          : 'Live'),
  }
}

const servicesByCategory = {
  chatgpt: [
    {
      name: 'ChatGPT Plus',
      subtitle: 'Priority access to premium ChatGPT features',
      price: 'from $20',
      stock: '12 in stock',
      badge: 'Popular',
      perks: ['Instant access', 'Coupon available', 'Top rated'],
    },
    {
      name: 'ChatGPT Plus Yearly',
      subtitle: 'Long-term premium access in one package',
      price: 'from $199',
      stock: '5 in stock',
      badge: 'Yearly',
      perks: ['Best value', 'Low stock', 'Verified fulfillment'],
    },
  ],
  business: [
    {
      name: 'ChatGPT Business',
      subtitle: 'Business-grade access for productivity workflows',
      price: 'from $25',
      stock: '7 in stock',
      badge: 'Business',
      perks: ['Team ready', 'Admin managed', 'Trusted delivery'],
    },
    {
      name: 'ChatGPT Business Admin 8 Slots',
      subtitle: 'Admin package for up to 8 managed slots',
      price: 'from $89',
      stock: '3 in stock',
      badge: 'Limited',
      perks: ['8 slots', 'Priority support', 'Manual approval'],
    },
  ],
  'other-ai': [
    {
      name: 'Gemini Pro',
      subtitle: 'Advanced AI subscription access',
      price: 'from $19',
      stock: '9 in stock',
      badge: 'Featured',
      perks: ['Premium access', 'Stable stock', 'Fast setup'],
    },
    {
      name: 'SuperGrok',
      subtitle: 'High-value alternative AI tool access',
      price: 'from $22',
      stock: '4 in stock',
      badge: 'Hot',
      perks: ['Trending', 'Limited stock', 'Trusted flow'],
    },
  ],
}


const couponOptionsByCategory = {
  chatgpt: [
    {
      code: 'USTAI10',
      title: 'Recommended personal coupon',
      discount: 10,
      note: 'Best match for ChatGPT personal subscriptions',
    },
    {
      code: 'YEARLY15',
      title: 'Higher savings for long-term access',
      discount: 15,
      note: 'Useful when choosing bigger value plans',
    },
  ],
  business: [
    {
      code: 'BIZ5',
      title: 'Business discount',
      discount: 5,
      note: 'Designed for business and team subscriptions',
    },
    {
      code: 'ADMIN8',
      title: 'Admin package savings',
      discount: 8,
      note: 'Good fit for admin-managed multi-slot offers',
    },
  ],
  'other-ai': [
    {
      code: 'ALT7',
      title: 'Alternative AI promo',
      discount: 7,
      note: 'Applies to selected premium non-ChatGPT tools',
    },
    {
      code: 'FAST5',
      title: 'Quick access savings',
      discount: 5,
      note: 'Simple discount before checkout',
    },
  ],
}


const reviewTemplateOptions = [
  {
    id: 'fast',
    label: 'Fast setup',
    text: 'Fast setup and smooth fulfillment. Highly recommended.',
  },
  {
    id: 'trusted',
    label: 'Trusted seller',
    text: 'Trusted experience and clear communication throughout the process.',
  },
  {
    id: 'premium',
    label: 'Premium access',
    text: 'Premium AI access delivered in a clean and reliable flow.',
  },
  {
    id: 'support',
    label: 'Helpful support',
    text: 'Helpful support and a very professional overall experience.',
  },
]

function App() {
  const [view, setView] = useState('home')
  const [selectedCategoryId, setSelectedCategoryId] = useState('chatgpt')
  const [selectedServiceName, setSelectedServiceName] = useState('')
  const [selectedQuantity, setSelectedQuantity] = useState(1)
  const [selectedCouponCode, setSelectedCouponCode] = useState('')
  const [selectedReviewRating, setSelectedReviewRating] = useState(5)
  const [selectedReviewTemplateId, setSelectedReviewTemplateId] = useState('')
  const [reviewText, setReviewText] = useState('')
  const [apiFeaturedServices, setApiFeaturedServices] = useState([])
  const [profileSummary, setProfileSummary] = useState(null)
  const [profileOrders, setProfileOrders] = useState([])
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState('')

  const profileUserId = Number(import.meta.env.VITE_TEST_USER_ID || 0)

  const selectedCategory =
    categories.find((item) => item.id === selectedCategoryId) ?? categories[0]

  const selectedServices = servicesByCategory[selectedCategoryId] ?? []
  const selectedServiceDetail =
    selectedServices.find((item) => item.name === selectedServiceName) ??
    selectedServices[0]

  const selectedStockCount = Number(
    selectedServiceDetail?.stock?.match(/\d+/)?.[0] ?? 1
  )
  const selectedUnitPrice = Number(
    selectedServiceDetail?.price?.match(/\d+/)?.[0] ?? 0
  )
  const selectedCouponOptions = couponOptionsByCategory[selectedCategoryId] ?? []
  const selectedCoupon =
    selectedCouponOptions.find((item) => item.code === selectedCouponCode) ?? null
  const selectedReviewTemplate =
    reviewTemplateOptions.find((item) => item.id === selectedReviewTemplateId) ??
    null
  const estimatedSubtotal = selectedUnitPrice * selectedQuantity
  const selectedDiscountPercent = selectedCoupon?.discount ?? 0
  const estimatedDiscountValue = selectedDiscountPercent
    ? Math.round(estimatedSubtotal * selectedDiscountPercent) / 100
    : 0
  const estimatedTotalLabel = selectedUnitPrice
    ? `$${estimatedSubtotal}`
    : selectedServiceDetail?.price ?? '—'
  const estimatedDiscountLabel = selectedDiscountValue
    ? `-$${Number.isInteger(estimatedDiscountValue) ? estimatedDiscountValue : estimatedDiscountValue.toFixed(2)}`
    : '$0'
  const finalTotalLabel = selectedUnitPrice
    ? `$${Number.isInteger(estimatedSubtotal - estimatedDiscountValue) ? estimatedSubtotal - estimatedDiscountValue : (estimatedSubtotal - estimatedDiscountValue).toFixed(2)}`
    : estimatedTotalLabel

  const homeFeaturedServices =
    apiFeaturedServices.length > 0 ? apiFeaturedServices : featuredServices

  useEffect(() => {
    let active = true

    async function loadFeaturedServices() {
      try {
        const response = await fetchCatalogServices({
          only_active: true,
          limit: 3,
        })

        const items = Array.isArray(response?.items) ? response.items : []
        const normalized = items.map(buildFeaturedCardFromApi)

        if (active && normalized.length > 0) {
          setApiFeaturedServices(normalized)
        }
      } catch (error) {
        console.error('Failed to load featured services from API:', error)
      }
    }

    loadFeaturedServices()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (view !== 'profile') return
    let active = true

    async function loadProfile() {
      if (!profileUserId) {
        setProfileSummary(null)
        setProfileOrders([])
        setProfileError('VITE_TEST_USER_ID is not set')
        setProfileLoading(false)
        return
      }

      setProfileLoading(true)
      setProfileError('')

      try {
        const [summary, ordersResponse] = await Promise.all([
          fetchProfileSummary(profileUserId),
          fetchProfileOrders(profileUserId),
        ])

        if (active) {
          setProfileSummary(summary ?? null)
          setProfileOrders(Array.isArray(ordersResponse?.items) ? ordersResponse.items : [])
        }
      } catch (error) {
        console.error('Failed to load profile data:', error)
        if (active) {
          setProfileSummary(null)
          setProfileOrders([])
          setProfileError(error?.message ?? 'Failed to load profile')
        }
      } finally {
        if (active) setProfileLoading(false)
      }
    }

    loadProfile()

    return () => {
      active = false
    }
  }, [view, profileUserId])

  const viewTitle = useMemo(() => {
    if (view === 'categories') return 'Categories'
    if (view === 'services') return selectedCategory.name
    if (view === 'detail') return selectedServiceDetail?.name ?? 'Service Detail'
    if (view === 'checkout') return 'Checkout'
    if (view === 'review') return 'Review'
    if (view === 'profile') return 'My Orders'
    return 'UstAiTech'
  }, [view, selectedCategory, selectedServiceDetail])

  const openCategory = (categoryId) => {
    setSelectedCategoryId(categoryId)
    setSelectedServiceName('')
    setSelectedQuantity(1)
    setSelectedCouponCode('')
    setView('services')
  }

  const openService = (serviceName) => {
    setSelectedServiceName(serviceName)
    setSelectedQuantity(1)
    setSelectedCouponCode('')
    setView('detail')
  }

  return (
    <div className="app-shell">
      <div className="bg-orb bg-orb-1" />
      <div className="bg-orb bg-orb-2" />

      <main className="phone-frame">
        <header className="topbar">
          <div className="brand brand-compact">
            {view === 'home' ? (
              <div className="brand-mark">U</div>
            ) : (
              <button
                className="icon-button"
                type="button"
                aria-label="Back"
                onClick={() =>
                  setView(
                    view === 'review'
                      ? 'checkout'
                      : view === 'checkout'
                        ? 'detail'
                        : view === 'detail'
                          ? 'services'
                          : view === 'services'
                            ? 'categories'
                            : view === 'profile'
                              ? 'home'
                              : 'home'
                  )
                }
              >
                ←
              </button>
            )}

            <div>
              <p className="brand-name">{viewTitle}</p>
              <p className="brand-subtitle">
                {view === 'categories' && 'Choose your AI access category'}
                {view === 'services' && 'Premium subscription options'}
                {view === 'detail' && 'Service detail overview'}
                {view === 'checkout' && 'Final order summary'}
                {view === 'review' && 'Rate your completed experience'}
                {view === 'home' && 'Premium AI Access'}
                {view === 'profile' && 'Live profile and order history'}
              </p>
            </div>
          </div>

          <button className="icon-button" type="button" aria-label="Profile" onClick={() => setView('profile')}>
            ◎
          </button>
        </header>

        {view === 'home' && (
          <>
            <section className="hero-card">
              <div className="hero-copy">
                <span className="eyebrow">Telegram Mini App</span>
                <h1>Premium AI subscriptions inside Telegram</h1>
                <p>
                  Fast, trusted access to ChatGPT, Business plans, Gemini,
                  Grok, and other premium AI services.
                </p>
              </div>

              <div className="hero-stats">
                <div className="stat-card">
                  <span className="stat-label">Verified</span>
                  <strong>Digital Fulfillment</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Active</span>
                  <strong>Coupons Available</strong>
                </div>
              </div>

              <div className="hero-actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => setView('categories')}
                >
                  Browse Services
                </button>
                <button className="secondary-button" type="button" onClick={() => setView('profile')}>
                  My Orders
                </button>
              </div>
            </section>

            <section className="section-block">
              <div className="section-head">
                <h2>Categories</h2>
                <button
                  className="text-button"
                  type="button"
                  onClick={() => setView('categories')}
                >
                  View all
                </button>
              </div>

              <div className="category-grid">
                {categories.map((category) => (
                  <article
                    className="category-card"
                    key={category.id}
                    onClick={() => openCategory(category.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <span className="category-icon">{category.icon}</span>
                    <h3>{category.name}</h3>
                    <p>{category.subtitle}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="section-block">
              <div className="section-head">
                <h2>Featured Services</h2>
                <span className="micro-note">Premium picks</span>
              </div>

              <div className="services-stack">
                {homeFeaturedServices.map((service) => (
                  <article className="service-card" key={service.name}>
                    <div className="service-main">
                      <div className="service-icon">{service.name.charAt(0)}</div>

                      <div className="service-copy">
                        <div className="service-topline">
                          <h3>{service.name}</h3>
                          <span className="chip chip-accent">{service.badge}</span>
                        </div>
                        <p>{service.subtitle}</p>
                      </div>
                    </div>

                    <div className="service-meta">
                      <span className="price">{service.price}</span>
                      <span className="stock">{service.stock}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="trust-card">
              <div>
                <span className="chip chip-success">Confirmed Customer</span>
                <h3>High-trust premium storefront experience</h3>
                <p>
                  Clean checkout, review flow, coupon support, and verified
                  manual fulfillment.
                </p>
              </div>
            </section>
          </>
        )}

        {view === 'categories' && (
          <>
            <section className="section-block">
              <div className="section-head">
                <h2>All Categories</h2>
                <span className="micro-note">3 active groups</span>
              </div>

              <div className="category-list">
                {categories.map((category) => (
                  <article className="category-detail-card" key={category.id}>
                    <div className="category-detail-main">
                      <span className="category-icon category-icon-lg">
                        {category.icon}
                      </span>

                      <div className="category-detail-copy">
                        <div className="service-topline">
                          <h3>{category.name}</h3>
                          <span className="chip chip-neutral">
                            {(servicesByCategory[category.id] ?? []).length} services
                          </span>
                        </div>

                        <p className="category-detail-subtitle">
                          {category.subtitle}
                        </p>
                        <p>{category.description}</p>
                      </div>
                    </div>

                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => openCategory(category.id)}
                    >
                      Open Category
                    </button>
                  </article>
                ))}
              </div>
            </section>

            <section className="trust-card trust-card-soft">
              <div>
                <span className="chip chip-accent">Premium Access</span>
                <h3>Choose the right AI subscription path</h3>
                <p>
                  Personal plans, business access, and advanced AI tools — all
                  presented in a clean, trusted Telegram-native flow.
                </p>
              </div>
            </section>
          </>
        )}

        {view === 'services' && (
          <>
            <section className="service-list-hero">
              <div className="service-list-head">
                <span className="category-icon category-icon-lg">
                  {selectedCategory.icon}
                </span>

                <div>
                  <span className="eyebrow">Category</span>
                  <h2>{selectedCategory.name}</h2>
                  <p>{selectedCategory.description}</p>
                </div>
              </div>

              <div className="filter-row">
                <span className="chip chip-neutral">In stock</span>
                <span className="chip chip-neutral">Coupon</span>
                <span className="chip chip-neutral">Premium</span>
              </div>
            </section>

            <section className="section-block">
              <div className="section-head">
                <h2>Available Services</h2>
                <span className="micro-note">{selectedServices.length} offers</span>
              </div>

              <div className="services-stack">
                {selectedServices.map((service) => (
                  <article className="service-card service-card-expanded" key={service.name}>
                    <div className="service-main">
                      <div className="service-icon">{service.name.charAt(0)}</div>

                      <div className="service-copy">
                        <div className="service-topline">
                          <h3>{service.name}</h3>
                          <span className="chip chip-accent">{service.badge}</span>
                        </div>
                        <p>{service.subtitle}</p>
                      </div>
                    </div>

                    <div className="perks-row">
                      {service.perks.map((perk) => (
                        <span className="chip chip-neutral" key={perk}>
                          {perk}
                        </span>
                      ))}
                    </div>

                    <div className="service-meta">
                      <div className="service-meta-block">
                        <span className="meta-label">Price</span>
                        <span className="price">{service.price}</span>
                      </div>

                      <div className="service-meta-block align-right">
                        <span className="meta-label">Availability</span>
                        <span className="stock">{service.stock}</span>
                      </div>
                    </div>

                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => openService(service.name)}
                    >
                      View Service
                    </button>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}

        {view === 'detail' && selectedServiceDetail && (
          <>
            <section className="detail-hero">
              <div className="detail-hero-top">
                <span className="category-icon category-icon-lg">
                  {selectedServiceDetail.name.charAt(0)}
                </span>

                <div className="detail-hero-copy">
                  <span className="eyebrow">{selectedCategory.name}</span>
                  <h2>{selectedServiceDetail.name}</h2>
                  <p>{selectedServiceDetail.subtitle}</p>
                </div>
              </div>

              <div className="filter-row">
                <span className="chip chip-accent">
                  {selectedServiceDetail.badge}
                </span>
                <span className="chip chip-neutral">
                  {selectedServiceDetail.stock}
                </span>
                <span className="chip chip-neutral">Coupon step available</span>
              </div>

              <div className="detail-meta-row">
                <div className="service-meta-block">
                  <span className="meta-label">Price</span>
                  <span className="price">{selectedServiceDetail.price}</span>
                </div>

                <div className="service-meta-block align-right">
                  <span className="meta-label">Flow</span>
                  <span className="stock">
                    Quantity → Coupon → Checkout
                  </span>
                </div>
              </div>
            </section>

            <section className="detail-grid">
              <article className="detail-panel">
                <div className="section-head">
                  <h2>What you get</h2>
                  <span className="micro-note">Included</span>
                </div>

                <div className="perks-row">
                  {selectedServiceDetail.perks.map((perk) => (
                    <span className="chip chip-neutral" key={perk}>
                      {perk}
                    </span>
                  ))}
                </div>
              </article>

              <article className="detail-panel">
                <div className="section-head">
                  <h2>Trust & delivery</h2>
                  <span className="micro-note">Verified</span>
                </div>

                <ul className="detail-list">
                  <li>Manual approval flow remains controlled inside Telegram</li>
                  <li>Coupon selection appears before final checkout</li>
                  <li>Review submission is shown after fulfillment is completed</li>
                </ul>
              </article>
            </section>

            <section className="detail-panel">
              <div className="section-head">
                <h2>Quantity</h2>
                <span className="micro-note">Step 1</span>
              </div>

              <div className="quantity-card">
                <div className="quantity-control">
                  <button
                    className="quantity-button"
                    type="button"
                    onClick={() =>
                      setSelectedQuantity((current) => Math.max(1, current - 1))
                    }
                    disabled={selectedQuantity <= 1}
                  >
                    −
                  </button>

                  <div className="quantity-value-block">
                    <span className="meta-label">Selected quantity</span>
                    <strong className="quantity-value">{selectedQuantity}</strong>
                    <span className="quantity-caption">
                      Max available: {selectedStockCount}
                    </span>
                  </div>

                  <button
                    className="quantity-button"
                    type="button"
                    onClick={() =>
                      setSelectedQuantity((current) =>
                        Math.min(selectedStockCount, current + 1)
                      )
                    }
                    disabled={selectedQuantity >= selectedStockCount}
                  >
                    +
                  </button>
                </div>

                <div className="quantity-summary">
                  <div className="service-meta-block">
                    <span className="meta-label">Unit price</span>
                    <span className="stock">{selectedServiceDetail.price}</span>
                  </div>

                  <div className="service-meta-block align-right">
                    <span className="meta-label">Estimated total</span>
                    <span className="price">{estimatedTotalLabel}</span>
                  </div>
                </div>
              </div>
            </section>

            <section className="detail-panel coupon-panel">
              <div className="section-head">
                <h2>Coupon</h2>
                <span className="micro-note">Step 2</span>
              </div>

              <div className="coupon-stack">
                {selectedCouponOptions.map((coupon) => (
                  <article
                    className={`coupon-card ${
                      selectedCouponCode === coupon.code
                        ? 'coupon-card-active'
                        : ''
                    }`}
                    key={coupon.code}
                  >
                    <div className="coupon-copy">
                      <div className="coupon-topline">
                        <h3>{coupon.code}</h3>
                        <span className="chip chip-accent">
                          {coupon.discount}% OFF
                        </span>
                      </div>
                      <p className="coupon-title">{coupon.title}</p>
                      <p className="coupon-note">{coupon.note}</p>
                    </div>

                    <button
                      className="coupon-action-button"
                      type="button"
                      onClick={() => setSelectedCouponCode(coupon.code)}
                    >
                      {selectedCouponCode === coupon.code ? 'Applied' : 'Use'}
                    </button>
                  </article>
                ))}
              </div>

              <div className="coupon-summary">
                <div className="service-meta-block">
                  <span className="meta-label">Estimated discount</span>
                  <span className="stock">{estimatedDiscountLabel}</span>
                </div>

                <div className="service-meta-block align-right">
                  <span className="meta-label">Total after coupon</span>
                  <span className="price">{finalTotalLabel}</span>
                </div>
              </div>

              <div className="detail-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setSelectedCouponCode('')}
                >
                  Skip Coupon
                </button>
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => setView('checkout')}
                >
                  Continue to Checkout
                </button>
              </div>
            </section>

            <section className="detail-panel">
              <div className="section-head">
                <h2>Ready to continue</h2>
                <span className="micro-note">Next step</span>
              </div>

              <p className="detail-note">
                Quantity and coupon selection are ready. The next patch will
                attach the checkout step with final order summary.
              </p>

              <div className="detail-actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => setView('checkout')}
                >
                  Continue to Checkout
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setView('services')}
                >
                  Back to Services
                </button>
              </div>
            </section>
          </>
        )}

        {view === 'checkout' && selectedServiceDetail && (
          <>
            <section className="checkout-hero">
              <div className="section-head">
                <h2>Order Summary</h2>
                <span className="micro-note">Final step</span>
              </div>

              <article className="checkout-summary-card">
                <div className="service-main">
                  <div className="service-icon">
                    {selectedServiceDetail.name.charAt(0)}
                  </div>

                  <div className="service-copy">
                    <div className="service-topline">
                      <h3>{selectedServiceDetail.name}</h3>
                      <span className="chip chip-accent">
                        {selectedServiceDetail.badge}
                      </span>
                    </div>
                    <p>{selectedServiceDetail.subtitle}</p>
                  </div>
                </div>

                <div className="checkout-grid">
                  <div className="service-meta-block">
                    <span className="meta-label">Quantity</span>
                    <span className="stock">{selectedQuantity}</span>
                  </div>

                  <div className="service-meta-block align-right">
                    <span className="meta-label">Stock</span>
                    <span className="stock">{selectedServiceDetail.stock}</span>
                  </div>

                  <div className="service-meta-block">
                    <span className="meta-label">Subtotal</span>
                    <span className="stock">{estimatedTotalLabel}</span>
                  </div>

                  <div className="service-meta-block align-right">
                    <span className="meta-label">Coupon</span>
                    <span className="stock">
                      {selectedCoupon ? `${selectedCoupon.code} (${selectedCoupon.discount}% OFF)` : 'Skipped'}
                    </span>
                  </div>
                </div>

                <div className="checkout-total-row">
                  <div className="service-meta-block">
                    <span className="meta-label">Discount</span>
                    <span className="stock">{estimatedDiscountLabel}</span>
                  </div>

                  <div className="service-meta-block align-right">
                    <span className="meta-label">Final total</span>
                    <span className="price">{finalTotalLabel}</span>
                  </div>
                </div>
              </article>
            </section>

            <section className="detail-grid">
              <article className="detail-panel">
                <div className="section-head">
                  <h2>Payment step</h2>
                  <span className="micro-note">Manual check</span>
                </div>

                <ul className="detail-list">
                  <li>Payment confirmation remains controlled through the bot flow</li>
                  <li>Manual approval/check step is preserved for trust and safety</li>
                  <li>Review step will appear after fulfillment is completed</li>
                </ul>
              </article>

              <article className="detail-panel">
                <div className="section-head">
                  <h2>Current status</h2>
                  <span className="micro-note">Preview</span>
                </div>

                <div className="perks-row">
                  <span className="chip chip-neutral">Pending payment check</span>
                  <span className="chip chip-neutral">Verified flow</span>
                  <span className="chip chip-neutral">Telegram-native</span>
                </div>
              </article>
            </section>

            <section className="detail-panel">
              <div className="section-head">
                <h2>Proceed</h2>
                <span className="micro-note">Next patch</span>
              </div>

              <p className="detail-note">
                Checkout shell is ready. The next patch can attach review flow
                after a completed order state.
              </p>

              <div className="detail-actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => setView('review')}
                >
                  Submit Order
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setView('detail')}
                >
                  Back to Detail
                </button>
              </div>
            </section>
          </>
        )}

        {view === 'profile' && (
          <>
            <section className="checkout-hero">
              <div className="section-head">
                <h2>Profile Summary</h2>
                <span className="micro-note">Live API</span>
              </div>

              {profileLoading && (
                <p className="detail-note">Loading profile data...</p>
              )}

              {!profileLoading && profileError && (
                <p className="detail-note" style={{ color: 'var(--color-danger, #f87171)' }}>
                  {profileError}
                </p>
              )}

              {!profileLoading && !profileError && profileSummary && (
                <article className="checkout-summary-card">
                  <div className="service-main">
                    <div className="service-icon">
                      {(profileSummary.full_name || profileSummary.username || 'U')
                        .charAt(0)
                        .toUpperCase()}
                    </div>

                    <div className="service-copy">
                      <div className="service-topline">
                        <h3>{profileSummary.full_name || 'User'}</h3>
                        <span
                          className={
                            profileSummary.confirmed_orders_count > 0
                              ? 'chip chip-accent'
                              : 'chip chip-neutral'
                          }
                        >
                          {profileSummary.confirmed_orders_count > 0
                            ? 'Confirmed customer'
                            : 'Standard user'}
                        </span>
                      </div>
                      {profileSummary.username && (
                        <p>@{profileSummary.username}</p>
                      )}
                    </div>
                  </div>

                  <div className="checkout-grid">
                    <div className="service-meta-block">
                      <span className="meta-label">Bonus balance</span>
                      <span className="stock">{profileSummary.bonus_balance ?? 0}</span>
                    </div>

                    <div className="service-meta-block align-right">
                      <span className="meta-label">Confirmed orders</span>
                      <span className="stock">{profileSummary.confirmed_orders_count ?? 0}</span>
                    </div>

                    <div className="service-meta-block">
                      <span className="meta-label">Total spent</span>
                      <span className="price">
                        {profileSummary.total_spent != null
                          ? `${profileSummary.total_spent} so'm`
                          : '—'}
                      </span>
                    </div>

                    <div className="service-meta-block align-right">
                      <span className="meta-label">Last service</span>
                      <span className="stock">{profileSummary.last_service_name || '—'}</span>
                    </div>

                    {profileSummary.last_confirmed_at && (
                      <div className="service-meta-block">
                        <span className="meta-label">Last confirmed</span>
                        <span className="stock">
                          {new Date(profileSummary.last_confirmed_at).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                </article>
              )}
            </section>

            <section className="section-block">
              <div className="section-head">
                <h2>My Orders</h2>
                <span className="micro-note">
                  {profileOrders.length} order{profileOrders.length !== 1 ? 's' : ''}
                </span>
              </div>

              {!profileLoading && !profileError && profileOrders.length === 0 && (
                <p className="detail-note">No orders found for this user.</p>
              )}

              {!profileLoading && profileOrders.length > 0 && (
                <div className="services-stack">
                  {profileOrders.map((order, index) => (
                    <article
                      className="service-card service-card-expanded"
                      key={order.id ?? index}
                    >
                      <div className="service-main">
                        <div className="service-icon">
                          {(order.service_name || 'O').charAt(0)}
                        </div>

                        <div className="service-copy">
                          <div className="service-topline">
                            <h3>{order.service_name || 'Order'}</h3>
                            <span
                              className={
                                order.status === 'confirmed'
                                  ? 'chip chip-accent'
                                  : 'chip chip-neutral'
                              }
                            >
                              {order.status || 'pending'}
                            </span>
                          </div>
                          <p>Order #{order.id}</p>
                        </div>
                      </div>

                      <div className="checkout-grid">
                        <div className="service-meta-block">
                          <span className="meta-label">Quantity</span>
                          <span className="stock">{order.quantity ?? 1}</span>
                        </div>

                        <div className="service-meta-block align-right">
                          <span className="meta-label">Created</span>
                          <span className="stock">
                            {order.created_at
                              ? new Date(order.created_at).toLocaleDateString()
                              : '—'}
                          </span>
                        </div>

                        <div className="service-meta-block">
                          <span className="meta-label">Final price</span>
                          <span className="price">
                            {order.final_price != null
                              ? `${order.final_price} so'm`
                              : '—'}
                          </span>
                        </div>

                        {order.coupon_code && (
                          <div className="service-meta-block align-right">
                            <span className="meta-label">Coupon</span>
                            <span className="stock">{order.coupon_code}</span>
                          </div>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="detail-panel">
              <div className="detail-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setView('home')}
                >
                  Back to Home
                </button>
              </div>
            </section>
          </>
        )}

        {view === 'review' && selectedServiceDetail && (
          <>
            <section className="review-hero">
              <div className="section-head">
                <h2>Leave a Review</h2>
                <span className="micro-note">Post-fulfillment</span>
              </div>

              <article className="review-summary-card">
                <div className="service-main">
                  <div className="service-icon">
                    {selectedServiceDetail.name.charAt(0)}
                  </div>

                  <div className="service-copy">
                    <div className="service-topline">
                      <h3>{selectedServiceDetail.name}</h3>
                      <span className="chip chip-success">Fulfilled</span>
                    </div>
                    <p>{selectedServiceDetail.subtitle}</p>
                  </div>
                </div>

                <div className="checkout-grid">
                  <div className="service-meta-block">
                    <span className="meta-label">Quantity</span>
                    <span className="stock">{selectedQuantity}</span>
                  </div>

                  <div className="service-meta-block align-right">
                    <span className="meta-label">Final total</span>
                    <span className="price">{finalTotalLabel}</span>
                  </div>
                </div>
              </article>
            </section>

            <section className="detail-panel review-panel">
              <div className="section-head">
                <h2>Rating</h2>
                <span className="micro-note">Step 1</span>
              </div>

              <div className="rating-row">
                {[5, 4, 3].map((rating) => (
                  <button
                    key={rating}
                    className={`rating-chip ${
                      selectedReviewRating === rating ? 'rating-chip-active' : ''
                    }`}
                    type="button"
                    onClick={() => setSelectedReviewRating(rating)}
                  >
                    {rating}★
                  </button>
                ))}
              </div>
            </section>

            <section className="detail-panel review-panel">
              <div className="section-head">
                <h2>Template Review</h2>
                <span className="micro-note">Step 2</span>
              </div>

              <div className="review-template-grid">
                {reviewTemplateOptions.map((template) => (
                  <button
                    key={template.id}
                    className={`review-template-chip ${
                      selectedReviewTemplateId === template.id
                        ? 'review-template-chip-active'
                        : ''
                    }`}
                    type="button"
                    onClick={() => {
                      setSelectedReviewTemplateId(template.id)
                      setReviewText(template.text)
                    }}
                  >
                    {template.label}
                  </button>
                ))}
              </div>

              <div className="review-text-wrap">
                <span className="meta-label">Custom text</span>
                <textarea
                  className="review-textarea"
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  placeholder="Share your experience with fulfillment, support, and overall service quality..."
                  rows={5}
                />
              </div>
            </section>

            <section className="detail-panel">
              <div className="section-head">
                <h2>Submit</h2>
                <span className="micro-note">Final step</span>
              </div>

              <p className="detail-note">
                Review screen is ready. The next patch can add Profile / My
                Orders UI with confirmed customer state and order history cards.
              </p>

              <div className="detail-actions">
                <button className="primary-button" type="button">
                  Submit Review
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setView('home')}
                >
                  Back to Home
                </button>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

export default App
