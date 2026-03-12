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
            "papers_per_day": 2,
            "keywords": ["self-evolving agent", "error correction reasoning", "iterative refinement", "adaptive agent", "learning from mistakes"],
        },
        {
            "name": "🧠 Lifelong & Long-range Memory",
            "category": "cs.LG",
            "papers_per_day": 2,
            "keywords": ["lifelong memory", "long-range memory", "memory management", "selective retrieval", "episodic memory", "hierarchical memory"],
        },
        {
            "name": "🦾 Robotics & Embodied AI",
            "category": "cs.RO",
            "papers_per_day": 2,
            "keywords": ["Gemini Robotics", "embodied AI", "robotics memory", "learning from historic errors", "VLA model", "manipulation"],
        },
        # {
        #     "name": "⏳ Advanced Reasoning (Long-Think)",
        #     "category": "cs.AI",
        #     "papers_per_day": 2,
        #     "keywords": ["slow inference", "deliberative reasoning", "long-form reasoning", "chain of thought optimization"],
        # }
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
    "technical": """아래 포맷을 정확히 따라 AI 논문을 한국어로 리뷰해주세요.

**한 줄 요약**: [15~30자. 동사 중심으로 핵심만]

**Background**:
[이 연구가 속한 AI 세부 분야(예: RLHF, RAG, VLA, Long-context LLM 등)와 최근 흐름.
선행 연구 1~2개를 언급하며 기존 방법의 한계까지 2~3문장으로]

**핵심 아이디어**:
- [기존과 다른 구조적/알고리즘적 차별점]
- [직관적 비유나 예시 포함]
- [구현상의 핵심 설계 결정]

**왜 중요한가**:
- [실용적 임팩트 — 어떤 문제가 실제로 해결되는가]
- [이 분야 연구 흐름에서 갖는 위치]
- [후속 연구나 응용에 미치는 영향]

**Research Questions**:
*Q1: [이 논문이 던지는 첫 번째 핵심 질문]*
A1: [논문이 제시하는 답. 한 문장으로]
*Q2: [두 번째 핵심 질문]*
A2: [논문이 제시하는 답. 한 문장으로]
*Q3: [세 번째 핵심 질문]*
A3: [논문이 제시하는 답. 한 문장으로]

**실험 결과**: [사용 데이터셋 + 벤치마크명 + baseline 대비 수치 + 인상적인 ablation 1개. 없으면 "본문에서 확인 불가"]

**한계**: [저자가 인정한 한계 또는 명확히 보이는 제약. 후속 연구 방향 포함. 2~3문장]

**재현성**: 코드 공개: O/X | [컴퓨팅 규모 언급 시만 추가]

주의사항:
- 위 포맷을 반드시 그대로 유지할 것
- 마크다운 헤더(#, ##, ###)는 절대 사용하지 말 것 — 볼드(**)만 사용
- Hugo shortcode 패턴 금지
- 본문에 없는 정보는 절대 지어내지 말고 "본문에서 확인 불가"로 표시
- Q/A의 질문은 반드시 이탤릭(*Q1: ...*)으로""",
}


# ════════════════════════════════════════════════════
# 유틸리티
# ════════════════════════════════════════════════════

def sanitize_for_hugo(text: str) -> str:
    """Hugo 빌드를 깨뜨리는 문자열 제거/치환"""
    if not text:
        return ""
    text = re.sub(r'\{\{[<>%].*?[<>%]\}\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\{\{.*?\}\}', '', text, flags=re.DOTALL)
    text = text.replace('```', '\n```\n')
    return text


def sanitize_title(title: str) -> str:
    """YAML front matter용 제목 안전 처리"""
    title = title.replace('"', '\\"')
    title = re.sub(r'\{.*?\}', '', title)
    title = title.replace("|", "-").replace("\n", " ").strip()
    return title


# ════════════════════════════════════════════════════
# 논문 수집
# ════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════
# 본문 파싱 (PDF → ar5iv → abstract 순 폴백)
# ════════════════════════════════════════════════════

def _extract_sections(full_text: str) -> dict:
    """텍스트에서 섹션별로 분리 (PDF/HTML 공통)"""
    patterns = {
        "introduction": (
            r'(Introduction|INTRODUCTION)',
            r'(Related Work|Background|Preliminary|Method|Approach|RELATED|2\.)\s'
        ),
        "method": (
            r'(Method|Methodology|Approach|Proposed|MODEL|METHOD)',
            r'(Experiment|Evaluation|Result|EXPERIMENT)'
        ),
        "experiments": (
            r'(Experiment|Evaluation|Result|EXPERIMENT)',
            r'(Conclusion|Limitation|Discussion|CONCLUSION)'
        ),
        "limitation": (
            r'(Limitation|Limitations|LIMITATION)',
            r'(Conclusion|Future Work|Reference|CONCLUSION)'
        ),
    }
    limits = {"introduction": 2000, "method": 2000, "experiments": 2000, "limitation": 500}

    sections = {}
    for key, (start_pat, end_pat) in patterns.items():
        m = re.search(f'{start_pat}(.*?){end_pat}', full_text, re.DOTALL)
        sections[key] = m.group(2)[:limits[key]].strip() if m else ""
    return sections


