# NeuroFlow Design System Guidelines

This document specifies the visual language, design tokens, typography, layout rules, and component specifications for NeuroFlow. Inspired by the clean, minimal, spacious, and premium aesthetic of modern human-interface design (e.g. apple.com).

Every future frontend feature, screen, and component must adhere strictly to these principles.

---

## 1. Core Philosophy & Aesthetics

1. **Content First, Decoration Second**: Let the typography, hierarchy, and whitespace carry the interface. Avoid unnecessary gradients, heavy outlines, and visual clutter.
2. **Generous Whitespace**: High density is the enemy of calm productivity. Allow ample breathing room around headlines, dashboards, and interactive elements.
3. **Restrained Color Usage**: The canvas is strictly monochrome neutral (pure white or deep black/graphite) energized by a single precision accent blue. Semantic and category colors use desaturated, muted tones.
4. **Precision Craftsmanship**: 1px hairline borders (`rgba(0,0,0,0.08)` or `rgba(255,255,255,0.08)`), pill-shaped action buttons, subtle frosted glass blurs, and whisper-quiet micro-interactions.
5. **No Emojis in the Core UI**: Use thin 1.5px stroke icons (Lucide or inline SVG).

---

## 2. Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
  "Helvetica Neue", var(--font-inter), Inter, Arial, sans-serif;
```
*Inter is loaded via `next/font/google` as the high-fidelity web fallback for non-Apple platforms.*

### Type Scale & Hierarchy
| Style | Size | Weight | Tracking | Line Height | Usage |
|---|---|---|---|---|---|
| **Hero Headline** | 56px–80px | 600 (Semibold) | -0.025em to -0.03em | 1.05 | Landing heroes, primary product statements |
| **Section Heading** | 32px–48px | 600 (Semibold) | -0.02em | 1.15 | Major page sections, feature headers |
| **Subsection Title** | 24px–28px | 600 (Semibold) | -0.015em | 1.25 | Card group headers, modal titles |
| **Card / Item Title** | 19px–21px | 600 (Semibold) | -0.01em | 1.30 | Schedule block titles, goal headlines |
| **Body (Default)** | 17px | 400 (Regular) | -0.005em | 1.47 | Primary reading text, descriptions |
| **Body Compact** | 15px | 400 / 500 | 0 | 1.45 | Dashboard widgets, table rows, form inputs |
| **Footnote / Label** | 12px–14px | 400 / 500 | 0 | 1.40 | Meta labels, timestamps, badges, secondary notes |

### Copy Rules
- Use **sentence case** for all headings, buttons, and badges (e.g., *"Today's focus timeline"*, not *"Today's Focus Timeline"*).
- Keep text short, crisp, confident, and direct.

---

## 3. Color System

### Neutral & Surface Tokens

| Token | Light Mode | Dark Mode | Purpose |
|---|---|---|---|
| `--color-bg-primary` | `#ffffff` | `#000000` | Main canvas background |
| `--color-bg-secondary` | `#f5f5f7` | `#161617` | Alternating section background, subtle containers |
| `--color-bg-elevated` | `#ffffff` | `#1d1d1f` | Cards, modals, elevated surfaces |
| `--color-text-primary` | `#1d1d1f` | `#f5f5f7` | Primary headlines and high-contrast copy |
| `--color-text-secondary`| `#6e6e73` | `#a1a1a6` | Subtitles, supporting copy, timestamps |
| `--color-border-subtle` | `#d2d2d7` (or `rgba(0,0,0,0.08)`) | `rgba(255,255,255,0.08)` | Hairline dividers, card outlines |
| `--color-fill-tertiary` | `#f5f5f7` | `#2c2c2e` | Text inputs, segmented control tracks |

### Primary Accent
| Token | Light Mode | Dark Mode | Purpose |
|---|---|---|---|
| `--color-accent` | `#0071e3` | `#2997ff` | Primary CTA buttons, active toggles, focus rings |
| `--color-accent-hover` | `#0077ed` | `#3ba2ff` | Hover state for accent buttons |
| `--color-link` | `#0066cc` | `#2997ff` | Inline links and secondary chevron links |

### Restrained Category & Timeline Palette
Never use high-saturation neon colors. Category indicators, timeline blocks, and charts must use soft, desaturated tones:

| Tone | Light Mode Fill | Light Mode Text | Dark Mode Fill | Dark Mode Text |
|---|---|---|---|---|
| **Soft Blue** | `rgba(0,113,227,0.10)` | `#0071e3` | `rgba(41,151,255,0.15)` | `#2997ff` |
| **Soft Green** | `rgba(52,199,89,0.12)` | `#248a3d` | `rgba(48,209,88,0.15)` | `#30d158` |
| **Soft Orange** | `rgba(255,149,0,0.12)` | `#c96500` | `rgba(255,159,10,0.15)` | `#ff9f0a` |
| **Soft Purple** | `rgba(175,82,222,0.12)` | `#893cb5` | `rgba(191,90,242,0.15)` | `#bf5af2` |
| **Soft Pink** | `rgba(255,45,85,0.12)` | `#c2183b` | `rgba(255,55,95,0.15)` | `#ff375f` |
| **Soft Teal** | `rgba(90,200,250,0.12)` | `#007a99` | `rgba(100,210,255,0.15)` | `#64d2ff` |

