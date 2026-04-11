# GitSyntropy Unified Design System

This file is the single source of truth for UI design decisions. Any intentional visual deviation from referenced mocks must be logged in the Drift Log section before implementation.

## 1) Source Map

Canonical source files:

- `design-styles/styles.css` (primary token baseline and reusable primitives)
- `design-styles/index.html` (landing baseline)
- `design-styles/dashboard.html` (dashboard information architecture baseline)
- `design-styles/uikit.html` (component references)
- `frontend-design/land.html` (expanded landing content and bento composition)
- `frontend-design/auth.html` (auth page composition)
- `frontend-design/assessment.html` (assessment flow structure)
- `frontend-design/workspace.html` (simulator/workspace structure)
- `frontend-design/insights.html` (insights page structure)
- `frontend-design/dash.html` (alt app-shell/dashboard pattern)
- `frontend-design/design-imporve.txt.txt` (contrast and accessibility guidance)

## 2) Design Principles

- Dark-first interface for high-focus analytics workflows.
- Electric purple as core brand signal, with restrained neon accents.
- Glassmorphism and bento cards as default layout vocabulary.
- High legibility over decorative effects.
- Motion should clarify state changes, not distract.

## 3) Canonical Tokens

The implementation must map all UI code to these semantic tokens.

### 3.1 Color Tokens

- `--bg-base: #121212`
- `--bg-elevated: #191919`
- `--surface-glass: rgba(255, 255, 255, 0.04)`
- `--surface-glass-strong: rgba(255, 255, 255, 0.08)`
- `--border-glass: rgba(255, 255, 255, 0.12)`
- `--primary-solid: #7f00ff`
- `--primary-text: #c480ff`
- `--primary-glow: rgba(127, 0, 255, 0.32)`
- `--accent-neon: #39ff14`
- `--accent-info: #00d4ff`
- `--text-primary: #f8f8f8`
- `--text-secondary: #b8b8c2`
- `--text-muted: #8d8d98`
- `--status-success: #39ff14`
- `--status-warning: #ffd166`
- `--status-danger: #ff4d6d`

Contrast target:

- Minimum 4.5:1 for standard text against `--bg-base` and card surfaces.

### 3.2 Typography Roles

- Display headings: `Space Grotesk` (fallback: `Orbitron`)
- UI headings and labels: `Montserrat`
- Body copy: `Inter` (fallback: `Open Sans`)
- Mono/metrics: `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`
- Optional decorative annotations only: `Reenie Beanie`

Type scale:

- Hero: clamp(2.5rem, 6vw, 5rem)
- H1: 2rem
- H2: 1.5rem
- H3: 1.25rem
- Body: 1rem
- Small: 0.875rem

### 3.3 Spacing and Radius

- Spacing unit: 4px base
- Card padding default: 24px
- Section spacing default: 48px
- Grid gap default: 24px
- `--radius-sm: 8px`
- `--radius-md: 16px`
- `--radius-lg: 24px`
- `--radius-pill: 999px`

### 3.4 Effects and Motion

- Glass blur: 12px to 24px
- Hover lift: max `translateY(-3px)`
- Primary glow only for key actions or highlighted metrics
- Transition duration: 180ms to 260ms, ease-out

## 4) Layout Patterns

- Max container width: 1400px (1600px only for data-dense dashboard views).
- Default app shell: left navigation + top contextual header + bento content grid.
- Bento grid: 12 columns desktop, collapsing progressively at tablet/mobile breakpoints.
- Navigation variants:
  - Marketing: floating top navigation.
  - App shell: left rail/sidebar with active state.
  - Insights: top section tabs/pills when context requires.

## 5) Component Baselines

- Buttons: `primary`, `secondary`, `ghost`, `danger`.
- Inputs: glass field, high-contrast focus ring, clear error state.
- Cards: glass panel, optional accent top border for primary data.
- Badges: status or category only, compact pill.
- Progress bars: neon accent with muted track.
- Loaders: subtle glow and minimal motion.
- Charts: dark plotting area, no hard white gridlines.

## 6) Route-to-Design Mapping

| Route | Primary Reference | Secondary Reference | Status |
| --- | --- | --- | --- |
| `/` | `design-styles/index.html` | `frontend-design/land.html` | Locked |
| `/auth` | `frontend-design/auth.html` | `design-styles/uikit.html` | Locked |
| `/dashboard` | `design-styles/dashboard.html` | `frontend-design/dash.html` | Locked |
| `/assessment` | `frontend-design/assessment.html` | `design-styles/uikit.html` | Locked |
| `/workspace` | `frontend-design/workspace.html` | `design-styles/dashboard.html` | Locked |
| `/insights` | `frontend-design/insights.html` | `frontend-design/dash.html` | Locked |

## 7) UI Definition of Done

A page is considered complete only when:

- Uses semantic tokens from this file (no arbitrary one-off colors).
- Matches mapped source layout and hierarchy.
- Includes loading, empty, success, and error states.
- Keyboard accessible navigation and focus states are present.
- Standard text contrast meets 4.5:1 minimum.
- No visual regression against reference structure for key components.

## 8) Drift Log

Record every intentional style deviation before implementation.

| Date | Area | Requested Change | Reason | Approved By | Status |
| --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | Open |

## 9) Iteration UI Checklist

For each iteration, verify:

1. Updated page follows its route mapping.
2. Any new component is mapped to existing baseline patterns.
3. Drift log updated (if needed) before coding.
4. Accessibility checks pass for text, focus, and interaction states.
