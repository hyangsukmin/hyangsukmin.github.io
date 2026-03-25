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
            "category": "cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 4,
            "keywords": ["dialogue", "conversation", "streaming", "summarization", "llm", "long-term", "memory"],
        },
        {
            "name": "🔄 Long-horizon",
            "category": "cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 4,
            "keywords": [
                "long-horizon", "memory", "llm", "large language model", "agent", "reasoning"
            ],
        },
        {
            "name": "🧠 Lifelong & Long-range Memory",
            "category": "cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 4,
            "keywords": [
                "lifelong learning", "continual learning", "long-horizon",
                "long-horizon reasoning", "long-horizon planning", "long-term memory",
                "episodic memory", "memory retrieval", "memory consolidation",
                "memory management", "hierarchical memory", "agent memory",
                "memory bank", "dynamic memory", "memory dynamic",
            ],
        },
        {
            "name": "🦾 Robotics & Embodied AI",
            "category": "cs.RO OR cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 2,
            "keywords": [
                "robotics", "embodied AI", "robotics memory", "learning from historic errors",
                "VLA", "manipulation", "benchmark", "vision-language-action",
            ],
        },
        {
            "name": "🌟 VVIP Intelligence (Global Top Labs)",
            "category": "cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 3,
            "keywords": [],
            "is_vvip_only": True,
        },
        {
            "name": "👤 VIP Authors Track",
            "category": "cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 5,
            "keywords": [],
            "is_vip_author_only": True,
        },
    ],
    # days_back은 페이지네이션 중단 조건으로만 사용
    # 실제로는 cutoff 이전 논문이 나오면 수집 중단
    "days_back": 720,
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
    "Yonsei", "Korea University", "KIST", "Upstage", "Lunit", "Rebellions", "FuriosaAI",
]

VVIP_LABS = [
    "OpenAI", "DeepMind", "Google DeepMind", "Kimi Team", "Moonshot AI",
    "Meta", "FAIR", "NVIDIA", "Anthropic",
]

TOP_CONFERENCES = [
    "ICLR", "NeurIPS", "ICML", "CVPR", "ECCV", "ICRA", "RSS",
    "AAAI", "IJCAI", "ACL", "EMNLP", "NAACL", "COLM",
]

VIP_AUTHORS = [
    "Andrej Karpathy", "Noam Shazeer", "Ilya Sutskever", "Yann LeCun",
    "Geoffrey Hinton", "Yoshua Bengio", "Andrew Ng", "Jim Fan",
    "Sergey Levine", "Chelsea Finn", "Joon Sung Park",
]

DOMAIN_GUIDES = {
    "cs.AI": """[Focus: Agent Autonomy & Reasoning]
- 에이전트의 '자가 수정(Self-correction)' 및 '추론 루프'의 구조적 혁신을 분석하세요.
- 단순히 성능이 좋은지가 아니라, 에이전트가 오류를 어떻게 감지하고 진화하는지에 집중하세요.""",
    "cs.LG": """[Focus: Memory & Learning Efficiency]
- 방대한 정보를 어떻게 압축하고(Compression), 필요한 시점에 어떻게 검색하는지(Retrieval) 분석하세요.
- '장기 기억' 유지 시 발생하는 정보 오염이나 망각 문제를 해결했는지 확인하세요.""",
    "cs.RO": """[Focus: Embodiment & Action]
- 고수준 명령(언어)이 물리적 행동(Action)으로 변환되는 VLA(Vision-Language-Action) 정렬 방식을 분석하세요.
- 시뮬레이션과 실제 환경(Sim-to-Real) 간의 간극을 어떻게 줄였는지 주목하세요.""",
}

# ════════════════════════════════════════════════════
# 📝 프롬프트 (6-레이어 구조)
# ════════════════════════════════════════════════════

