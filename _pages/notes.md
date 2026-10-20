---
layout: page
permalink: /notes/
title: notes
description: Short notes on research questions I keep coming back to.
nav: true
nav_order: 4
---

{% assign notes = site.categories.notes %}
<ul class="post-list">
  {% for post in notes %}
    <li>
      <h3><a class="post-title" href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
      {% if post.description %}<p>{{ post.description }}</p>{% endif %}
      <p class="post-meta">{{ post.date | date: '%B %d, %Y' }}</p>
    </li>
  {% endfor %}
</ul>
