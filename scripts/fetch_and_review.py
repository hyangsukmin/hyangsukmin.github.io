import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from difflib import SequenceMatcher
import anthropic

KST = timezone(timedelta(hours=9))

MODEL_NAME = "Haiku"
MODEL_API = {"Haiku": "claude-haiku-4-5-20251001", "Sonnet": "claude-sonnet-4-6"}

CONFIG = {
    "categories": [
        {
            "name": "💬 Dialogue Summarization",
            "category": "cs.CL",
            "papers_per_day": 4,
            "keywords": ["dialogue", "conversation", "streaming", "summarization", "llm", "long-term", "memory"],
        },
        {
            "name": "🔄 Self-Evolving & Agents",
            "category": "cs.AI",
            "papers_per_day": 2,
            "keywords": ["self-evolving", "self-improvement", "self-reflection", "self-correction",
                         "error correction reasoning", "iterative refinement", "adaptive agent", "learning from mistakes",
                         "continual learning", "agent", "self-training"],
        },
        {
            "name": "🧠 Lifelong & Long-range Memory",
            "category": "cs.LG",
            "papers_per_day": 4,
            "keywords": [
                "lifelong learning", "continual learning", "long-horizon",
                "long-horizon reasoning", "long-horizon planning", "long-term memory",
                "episodic memory", "memory retrieval", "memory consolidation",
                "memory management", "hierarchical memory", "agent memory",
                "memory bank", "dynamic memory", "memory dynamic"
            ],
        },
        {
            "name": "🦾 Robotics & Embodied AI",
            "category": "cs.RO",
            "papers_per_day": 2,
            "keywords": ["robotics", "embodied AI", "robotics memory", "learning from historic errors",
                         "VLA", "manipulation", "benchmark", "vision-language-action"],
        },
    ],
    "days_back": 90,
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
# 🔤 유연한 키워드 매칭 유틸리티
# ════════════════════════════════════════════════════

# 키워드 유사어/변형 사전
KEYWORD_SYNONYMS = {
    "dialogue":         ["dialog", "dialogues", "dialogs", "conversational"],
    "conversation":     ["conversations", "conversational", "chat", "discourse"],
    "summarization":    ["summarizing", "summarize", "summary", "summaries", "abstractive"],
    "llm":              ["large language model", "language model", "gpt", "bert", "transformer"],
    "memory":           ["memorization", "memorize", "memories", "memoization"],
    "agent":            ["agents", "agentic", "autonomous agent", "multi-agent"],
    "self-evolving":    ["self-evolution", "self-evolved", "self evolving"],
    "self-improvement": ["self-improve", "self-improved", "self improving"],
    "self-reflection":  ["self-reflect", "self-reflected", "self reflecting"],
    "self-correction":  ["self-correct", "self-corrected", "self correcting", "error correction"],
    "continual learning": ["continuous learning", "incremental learning", "online learning"],
    "lifelong learning":  ["lifelong", "life-long learning", "perpetual learning"],
    "long-horizon":     ["long horizon", "long-term planning", "extended horizon"],
    "long-term memory": ["long term memory", "persistent memory", "long-range memory"],
    "episodic memory":  ["episodic", "episode memory", "experience replay"],
    "memory retrieval": ["retrieval memory", "memory recall", "retrieve memory"],
    "embodied AI":      ["embodied intelligence", "embodied agent", "physical AI"],
    "manipulation":     ["grasping", "robotic manipulation", "dexterous manipulation"],
    "vision-language-action": ["VLA model", "vision language action"],
    "benchmark":        ["benchmarks", "benchmarking", "evaluation suite", "leaderboard"],
}

def fuzzy_match(word: str, keyword: str, threshold: float = 0.82) -> bool:
    """SequenceMatcher 기반 퍼지 매칭 (짧은 단어는 정확 매칭 강제)"""
    if len(keyword) <= 4:
        return word == keyword
    ratio = SequenceMatcher(None, word, keyword).ratio()
    return ratio >= threshold

def flexible_keyword_match(text: str, keywords: list, min_match: int = 2) -> int:
    """
    유연한 키워드 매칭:
    1. 정확한 문자열 포함 여부 (멀티워드 키워드 포함)
    2. 유사어 사전 확장 매칭
    3. 단일 단어 퍼지 매칭 (임계값 0.82)
    """
    text_lower = text.lower()
    words = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', text_lower)  # 하이픈 포함 토크나이징
    matched = 0

    for kw in keywords:
        kw_lower = kw.lower()
        found = False

        # 1) 정확한 포함 (멀티워드 키워드는 이걸로 커버)
        if kw_lower in text_lower:
            found = True

        # 2) 유사어 사전 확장
        if not found:
            for synonym in KEYWORD_SYNONYMS.get(kw_lower, []):
                if synonym.lower() in text_lower:
                    found = True
                    break

        # 3) 단일 단어 퍼지 매칭 (멀티워드 키워드는 제외)
        if not found and ' ' not in kw_lower and '-' not in kw_lower:
            for word in words:
                if fuzzy_match(word, kw_lower):
                    found = True
                    break

        if found:
            matched += 1

    return matched


# ════════════════════════════════════════════════════
# 🏛️ Semantic Scholar API로 기관 정보 조회
# ════════════════════════════════════════════════════

def fetch_institutions_from_semantic_scholar(arxiv_id: str) -> list[str]:
    """
    Semantic Scholar API를 통해 저자 소속 기관 목록 반환.
    arXiv API는 affiliation을 제공하지 않으므로 외부 API 활용.
    Rate limit: 100 req/5min (unauthenticated) → sleep으로 처리.
    """
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
    params = {"fields": "authors.affiliations"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 429:
            print("    ⚠️  Semantic Scholar rate limit, 10초 대기...")
            time.sleep(10)
            resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        institutions = []
        for author in data.get("authors", []):
            for aff in author.get("affiliations", []):
                if aff and aff not in institutions:
                    institutions.append(aff)
        return institutions
    except Exception as e:
        print(f"    ⚠️  Semantic Scholar 조회 실패 ({arxiv_id}): {e}")
        return []


def detect_institution_from_list(institution_list: list[str]) -> tuple[str, bool]:
    """
    기관 목록에서 TOP_INSTITUTIONS / VVIP_LABS 매칭.
    Returns: (기관명, is_vvip)
    """
    joined = " ".join(institution_list).lower()

    for inst in VVIP_LABS:
        if inst.lower() in joined:
            return inst, True

    for inst in TOP_INSTITUTIONS:
        if inst.lower() in joined:
            return inst, False

    return "", False


# ════════════════════════════════════════════════════
# 📄 arXiv HTML에서 Intro 파싱
# ════════════════════════════════════════════════════

def fetch_intro_from_arxiv_html(arxiv_id: str, max_chars: int = 1500) -> str:
    """
    arXiv HTML 버전(ar5iv)에서 Introduction 섹션 텍스트 추출.
    ar5iv: https://ar5iv.labs.arxiv.org/html/{id}
    실패 시 빈 문자열 반환 (Abstract로 대체).
    """
    url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return ""

        # Introduction 섹션 추출 (정규식으로 태그 파싱 최소화)
        html = resp.text

        # <section> 또는 <div> 안에 "Introduction" 헤더를 찾아 텍스트 추출
        # ar5iv 구조: <section id="S1"> <h2>1 Introduction</h2> ...
        pattern = re.compile(
            r'<(?:section|div)[^>]*?(?:id=["\']S1["\']|class=["\'][^"\']*introduction[^"\']*["\'])[^>]*?>'
            r'(.*?)</(?:section|div)>',
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(html)

        if not match:
            # 폴백: "Introduction" 텍스트 직후 단락들
            idx = html.lower().find("introduction")
            if idx == -1:
                return ""
            snippet = html[idx:idx + 8000]
        else:
            snippet = match.group(1)

        # HTML 태그 제거
        clean = re.sub(r'<[^>]+>', ' ', snippet)
        clean = re.sub(r'\s+', ' ', clean).strip()

        return clean[:max_chars]

    except Exception as e:
        print(f"    ⚠️  Intro 파싱 실패 ({arxiv_id}): {e}")
        return ""


# ════════════════════════════════════════════════════
# 📡 논문 수집
# ════════════════════════════════════════════════════

def fetch_papers_by_category(cat_config: dict, cutoff: datetime) -> list:
    category = cat_config["category"]
    keywords = cat_config.get("keywords", [])
    limit = cat_config["papers_per_day"]

    terms = [f'(ti:"{kw}" OR abs:"{kw}")' for kw in keywords]
    query = f"cat:{category} AND ({' OR '.join(terms)})"

    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": 150,  # 버퍼를 넉넉히 (필터링 후 limit 적용)
    }

    try:
        resp = requests.get("https://export.arxiv.org/api/query", params=params, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ arXiv API 요청 실패: {e}")
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom"
    }

    root = ET.fromstring(resp.content)
    candidates = []
    seen_titles = set()

    for entry in root.findall("atom:entry", ns):
        published_el = entry.find("atom:published", ns)
        if published_el is None:
            continue
        published = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
        if published < cutoff:
            continue

        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        if title_el is None or summary_el is None:
            continue

        title = title_el.text.strip().replace("\n", " ")
        summary = summary_el.text.strip().replace("\n", " ")

        if title in seen_titles:
            continue
        seen_titles.add(title)

        comment_el = entry.find("arxiv:comment", ns)
        comment_text = comment_el.text.lower() if comment_el is not None else ""

        full_text = title.lower() + " " + summary.lower()

        # ✅ 유연한 키워드 매칭 (min_match=2)
        kw_count = flexible_keyword_match(full_text, keywords, min_match=2)
        if kw_count < 2:
            continue

        score = kw_count * 5

        # 코드/구현 공개 여부
        if any(x in full_text for x in ["github.com", "code available", "project page", "implementation", "huggingface"]):
            score += 10

        # 컨퍼런스 언급
        if any(conf.lower() in comment_text for conf in TOP_CONFERENCES):
            score += 20

        paper_id = entry.find("atom:id", ns).text.split("/abs/")[-1]

        # ✅ Semantic Scholar로 기관 정보 조회 (arXiv API에는 없음)
        print(f"    🔍 기관 조회: {paper_id}")
        raw_institutions = fetch_institutions_from_semantic_scholar(paper_id)
        institution_found, is_vvip = detect_institution_from_list(raw_institutions)

        if is_vvip:
            score += 15
        elif institution_found:
            score += 5

        if score < 10:
            continue

        # ✅ Intro 텍스트 수집
        print(f"    📄 Intro 파싱: {paper_id}")
        intro_text = fetch_intro_from_arxiv_html(paper_id)
        time.sleep(1)  # ar5iv rate limit 방지

        candidates.append({
            "id": paper_id,
            "title": title,
            "summary": summary,
            "intro": intro_text,  # NEW: intro 텍스트
            "authors": [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)],
            "abs_url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
            "score": score,
            "is_vvip": is_vvip,
            "institution": institution_found,
            "raw_institutions": raw_institutions,  # 디버깅용
        })
        time.sleep(1)  # Semantic Scholar rate limit 방지

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]