STYLE_PROMPTS = {
    "technical": """당신은 AI/ML 연구를 깊이 있게 분석하는 리서치 커뮤니케이터입니다.
아래 논문을 다음 6개 섹션으로 작성하세요.
각 섹션은 비전공자가 읽어도 맥락을 이해할 수 있고, 전공자가 읽어도 깊이가 충분해야 합니다.

작성 규칙:
- # 헤더 절대 사용 금지. 오직 **볼드**만 사용.
- 전문 용어는 유지하되, 첫 등장 시 괄호 안에 한 줄 설명 추가.
  예: 대조학습(contrastive learning: 유사한 샘플은 가깝게, 다른 샘플은 멀게 표현을 학습하는 방법)
- 수치는 반드시 맥락과 함께: "ICC 86%" → "5명 환자 데이터만으로 전문가 일치도 ICC 86% 달성"
- 줄바꿈 주의. 섹션 간 한 줄 공백.

**한 줄 요약**: [핵심 기여를 20자 내외로. 동작 원리 중심.]

**[왜 어려운 문제인가]**: 이 연구가 해결하려는 현실적 병목을 서술하세요.
비전공자는 "이게 왜 어렵고 중요한지"를 납득할 수 있어야 하고,
전공자는 research gap과 기존 접근의 한계를 정확히 파악할 수 있어야 합니다. (3~4문장)

**[선행 연구와의 관계]**: 이 논문이 어떤 연구 흐름 위에 있는지,
기존 방법들(논문명 또는 방법명 명시)이 왜 불충분했는지를 서술하세요.
전공자가 이 논문의 포지셔닝을 즉시 파악할 수 있어야 합니다. (2~3문장)

**[핵심 기여]**
- **직관**: 비유 하나로 핵심 원리를 설명. 비유는 반드시 "왜 기존보다 나은지"까지 연결될 것.
- **기술적 delta**: 기존 방법과 이 논문의 차이를 한 문장으로 명시.
  예: "Rank-N-Contrast의 레이블 기반 순위를 → 방문 시간 순서로 대체"

**[설계 선택과 tradeoff]**: 왜 이 방법을 선택했는지, 그 선택이 만드는 한계를 함께 서술.
"이 방법이 강력한 조건"과 "이 방법이 실패하는 조건"을 명시하세요. (2~3문장)

**[실험]**: 데이터셋, baseline, 핵심 수치를 맥락과 함께 서술.
ablation이 있다면 어떤 설계 요소의 기여를 분리 검증했는지 한 줄로 설명하세요.

**[이 분야에서의 위치]**: 성능 수치가 아닌, 이 논문이 해당 분야의 방향을 어떻게 바꾸는지.
어떤 후속 연구나 실용화 경로로 이어질 수 있는지를 마지막 문장으로 마무리하세요.

**재현성**: 코드 공개: [O/X] | [컴퓨팅 자원 정보]"""
}

CATEGORY_SUMMARY_PROMPT = """당신은 AI 연구를 깊이 있게 전달하는 과학 커뮤니케이터입니다.

아래는 오늘 [{category_name}] 분야에서 주목할 논문들입니다.
이 논문들을 바탕으로, 오늘의 핵심 흐름을 하나의 이야기로 엮어 작성하세요.

작성 규칙:
- 친한 선배가 설명해주는 구어체 톤
- 각 논문을 개별 나열하지 말고, 오늘의 공통 테마나 흐름으로 엮을 것
- 전문 용어는 쉬운 말로 풀되, 기술적 맥락은 희석하지 말 것
  예: "자기지도학습"을 "레이블 없이 스스로 패턴을 배우는 방법"으로 풀되,
      "그래서 annotation 비용 없이도 쓸 수 있다"는 함의는 유지
- **3~5문장**, 마지막 문장은 이 흐름이 왜 중요한지 전망으로 마무리
- # 헤더 금지, **볼드**는 핵심 키워드에만 최소한으로

논문 목록:
{papers_text}

오늘의 핵심 인사이트 (3~5문장):"""


