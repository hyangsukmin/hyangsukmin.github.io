"""
arxiv 논문 자동 크롤링 + AI 리뷰 생성기
카테고리별로 각 3~5편씩 가져와서 하루 1페이지로 정리합니다.
"""
import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
import anthropic

# ════════════════════════════════════════════════════
# ✏️ [설정] 연구 카테고리 및 키워드 (유망 논문 필터링 포함)
# ════════════════════════════════════════════════════
CONFIG = {
    "categories": [
        {
            "name": "🔄 Self-Evolving & Agents",
            "category": "cs.AI",
            "papers_per_day": 3,
            "keywords": ["self-evolving agent", "error correction reasoning", "iterative refinement", "adaptive agent", "learning from mistakes"],
        },
        {
            "name": "🧠 Lifelong & Long-range Memory",
            "category": "cs.LG",
            "papers_per_day": 3,
            "keywords": ["lifelong memory", "long-range memory", "memory management", "selective retrieval", "episodic memory", "hierarchical memory"],
        },
        {
            "name": "🦾 Robotics & Embodied AI",
            "category": "cs.RO",
            "papers_per_day": 3,
            "keywords": ["Gemini Robotics", "embodied AI", "robotics memory", "learning from historic errors", "VLA model", "manipulation"],
        },
        {
            "name": "⏳ Advanced Reasoning (Long-Think)",
            "category": "cs.AI",
            "papers_per_day": 3,
            "keywords": ["slow inference", "deliberative reasoning", "long-form reasoning", "chain of thought optimization"],
        }
    ],
    "days_back": 60,
    "review_language": "Korean",
    "review_style": "technical",
}

TOP_INSTITUTIONS = [
    "DeepMind", "OpenAI", "Google", "Meta", "FAIR", "Microsoft", "Anthropic",
    "NVIDIA", "Tesla", "Amazon Science", "Apple", "IBM Research", "X.AI", "AWS", "Amazon",
    "Stanford", "MIT", "CMU", "Carnegie Mellon", "UC Berkeley", "BAIR", "Georgia Tech",
    "Princeton", "Harvard", "Caltech", "UPenn", "Cornell", "UCLA", "UW", "University of Washington",
    "Oxford", "Cambridge", "ETH Zurich", "EPFL", "University of Toronto", "Vector Institute",
    "Mila", "McGill", "Max Planck", "TUM", "Technical University of Munich", "INRIA", "DFKI",
    "Tsinghua", "Peking University", "HKUST", "Nanyang Technological University", "NTU",
    "Boston Dynamics", "Agility Robotics", "Figure AI", "Sanctuary AI", "Intuitive Surgical",
    "Dyson Robotics", "TRI", "Toyota Research Institute", "Standard Bots",
    "Samsung Research", "NAVER", "SK Telecom", "LG AI Research", "Kakao Brain",
    "Hyundai Motor", "SNU", "Seoul National University", "KAIST", "POSTECH",
    "Yonsei", "Korea University", "KIST", "Upstage", "Lunit", "Rebellions", "FuriosaAI"
]
VVIP_LABS = ["DeepMind", "OpenAI", "Stanford", "KAIST", "Google DeepMind", "AWS"]
TOP_CONFERENCES = ["ICLR", "NeurIPS", "ICML", "CVPR", "ECCV", "ICRA", "RSS", "AAAI", "IJCAI", "ACL", "EMNLP", "NAACL", "COLM"]

# ════════════════════════════════════════════════════

STYLE_PROMPTS = {
    "technical": """아래 구조로 AI 논문을 한국어로 리뷰해주세요.

**🎯 한 줄 핵심** (30자 내외)
해결한 문제를 동사 중심으로. 예: "sparse attention으로 O(n²) 복잡도 문제 해결"

**📚 Background**
- 이 연구가 속한 AI 세부 분야 (예: RLHF, RAG, VLA, Long-context LLM 등)
- 최근 흐름과 왜 이 시점에 이 연구가 필요했는지
- 선행 연구 1~2개를 언급하며 맥락 연결

**😤 기존 방법의 한계**
- 기존 SOTA 또는 주류 방법이 가진 구체적 문제점
- 수치나 사례로 "얼마나" 문제인지 표현

**❓ Research Questions**
Q1: [핵심 질문] → A1: [논문의 답]
Q2: [핵심 질문] → A2: [논문의 답]
Q3: [핵심 질문] → A3: [논문의 답]

**💡 핵심 방법론**
- 제안하는 모델/알고리즘의 구조를 3~4문장으로
- 기존 방법과 구조적으로 다른 점을 명확히
- 가능하면 직관적 비유 1개 포함

**📊 실험 및 결과**
- 사용 데이터셋 및 평가 벤치마크
- 주요 Baseline 대비 성능 향상 수치
- 가장 인상적인 ablation study 결과 1개

**⚠️ 한계 및 Future Work**
- 저자가 인정한 한계
- 이 방법이 실제 적용될 때 생길 수 있는 문제
- 자연스럽게 이어지는 후속 연구 방향

**🔁 Reproducibility**
- 코드/모델 공개 여부 (GitHub 링크 있으면 포함)
- 재현에 필요한 컴퓨팅 규모 (GPU 수, 학습 시간 등 언급 시)

주의: 마크다운 헤더(#, ##)는 사용하지 마세요. Hugo shortcode 패턴 금지.
초록에 정보가 없는 항목은 "초록에서 확인 불가"로 표시하세요.""",
}


