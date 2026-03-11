"""
arxiv 논문 자동 크롤링 + AI 리뷰 생성기
카테고리별로 각 3~5편씩 가져와서 하루 1페이지로 정리합니다.
"""

import os
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
import anthropic

# ════════════════════════════════════════════════════
# ✏️  여기서 설정을 바꾸세요!
# ════════════════════════════════════════════════════
CONFIG = {
    # 카테고리별 설정
    # name: 페이지에 표시될 이름
    # category: arxiv 카테고리 코드
    # papers_per_day: 하루에 가져올 논문 수
    # keywords: 이 카테고리 안에서 추가 필터 키워드 (비우면 카테고리 전체)
    "categories": [
        {
            "name": "🤖 Robotics",
            "category": "cs.RO",
            "papers_per_day": 4,
            "keywords": ["robot", "robotic", "manipulation", "vla", "vision-language-action model", "memory management", "self-evolving", "experiment"],
        },
        {
            "name": "🧠 AI / LLM",
            "category": "cs.AI",
            "papers_per_day": 4,
            "keywords": ["large language model", "LLM", "agent", "reasoning", "memory", "long-context"],
        },
        {
            "name": "💬 NLP",
            "category": "cs.CL",
            "papers_per_day": 3,
            "keywords": ["long horizon", "long-horizon", "episodic memory", "memory management", "LLM"],
        },
    ],

    # 최근 며칠 이내 논문 (1 = 어제~오늘)
    "days_back": 7,

    # 리뷰 언어
    "review_language": "Korean",

    # 리뷰 스타일: "technical" / "beginner" / "practical"
    "review_style": "technical",
}
# ════════════════════════════════════════════════════


STYLE_PROMPTS = {
    "technical": """다음 형식으로 **간결하게** 분석해주세요 (각 섹션 2~4줄):

## 핵심 기여
기존 연구와 무엇이 다른가?

## 방법론
핵심 아이디어를 직관적으로 설명

## 실험 결과
주요 성능 수치와 의미

## 한계 및 향후 연구
주요 한계점과 열어주는 방향

**종합 평가**: ⭐(1~5) — 한 줄 평""",

    "beginner": """다음 형식으로 **간결하게** 설명해주세요 (각 섹션 2~3줄):

## 한 줄 요약
10살도 이해할 수 있게

## 핵심 아이디어
비유를 들어 설명

## 실생활 응용
어디에 쓰일 수 있나?

**흥미도**: ⭐(1~5) — 한 줄 평""",

    "practical": """다음 형식으로 **간결하게** 분석해주세요 (각 섹션 2~3줄):

## 즉시 활용 가능성
코드/모델 공개 여부, 난이도

## 적용 분야
어느 산업에 유용한가?

## 컴퓨팅 요구사항
GPU 등 하드웨어 요구사항

**실용성**: ⭐(1~5) — 한 줄 평""",
}

STYLE_LABELS = {
    "technical": "기술 심층 분석",
    "beginner": "입문자 리뷰",
    "practical": "실용성 분석",
}


def fetch_papers_by_category(cat_config: dict, cutoff: datetime) -> list[dict]:
    """카테고리별로 논문 가져오기"""
    category = cat_config["category"]
    keywords = cat_config.get("keywords", [])
    limit = cat_config["papers_per_day"]

    # 쿼리 구성: 카테고리 필수 + 키워드는 있으면 OR 조건
    if keywords:
        kw_query = " OR ".join([f'all:"{kw}"' for kw in keywords])
        query = f"cat:{category} AND ({kw_query})"
    else:
        query = f"cat:{category}"

    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": limit * 3,  # 날짜 필터 후 줄어들 것을 감안
    }

    resp = requests.get("https://export.arxiv.org/api/query", params=params, timeout=30)
    resp.raise_for_status()

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.content)

    papers = []
    for entry in root.findall("atom:entry", ns):
        published_str = entry.find("atom:published", ns).text
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        if published < cutoff:
            continue

        paper_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        categories = [c.get("term") for c in entry.findall("atom:category", ns)]

        papers.append({
            "id": paper_id,
            "title": title,
            "authors": authors,
            "summary": summary,
            "published": published.strftime("%Y-%m-%d"),
            "abs_url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
            "categories": categories,
            "section": cat_config["name"],  # 어느 섹션인지 표시
        })

        if len(papers) >= limit:
            break

    return papers


def load_reviewed_ids() -> set:
    path = Path("data/reviewed_ids.json")
    if path.exists():
        return set(json.loads(path.read_text()))
    return set()