# ════════════════════════════════════════════════════
# 🔤 유연한 키워드 매칭
# ════════════════════════════════════════════════════

KEYWORD_SYNONYMS = {
    "dialogue":               ["dialog", "dialogues", "dialogs", "conversational"],
    "conversation":           ["conversations", "conversational", "chat", "discourse"],
    "summarization":          ["summarizing", "summarize", "summary", "summaries", "abstractive"],
    "llm":                    ["large language model", "language model", "gpt", "bert", "transformer"],
    "memory":                 ["memorization", "memorize", "memories", "memoization"],
    "agent":                  ["agents", "agentic", "autonomous agent", "multi-agent"],
    "self-evolving":          ["self-evolution", "self-evolved", "self evolving"],
    "self-improvement":       ["self-improve", "self-improved", "self improving"],
    "self-reflection":        ["self-reflect", "self-reflected", "self reflecting"],
    "self-correction":        ["self-correct", "self-corrected", "self correcting", "error correction"],
    "continual learning":     ["continuous learning", "incremental learning", "online learning"],
    "lifelong learning":      ["lifelong", "life-long learning", "perpetual learning"],
    "long-horizon":           ["long horizon", "long-term planning", "extended horizon"],
    "long-term memory":       ["long term memory", "persistent memory", "long-range memory"],
    "episodic memory":        ["episodic", "episode memory", "experience replay"],
    "memory retrieval":       ["retrieval memory", "memory recall", "retrieve memory"],
    "embodied AI":            ["embodied intelligence", "embodied agent", "physical AI"],
    "manipulation":           ["grasping", "robotic manipulation", "dexterous manipulation"],
    "vision-language-action": ["VLA model", "vision language action"],
    "benchmark":              ["benchmarks", "benchmarking", "evaluation suite", "leaderboard"],
}


def fuzzy_match(word, keyword, threshold=0.82):
    if len(keyword) <= 4:
        return word == keyword
    return SequenceMatcher(None, word, keyword).ratio() >= threshold


def flexible_keyword_match(text, keywords, min_match=2):
    text_lower = text.lower()
    words = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', text_lower)
    matched = 0
    for kw in keywords:
        kw_lower = kw.lower()
        found = False
        if kw_lower in text_lower:
            found = True
        if not found:
            for synonym in KEYWORD_SYNONYMS.get(kw_lower, []):
                if synonym.lower() in text_lower:
                    found = True
                    break
        if not found and " " not in kw_lower and "-" not in kw_lower:
            for word in words:
                if fuzzy_match(word, kw_lower):
                    found = True
                    break
        if found:
            matched += 1
    return matched


def detect_vip_author(paper_authors):
    found_authors = []
    for paper_auth in paper_authors:
        for vip_auth in VIP_AUTHORS:
            if vip_auth.lower() in paper_auth.lower():
                found_authors.append(vip_auth)
    return list(set(found_authors))


# ════════════════════════════════════════════════════
# 🏛️ 기관 정보 수집 — S2 우선, ar5iv fallback
# ════════════════════════════════════════════════════

def fetch_affiliations_from_s2(arxiv_id: str) -> list[str]:
    """
    Semantic Scholar API로 기관 정보 조회.
    최신 논문도 arXiv 제출 당일~익일 내 인덱싱되는 경우가 많음.
    rate limit: 100 req/5min (unauthenticated)
    """
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
    params = {"fields": "authors.affiliations,authors.name"}
    try:
        resp = requests.get(url, params=params, timeout=12,
                            headers={"User-Agent": "daily-digest-bot/1.0"})
        if resp.status_code == 429:
            print("    [S2] rate limit — 60초 대기")
            time.sleep(60)
            resp = requests.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
        affiliations = []
        for author in data.get("authors", []):
            for aff in author.get("affiliations", []):
                if aff and aff not in affiliations:
                    affiliations.append(aff)
        return affiliations
    except Exception as e:
        print(f"    [S2] 요청 실패 ({arxiv_id}): {e}")
        return []


