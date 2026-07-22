# UI/UX Brief

## Design objective

Create a calm, premium finance workspace that surfaces the financial picture before operational detail. The visual direction is editorial finance: warm paper backgrounds, dark ink navigation, sand/terracotta highlights, restrained data colors, rounded surfaces, and generous spacing.

## Design system

| Token | Use |
|---|---|
| Warm paper `#F7F5EF` | Primary page background |
| Ink `#0B100C` | Sidebar and high-contrast surfaces |
| Cream `#FDFCFB` | Cards and panels |
| Sand `#DECAA0` | Selected navigation and subtle highlights |
| Terracotta `#CC7C31` | Primary chart/action accent |
| Muted plum `#8E7690` | Secondary data series |
| Sage | Positive/budget-healthy state |

## Information hierarchy

1. Welcome/header and period context.
2. KPI cards: income, expenses, investments, cash flow, review count.
3. Visual charts and budget progress.
4. Action-required items: reviews and bills.
5. Operational tools: Gmail sync, logs, uploads, exports.
6. Long lists/details behind expandable panels.

## Interaction rules

- Charts must be keyboard-focusable and expose a text tooltip/title.
- Clicking a trend month opens the corresponding report.
- Clicking a category opens filtered transactions.
- Destructive or irreversible actions require a clear label and confirmation where appropriate.
- Loading, empty, error, and disabled states must remain explicit.
- Use motion only for orientation/feedback; honor `prefers-reduced-motion`.

## Responsive rules

- Desktop: persistent sidebar, four-column KPI grid, two-column analytics.
- Tablet: two-column KPI grid and single-column analytics as needed.
- Mobile: drawer navigation, stacked cards, scrollable table container, touch-friendly controls.

## Accessibility requirements

- Semantic headings, buttons, labels, tables, summaries/details, and live-status messages.
- Visible keyboard focus and sufficient contrast in both themes.
- Never communicate status through color alone; retain text/badges.
- Use concise labels and do not hide essential actions behind hover-only UI.

## Component guidance

- Reuse `metric-card`, chart, KPI, timeline, progress, badge, and expandable-detail patterns.
- Avoid adding a UI framework unless the current CSS approach becomes unmaintainable.
- Split `App.tsx` into page/component files only as a behavior-preserving refactor.
