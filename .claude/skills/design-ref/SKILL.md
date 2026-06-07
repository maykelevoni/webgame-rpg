---
name: design-ref
description: "Live design reference fetcher for professional UI. Grabs real components from 21st.dev, uses real Unsplash images, curated palettes, and varied layouts. Use for any UI build, design, or review task."
---

# Design Reference — Live & Human-Quality UI

Fetch real design references before building. Never produce generic AI layouts.

---

## Step 1 — Fetch a Live Component Reference

Use Playwright to grab a real component from 21st.dev that matches the task:

```
Navigate → https://21st.dev/community/components
Find a component matching the task (hero, card, pricing, dashboard, etc.)
Take a screenshot + read the source HTML/CSS
Extract: color palette, font choices, spacing system, layout structure
```

Use the extracted patterns as the baseline for your implementation. Do not invent a generic layout when a real one is available.

---

## Step 2 — Use Real Media (Never Placeholders)

### Images
Always use real Unsplash URLs. Format: `https://images.unsplash.com/photo-{ID}?w=1200&q=80`

| Category | Photo IDs to use |
|---|---|
| Tech / SaaS | `1714698628`, `1605379399`, `1633356122`, `1518770660`, `1551288049` |
| Lifestyle / Wellness | `1545205597`, `1571019613`, `1506126613`, `1544161515`, `1507003211169` |
| Business / Finance | `1460925895917`, `1521737604`, `1556742049`, `1553484774` |
| Food / Restaurant | `1565299624596`, `1482049016823`, `1414235077`, `1504674671` |
| Fashion / E-commerce | `1558618666`, `1566174476869`, `1434389160`, `1490481505` |
| People / Avatars | Use `https://i.pravatar.cc/150?img={1–70}` |
| Abstract / Texture | `1618005182`, `1557682237`, `1550745441`, `1579547608` |

### Video
For video sections, embed a real YouTube iframe — never use a gray box.

### Icons
Use Lucide React, Heroicons, or Phosphor. Never emoji as icons.

### Fonts
Load from Google Fonts. Pick a pairing from the table below.

---

## Step 3 — Pick a Palette & Font Pairing

| Product Type | Background | Primary | Accent | Font Pairing |
|---|---|---|---|---|
| SaaS / Tech | `#0F172A` | `#6366F1` | `#F8FAFC` | Inter + JetBrains Mono |
| Startup / Landing | `#FAFAFA` | `#111827` | `#3B82F6` | Geist + Geist Mono |
| Wellness / Health | `#F9F5F0` | `#2D6A4F` | `#95D5B2` | Playfair Display + Lato |
| Finance / Fintech | `#0A0A0A` | `#D4AF37` | `#1C1C1C` | DM Sans + DM Serif Display |
| Creative / Agency | `#FAFAFA` | `#FF3366` | `#1A1A1A` | Syne + Manrope |
| E-commerce | `#FFF8F0` | `#FF6B2B` | `#2D2D2D` | Nunito + Merriweather |
| Portfolio | `#111111` | `#FFFFFF` | `#FACC15` | Space Grotesk + Space Mono |
| Healthcare | `#F0F4FF` | `#1D4ED8` | `#DBEAFE` | Plus Jakarta Sans + Inter |
| Food / Restaurant | `#1A0A00` | `#E8A049` | `#FFF9F0` | Cormorant Garamond + Jost |
| Education | `#F8F9FA` | `#7C3AED` | `#EDE9FE` | Outfit + Literata |

---

## Step 4 — Layout Rules (No Generic AI Defaults)

**Forbidden patterns:**
- 3-column identical feature cards as the hero section
- Stock gradient blobs behind centered text
- Gray `bg-gray-100` placeholder image boxes
- Lorem ipsum text
- `text-gray-500` everywhere with no visual hierarchy

**Use instead:**

| Instead of | Use |
|---|---|
| 3-column cards | Bento grid, asymmetric split, staggered masonry |
| Centered hero text | Full-bleed image with overlay text, split-screen 60/40 |
| Plain white background | Subtle texture, gradient mesh, or grain overlay |
| Generic blue CTA | Brand-color button with real hover state (scale + shadow) |
| Empty sections | Fill every section with real images or real data |

**Layout variety — pick one per page section:**
- **Hero**: full-bleed background image + frosted glass card overlay
- **Features**: bento grid (2×2 large + 2×1 narrow) or horizontal scroll cards
- **Testimonials**: asymmetric 2-column with large quote mark + avatar
- **Pricing**: 3-tier with the middle card elevated (scale-105, shadow-xl)
- **CTA section**: full-width dark band with background image at 20% opacity
- **Footer**: 4-column grid with logo, tagline, and real social icons

---

## Step 5 — Quality Checklist Before Delivering

- [ ] At least 2 real Unsplash images are used per full page
- [ ] All fonts are loaded from Google Fonts or are system fonts intentionally
- [ ] No emoji used as icons
- [ ] No Lorem ipsum — all copy has personality
- [ ] Hover/focus states defined on all interactive elements
- [ ] Dark/light contrast ratio ≥ 4.5:1 for body text
- [ ] Mobile layout checked (no horizontal scroll, min 44px tap targets)
- [ ] At least one "wow" element: glassmorphism card, parallax, animated counter, gradient text, or video background

---

## When to Fetch Live vs Use Static

| Situation | Action |
|---|---|
| Building a new page or major component | Fetch from 21st.dev first |
| Fixing a bug or small tweak | Use static rules above, skip fetch |
| User asks for a specific style (glassmorphism, brutalism, etc.) | Fetch + filter by style on 21st.dev |
| Reviewing existing UI | Use quality checklist only |