def save_reviewed_ids(ids: set):
    path = Path("data/reviewed_ids.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(ids), indent=2))


def review_paper(paper: dict, client: anthropic.Anthropic) -> str:
    style_prompt = STYLE_PROMPTS[CONFIG["review_style"]]
    lang = CONFIG["review_language"]

    prompt = f"""다음 arxiv 논문을 {lang}로 리뷰해주세요.

제목: {paper['title']}
저자: {', '.join(paper['authors'][:5])}{'외' if len(paper['authors']) > 5 else ''}
카테고리: {', '.join(paper['categories'][:3])}
초록: {paper['summary']}

{style_prompt}

마크다운 형식으로 작성하고, 리뷰 내용만 바로 시작해주세요."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def save_daily_digest(date_str: str, sections: dict[str, list], reviews: dict[str, list]):
    """카테고리별로 묶어서 하루치 1페이지로 저장"""

    today = datetime.now(timezone.utc).strftime("%Y년 %m월 %d일")
    style_label = STYLE_LABELS.get(CONFIG["review_style"], CONFIG["review_style"])
    total = sum(len(v) for v in sections.values())

    # 전체 목차
    toc_lines = []
    paper_num = 1
    for cat_config in CONFIG["categories"]:
        section_name = cat_config["name"]
        papers = sections.get(section_name, [])
        if not papers:
            continue
        toc_lines.append(f"\n**{section_name}**")
        for paper in papers:
            short_title = paper['title'][:55] + ("..." if len(paper['title']) > 55 else "")
            toc_lines.append(f"  {paper_num}. [{short_title}](#paper-{paper_num})")
            paper_num += 1
    toc = "\n".join(toc_lines)

    # 카테고리별 섹션 본문
    body_sections = []
    paper_num = 1
    for cat_config in CONFIG["categories"]:
        section_name = cat_config["name"]
        papers = sections.get(section_name, [])
        review_list = reviews.get(section_name, [])
        if not papers:
            continue

        body_sections.append(f"\n---\n\n# {section_name}\n")

        for paper, review in zip(papers, review_list):
            authors_str = ", ".join(paper['authors'][:3])
            if len(paper['authors']) > 3:
                authors_str += " 외"
            cats_str = " · ".join(paper['categories'][:2])

            section = f"""## {paper_num}. {paper['title']} {{#paper-{paper_num}}}

> 👥 **저자**: {authors_str}  
> 🏷️ **분류**: {cats_str}  
> 📄 **원문**: [{paper['abs_url']}]({paper['abs_url']}) · [PDF]({paper['pdf_url']})

{review}

"""
            body_sections.append(section)
            paper_num += 1

    body = "\n".join(body_sections)

    # 태그
    cat_codes = [c["category"] for c in CONFIG["categories"]]
    tags_yaml = "\n".join([f'  - "{t}"' for t in cat_codes])

    front_matter = f"""---
title: "📚 {today} 논문 Daily Digest ({total}편)"
date: {date_str}
draft: false
tags:
{tags_yaml}
  - "Daily Digest"
categories:
  - "Paper Review"
summary: "Robotics · AI/LLM · NLP 최신 논문 {total}편 | {style_label}"
---

> 🤖 **리뷰 방식**: {style_label}  
> 📅 **수집 기준**: 최근 {CONFIG['days_back']}일 이내 최신 논문  
> 📊 **총 {total}편** ({' / '.join([f"{c['name']} {len(sections.get(c['name'], []))}편" for c in CONFIG['categories']])})

## 📋 목차
{toc}

{body}
"""

    post_dir = Path(f"content/post/{date_str}-daily-digest")
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / "index.md").write_text(front_matter, encoding="utf-8")
    print(f"  💾 저장 완료: content/post/{date_str}-daily-digest/index.md")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("❌ ANTHROPIC_API_KEY 환경변수가 없습니다!")

    client = anthropic.Anthropic(api_key=api_key)
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONFIG["days_back"])
    reviewed_ids = load_reviewed_ids()

    # 카테고리별로 논문 수집 & 리뷰
    sections = {}   # section_name → [paper, ...]
    reviews = {}    # section_name → [review_text, ...]

    for cat_config in CONFIG["categories"]:
        section_name = cat_config["name"]
        print(f"\n📡 [{section_name}] 논문 검색 중...")

        papers = fetch_papers_by_category(cat_config, cutoff)
        new_papers = [p for p in papers if p["id"] not in reviewed_ids]
        print(f"  → {len(new_papers)}편 새 논문 발견")

        if not new_papers:
            sections[section_name] = []
            reviews[section_name] = []
            continue

        section_reviews = []
        section_papers = []
        for i, paper in enumerate(new_papers, 1):
            print(f"  [{i}/{len(new_papers)}] 리뷰 중: {paper['title'][:50]}...")
            try:
                review = review_paper(paper, client)
                section_reviews.append(review)
                section_papers.append(paper)
                reviewed_ids.add(paper["id"])
                time.sleep(2)
            except Exception as e:
                print(f"  ⚠️ 오류: {e}")
                continue

        sections[section_name] = section_papers
        reviews[section_name] = section_reviews
        time.sleep(1)

    # 하나라도 논문이 있으면 페이지 생성
    total = sum(len(v) for v in sections.values())
    if total == 0:
        print("\n📭 오늘 새 논문 없음. 종료합니다.")
        return

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n📝 Daily Digest 페이지 생성 중... (총 {total}편)")
    save_daily_digest(date_str, sections, reviews)
    save_reviewed_ids(reviewed_ids)

    print(f"\n🎉 완료! 총 {total}편 → 하루 1페이지로 저장했습니다.")


if __name__ == "__main__":
    main()
