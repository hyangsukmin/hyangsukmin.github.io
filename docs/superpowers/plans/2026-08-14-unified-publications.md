# Unified Publications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the separate Research and Publications pages with one visually rich, chronological Publications page containing eight papers, seven extracted paper figures, one ReMEMBER animation, one-line explanations, keyword chips, and highlighted author-name occurrences. The anonymous CHI submission is omitted entirely.

**Architecture:** Keep `/publication/` as the canonical Hugo content page and express each paper as semantic raw HTML inside the Markdown page. Put reusable responsive styling in `assets/scss/custom.scss`, extracted figure assets in `static/uploads/publications/`, and route compatibility in Hugo aliases. A rendered-site validator exercises Hugo's actual output before and after implementation, followed by screenshot inspection.

**Tech Stack:** Hugo 0.152.2, Hugo Blox, SCSS, semantic HTML, Python 3 standard library, PyMuPDF, Pillow.

## Global Constraints

- Canonical route is `/publication/`; `/research/` and `/publications/` redirect there.
- Show eight unique entries grouped by 2026, 2025, 2023, 2022, and 2020.
- Use seven paper figures and the existing ReMEMBER animation.
- Never track or publish the source PDFs under `assets/papers/` or `tmp/pdfs/`.
- Use English one-sentence descriptions and three to five English keyword chips per entry.
- Keep `Hyangsuk Min` bold and green-highlighted wherever the author list contains the name.
- Omit the CHI entry entirely (title, badges, author line, figure, animation, PDF, and paper link) while the submission remains anonymous.
- Preserve unrelated untracked animation files without adding or deleting them.

---

### Task 1: Add a failing rendered-site validator

**Files:**
- Create: `scripts/verify_publications.py`
- Test: `scripts/verify_publications.py`

**Interfaces:**
- Consumes: `public/publication/index.html`, `public/research/index.html`, `public/publications/index.html`, `static/uploads/publications/`.
- Produces: exit code `0` and `publications verification passed` only when the merged page satisfies the structural contract.

- [ ] **Step 1: Write the rendered-site validator**

Create a Python script that checks:

```python
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
page = (ROOT / "public/publication/index.html").read_text()
research_redirect = (ROOT / "public/research/index.html").read_text()
publications_redirect = (ROOT / "public/publications/index.html").read_text()

entries = re.findall(r'<article class="publication-entry[^>]*>.*?</article>', page, re.S)
assert len(entries) == 8, f"expected 8 entries, found {len(entries)}"
assert page.count('class="publication-figure"') == 7
assert page.count('class="publication-animation"') == 1
assert page.count('class="publication-entry publication-entry--text-only"') == 0
assert page.count('class="publication-summary"') == 8
assert page.count('class="author-highlight"') == 8
assert '/uploads/research/remember-loop.html' in page
assert 'href="/publication/"' in page
assert 'href="/research/"' not in page
assert 'url=/publication/' in research_redirect.lower()
assert 'url=/publication/' in publications_redirect.lower()

for index, entry in enumerate(entries, start=1):
    keywords = re.findall(r'class="publication-keyword"', entry)
    assert 3 <= len(keywords) <= 5, f"entry {index} has {len(keywords)} keywords"

for name in (
    "dream.png",
    "hamlet.png",
    "refeed.png",
    "msumbench.png",
    "tcts.png",
    "covid-eenet.png",
    "hi-covidnet.png",
):
    assert (ROOT / "static/uploads/publications" / name).is_file(), name

print("publications verification passed")
```

- [ ] **Step 2: Build the current site and run the validator to confirm RED**

Run: `hugo --minify && python3 scripts/verify_publications.py`

Expected: failure containing `expected 8 entries, found 0` because Hugo's current canonical page still renders the legacy markup.

- [ ] **Step 3: Commit the validator with the feature implementation, not separately**

The validator remains uncommitted until the production page passes it, avoiding a standalone commit that intentionally fails the repository check.

---

### Task 2: Extract and verify seven paper figures

**Files:**
- Create: `static/uploads/publications/dream.png`
- Create: `static/uploads/publications/hamlet.png`
- Create: `static/uploads/publications/refeed.png`
- Create: `static/uploads/publications/msumbench.png`
- Create: `static/uploads/publications/tcts.png`
- Create: `static/uploads/publications/covid-eenet.png`
- Create: `static/uploads/publications/hi-covidnet.png`

**Interfaces:**
- Consumes: the seven source PDFs and the page-index/clip rectangles below.
- Produces: sharp PNG crops with no surrounding paper body text.