def sanitize_for_hugo(text: str) -> str:
    """Hugo 빌드를 깨뜨리는 문자열 제거/치환"""
    if not text:
        return ""
    # Hugo shortcode 패턴 제거: {{< >}}, {{% %}}, {{ }}
    text = re.sub(r'\{\{[<>%].*?[<>%]\}\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\{\{.*?\}\}', '', text, flags=re.DOTALL)
    # YAML front matter를 깨는 문자 처리 (백틱 3개 연속 제거)
    text = text.replace('```', '\n```\n')
    return text


def sanitize_title(title: str) -> str:
    """YAML front matter용 제목 안전 처리"""
    # 큰따옴표 escape
    title = title.replace('"', '\\"')
    # Hugo shortcode 패턴 제거
    title = re.sub(r'\{.*?\}', '', title)
    # 파이프, 줄바꿈 제거
    title = title.replace("|", "-").replace("\n", " ").strip()
    return title


def fetch_papers_by_category(cat_config: dict, cutoff: datetime) -> list:
    """유망한 논문을 점수제로 필터링하여 가져오기"""
    category = cat_config["category"]
    keywords = cat_config.get("keywords", [])
    limit = cat_config["papers_per_day"]

    kw_query = " OR ".join([f'all:"{kw}"' for kw in keywords])
    query = f"cat:{category} AND ({kw_query})"

    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": 40,
    }

    for attempt in range(3):
        try:
            resp = requests.get(
                "https://export.arxiv.org/api/query",
                params=params,
                timeout=90
            )
            resp.raise_for_status()
            break
        except requests.exceptions.Timeout:
            print(f"  ⏳ arxiv 응답 느림, 재시도 중... ({attempt + 1}/3)")
            time.sleep(10)
    else:
        print(f"  ❌ arxiv 연결 실패, 이 카테고리 건너뜀")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(resp.content)

    candidates = []
    for entry in root.findall("atom:entry", ns):
        published_str = entry.find("atom:published", ns).text
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        if published < cutoff:
            continue

        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        comment = entry.find("arxiv:comment", ns)
        comment_text = comment.text if comment is not None else ""

        score = 0
        if any(conf.lower() in comment_text.lower() for conf in TOP_CONFERENCES):
            score += 10
        if "github.com" in summary.lower() or "github.com" in comment_text.lower():
            score += 7
        if any(inst.lower() in summary.lower() or inst.lower() in comment_text.lower() for inst in TOP_INSTITUTIONS):
            score += 5
        for inst in VVIP_LABS:
            if inst.lower() in summary.lower() or inst.lower() in comment_text.lower():
                score += 20
        if any(kw.lower() in title.lower() for kw in keywords):
            score += 3

        if score == 0:
            continue

        paper_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
        candidates.append({
            "id": paper_id,
            "title": title,
            "summary": summary,
            "authors": [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)],
            "published": published.strftime("%Y-%m-%d"),
            "abs_url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
            "categories": [c.get("term") for c in entry.findall("atom:category", ns)],
            "score": score,
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]