def _parse_pdf(pdf_url: str) -> dict:
    """1차: PDF 직접 파싱"""
    try:
        import urllib.request, io
        from pypdf import PdfReader

        req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
        pdf_bytes = io.BytesIO(urllib.request.urlopen(req, timeout=30).read())
        reader = PdfReader(pdf_bytes)
        full_text = "\n".join(p.extract_text() or "" for p in reader.pages[:8])
        return _extract_sections(full_text)
    except Exception as e:
        print(f"    ❌ PDF 파싱 오류: {e}")
        return {}


def _parse_ar5iv(abs_url: str) -> dict:
    """2차 폴백: ar5iv HTML 버전 파싱 (PDF보다 텍스트 품질 우수)"""
    try:
        import urllib.request
        from html.parser import HTMLParser

        ar5iv_url = abs_url.replace("arxiv.org", "ar5iv.org")

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "footer"):
                    self.skip = True

            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer"):
                    self.skip = False

            def handle_data(self, data):
                if not self.skip:
                    self.text.append(data)

        req = urllib.request.Request(ar5iv_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
        parser = TextExtractor()
        parser.feed(html)
        full_text = "\n".join(parser.text)
        return _extract_sections(full_text)
    except Exception as e:
        print(f"    ❌ ar5iv 파싱 오류: {e}")
        return {}


def fetch_paper_content(pdf_url: str, abs_url: str) -> dict:
    """PDF → ar5iv → abstract 순으로 폴백하며 본문 추출"""

    # 1차: PDF 직접 파싱
    sections = _parse_pdf(pdf_url)
    if sections.get("introduction"):
        print(f"    ✅ PDF 파싱 성공")
        return sections

    # 2차: ar5iv HTML 파싱
    print(f"    ⚠️ PDF 파싱 실패 → ar5iv 시도 중...")
    sections = _parse_ar5iv(abs_url)
    if sections.get("introduction"):
        print(f"    ✅ ar5iv 파싱 성공")
        return sections

    # 3차: abstract만 사용 (Claude에게 명시적으로 알림)
    print(f"    ⚠️ ar5iv 실패 → abstract만 사용")
    return {}


# ════════════════════════════════════════════════════
# 리뷰 생성
# ════════════════════════════════════════════════════

def review_paper(paper: dict, client: anthropic.Anthropic) -> str:
    """Claude AI를 사용해 논문 리뷰 생성"""
    style_prompt = STYLE_PROMPTS.get(CONFIG["review_style"], STYLE_PROMPTS["technical"])

    print(f"    📄 본문 파싱 중...")
    sections = fetch_paper_content(paper["pdf_url"], paper["abs_url"])

    # 파싱된 섹션 로깅
    parsed = [k for k, v in sections.items() if v]
    if parsed:
        print(f"    📑 파싱 완료: {parsed}")
    else:
        print(f"    📑 파싱 실패 — abstract만 사용")

    # 논문 콘텐츠 조립
    only_abstract = not any(sections.values())
    paper_content = f"""제목: {paper['title']}
저자: {', '.join(paper['authors'][:5])}
유망 점수: {paper['score']}점

[Abstract]
{paper['summary']}
"""
    section_labels = {
        "introduction": "Introduction",
        "method":       "Method",
        "experiments":  "Experiments & Results",
        "limitation":   "Limitations",
    }
    for key, label in section_labels.items():
        if sections.get(key):
            paper_content += f"\n[{label}]\n{sections[key]}\n"

    # abstract만 있을 때 Claude에게 명시
    content_note = (
        "\n※ 주의: 본문 파싱에 실패하여 Abstract만 제공됩니다. "
        "본문에서 확인할 수 없는 항목은 반드시 '본문에서 확인 불가'로 표시하세요.\n"
        if only_abstract else ""
    )

    prompt = f"""다음 arxiv 논문을 한국어로 리뷰해주세요.
{content_note}
{paper_content}

{style_prompt}
리뷰 내용만 바로 시작하세요."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return sanitize_for_hugo(message.content[0].text)


# ════════════════════════════════════════════════════
# 저장
# ════════════════════════════════════════════════════

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

    post_dir = Path(f"content/post/{date_str}-digest")
    post_dir.mkdir(parents=True, exist_ok=True)
    output_path = post_dir / "index.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"  💾 저장 완료: {output_path}")


# ════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════

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