- [ ] **Step 1: Extract figures at 3x resolution**

Use PyMuPDF with these zero-based pages and point-space crop rectangles:

```python
JOBS = {
    "dream.png": ("assets/papers/10455_Completing_Missing_Annot (5).pdf", 1, (105, 58, 505, 190)),
    "msumbench.png": ("assets/papers/2025.acl-long.702 (3).pdf", 1, (70, 72, 530, 175)),
    "hamlet.png": ("tmp/pdfs/hamlet.pdf", 1, (72, 70, 528, 195)),
    "refeed.png": ("tmp/pdfs/refeed.pdf", 1, (108, 75, 510, 232)),
    "tcts.png": ("tmp/pdfs/tcts.pdf", 3, (60, 65, 305, 185)),
    "covid-eenet.png": ("tmp/pdfs/covid-eenet.pdf", 4, (60, 45, 300, 224)),
    "hi-covidnet.png": ("tmp/pdfs/hi-covidnet.pdf", 2, (52, 58, 560, 310)),
}
```

For each job, call `page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=fitz.Rect(*rect), alpha=False)` and save into `static/uploads/publications/`.

- [ ] **Step 2: Inspect every crop visually**

Open all seven PNG files and confirm the complete diagram is visible, labels are not clipped, paper body paragraphs are excluded, and the crop is legible when scaled to a 320 px-wide panel.

- [ ] **Step 3: Confirm source PDFs remain untracked**

Run: `git status --short assets/papers tmp/pdfs`

Expected: no tracked or staged PDF paths.

---

### Task 3: Implement the merged page and responsive styles

**Files:**
- Modify: `content/publication/_index.md`
- Modify: `assets/scss/custom.scss`
- Modify: `config/_default/menus.yaml`
- Modify: `config/_default/hugo.yaml`
- Delete: `content/research/_index.md`
- Delete: `content/publications/_index.md`
- Move: `content/publications/paper1/` to `content/publication/paper1/`
- Modify: `docs/superpowers/specs/2026-08-14-unified-publications-design.md`
- Test: `scripts/verify_publications.py` against Hugo-generated output

**Interfaces:**
- Consumes: the seven PNG assets and `/uploads/research/remember-loop.html`.
- Produces: canonical `/publication/`, aliases, responsive entries, green author highlighting, keyword chips, and a readable ReMEMBER iframe.

- [ ] **Step 1: Amend the design spec for anonymous CHI handling**

State that full authors are shown for eight public papers, CHI omits the author line, and the expected author-highlight count is eight.

- [ ] **Step 2: Replace the canonical page content**

Add front matter aliases:

```yaml
aliases:
  - /research/
  - /publications/
```

Use one `<article class="publication-entry">` per paper, `publication-entry--text-only` for CHI, `publication-figure` for seven figures, `publication-animation` for the ReMEMBER iframe, `publication-summary` for every one-line explanation, `publication-keywords` around keyword chips, and `author-highlight` around each public occurrence of the owner's name.

Use the following grounded descriptions and keywords:

1. **DREAM** - "Uses adversarial multi-agent debate to fill missing relevance judgments in IR benchmarks, auto-labeling agreement cases and escalating only disagreements to human annotators." Keywords: Information Retrieval; Missing Relevance Judgments; Multi-Agent Debate; Human-in-the-Loop; Benchmark Refinement.
2. **ReMEMBER** - "Retrieves evidence for unresolved window dependencies and refines it into evidence-dense memory for streaming dialogue summarization under a fixed budget." Keywords: Streaming Summarization; Long-Context Dialogue; Missing Evidence; Memory Construction; Retrieval.
3. **HAMLET** - "Builds a hierarchical key-fact evaluation pipeline that probes recall and faithfulness at multiple abstraction levels in book-length contexts." Keywords: Long-Context Evaluation; Book-Length Comprehension; Key-Fact Hierarchy; Query-Focused Summarization; Faithfulness.
4. **ReFeed** - "Refines summaries across faithfulness, completeness, and conciseness by using reflective reasoning to reconcile multi-dimensional feedback and resist order and noise effects." Keywords: Summary Refinement; Reflective Reasoning; Multi-Dimensional Feedback; Long Chain-of-Thought; Feedback Robustness.
5. **MSumBench** - "Benchmarks summarization across six domains and two languages with domain-specific key facts and multi-agent-assisted human judgments of faithfulness, completeness, and conciseness." Keywords: Summarization Evaluation; Multi-Domain Benchmark; Multilingual NLP; Multi-Agent Debate; Human Evaluation.
6. **TCTS** - "Jointly learns multi-scale temporal patterns with a temporal convolutional network and cluster-separable representations for unsupervised time-series segmentation." Keywords: Time-Series Segmentation; Temporal Convolutional Network; Temporal Clustering; Unsupervised Learning.
7. **COVID-EENet** - "Models how concurrent infection events affect district- and business-level sales using microscopic multi-view encoders and a macroscopic gated aggregator." Keywords: Economic Impact Forecasting; COVID-19; Multi-View Learning; Fine-Grained Prediction; Credit Card Data.
8. **Hi-COVIDNet** - "Predicts imported COVID-19 cases with country- and continent-level encoders that combine epidemic signals with international inflow patterns." Keywords: Epidemic Forecasting; Hierarchical Modeling; Imported Cases; Transformer; LSTM.