---

## 4. Layout, Shape, and Spacing

### Max Width Constraints
- **Text & Editorial Sections**: `max-w-[980px]` centered with `px-6`.
- **Dashboards & Timelines**: `max-w-[1200px]` centered with `px-8`.
- **Vertical Spacing**: `py-20` to `py-28` (80px–120px) between major page sections on desktop.

### Shape & Border Radius Tokens
- **Pill (Buttons, Badges, Search Bars)**: `rounded-full` (`border-radius: 980px`).
- **Cards & Content Panels**: `rounded-[22px]` (18px–24px).
- **Form Inputs & Smaller Widgets**: `rounded-xl` (12px–14px).
- **Modals / Sheets**: `rounded-[24px]` (desktop) or `rounded-t-[28px]` (mobile bottom sheet).

### Shadows
- **Card**: `0 4px 24px rgba(0, 0, 0, 0.04)` (Light) / `0 8px 32px rgba(0, 0, 0, 0.4)` (Dark).
- **Elevated Hover**: `0 12px 36px rgba(0, 0, 0, 0.08)`.
- **Modal / Popover**: `0 24px 60px rgba(0, 0, 0, 0.16)`.

---

## 5. Navigation Bar Specification
- **Height**: Fixed `48px` height.
- **Surface**: Sticky top with translucent blur:
  ```css
  background: rgba(255, 255, 255, 0.8); /* dark: rgba(0, 0, 0, 0.8) */
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--color-border-subtle);
  ```
- **Typography**: 12px font size, weight 400, muted `#6e6e73` (dark `#a1a1a6`), transitioning to primary on hover.
- **Layout**: Centered horizontal link strip on desktop; clean hamburger modal menu on mobile.

---

## 6. Motion & Transitions

- **Duration**: `200ms` for hover states; `600ms` with `cubic-bezier(0.16, 1, 0.3, 1)` for reveal animations.
- **Scroll Reveal**: Elements fade in while rising 16px (`opacity: 0; transform: translateY(16px)` to `opacity: 1; transform: translateY(0)`), triggered once via `IntersectionObserver`.
- **No Spring / Bounce**: No elastic or flashy animations. Motions must feel grounded, damped, and instantaneous.
- **Respect Accessibility**: Always disable or reduce motion if `@media (prefers-reduced-motion: reduce)` is active.

---

## 7. Component Library Specifications

### 7.1 Button
- **Primary**: Pill-shaped (`rounded-full`), solid accent blue (`#0071e3`), white text, subtle hover lift/tint.
- **Secondary (Link style)**: Blue text with an inline chevron (`Learn more >` or `View schedule →`), hover underline or chevron nudge.
- **Secondary (Pill outlined)**: Transparent fill, 1px subtle border, text primary.
- **Sizes**: Small (28px height, 12px text), Medium (36px height, 14px text), Large (44px height, 17px text).

### 7.2 Card
- Surface: `#ffffff` in light mode, `#1d1d1f` in dark mode.
- Radius: `rounded-[22px]`.
- Border: 1px hairline `var(--color-border-subtle)`.
- Padding: 24px to 32px.

### 7.3 Input & Form Controls
- Height: 44px.
- Radius: `rounded-xl` (12px).
- Background: `#f5f5f7` (light) / `#2c2c2e` (dark).
- Border: Transparent by default; 2px focus ring with `var(--color-accent)`.

### 7.4 Badge / Pill
- Height: 24px–26px.
- Radius: `rounded-full`.
- Padding: `px-3 py-0.5`.
- Text: 12px, weight 500, sentence case.

### 7.5 Toggle (iOS Switch)
- Dimensions: 50px width × 30px height track; 26px round thumb.
- Track inactive: `#e5e5ea` (light) / `#39393d` (dark).
- Track active: `#34c759` (or `#0071e3` depending on context).
- Thumb: Pure white `#ffffff`, soft shadow `0 2px 6px rgba(0,0,0,0.2)`.

### 7.6 Tabs (Segmented Control)
- Track: `#e5e5ea` (light) / `#2c2c2e` (dark), `rounded-full`, 4px padding.
- Active Segment: Pure white (light) / `#636366` (dark), `rounded-full`, soft drop shadow, smooth position transition.

### 7.7 Modal / Sheet
- Backdrop: `rgba(0, 0, 0, 0.4)` with 12px backdrop-blur.
- Container: Desktop centered dialog (`rounded-[24px]`) or mobile bottom sheet (`rounded-t-[28px]`).
- Clean dismiss button with subtle circular hover background.

### 7.8 Toast
- Floating pill-shaped card (`rounded-full`), centered top/bottom.
- Height: 40px–44px, blurred background, subtle border, concise message.

### 7.9 Skeleton Loader
- Subtle pulse / shimmer between `#f5f5f7` and `#e5e5ea` (light) or `#1d1d1f` and `#2c2c2e` (dark).

---

## 8. Accessibility Requirements
- **WCAG AA Compliance**: All text colors must maintain at least 4.5:1 contrast against their surfaces.
- **Visible Keyboard Focus**: All interactive elements must show a distinct, accessible focus ring (`focus-visible:ring-2 focus-visible:ring-[#0071e3] focus-visible:outline-none`).
- **Semantic HTML**: Proper button, input, dialog, and heading hierarchy throughout.