def review_paper(paper: dict, client: anthropic.Anthropic) -> str:
    """Claude AI를 사용해 논문 리뷰 생성"""
    style_prompt = STYLE_PROMPTS.get(CONFIG["review_style"], STYLE_PROMPTS["technical"])
    lang = CONFIG["review_language"]

    prompt = f"""다음 arxiv 논문을 {lang}로 리뷰해주세요. 유망 점수 {paper['score']}점인 중요한 논문입니다.

제목: {paper['title']}
저자: {', '.join(paper['authors'][:5])}
초록: {paper['summary']}

{style_prompt}
마크다운 형식으로 작성하고, 리뷰 내용만 바로 시작해주세요.
주의: Hugo 정적 사이트 빌드에 사용되므로 {{{{, }}}}, {{{{< >}}}}, {{{{%  %}}}} 같은 Hugo shortcode 패턴은 절대 사용하지 마세요."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text
    return sanitize_for_hugo(raw)


def save_daily_digest(date_str: str, sections: dict, reviews: dict):
    """결과를 GitHub Pages용 마크다운으로 저장"""
    today = datetime.now(timezone.utc).strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in sections.values())

    # ── 목차: 표 형식 ──
    toc_rows = []
    paper_idx = 1
    for cat in CONFIG["categories"]:
        name = cat["name"]
        if not sections.get(name):
            continue
        for p in sections[name]:
            short_title = p['title'][:55] + ("..." if len(p['title']) > 55 else "")
            short_title = short_title.replace("|", "-")
            toc_rows.append(f"| {paper_idx} | {name} | {short_title} |")
            paper_idx += 1

    toc_str = "| # | 분야 | 제목 |\n|---|------|------|\n" + "\n".join(toc_rows)

    # ── 본문 ──
    body_parts = []
    paper_idx = 1
    for cat in CONFIG["categories"]:
        name = cat["name"]
        if not sections.get(name):
            continue

        body_parts.append(f"\n---\n\n## {name}\n")

        for p, r in zip(sections[name], reviews[name]):
            authors_str = ", ".join(p['authors'][:3])
            if len(p['authors']) > 3:
                authors_str += " 외"

            safe_title = sanitize_title(p['title'])

            body_parts.append(f"### {paper_idx}. {safe_title}\n")
            body_parts.append(
                f"**저자**: {authors_str} | "
                f"[원문]({p['abs_url']}) | [PDF]({p['pdf_url']}) \n"
            )
            body_parts.append(f"{r}\n")
            paper_idx += 1

    body_str = "\n".join(body_parts)

    # YAML front matter — title을 큰따옴표로 감싸고 내부 따옴표 escape
    digest_title = sanitize_title(f"논문 Daily Digest {today} ({total}편)")

    content = f"""---
title: "{digest_title}"
date: {date_str}T00:00:00Z
draft: false
tags: ["Daily", "AI", "Robotics", "Memory"]
summary: "Self-Evolving, Memory, Robotics, Reasoning 분야 유망 논문 {total}편"
---

## 목차

{toc_str}

{body_str}
"""

    # HugoBlox academic-cv의 블로그 포스트 경로
    post_dir = Path(f"content/post/{date_str}-digest")
    post_dir.mkdir(parents=True, exist_ok=True)
    output_path = post_dir / "index.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"  💾 저장 완료: {output_path}")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 환경변수를 설정해주세요.")
        return

    client = anthropic.Anthropic(api_key=api_key)
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONFIG["days_back"])

    history_path = Path("data/reviewed_ids.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed_ids = set(json.loads(history_path.read_text())) if history_path.exists() else set()

    sections, reviews_dict = {}, {}

    for cat_config in CONFIG["categories"]:
        name = cat_config["name"]
        print(f"\n📡 [{name}] 유망 논문 검색 중...")

        papers = fetch_papers_by_category(cat_config, cutoff)
        new_papers = [p for p in papers if p["id"] not in reviewed_ids]
        print(f"  → {len(new_papers)}편 새 논문 발견")

        sections[name] = []
        reviews_dict[name] = []

        for i, paper in enumerate(new_papers, 1):
            print(f"  [{i}/{len(new_papers)}] 리뷰 중: {paper['title'][:45]}...")
            try:
                review = review_paper(paper, client)
                sections[name].append(paper)
                reviews_dict[name].append(review)
                reviewed_ids.add(paper["id"])
                time.sleep(2)
            except Exception as e:
                print(f"  ⚠️ 오류: {e}")

    total = sum(len(v) for v in sections.values())
    if total > 0:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(f"\n📝 Daily Digest 생성 중... (총 {total}편)")
        save_daily_digest(date_str, sections, reviews_dict)
        history_path.write_text(json.dumps(list(reviewed_ids), indent=2))
        print(f"🎉 완료! 총 {total}편 저장됨")
    else:
        print("\n📭 새로운 유망 논문이 없습니다.")


if __name__ == "__main__":
    main()