# ════════════════════════════════════════════════════
# ✏️ 프롬프트 정의
# ════════════════════════════════════════════════════

DOMAIN_GUIDES = {
    "cs.AI": """[Focus: Agent Autonomy & Reasoning]
- 에이전트의 '자가 수정(Self-correction)' 및 '추론 루프'의 구조적 혁신을 분석하세요.
- 단순히 성능이 좋은지가 아니라, 에이전트가 오류를 어떻게 감지하고 진화하는지에 집중하세요.""",

    "cs.LG": """[Focus: Memory & Learning Efficiency]
- 방대한 정보를 어떻게 압축하고(Compression), 필요한 시점에 어떻게 검색하는지(Retrieval) 분석하세요.
- '장기 기억' 유지 시 발생하는 정보 오염이나 망각 문제를 해결했는지 확인하세요.""",

    "cs.RO": """[Focus: Embodiment & Action]
- 고수준 명령(언어)이 물리적 행동(Action)으로 변환되는 VLA(Vision-Language-Action) 정렬 방식을 분석하세요.
- 시뮬레이션과 실제 환경(Sim-to-Real) 간의 간극을 어떻게 줄였는지 주목하세요."""
}

STYLE_PROMPTS = {
    "technical": """당신은 리서치 분야의 권위자입니다. 다음 지침을 엄수하여 리뷰를 작성하세요:
1. # 헤더 절대 사용 금지. 오직 **볼드**만 사용.
2. 각 논문의 전문 분야(Category)에 특화된 깊이 있는 분석을 제공할 것.
3. 제공된 '기관 명성'과 '유망 점수'를 참고하여 이 연구의 위상을 서두에 언급할 것.
4. 줄바꿈 주의.
5. 모든 문장은 직관적이고, 간결하고, 핵심만 담으며, 기술용어는 그대로 사용할 것.

**한 줄 요약**: [20자 내외, 핵심 동작 원리 중심]

**Background**: [분야의 흐름 + 기존 연구의 한계점 2~3문장]

**핵심 아이디어**
- **구조적 차별점**: [기존과 다른 알고리즘/아키텍처 설계 2~3문장]
- **직관적 비유**: [이 논문의 핵심 원리를 쉬운 예시로 설명 2~3문장]

**왜 중요한가**: [실용적 임팩트 및 연구 트렌드에서의 위치 1~2문장]

**Research Questions**
*Q1: [핵심 질문]* A1: [답변]
*Q2: [실험 질문]* A2: [답변]
*Q3: [확장성 질문]* A3: [답변]

**실험 결과**: [데이터셋 + Baseline 대비 수치 + 핵심 실험 결과]
**한계**: [저자가 인정한 제약 혹은 잠재적 위험]
**재현성**: 코드 공개: [O/X] | [컴퓨팅 자원 정보]"""
}


