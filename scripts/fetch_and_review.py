"""
arxiv 논문 자동 크롤링 + AI 리뷰 생성기
Hugo + HugoBlox Academic CV 테마에 맞게 포스트를 생성합니다.
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
# ✏️  여기서 키워드와 설정을 바꾸세요!
# ════════════════════════════════════════════════════
CONFIG = {
    # 검색할 키워드 목록
    "keywords": [
        "large language model",
        "multimodal",
        "RAG",
        "diffusion model",
        "agent",
    ],

    # "OR" = 하나라도 포함 / "AND" = 모두 포함
    "keyword_mode": "OR",

    # arxiv 카테고리 (비워두면 전체)
    # cs.AI / cs.LG / cs.CV / cs.CL / cs.RO / stat.ML
    "categories": ["cs.AI", "cs.LG", "cs.CV", "cs.CL"],

    # 최근 며칠 이내 논문
    "days_back": 1,

    # 최대 논문 수 (API 비용 절약)
    "max_papers": 5,

    # 리뷰 언어: "Korean" 또는 "English"
    "review_language": "Korean",

    # 리뷰 스타일
    # "beginner"  : 쉽고 친근하게 (비유 활용)
    # "technical" : 깊은 기술 분석
    # "practical" : 실용성·활용 중심
    "review_style": "beginner",
}
# ════════════════════════════════════════════════════


STYLE_PROMPTS = {
    "technical": """
다음 형식으로 심층 기술 분석해주세요:
## 핵심 기여
기존 연구와 무엇이 다른가?

## 방법론
핵심 알고리즘/아키텍처를 수식 없이 직관적으로 설명

## 실험 결과
주요 벤치마크 성능과 의미

## 한계점
저자들이 인정하는 한계 + 숨겨진 약점

## 후속 연구 방향
이 논문이 열어주는 연구 방향

## 총평
혁신성/완성도/영향력 기준으로 별점(⭐1~5개)과 한줄 요약
""",

    "beginner": """
전공자가 아닌 일반인도 이해할 수 있도록 설명해주세요:
## 한 줄 요약
이 논문을 10살 아이에게 설명한다면?

## 어떤 문제를 풀었나
기존에 어떤 불편함/한계가 있었고 이를 어떻게 해결했는가?

## 핵심 아이디어
가장 중요한 아이디어 1~2가지를 비유를 들어 설명

## 실생활 응용
이 기술이 실제로 어디에 쓰일 수 있을까?

## 이런 분께 추천
누가 읽으면 좋을지 추천 대상과 이유

## 총평
흥미도 별점(⭐1~5개)과 한 줄 평
""",

    "practical": """
실용적 가치를 중심으로 분석해주세요:
## 즉시 활용 가능성
코드/모델이 공개되어 있는가? 바로 사용할 수 있는가?

## 적용 분야
어느 산업/서비스에 가장 유용한가?

## 구현 난이도
재현하려면 얼마나 어려운가? (쉬움/보통/어려움)과 이유

## 컴퓨팅 요구사항
돌리려면 GPU가 얼마나 필요한가?

## 비슷한 대안
같은 목적의 다른 방법론과 비교

## 총평
실용성 별점(⭐1~5개)과 한 줄 평
""",
}

STYLE_LABELS = {
    "beginner": "입문자 리뷰",
    "technical": "기술 심층 분석",
    "practical": "실용성 분석",
}


def build_arxiv_query() -> str:
    kw_joiner = " OR " if CONFIG["keyword_mode"] == "OR" else " AND "
    keyword_query = kw_joiner.join([f'all:"{kw}"' for kw in CONFIG["keywords"]])
    if CONFIG["categories"]:
        cat_query = " OR ".join([f"cat:{c}" for c in CONFIG["categories"]])
        return f"({keyword_query}) AND ({cat_query})"
    return keyword_query


def fetch_papers() -> list[dict]:
    print("📡 arxiv에서 논문 검색 중...")
    query = build_arxiv_query()
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONFIG["days_back"])

    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": CONFIG["max_papers"] * 3,
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
            "published_dt": published,
            "abs_url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
            "categories": categories,
        })

        if len(papers) >= CONFIG["max_papers"]:
            break

    print(f"✅ {len(papers)}개 논문 발견")
    return papers


def load_reviewed_ids() -> set:
    path = Path("data/reviewed_ids.json")
    if path.exists():
        return set(json.loads(path.read_text()))
    return set()


def save_reviewed_id(paper_id: str):
    path = Path("data/reviewed_ids.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_reviewed_ids()
    existing.add(paper_id)
    path.write_text(json.dumps(list(existing), indent=2))


def review_paper(paper: dict, client: anthropic.Anthropic) -> str:
    style_prompt = STYLE_PROMPTS[CONFIG["review_style"]]
    lang = CONFIG["review_language"]

    prompt = f"""다음 arxiv 논문을 {lang}로 리뷰해주세요.

