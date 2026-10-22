---
name: a11y-review
description: Accessibility review procedure. Trigger when a UI component, form, dialog, navigation, or color change is proposed.
---

# Accessibility review

## Procedure

1. **Keyboard pass.** Tab through the changed UI. Every action reachable? Focus
   visible? No trap? Escape closes overlays? Focus returns to the trigger?
2. **Screen-reader pass.** Name, role, value, state for every control. Use
   VoiceOver/NVDA/Orca for a spot check; the accessibility tree in DevTools is
   a fast first look.
3. **Zoom and reflow.** 200% zoom, 320px width, no horizontal scroll for
   content, text not clipped.
4. **Contrast.** Text 4.5:1, large text 3:1, UI/focus 3:1. Check both themes.
5. **Forms.** Label, required state, error text associated and announced,
   autocomplete attributes, no timeout without warning.
6. **Motion.** `prefers-reduced-motion` respected; no auto-play; no flashing.
7. **Automated scan.** axe or equivalent; fix serious/critical. Do not treat a
   clean scan as proof.

## Test matrix

| Flow | Keyboard | Screen reader | Zoom | Contrast |
|---|---|---|---|---|
| Primary action | | | | |
| Form + error | | | | |
| Dialog | | | | |
| Navigation | | | | |
| Empty/loading/error | | | | |

## Common findings

- Clickable `div` without role/tabindex/key handler.
- Icon-only button with no accessible name.
- `aria-hidden="true"` on a container with a focusable child.
- Focus outline removed with `outline: none` and nothing replacing it.
- Error message rendered but not linked to the input.
- Disabled button used where a validation message is needed.
- Color-only status (red/green dot).
- Placeholder used as the only label.

## Verdict

`BLOCKER` for a keyboard trap or an inaccessible primary action; `HIGH` for a
missing label or contrast failure; `MEDIUM` for a focus-order or announcement
issue. Do not report a WCAG criterion without the element and the user impact.