def fetch_affiliation_and_intro_ar5iv(arxiv_id: str, max_intro_chars: int = 1500) -> tuple[list, str]:
    """
    ar5iv HTML에서 기관 + Introduction 동시 파싱.
    최신 논문은 변환 미완료일 수 있으므로 S2 실패 시 fallback으로만 사용.
    """
    url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return [], ""
        html = resp.text
    except Exception as e:
        print(f"    [ar5iv] 요청 실패 ({arxiv_id}): {e}")
        return [], ""

    # Affiliation 파싱
    aff_pattern = re.compile(
        r'<(?:span|div)[^>]*?class="[^"]*(?:ltx_role_affiliation|ltx_affiliation)[^"]*"[^>]*?>'
        r'(.*?)</(?:span|div)>',
        re.IGNORECASE | re.DOTALL,
    )
    institutions = []
    for raw in aff_pattern.findall(html):
        clean_aff = re.sub(r"<[^>]+>", " ", raw)
        clean_aff = re.sub(r"\s+", " ", clean_aff).strip()
        clean_aff = re.sub(r"^\d+\s*", "", clean_aff).strip()
        if clean_aff and clean_aff not in institutions and len(clean_aff) > 3:
            institutions.append(clean_aff)

    # Introduction 파싱
    intro_text = ""
    intro_pattern = re.compile(
        r'<section[^>]*?id=["\']S1["\'][^>]*?>(.*?)</section>',
        re.IGNORECASE | re.DOTALL,
    )
    match = intro_pattern.search(html)
    if match:
        snippet = match.group(1)
    else:
        idx = html.lower().find(">introduction<")
        snippet = html[idx:idx + 8000] if idx != -1 else ""

    if snippet:
        intro_text = re.sub(r"<[^>]+>", " ", snippet)
        intro_text = re.sub(r"\s+", " ", intro_text).strip()
        intro_text = intro_text[:max_intro_chars]

    return institutions, intro_text


def get_affiliations_with_fallback(arxiv_id: str) -> tuple[list, str]:
    """
    S2 → ar5iv 순서로 기관 정보 조회.
    S2에서 기관을 찾으면 ar5iv는 Introduction 파싱에만 사용.
    """
    # 1) S2로 기관 정보 시도
    s2_affiliations = fetch_affiliations_from_s2(arxiv_id)
    time.sleep(0.5)  # S2 rate limit 보호

    # 2) ar5iv로 Introduction 파싱 (기관 정보 보완 포함)
    ar5iv_affiliations, intro_text = fetch_affiliation_and_intro_ar5iv(arxiv_id)

    # S2가 비어있으면 ar5iv 기관 정보 사용
    affiliations = s2_affiliations if s2_affiliations else ar5iv_affiliations
    return affiliations, intro_text


def detect_institution_from_list(institution_list: list) -> tuple[str, bool]:
    """VVIP_LABS / TOP_INSTITUTIONS 매칭. Returns: (기관명, is_vvip)"""
    joined = " ".join(institution_list).lower()
    for inst in VVIP_LABS:
        if inst.lower() in joined:
            return inst, True
    for inst in TOP_INSTITUTIONS:
        if inst.lower() in joined:
            return inst, False
    return "", False


def detect_vvip_from_abstract(title: str, summary: str) -> tuple[str, bool]:
    """
    abstract/title 텍스트에서 VVIP 기관명 직접 감지.
    arXiv abstract에 소속 기관을 명시하는 논문(특히 산업계)에 유효.
    """
    text = (title + " " + summary).lower()
    for lab in VVIP_LABS:
        if lab.lower() in text:
            return lab, True
    return "", False


# ════════════════════════════════════════════════════
# 📡 arXiv 페이지네이션 수집
# ════════════════════════════════════════════════════

