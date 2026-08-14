# ReMEMBER 9:20 viewport fit design

## Goal

Fit the complete ReMEMBER animation inside one 9:20 portrait viewport without internal scrolling, clipping, or changes to its narrative sequence.

## Layout

- Keep the existing single-column order: header, chat window, unresolved gaps, history archive, and final summary.
- Set the publication iframe container to an exact `9 / 20` aspect ratio.
- Let the animation stage fill the iframe viewport at `100%` width and height.
- Allocate bounded grid rows to each panel and use responsive spacing and typography so every panel remains visible at the 380px-wide publication cap and narrower mobile widths.
- Preserve all current messages, gap labels, evidence cards, and summary text.

## Behavior

- Preserve the 22-second phase sequence, click-to-pause behavior, hash-based phase jump, and reduced-motion final frame.
- Keep vertical query movement aligned with the portrait layout.
- Do not add page-level or iframe-level scrolling.

## Files

- `static/uploads/research/remember-loop.html`: compact the internal portrait layout.
- `assets/css/custom.css`: retain the `9 / 20` publication animation container and remove constraints that distort the ratio.
- `scripts/verify_publications.py`: assert the 9:20 container and full-viewport animation contract.

## Verification

- Run the animation contract test and the publication-page verification test.
- Build the Hugo site.
- Render the animation at 380x844 and a narrower mobile width, then confirm no element exceeds the viewport and the final summary remains readable.

## Scope boundary

This change does not alter publication metadata, animation copy, phase timing, colors, or unrelated site motion.