# ════════════════════════════════════════════════════
# 🧠 AI 리뷰 생성
# ════════════════════════════════════════════════════

def review_paper_with_cache(paper: dict, category_id: str, client: anthropic.Anthropic) -> str:
    domain_guide = DOMAIN_GUIDES.get(category_id, "일반적인 AI 기술 분석에 집중하세요.")

    inst_info = f"기관: {paper['institution']}" if paper['institution'] else "기관 정보 없음"
    if paper['is_vvip']:
        inst_info += " (업계 최고 권위 연구소)"

    # ✅ Abstract + Intro 모두 활용
    abstract_text = paper['summary'][:1500]
    intro_text = paper.get('intro', '')
    intro_section = f"\nIntroduction (요약):\n{intro_text[:800]}" if intro_text else ""

    try:
        message = client.messages.create(
            model=MODEL_API[MODEL_NAME],
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{STYLE_PROMPTS['technical']}\n\n[Domain Guide]\n{domain_guide}",
                            "cache_control": {"type": "ephemeral"}
                        },
                        {
                            "type": "text",
                            "text": (
                                f"\n\n[Input Paper Context]\n"
                                f"{inst_info}\n"
                                f"Title: {paper['title']}\n"
                                f"Abstract:\n{abstract_text}"
                                f"{intro_section}\n\n"
                                f"리뷰 시작:"
                            )
                        }
                    ]
                }
            ],
        )
        return sanitize_for_hugo(message.content[0].text)
    except Exception as e:
        print(f"  ❌ Claude API 에러: {e}")
        return "리뷰 생성 실패"


