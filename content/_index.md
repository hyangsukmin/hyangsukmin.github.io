---
# Leave the homepage title empty to use the site title
title: ''
date: 2022-10-24
type: landing

design:
  # Default section spacing
  spacing: '6rem'

sections:
  - block: resume-biography-3
    content:
      # Choose a user profile to display (a folder name within `content/authors/`)
      username: me
      text: ''
      # Show a call-to-action button under your biography? (optional)
      button:
        text: Download CV
        url: uploads/resume.pdf
      headings:
        about: ''
        education: ''
        interests: ''
    design:
      # Use the new Gradient Mesh which automatically adapts to the selected theme colors
      background:
        gradient_mesh:
          enable: true

      # Name heading sizing to accommodate long or short names
      name:
        size: md # Options: xs, sm, md, lg (default), xl

      # Avatar customization
      avatar:
        size: large # Options: small (150px), medium (200px, default), large (320px), xl (400px), xxl (500px)
        shape: circle # Options: circle (default), square, rounded
  - block: markdown
    content:
      title: ''
      subtitle: ''
      text: |-
        <div class="home-publications">
          <div class="home-publications__header">
            <h2>Publications</h2>
            <a href="/publication/" class="home-publications__more">More →</a>
          </div>
          <div class="home-publications__list">
            <article class="home-pub-entry">
              <div class="publication-badges">
                <span class="publication-badge publication-badge--orange">ICLR 2026</span>
                <span class="publication-badge publication-badge--magenta">NLP</span>
              </div>
              <h3><a href="/publication/#dream">Completing Missing Annotation: Multi-Agent Debate for Accurate and Scalable Relevant Assessment for IR Benchmarks</a></h3>
              <p class="publication-venue">International Conference on Learning Representations, 2026</p>
              <p class="publication-summary"><strong>Core idea.</strong> Uses adversarial multi-agent debate to fill missing relevance judgments in IR benchmarks, auto-labeling agreement cases and escalating only disagreements to human annotators.</p>
            </article>
            <article class="home-pub-entry">
              <div class="publication-badges">
                <span class="publication-badge publication-badge--gray">Under Review</span>
                <span class="publication-badge publication-badge--magenta">NLP</span>
              </div>
              <h3><a href="/publication/#remember">Don't Scroll Back: Missing-Evidence Memory for Streaming Dialogue Summarization</a></h3>
              <p class="publication-venue">Preprint, 2026</p>
              <p class="publication-summary"><strong>Core idea.</strong> Retrieves evidence for unresolved window dependencies and refines it into evidence-dense memory for streaming dialogue summarization under a fixed budget.</p>
            </article>
            <article class="home-pub-entry">
              <div class="publication-badges">
                <span class="publication-badge publication-badge--green">EMNLP 2025</span>
                <span class="publication-badge publication-badge--magenta">NLP</span>
              </div>
              <h3><a href="/publication/#hamlet">Towards a Holistic and Automated Evaluation Framework for Multi-Level Comprehension of LLMs in Book-Length Contexts</a></h3>
              <p class="publication-venue">International Conference on Empirical Methods in Natural Language Processing (Main), 2025</p>
              <p class="publication-summary"><strong>Core idea.</strong> Builds a hierarchical key-fact evaluation pipeline that probes recall and faithfulness at multiple abstraction levels in book-length contexts.</p>
            </article>
            <article class="home-pub-entry">
              <div class="publication-badges">
                <span class="publication-badge publication-badge--green">COLM 2025</span>
                <span class="publication-badge publication-badge--magenta">NLP</span>
              </div>
              <h3><a href="/publication/#refeed">ReFeed: Multi-Dimensional Summarization Refinement with Reflective Reasoning on Feedback</a></h3>
              <p class="publication-venue">Conference on Language Modeling, 2025</p>
              <p class="publication-summary"><strong>Core idea.</strong> Refines summaries across faithfulness, completeness, and conciseness by using reflective reasoning to reconcile multi-dimensional feedback and resist order and noise effects.</p>
            </article>
            <article class="home-pub-entry">
              <div class="publication-badges">
                <span class="publication-badge publication-badge--green">ACL 2025</span>
                <span class="publication-badge publication-badge--magenta">NLP</span>
              </div>
              <h3><a href="/publication/#msumbench">Towards Multi-dimensional Evaluation of LLM Summarization across Domains and Languages</a></h3>
              <p class="publication-venue">Annual Meeting of the Association for Computational Linguistics (Main), 2025</p>
              <p class="publication-summary"><strong>Core idea.</strong> Benchmarks summarization across six domains and two languages with domain-specific key facts and multi-agent-assisted human judgments of faithfulness, completeness, and conciseness.</p>
            </article>
          </div>
        </div>
    design:
      columns: '1'
  # - block: markdown
  #   content:
  #     title: '📚 My Research'
  #     subtitle: ''
  #     text: |-
  #       Use this area to speak to your mission. I'm a research scientist in the Moonshot team at DeepMind. I blog about machine learning, deep learning, and moonshots.

  #       I apply a range of qualitative and quantitative methods to comprehensively investigate the role of science and technology in the economy.

  #       Please reach out to collaborate 😃
  #   design:
  #     columns: '1'
  # - block: collection
  #   id: papers
  #   content:
  #     title: Featured Publications
  #     filters:
  #       folders:
  #         - publications
  #       featured_only: true
  #   design:
  #     view: article-grid
  #     columns: 1
  # - block: collection
  #   content:
  #     title: Recent Publications
  #     text: ''
  #     filters:
  #       folders:
  #         - publications
  #       exclude_featured: false
  #   design:
  #     view: citation
  # - block: collection
  #   id: experiences
  #   content:
  #     title: Experiences
  #     filters:
  #       folders:
  #         - experiences
  #   design:
  #     view: card
  # - block: collection
  #   id: news
  #   content:
  #     title: Recent News
  #     subtitle: ''
  #     text: ''
  #     # Page type to display. E.g. post, talk, publication...
  #     page_type: blog
  #     # Choose how many pages you would like to display (0 = all pages)
  #     count: 10
  #     # Filter on criteria
  #     filters:
  #       author: ''
  #       category: ''
  #       tag: ''
  #       exclude_featured: false
  #       exclude_future: false
  #       exclude_past: false
  #       publication_type: ''
  #     # Choose how many pages you would like to offset by
  #     offset: 0
  #     # Page order: descending (desc) or ascending (asc) date.
  #     order: desc
  #   design:
  #     # Choose a layout view
  #     view: card
  #     # Reduce spacing
  #     spacing:
  #       padding: [0, 0, 0, 0]
  # - block: cta-card
  #   demo: true # Only display this section in the Hugo Blox Builder demo site
  #   content:
  #     title: 👉 Build your own academic website like this
  #     text: |-
  #       This site is generated by Hugo Blox Builder - the FREE, Hugo-based open source website builder trusted by 250,000+ academics like you.

  #       <a class="github-button" href="https://github.com/HugoBlox/hugo-blox-builder" data-color-scheme="no-preference: light; light: light; dark: dark;" data-icon="octicon-star" data-size="large" data-show-count="true" aria-label="Star HugoBlox/hugo-blox-builder on GitHub">Star</a>

  #       Easily build anything with blocks - no-code required!

  #       From landing pages, second brains, and courses to academic resumés, conferences, and tech blogs.
  #     button:
  #       text: Get Started
  #       url: https://hugoblox.com/templates/
  #   design:
  #     card:
  #       # Card background color (CSS class)
  #       css_class: 'bg-primary-300 dark:bg-primary-700'
  #       css_style: ''
---