def parse_arxiv_entries(xml_content: bytes, ns: dict) -> list:
    """arXiv API XML 응답을 파싱하여 entry 리스트 반환"""
    root = ET.fromstring(xml_content)
    entries = []
    for entry in root.findall("atom:entry", ns):
        published_el = entry.find("atom:published", ns)
        if published_el is None:
            continue
        published = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        paper_id = entry.find("atom:id", ns).text.split("/abs/")[-1]

        # arXiv author affiliation 태그 시도 (일부 논문에만 존재)
        inline_affiliations = []
        for author in entry.findall("atom:author", ns):
            aff = author.find("atom:affiliation", ns)
            if aff is not None and aff.text:
                inline_affiliations.append(aff.text)

        entries.append({
            "id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "published": published,
            "inline_affiliations": inline_affiliations,
            "abs_url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
        })
    return entries


def fetch_arxiv_paginated(query: str, cutoff: datetime,
                          max_per_page: int = 200, max_pages: int = 15) -> list:
    """
    cutoff 날짜까지 arXiv API를 페이지네이션으로 수집.
    - max_per_page * max_pages = 최대 3000건까지 탐색 가능
    - cutoff 이전 논문이 처음 등장하면 즉시 중단 (submittedDate 내림차순)
    - arXiv API 권장 대기: 페이지 간 3초
    """
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    all_entries = []

    for page in range(max_pages):
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": page * max_per_page,
            "max_results": max_per_page,
        }
        try:
            resp = requests.get("https://export.arxiv.org/api/query",
                                params=params, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"    [arXiv] 페이지 {page} 요청 실패: {e}")
            break

        entries = parse_arxiv_entries(resp.content, ns)
        if not entries:
            print(f"    [arXiv] 페이지 {page}: 결과 없음, 중단")
            break

        reached_cutoff = False
        for entry in entries:
            if entry["published"] < cutoff:
                reached_cutoff = True
                break
            all_entries.append(entry)

        print(f"    [arXiv] 페이지 {page}: {len(entries)}건 수집, 누적 {len(all_entries)}건")

        if reached_cutoff:
            print(f"    [arXiv] cutoff({cutoff.date()}) 도달, 수집 중단")
            break

        time.sleep(3)  # arXiv API 매너 대기

    return all_entries


# ════════════════════════════════════════════════════
# 🔍 논문 수집 및 스코어링
# ════════════════════════════════════════════════════

def score_paper(paper: dict, keywords: list, is_vvip_only: bool,
                is_vip_author_only: bool) -> int:
    """논문 관련성 점수 계산"""
    score = 0
    text = paper["title"] + " " + paper["summary"]

    # VIP 저자 점수 (최우선)
    if paper.get("matched_vips"):
        score += 5000

    # VVIP 기관 (abstract 텍스트 기반 선제 감지)
    _, is_vvip_text = detect_vvip_from_abstract(paper["title"], paper["summary"])
    if is_vvip_text:
        score += 3000

    # 키워드 점수
    if keywords:
        score += flexible_keyword_match(text, keywords) * 10

    # 코드 공개 보너스
    if any(x in text.lower() for x in ["github.com", "code available", "code is available"]):
        score += 50

    # 최신성 보너스 (최근 7일 논문 우대)
    days_old = (datetime.now(KST) - paper["published"]).days
    if days_old <= 7:
        score += 30
    elif days_old <= 30:
        score += 10

    return score


