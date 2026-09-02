#!/usr/bin/env python3
"""Import the Research Radar artifact into Hugo posts.

The radar lives as a single continuously-updated Claude artifact that keeps
every past edition inside itself as an accordion section. This splits it back
apart: one Hugo post per issue under content/post/<date>-radar/, holding the
artifact's own markup so layouts/post/radar.html can render it in the
artifact's design.

Usage:
    python scripts/import_radar.py <artifact.html> [<older-export.html> ...]

Sources are applied in order, so put the freshest export last -- it wins for
any date the earlier ones also contain. Dates not present in a source are
left alone, so old issues the artifact has since dropped stay published.

The artifact is behind a claude.ai login, so it can't be curl'd; fetch it
with Claude Code's WebFetch (which writes the full HTML to a local file) and
pass that file here. See .claude/commands/daily-radar.md.
"""
import html
import os
import re
import sys

OUT = 'content/post'
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


def write_issue(date, label, body, summary):
    d = os.path.join(OUT, '%s-radar' % date)
    os.makedirs(d, exist_ok=True)
    page = '\n'.join([
        '---',
        'title: "%s — %s"' % (TITLE, label),
        'date: %sT07:30:00+09:00' % date,
        'draft: false',
        'issue_label: "%s"' % label,
        'summary: "%s"' % summary,
        'tags: ["Daily", "Research Radar"]',
        'layout: radar',
        '---',
        '',
    ]) + body + '\n'

    path = os.path.join(d, 'index.html')
    if os.path.exists(path) and open(path, encoding='utf-8').read() == page:
        return False
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page)
    return True


def import_source(path):
    src = open(path, encoding='utf-8').read()
    stats = issue_stats(src)
    written = []
    for date, block in ISSUE_RE.findall(src):
        m = re.search(r'<span class="issue__date">([^<]*)</span>', block)
        label = html.unescape(m.group(1)) if m else date
        body = re.search(r'<div class="issue__body">(.*)\s*$', block, re.S).group(1).strip()
        if write_issue(date, label, body, stats.get(date, '')):
            written.append(date)
    return sorted(ISSUE_RE.findall(src) and [d for d, _ in ISSUE_RE.findall(src)]), written


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
