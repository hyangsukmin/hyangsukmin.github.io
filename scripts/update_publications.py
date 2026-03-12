"""
Google Scholar → Hugo Blox Publications 자동 업데이트
scholarly로 논문 목록을 가져와 content/publication/ 에 마크다운으로 저장합니다.
"""

import os
import re
import time
from pathlib import Path
from datetime import datetime

# ════════════════════════════════════════════════════
# ✏️ [설정]
# ════════════════════════════════════════════════════
CONFIG = {
    "scholar_id": "U24LXHAAAAAJ",
    "output_dir": "content/publication",   # Hugo Blox publication 경로
    "min_year": 2018,                       # 이 연도 이전 논문은 제외
    "use_proxy": False,                     # 차단 시 True로 변경
}


# ════════════════════════════════════════════════════
# Scholar 크롤링
# ════════════════════════════════════════════════════

def fetch_publications(scholar_id: str) -> list:
    """Google Scholar에서 논문 목록 가져오기"""
    try:
        from scholarly import scholarly, ProxyGenerator

        if CONFIG["use_proxy"]:
            pg = ProxyGenerator()
            pg.FreeProxies()
            scholarly.use_proxy(pg)
            print("  🔀 프록시 사용 중...")

        print(f"  🔍 Scholar ID [{scholar_id}] 검색 중...")
        author = scholarly.search_author_id(scholar_id)
        scholarly.fill(author, sections=["publications"])

        papers = []
        total = len(author["publications"])

        for i, pub in enumerate(author["publications"], 1):
            try:
                print(f"  [{i}/{total}] 논문 정보 수집 중...")
                scholarly.fill(pub)
                bib = pub.get("bib", {})

                year = int(bib.get("pub_year", 0) or 0)
                if year < CONFIG["min_year"]:
                    continue

                papers.append({
                    "title":     bib.get("title", "Untitled"),
                    "authors":   bib.get("author", ""),
                    "year":      year,
                    "venue":     bib.get("venue", ""),
                    "abstract":  bib.get("abstract", ""),
                    "citations": pub.get("num_citations", 0),
                    "url":       pub.get("pub_url", ""),
                    "eprint":    bib.get("eprint", ""),   # arxiv ID 등
                })
                time.sleep(1)  # 차단 방지

            except Exception as e:
                print(f"  ⚠️ 논문 정보 수집 실패: {e}")
                continue

        papers.sort(key=lambda x: (x["year"], x["citations"]), reverse=True)
        print(f"  ✅ 총 {len(papers)}편 수집 완료")
        return papers

    except ImportError:
        print("❌ scholarly 미설치: pip install scholarly")
        return []
    except Exception as e:
        print(f"❌ Scholar 크롤링 실패: {e}")
        print("  💡 차단된 경우 CONFIG['use_proxy'] = True 로 변경하세요")
        return []


# ════════════════════════════════════════════════════
# Hugo 마크다운 생성
# ════════════════════════════════════════════════════

def slugify(title: str) -> str:
    """제목을 Hugo slug로 변환"""
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:80]  # 너무 길면 자름


def guess_pub_type(venue: str) -> str:
    """학술지/학회 구분"""
    venue_lower = venue.lower()
    conferences = ["conference", "workshop", "symposium", "proceedings",
                   "acl", "emnlp", "naacl", "neurips", "icml", "iclr",
                   "cvpr", "eccv", "aaai", "ijcai", "acl", "colm", "bigcomp"]
    if any(c in venue_lower for c in conferences):
        return "1"   # Conference paper
    if venue:
        return "2"   # Journal article
    return "3"       # Preprint


def make_publication_md(paper: dict) -> str:

    # ... 기존 코드 동일 ...

    # [Paper] 링크 결정: arxiv > url 순서
    paper_url = ""
    if arxiv_id:
        paper_url = f"https://arxiv.org/abs/{arxiv_id}"
    elif paper.get("url"):
        paper_url = paper["url"]

    links_block = ""
    if paper_url:
        links_block = f"""
links:
  - name: Paper
    url: "{paper_url}"
"""

    return f"""---
title: "{title}"
authors:
{authors_yaml}
date: "{date_str}"
publication_types: ["{pub_type}"]
publication: "{venue}"
abstract: "{abstract}"
featured: false
{links_block}
url_pdf: ""
url_code: ""
---
"""


def save_publications(papers: list):
    """각 논문을 Hugo publication 형식으로 저장"""
    out_dir = Path(CONFIG["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    saved, skipped = 0, 0

    for paper in papers:
        slug = slugify(paper["title"])
        pub_dir = out_dir / slug
        pub_dir.mkdir(exist_ok=True)
        index_path = pub_dir / "index.md"

        # 이미 존재하면 덮어쓰기 (업데이트)
        content = make_publication_md(paper)
        index_path.write_text(content, encoding="utf-8")
        print(f"  💾 [{paper['year']}] {paper['title'][:50]}...")
        saved += 1

    print(f"\n✅ {saved}편 저장 완료 → {out_dir}/")
    if skipped:
        print(f"⏭️  {skipped}편 스킵")


# ════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════

def main():
    print("📚 Google Scholar → Hugo Publications 업데이트 시작\n")

    papers = fetch_publications(CONFIG["scholar_id"])

    if not papers:
        print("📭 수집된 논문이 없습니다.")
        return

    print(f"\n📝 {len(papers)}편 Hugo 마크다운으로 변환 중...")
    save_publications(papers)

    print("\n🎉 완료! Hugo 빌드 후 Publications 섹션에서 확인하세요.")
    print("  hugo server -D")


if __name__ == "__main__":
    main()