def fetch_papers_by_category(cat_config: dict, cutoff: datetime) -> list:
    """
    카테고리 설정에 따라 논문 수집 → 스코어링 → 상세 정보(기관/Intro) 보강 → 상위 N편 반환.

    개선 사항:
    1. 페이지네이션으로 cutoff까지 전수 수집
    2. VVIP 모드: abstract 텍스트 선제 감지 → S2 → ar5iv 순 fallback
    3. 일반 모드: S2 우선 기관 정보 + ar5iv Introduction
    4. ar5iv 확인 대상을 상위 20→50개로 확장
    """
    keywords = cat_config.get("keywords", [])
    limit = cat_config["papers_per_day"]
    is_vvip_only = cat_config.get("is_vvip_only", False)
    is_vip_author_only = cat_config.get("is_vip_author_only", False)
    category = cat_config["category"]

    # ── 1. 쿼리 생성 ──
    if is_vip_author_only:
        author_queries = [f"au:{auth.replace(' ', '_')}" for auth in VIP_AUTHORS[:15]]
        query = f"({'  OR '.join(author_queries)}) AND ({category})"
    elif is_vvip_only:
        # VVIP 기관명을 abstract 검색에 직접 포함 → 정밀도 향상
        lab_queries = [f'abs:"{lab}"' for lab in VVIP_LABS]
        query = f"({'  OR '.join(lab_queries)}) AND ({category})"
    else:
        terms = [f"(ti:{kw} OR abs:{kw})" for kw in keywords]
        query = "(" + " OR ".join(terms) + ") AND (" + category + ")"

    print(f"    쿼리: {query[:120]}...")

    # ── 2. 페이지네이션 수집 ──
    # VVIP/VIP 모드는 더 많이 탐색, 일반 모드는 제한
    max_pages = 5 if (is_vvip_only or is_vip_author_only) else 3
    raw_entries = fetch_arxiv_paginated(query, cutoff, max_per_page=200, max_pages=max_pages)

    if not raw_entries:
        return []

    # ── 3. VIP 저자 감지 및 초기 필터링 ──
    candidates = []
    for entry in raw_entries:
        matched_vips = detect_vip_author(entry["authors"])
        if is_vip_author_only and not matched_vips:
            continue
        entry["matched_vips"] = matched_vips
        entry["score"] = score_paper(entry, keywords, is_vvip_only, is_vip_author_only)
        candidates.append(entry)

    # ── 4. 점수 기준 정렬 ──
    candidates.sort(key=lambda x: x["score"], reverse=True)
    print(f"    후보 {len(candidates)}건, 상위 점수: {[c['score'] for c in candidates[:5]]}")

    # ── 5. 상위 후보 상세 정보 보강 (기관 + Introduction) ──
    # VVIP 모드는 더 많이 확인 (50개), 일반은 30개
    check_count = 50 if (is_vvip_only or is_vip_author_only) else 30
    final_candidates = []

    for paper in candidates[:check_count]:
        # 5-1. abstract 텍스트에서 VVIP 선제 감지
        inst_from_text, is_vvip_text = detect_vvip_from_abstract(paper["title"], paper["summary"])

        # 5-2. inline affiliation (arXiv entry 태그)
        inst_from_inline, is_vvip_inline = detect_institution_from_list(
            paper.get("inline_affiliations", [])
        )

        # 5-3. S2 + ar5iv fallback으로 상세 기관 정보 조회
        affiliations, intro_text = get_affiliations_with_fallback(paper["id"])
        inst_from_api, is_vvip_api = detect_institution_from_list(affiliations)

        # 5-4. 최종 기관 결정 (우선순위: API > inline > 텍스트)
        if inst_from_api:
            inst_name, is_vvip = inst_from_api, is_vvip_api
        elif inst_from_inline:
            inst_name, is_vvip = inst_from_inline, is_vvip_inline
        elif inst_from_text:
            inst_name, is_vvip = inst_from_text, is_vvip_text
        else:
            inst_name, is_vvip = "", False

        # 5-5. VVIP 전용 모드 필터링
        if is_vvip_only and not is_vvip:
            print(f"    [VVIP 필터] 제외: {paper['title'][:50]}")
            time.sleep(0.3)
            continue

        paper.update({
            "institution": inst_name,
            "is_vvip": is_vvip,
            "intro": intro_text,
        })
        final_candidates.append(paper)
        print(f"    ✓ 선정: [{inst_name or '기관미상'}] {paper['title'][:50]}")

        if len(final_candidates) >= limit:
            break

        time.sleep(1.0)  # S2 + ar5iv 연속 요청 보호

    return final_candidates


