# ReMEMBER 20:9 viewport fit design

## Goal

Fit the complete ReMEMBER animation inside one 20:9 landscape viewport without internal scrolling, clipping, or changes to its narrative sequence.

## Layout

- Use a three-column narrative: chat on the left, unresolved gaps in the center, and history evidence on the right.
- Place the final summary below the center and right columns while the chat spans both content rows.
- Set the publication iframe container to an exact `20 / 9` aspect ratio and allow the animation entry to expand to 800px wide.
- Let the animation stage fill the iframe viewport at `100%` width and height.
- Preserve all current messages, gap labels, evidence cards, and summary text.

## Behavior

- Preserve the 22-second phase sequence, click-to-pause behavior, hash-based phase jump, and reduced-motion final frame.
- Move gap queries horizontally from the center column toward the history archive.
- Do not add page-level or iframe-level scrolling.

## Verification

- Run the browser layout contract at 800x360 and 700x315.
- Confirm the publication wrapper renders at 20:9 and is not capped at the static-figure width.
- Capture and inspect the 800x360 final frame.

## Scope boundary

This change does not alter publication metadata, animation copy, phase timing, colors, or unrelated site motion.
