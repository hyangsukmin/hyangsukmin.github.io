# Unified Research and Publications Page Design

## Goal

Merge the current Research and Publications pages into one chronological Publications page that combines complete publication metadata with paper-specific visual explanations.

## Scope

- Use `/publication/` as the canonical page.
- Show eight unique papers after deduplicating the existing Research and Publications entries. The anonymous CHI submission is omitted entirely (see below).
- Remove the Research item from the main navigation.
- Preserve `/research/` and `/publications/` as redirects to `/publication/`.
- Keep the existing Daily Update, Bio, and Experience pages unchanged.

## Page Structure

The page keeps the current Publications page's year-grouped reading order. Each year has a divider followed by publication entries in reverse chronological order.

The anonymous CHI submission is not represented on the page at all — no title, badges, description, or keywords. It stays unpublished until it has a public identity.

Each publication entry contains:

1. Venue and topic badges.
2. Paper title.
3. Full author list.
4. Venue and year.
5. One sentence stating the paper's central contribution.
6. Three to five keyword chips.
7. A paper link when a public paper URL exists.

The one-sentence descriptions and keywords must be grounded in each paper's abstract and method, not inferred from the title alone.

## Publication Set

### 2026

- **Completing Missing Annotation: Multi-Agent Debate for Accurate and Scalable Relevant Assessment for IR Benchmarks**
  - Visual: the paper's main framework or pipeline figure.
  - Public link: OpenReview PDF.
- **Don't Scroll Back: Missing-Evidence Memory for Streaming Dialogue Summarization**
  - Visual: the existing interactive ReMEMBER animation at `/uploads/research/remember-loop.html`, embedded at 20:9 in the visual column.
  - Public link: arXiv.

### 2025

- **Towards a Holistic and Automated Evaluation Framework for Multi-Level Comprehension of LLMs in Book-Length Contexts**
  - Visual: the paper's main framework or benchmark overview figure.
- **ReFeed: Multi-Dimensional Summarization Refinement with Reflective Reasoning on Feedback**
  - Visual: the paper's main method or refinement-loop figure.
- **Towards Multi-dimensional Evaluation of LLM Summarization across Domains and Languages**
  - Visual: the paper's main evaluation framework or benchmark overview figure.

### 2023

- **Temporal Convolutional Network-based Time-Series Segmentation**
  - Visual: the principal model architecture or segmentation pipeline figure.

### 2022

- **Covid-EENet: Predicting Fine-Grained Impact of COVID-19 on Local Economies**
  - Visual: the principal model architecture or forecasting pipeline figure.

### 2020

- **Hi-COVIDNet: Deep Learning Approach to Predict Inbound COVID-19 Patients and Case Study in South Korea**
  - Visual: the principal model architecture or end-to-end framework figure.

## Entry Layout

### Static-figure entries

Each entry is a single stacked column, capped at 380px wide and centered:

- Top: a bounded figure panel.
- Below: publication metadata, one-line explanation, keywords, and links (full entry width).

Figures use `object-fit: contain` so labels and axes are not cropped. A short caption identifies the source figure. The original figure aspect ratio is preserved inside a neutral panel.

### ReMEMBER entry

ReMEMBER uses a 20:9 landscape animation above its metadata. Its three-column internal layout shows chat, unresolved gaps, and retrieved history side by side, with the final summary below the two right columns. The animation may expand to 800px wide and must fit its complete narrative without internal scrolling or clipped panels.

### Responsive behavior

Keyword chips wrap naturally. The stacked figure/animation-then-metadata order already matches the mobile layout, so no column reflow is needed at narrower widths.

## Name Emphasis

Every occurrence of `Hyangsuk Min` in an author list remains bold and receives a green highlight. The style uses a light green background and dark green foreground with sufficient contrast in both light and dark themes. Highlighting is limited to the name and does not extend to punctuation or co-first-author braces.

## Visual and Content Rules

- Extract figures from public or locally supplied paper PDFs at readable resolution.
- Do not publish source PDFs stored under `assets/papers/`.
- Do not add the CHI entry, its figure, or the generated CHI animation.
- Do not use paper first pages as final visuals when a meaningful framework or architecture figure is available.
- Use descriptive `alt` text for each static figure.
- Give the ReMEMBER iframe a descriptive `title` and lazy loading.
- Keep venue and topic badges consistent with the current Publications color system.
- Use English for descriptions and keywords to match the existing page.
- Keep each core description to one sentence and each keyword to a short noun phrase.

## Implementation Structure

- `content/publication/_index.md` becomes the single source for the nine publication entries.
- `config/_default/menus.yaml` removes the Research navigation item.
- `assets/scss/custom.scss` defines reusable publication-entry, figure, keyword, and author-highlight classes, including responsive and dark-theme behavior.
- `static/uploads/publications/` stores extracted public figure assets.
- `content/research/_index.md` and `content/publications/_index.md` are removed after their routes are represented as aliases on the canonical Publications page.
- Existing untracked animations for MSumBench and Completing Missing Annotation remain outside the merged page and are not added by this feature. The untracked CHI animation is orphaned entirely, since the CHI entry itself is omitted.

## Error and Fallback Behavior

- If an official PDF cannot be retrieved, use another public author- or venue-hosted copy of the same paper.
- If a paper has multiple candidate figures, choose the figure that best explains the method or evaluation pipeline without requiring surrounding paper text.
- If no usable explanatory figure exists, use a clearly labeled results or architecture figure rather than a first-page screenshot.
- Broken or unavailable public paper links must not be added.

## Verification

- Build the full Hugo site without warnings or errors.
- Confirm `/publication/` renders eight unique entries in the intended year groups, with no CHI entry present.
- Confirm `/research/` and `/publications/` redirect to `/publication/`.
- Confirm the main navigation contains Publications but not Research.
- Confirm seven static figure entries and one ReMEMBER animation entry.
- Confirm all eight author-list occurrences of `Hyangsuk Min` are bold and green-highlighted.
- Confirm every entry has one core-description sentence and three to five keyword chips.
- Confirm figure assets load locally, preserve aspect ratios, and have descriptive alternative text.
- Confirm the ReMEMBER iframe loads and remains readable on desktop and mobile layouts.
- Confirm no files under `assets/papers/` become tracked.

## Risk Boundary

The CHI submission is not represented on the public site at all — no title, badges, description, keywords, figure, animation, PDF, or link. This avoids any disclosure of the anonymous submission until it has a public identity.