# ════════════════════════════════════════════════════
# 🧠 AI 리뷰 생성
# ════════════════════════════════════════════════════

def review_paper_with_cache(paper: dict, category_id: str, client) -> str:
    domain_guide = DOMAIN_GUIDES.get(category_id, "일반적인 AI 기술 분석에 집중하세요.")

    inst_info = "기관: " + paper["institution"] if paper["institution"] else "기관 정보 없음"
    if paper["is_vvip"]:
        inst_info += " (업계 최고 권위 연구소)"

    vip_info = ""
    if paper.get("matched_vips"):
        vip_info = f"\n[Special Note] This paper is authored by: {', '.join(paper['matched_vips'])}"

    intro_section = "\nIntroduction (요약):\n" + paper["intro"] if paper.get("intro") else ""

    try:
        message = client.messages.create(
            model=MODEL_API[MODEL_NAME],
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": STYLE_PROMPTS["technical"] + "\n\n[Domain Guide]\n" + domain_guide,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "\n\n[Input Paper Context]\n"
                                + inst_info + "\n"
                                + vip_info + "\n"
                                + "Title: " + paper["title"] + "\n"
                                + "Abstract:\n" + paper["summary"]
                                + intro_section + "\n\n리뷰 시작:"
                            ),
                        },
                    ],
                }
            ],
        )
        return sanitize_for_hugo(message.content[0].text)
    except Exception as e:
        print(f"  Claude API 에러: {e}")
        return "리뷰 생성 실패"


# ════════════════════════════════════════════════════
# 📝 카테고리 요약 생성
# ════════════════════════════════════════════════════

def generate_category_summary(cat_name: str, papers: list, client) -> str:
    if not papers:
        return ""

    papers_text = ""
    for i, p in enumerate(papers, 1):
        papers_text += f"{i}. 제목: {p['title']}\n   요약: {p['summary'][:300]}\n\n"

    prompt = CATEGORY_SUMMARY_PROMPT.format(
        category_name=cat_name,
        papers_text=papers_text,
    )

    try:
        message = client.messages.create(
            model=MODEL_API[MODEL_NAME],
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return sanitize_for_hugo(message.content[0].text)
    except Exception as e:
        print(f"  카테고리 요약 생성 실패 ({cat_name}): {e}")
        return ""


# ════════════════════════════════════════════════════
# 🛠️ 유틸리티
# ════════════════════════════════════════════════════

def sanitize_for_hugo(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"**\1**", text, flags=re.MULTILINE)
    return text


def sanitize_title(title: str) -> str:
    return re.sub(r"\{.*?\}", "", title).replace('"', '\\"').replace("|", "-").strip()


# ════════════════════════════════════════════════════
# 💾 저장
# ════════════════════════════════════════════════════

def save_daily_digest(date_str: str, sections: dict, reviews: dict,
                      category_summaries: dict):
    today_kst = datetime.now(KST).strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in sections.values())

    cat_names = [cat["name"].split(" ")[-1] for cat in CONFIG["categories"] if sections.get(cat["name"])]
    summary_text = " · ".join(cat_names) + f" 분야 유망 논문 {total}편 | {MODEL_NAME} 자동 분석"

    # 목차 생성
    toc_rows = []
    idx = 1
    for cat_name, papers in sections.items():
        for p in papers:
            anchor = f"paper{idx}"
            toc_rows.append(
                f"| {idx} | {cat_name} | [{p['title'].replace('|', '-')}](#{anchor}) |"
            )
            idx += 1

    toc_str = (
        '<div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">\n\n'
        "| # | 분야 | 제목 |\n|---|------|------|\n"
        + "\n".join(toc_rows)
        + "\n\n</div>"
    )

    # 본문 생성
    body_parts = []
    idx = 1
    for cat_name, papers in sections.items():
        if not papers:
            continue
        body_parts.append(f"\n---\n\n**{cat_name}**\n")

        summary = category_summaries.get(cat_name, "")
        if summary:
            body_parts.append(f"\n> 💡 {summary}\n")

        for p, r in zip(papers, reviews[cat_name]):
            anchor = f"paper{idx}"
            body_parts.append(f'\n<a id="{anchor}"></a>\n**{idx}. {sanitize_title(p["title"])}**\n')
            body_parts.append(
                f"\n**저자**: {', '.join(p['authors'][:3])}"
                f" | [원문]({p['abs_url']}) | [PDF]({p['pdf_url']})\n\n{r}\n"
            )
            idx += 1

    ai_notice = f"\n\n---\n\n*본 리포트의 논문 리뷰는 Anthropic의 **{MODEL_NAME}** 모델을 사용하여 자동 생성되었습니다.*"

    content = (
        "---\n"
        f'title: "논문 Daily Digest {today_kst} ({total}편)"\n'
        f"date: {date_str}T00:00:00+09:00\n"
        "draft: false\n"
        f'summary: "{summary_text}"\n'
        'tags: ["Daily", "AI", "Research"]\n'
        "---\n\n"
        "**목차**\n\n"
        + toc_str + "\n\n"
        + "".join(body_parts)
        + ai_notice + "\n"
    )

    # 중복 방지 경로 생성
    base_dir = Path("content/post")
    post_dir = base_dir / f"{date_str}-digest"
    counter = 0
    final_post_dir = post_dir
    while final_post_dir.exists():
        counter += 1
        final_post_dir = base_dir / f"{date_str}-digest_{counter}"

    final_post_dir.mkdir(parents=True, exist_ok=True)
    file_path = final_post_dir / "index.md"
    file_path.write_text(content, encoding="utf-8")
    print(f"✅ 저장 완료: {file_path}")