논문 제목: {paper['title']}
저자: {', '.join(paper['authors'][:5])}{'외' if len(paper['authors']) > 5 else ''}
카테고리: {', '.join(paper['categories'][:3])}
초록: {paper['summary']}

{style_prompt}

마크다운 형식으로 작성하고, 응답은 리뷰 내용만 포함해주세요."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def slugify(text: str) -> str:
    import unicodedata
    # 영문/숫자만 남기고 slug 생성
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() or c == " " else "" for c in ascii_text.lower())
    return "-".join(safe.split())[:60]


def save_as_hugo_post(paper: dict, review: str):
    """Hugo + HugoBlox Academic 테마 형식의 포스트 생성"""
    date_str = paper["published"]
    slug = slugify(paper["title"])
    folder_name = f"{date_str}-{slug}"

    # Hugo는 content/post/폴더명/index.md 구조
    post_dir = Path(f"content/post/{folder_name}")
    post_dir.mkdir(parents=True, exist_ok=True)

    # 태그 생성
    matched_keywords = [
        kw for kw in CONFIG["keywords"]
        if kw.lower() in paper["title"].lower() or kw.lower() in paper["summary"].lower()
    ]
    tags = list(set(matched_keywords + paper["categories"][:2]))
    tags_yaml = "\n".join([f'  - "{t}"' for t in tags])

    authors_yaml = "\n".join([f'  - "{a}"' for a in paper["authors"][:3]])
    style_label = STYLE_LABELS.get(CONFIG["review_style"], CONFIG["review_style"])

    # 제목에서 특수문자 처리
    safe_title = paper["title"].replace('"', "'").replace("\\", "")

    front_matter = f"""---
title: "{safe_title}"
date: {date_str}
draft: false

# 태그와 카테고리
tags:
{tags_yaml}
categories:
  - "Paper Review"

# 저자 (사이트에 등록된 author 이름과 일치시키면 프로필 연동됨)
# authors:
#   - admin

# 요약 (목록 페이지에 표시됨)
summary: "arxiv 논문 자동 리뷰 | {style_label} | {', '.join(paper['categories'][:2])}"

# 추가 메타데이터 (Hugo params)
params:
  arxiv_id: "{paper['id']}"
  arxiv_url: "{paper['abs_url']}"
  pdf_url: "{paper['pdf_url']}"
  paper_authors: {json.dumps(paper['authors'][:5])}
  review_style: "{style_label}"
---

> 📄 **원문**: [{paper['abs_url']}]({paper['abs_url']})  
> 👥 **저자**: {', '.join(paper['authors'][:3])}{'외' if len(paper['authors']) > 3 else ''}  
> 🏷️ **분류**: {' · '.join(paper['categories'][:3])}  
> 🤖 **리뷰 방식**: {style_label}

---

{review}
"""

    (post_dir / "index.md").write_text(front_matter, encoding="utf-8")
    print(f"  💾 저장: content/post/{folder_name}/index.md")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("❌ ANTHROPIC_API_KEY 환경변수가 없습니다!")

    client = anthropic.Anthropic(api_key=api_key)

    papers = fetch_papers()
    if not papers:
        print("📭 새 논문 없음. 종료합니다.")
        return

    reviewed_ids = load_reviewed_ids()
    new_papers = [p for p in papers if p["id"] not in reviewed_ids]
    print(f"🆕 새로 리뷰할 논문: {len(new_papers)}개")

    if not new_papers:
        print("✅ 모두 이미 리뷰됨. 종료합니다.")
        return

    for i, paper in enumerate(new_papers, 1):
        print(f"\n[{i}/{len(new_papers)}] 리뷰 중: {paper['title'][:60]}...")
        try:
            review = review_paper(paper, client)
            save_as_hugo_post(paper, review)
            save_reviewed_id(paper["id"])
            time.sleep(2)
        except Exception as e:
            print(f"  ⚠️ 오류: {e}")
            continue

    print(f"\n🎉 완료! {len(new_papers)}개 논문 리뷰 생성됨")


if __name__ == "__main__":
    main()
