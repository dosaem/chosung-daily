## Brand & Style

This design system establishes a dark minimal aesthetic tailored for a daily Korean word puzzle experience. The interface is optimized for focused, distraction-free gameplay, evoking a calm yet intellectually stimulating atmosphere. 

- **Brand Personality:** Minimal, focused, modern, and cerebral.
- **Target Audience:** Language learners, puzzle enthusiasts, and native speakers seeking a clean daily ritual.
- **Emotional Response:** Calm concentration, satisfaction of discovery, and effortless navigation.
- **Design Style:** Strict minimalism combined with low-contrast outlines and flat surfaces. Shadows are entirely absent to maintain a pure, two-dimensional plane that emphasizes linguistic characters over decorative chrome.

## Layout & Spacing

A centered, fixed-width column layout optimized for mobile screens and desktop web wrappers. The interface utilizes a structured 12-column grid system with consistent 16px gutters and 24px outer margins.

- **Mobile:** Single-column stacking with edge-to-edge puzzle tiles bounded by safe area margins.
- **Desktop:** Centered app container with a max-width of `480px` to preserve handheld ergonomics and focus.
- **Rhythm:** Spacing follows a strict 4px/8px incremental rhythm, ensuring predictable vertical stacks between the header, Choseong clues, virtual keyboard, and score trackers.

## Elevation & Depth

Depth is deliberately eliminated in favor of a pure flat architecture. 
- **Low-Contrast Outlines:** Surfaces, tiles, and input slots are delineated using thin, 1px ghost borders (`#334155`) against the deep slate background.
- **State Changes:** Hierarchy and interactivity are communicated purely through color shifts (e.g., swapping border or fill colors to the accent orange `#F97316`) rather than drop shadows or tonal elevation lifts.

## Components

All components adhere strictly to the flat, shadowless, dark minimal narrative.

- **Buttons:** Solid accent orange (`#F97316`) for primary calls-to-action with high-contrast text. Secondary buttons feature transparent fills with a 1px neutral outline and hover/active color inversion.
- **Input Fields & Puzzle Tiles:** Square or slightly rounded containers featuring a flat neutral surface and thin border. Active input slots display an accent orange border.
- **Virtual Keyboard:** Flat grid keys mirroring the puzzle tile shapes, optimized for thumb ergonomics with instant tactile color feedback on press.
- **Chips & Tags:** Used for category indicators or streak counters, utilizing muted slate backgrounds and subtle text.
- **Checkboxes & Toggles:** Minimalist switch tracks with flat geometric thumbs.
- **Cards:** Flat panel containers used for daily stats, definitions, and results summaries, bordered cleanly with 1px neutral strokes.
- **Additional Components:** Toast notifications for puzzle hints, modal dialogs for daily completion stats, and progress dot indicators for multi-stage word chains.