# ════════════════════════════════════════════════════
# 🚀 Main
# ════════════════════════════════════════════════════

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY 환경변수 없음")
        return

    client = anthropic.Anthropic(api_key=api_key)
    now_kst = datetime.now(KST)
    cutoff = now_kst - timedelta(days=CONFIG["days_back"])

    history_path = Path("data/reviewed_ids.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed_ids = (
        set(json.loads(history_path.read_text())) if history_path.exists() else set()
    )

    sections: dict = {}
    reviews_dict: dict = {}
    category_summaries: dict = {}

    for cat_config in CONFIG["categories"]:
        name = cat_config["name"]
        print(f"\n{'='*60}")
        print(f"[{name}] 수집 시작")
        print(f"{'='*60}")

        all_papers = fetch_papers_by_category(cat_config, cutoff)
        new_papers = [p for p in all_papers if p["id"] not in reviewed_ids]

        sections[name] = []
        reviews_dict[name] = []

        for paper in new_papers:
            print(f"  리뷰 생성: {paper['title'][:60]}...")
            review = review_paper_with_cache(paper, cat_config["category"], client)
            sections[name].append(paper)
            reviews_dict[name].append(review)
            reviewed_ids.add(paper["id"])
            time.sleep(1)

        if sections[name]:
            print(f"  카테고리 요약 생성 중: {name}")
            category_summaries[name] = generate_category_summary(name, sections[name], client)
        else:
            category_summaries[name] = ""

        print(f"  → {len(sections[name])}편 완료")

    total = sum(len(v) for v in sections.values())
    if total > 0:
        date_str = now_kst.strftime("%Y-%m-%d")
        save_daily_digest(date_str, sections, reviews_dict, category_summaries)
        history_path.write_text(json.dumps(list(reviewed_ids), indent=2))
        print(f"\n✅ 완료! 총 {total}편 처리.")
    else:
        print("\n오늘 업데이트할 새 논문이 없습니다.")


if __name__ == "__main__":
    main()