# ════════════════════════════════════════════════════
# 🛠️ 공통 유틸리티
# ════════════════════════════════════════════════════

def sanitize_for_hugo(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\{\{.*?\}\}', '', text, flags=re.DOTALL)
    text = re.sub(r'^#{1,6}\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
    return text


def sanitize_title(title: str) -> str:
    return re.sub(r'\{.*?\}', '', title).replace('"', '\\"').replace("|", "-").strip()


# ════════════════════════════════════════════════════
# 💾 저장
# ════════════════════════════════════════════════════

def save_daily_digest(date_str: str, sections: dict, reviews: dict):
    today_kst = datetime.now(KST).strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in sections.values())

    cat_names = [cat['name'].split(' ')[-1] for cat in CONFIG["categories"] if sections.get(cat['name'])]
    cat_str = " · ".join(cat_names)
    summary_text = f"{cat_str} 분야 유망 논문 {total}편 | {MODEL_NAME} 자동 분석"

    toc_rows = []
    idx = 1
    for cat_name, papers in sections.items():
        for p in papers:
            title = p['title'][:55] + "..." if len(p['title']) > 55 else p['title']
            toc_rows.append(f"| {idx} | {cat_name} | {title.replace('|', '-')} |")
            idx += 1
    toc_str = "| # | 분야 | 제목 |\n|---|------|------|\n" + "\n".join(toc_rows)

    body_parts = []
    idx = 1
    for cat_name, papers in sections.items():
        if not papers:
            continue
        body_parts.append(f"\n---\n\n**{cat_name}**\n")
        for p, r in zip(papers, reviews[cat_name]):
            body_parts.append(f"\n**{idx}. {sanitize_title(p['title'])}**\n")
            body_parts.append(
                f"\n**저자**: {', '.join(p['authors'][:3])} | "
                f"[원문]({p['abs_url']}) | [PDF]({p['pdf_url']})\n\n{r}\n"
            )
            idx += 1

    ai_model_notice = (
        f"\n\n---\n\n"
        f"*본 리포트의 논문 리뷰는 Anthropic의 **{MODEL_NAME}** 모델을 사용하여 자동 생성되었습니다.*"
    )

    content = f"""---
title: "논문 Daily Digest {today_kst} ({total}편)"
date: {date_str}T00:00:00+09:00
draft: false
summary: "{summary_text}"
tags: ["Daily", "AI", "Research"]
---

**목차**

{toc_str}

{"".join(body_parts)}

{ai_model_notice}
"""

    post_dir = Path(f"content/post/{date_str}-digest")
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / "index.md").write_text(content, encoding="utf-8")
    print(f"  💾 저장 완료: {post_dir / 'index.md'}")


