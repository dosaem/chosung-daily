## Brand & Style

This design system establishes an editorial, calm, and intellectually engaging environment tailored for a daily Korean word puzzle game. Inspired by premier journalistic word games, the aesthetic prioritizes extreme clarity, literary elegance, and focus. 

### Brand Personality & Audience
- **Target Audience:** Language learners, puzzle enthusiasts, and daily gamers seeking a refined intellectual ritual.
- **Personality:** Intellectual, understated, refined, and approachable.
- **Emotional Response:** Calm focus, intellectual satisfaction, and quiet accomplishment.

### Design Style
The design style is rooted in a refined Editorial Minimalism characterized by high-contrast typography, generous whitespace, strict grid alignment, and a complete absence of shadows or gradients. Structure is communicated purely through crisp hairline dividers and precise typographic hierarchy.

## Layout & Spacing

The layout employs a fixed-width centered container philosophy on desktop, transitioning to a fluid layout with generous outer margins on mobile devices. This ensures the central puzzle board remains anchored and easy to focus on.

### Rhythm & Structure
- Vertical rhythm is maintained through a strict 8px baseline grid.
- Structural separation relies exclusively on 1px hairline borders (`#E7E5E4`) rather than tonal container stacking.
- Generous whitespace (`space-xl`) surrounds the primary puzzle grid to eliminate visual clutter and emphasize the contemplative nature of the game.

## Elevation & Depth

Depth is treated with absolute flatness. Shadows, blurs, and gradient fills are strictly prohibited. 

### Structural Hierarchy
- Visual hierarchy is established entirely through typographic scale, density, and crisp hairline outlines (`#E7E5E4`).
- Interactive layering relies on hard border color shifts from neutral gray to near-black or warm orange, maintaining a clean, print-like graphic quality.

## Components

### Buttons
- **Primary:** Near-black background (`#0F172A`) with white text, square or softly rounded corners (`0.25rem`), zero shadow. Hover states invert or subtly deepen the tone.
- **Secondary / Ghost:** Transparent background with a 1px hairline border (`#E7E5E4`) and near-black text.

### Puzzle Tiles (Wordle-style)
- **Default / Empty:** Light gray background (`#F5F5F4`) with a 1px border.
- **Correct State:** Solid green (`#16A34A`) background with crisp white text.
- **Incorrect State:** Muted gray-stone (`#D6D3D1`) background with near-black text.
- **Active Input:** Highlighted with a warm orange (`#EA580C`) thin border.

### Chips & Tabs
- Inactive tabs feature muted gray text with generous padding. Active tabs are anchored by a 2px warm orange (`#EA580C`) bottom underline.

### Input Fields & Keyboards
- On-screen game keyboards use flat light-gray keys with high-contrast character labels. Key presses trigger immediate flat color transitions.
- Checkboxes and radio options use crisp square outlines with solid fill indicators upon selection.

### Additional Components
- **Streak Counter:** A minimalist numeric display paired with a warm orange flame or marker icon.
- **Editorial Modal:** Clean off-white pop-ups framed by a 1px hairline border, housing game summaries and share options.