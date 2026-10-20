#!/usr/bin/env python3
"""Import the Research Radar artifact into Jekyll posts.

The radar lives as a single continuously-updated Claude artifact that keeps
every past edition inside itself as an accordion section. This splits it back
apart: one post per issue at _posts/<date>-radar.html, holding the artifact's
own markup so _layouts/radar.liquid can render it in the artifact's design.

Usage:
    python3 scripts/import_radar.py <artifact.html> [<older-export.html> ...]

Sources are applied in order, so put the freshest export last -- it wins for
any date the earlier ones also contain. Dates not present in a source are
left alone, so old issues the artifact has since dropped stay published.

The artifact is behind a claude.ai login, so it can't be curl'd; read it with
Claude Code's Artifact tool (action: read), which saves the full HTML to a
local file, and pass that file here. See .claude/commands/daily-radar.md.
"""
import html
import json
import os
import re
import sys

OUT = '_posts'
TITLE = '리서치 레이더'

# The Korean edition's issues. Newer artifacts prefix the language
# (issue-ko-2026-09-02); the first exports did not (issue-2026-08-18).
ISSUE_RE = re.compile(
    r'<details class="issue" id="issue-(?:ko-)?(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</details>',
    re.S)
STRIP_RE = re.compile(
    r'<a class="strip__row" href="#issue-(?:ko-)?(\d{4}-\d{2}-\d{2})">(.*?)</a>', re.S)
CHIP_RE = re.compile(
    r'<span class="chip__k">([^<]*)</span><span class="chip__v">([^<]*)</span>')


def issue_stats(src):
    """Per-date counts from the artifact's own back-issue strip."""
    stats = {}
    for date, frag in STRIP_RE.findall(src):
        bits = re.findall(r'<span class="mini[^"]*">([^<]*)</span>', frag)
        bits += ['%s %s' % p for p in CHIP_RE.findall(frag)]
        stats[date] = ' · '.join(html.unescape(b) for b in bits)
    return stats


def write_issue(date, label, body, summary, out=OUT):
    """Write one issue; return True if the file changed."""
    os.makedirs(out, exist_ok=True)
    q = lambda s: json.dumps(s, ensure_ascii=False)  # JSON strings are valid YAML
    page = '\n'.join([
        '---',
        'layout: radar',
        'title: %s' % q('%s — %s' % (TITLE, label)),
        'date: %s 07:30:00 +0900' % date,
        'description: %s' % q(summary),
        'categories: [daily]',
        'tags: [research-radar]',
        # keep the old site's URLs so existing links still work
        'permalink: /post/%s-radar/' % date,
        'render_with_liquid: false',
        'related_posts: false',
        '---',
        '',
    ]) + body.strip() + '\n'

    path = os.path.join(out, '%s-radar.html' % date)
    if os.path.exists(path) and open(path, encoding='utf-8').read() == page:
        return False
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page)
    return True


def import_source(path):
    src = open(path, encoding='utf-8').read()
    stats = issue_stats(src)
    found, written = [], []
    for date, block in ISSUE_RE.findall(src):
        found.append(date)
        m = re.search(r'<span class="issue__date">([^<]*)</span>', block)
        label = html.unescape(m.group(1)) if m else date
        body = re.search(r'<div class="issue__body">(.*)\s*$', block, re.S).group(1)
        # the block ends with the issue__body's own closing </div>
        body = re.sub(r'</div>\s*$', '', body.strip())
        if write_issue(date, label, body, stats.get(date, '')):
            written.append(date)
    return found, written


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    seen, changed = [], []
    for path in argv[1:]:
        found, written = import_source(path)
        seen += found
        changed += written
    print('issues found: %d' % len(set(seen)))
    if changed:
        print('written: %s' % ', '.join(sorted(set(changed))))
    else:
        print('written: none (already up to date)')


if __name__ == '__main__':
    main(sys.argv)