# ════════════════════════════════════════════════════
# 🚀 Main
# ════════════════════════════════════════════════════

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 환경변수 없음")
        return

    client = anthropic.Anthropic(api_key=api_key)
    now_kst = datetime.now(KST)
    cutoff = now_kst - timedelta(days=CONFIG["days_back"])

    history_path = Path("data/reviewed_ids.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed_ids: set = set(json.loads(history_path.read_text())) if history_path.exists() else set()

    sections: dict = {}
    reviews_dict: dict = {}

    for cat_config in CONFIG["categories"]:
        name = cat_config["name"]
        print(f"\n📡 [{name}] 검색 중...")

        # ✅ fetch 단계에서는 reviewed_ids 필터 없이 전체 후보 수집
        all_papers = fetch_papers_by_category(cat_config, cutoff)

        # ✅ reviewed_ids 필터는 fetch 이후에 적용 (papers_per_day 제한 전)
        new_papers = [p for p in all_papers if p["id"] not in reviewed_ids]

        sections[name] = []
        reviews_dict[name] = []

        for paper in new_papers:
            print(f"  📝 리뷰 생성: {paper['title'][:55]}...")
            review = review_paper_with_cache(paper, cat_config["category"], client)
            sections[name].append(paper)
            reviews_dict[name].append(review)
            reviewed_ids.add(paper["id"])
            time.sleep(1)

    total = sum(len(v) for v in sections.values())
    if total > 0:
        date_str = now_kst.strftime("%Y-%m-%d")
        save_daily_digest(date_str, sections, reviews_dict)
        history_path.write_text(json.dumps(list(reviewed_ids), indent=2))
        print(f"\n🎉 완료! 총 {total}편 처리.")
    else:
        print("\n📭 오늘 업데이트할 새 논문이 없습니다.")


if __name__ == "__main__":
    main()