- [ ] **Step 3: Add component styles**

Add SCSS classes for:

- `.publication-year`, `.publication-entry`, `.publication-entry__visual`, `.publication-entry__content`.
- `.publication-figure`, `.publication-figure img`, `.publication-figure figcaption` with `object-fit: contain` and neutral surfaces.
- `.publication-animation` with `aspect-ratio: 16 / 9` and a full-size iframe.
- `.publication-summary`, `.publication-keywords`, `.publication-keyword`.
- `.author-highlight` with bold text, light green background, dark green foreground, small inline padding, and rounded corners.
- Dark-theme overrides under both `.dark` and `@media (prefers-color-scheme: dark)`.
- A mobile breakpoint at `760px` that stacks the figure above metadata and removes fixed visual width.

- [ ] **Step 4: Consolidate routes and navigation**

Remove the Research menu entry from `config/_default/menus.yaml` and set `disableAliases: false` in `config/_default/hugo.yaml`, then delete the two obsolete index files. Move the tracked `paper1` page bundle from the plural section to `content/publication/paper1/` and give it the alias `/publications/paper1/`; this preserves the detail page while allowing Hugo to generate the root `/publications/` alias from the canonical page.

- [ ] **Step 5: Rebuild, run the validator, and confirm GREEN**

Run: `hugo --minify && python3 scripts/verify_publications.py`

Expected: `publications verification passed`.

---

### Task 4: Build and visually verify the site

**Files:**
- Verify: `public/publication/index.html`
- Verify: `public/research/index.html`
- Verify: `public/publications/index.html`

**Interfaces:**
- Consumes: all implementation files from Tasks 1-3.
- Produces: a warning-free Hugo build and a visually checked Publications page.

- [ ] **Step 1: Build the site**

Run: `hugo --minify` with Hugo 0.152.2. If Hugo is not installed, use a temporary verified Hugo 0.152.2 binary outside the repository.

Expected: exit code `0` with no template, asset, or missing-resource errors.

- [ ] **Step 2: Verify generated routes and structure**

Confirm the canonical output contains eight entries (no CHI entry), all seven figure URLs, the ReMEMBER iframe, eight author highlights, eight summaries, and thirty-nine keyword chips. Confirm both alias pages target `/publication/`.

- [ ] **Step 3: Render desktop and mobile screenshots**

Serve the generated site locally, capture `/publication/` at desktop and mobile widths, and inspect both screenshots for clipped figures, unreadable labels, broken iframe layout, keyword overflow, and name-highlight contrast.

- [ ] **Step 4: Re-run all checks**

Run:

```bash
python3 scripts/verify_publications.py
hugo --minify
git diff --check
git status --short
```

Expected: validator pass, Hugo build pass, no whitespace errors, and only intended feature files plus the preserved unrelated untracked animations.

---

### Task 5: Commit the implementation

**Files:**
- Commit all intended files from Tasks 1-4.

**Interfaces:**
- Consumes: verified implementation.
- Produces: one implementation commit without source PDFs or unrelated animations.

- [ ] **Step 1: Stage only intended files**

Stage the canonical page, menu, SCSS, validator, seven PNG figures, obsolete-page deletions, amended spec, and this plan.

- [ ] **Step 2: Inspect the staged diff**

Run: `git diff --cached --check`, `git diff --cached --stat`, and `git status --short`.

Expected: no `assets/papers/`, `tmp/pdfs/`, or untracked animation HTML files are staged.

- [ ] **Step 3: Commit**

Run: `git commit -m "feat: unify research and publications"`.
