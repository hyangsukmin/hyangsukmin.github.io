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
        # {
        #     "name": "🔄 Self-Evolving & Agents",
        #     "category": "cs.AI OR cat:cs.CL OR cat:cs.LG",
        #     "papers_per_day": 2,
        #     "keywords": [
        #         "self-evolving", "self-improvement", "self-reflection", "self-correction",
        #         "error correction reasoning", "iterative refinement", "adaptive agent",
        #         "learning from mistakes", "continual learning", "agent", "self-training",
        #     ],
        # },
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
            "keywords": [], # 키워드 제한 없음
            "is_vvip_only": True # 로직 구분을 위한 플래그
        },
        {
            "name": "👤 VIP Authors Track",
            "category": "cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 5,
            "keywords": [], 
            "is_vip_author_only": True # 저자 기반 필터링 플래그
        }
    ],
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
# VVIP_LABS = ["DeepMind", "OpenAI", "Stanford", "KAIST", "Google DeepMind", "AWS"]
VVIP_LABS = ["OpenAI", "DeepMind", "Google DeepMind", "Kimi Team", "Moonshot AI", "Meta", "FAIR", "NVIDIA", "Anthropic"]
TOP_CONFERENCES = [
    "ICLR", "NeurIPS", "ICML", "CVPR", "ECCV", "ICRA", "RSS",
    "AAAI", "IJCAI", "ACL", "EMNLP", "NAACL", "COLM",
]

VIP_AUTHORS = [
    "Andrej Karpathy", "Noam Shazeer", "Ilya Sutskever", "Yann LeCun", 
    "Geoffrey Hinton", "Yoshua Bengio", "Andrew Ng", "Jim Fan",
    "Sergey Levine", "Chelsea Finn", "Joon Sung Park" # 예시
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
    """SequenceMatcher 기반 퍼지 매칭. 4자 이하 단어는 정확 매칭 강제."""
    if len(keyword) <= 4:
        return word == keyword
    return SequenceMatcher(None, word, keyword).ratio() >= threshold


def flexible_keyword_match(text, keywords, min_match=2):
    """
    유연한 키워드 매칭 — 3단계:
    1) 정확한 문자열 포함 (멀티워드 포함)
    2) 유사어 사전 확장 매칭
    3) 단일 단어 퍼지 매칭 (임계값 0.82)
    """
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
    """
    논문 저자 목록 중 VIP_AUTHORS에 해당되는 사람이 있는지 확인
    """
    found_authors = []
    for paper_auth in paper_authors:
        for vip_auth in VIP_AUTHORS:
            # 단순 포함 관계 혹은 소문자 비교
            if vip_auth.lower() in paper_auth.lower():
                found_authors.append(vip_auth)
    
    return list(set(found_authors)) # 중복 제거 후 반환
    
# ════════════════════════════════════════════════════
# 🏛️ ar5iv HTML에서 기관 정보 + Intro 동시 파싱
# ════════════════════════════════════════════════════

def fetch_affiliation_and_intro(arxiv_id, max_intro_chars=1500):
    """
    ar5iv HTML 한 번 요청으로 기관(affiliation) + Introduction 텍스트를 동시에 추출.

    Semantic Scholar 대신 ar5iv를 사용하는 이유:
      - SS는 최신 arXiv 논문을 수일~수주 지연 인덱싱 -> 당일/최근 논문 404 빈번
      - ar5iv는 arXiv 제출 즉시 latexml HTML 변환 -> 최신 논문도 바로 접근 가능

    Returns: ([기관명, ...], intro_text)
    """
    url = "https://ar5iv.labs.arxiv.org/html/" + arxiv_id
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return [], ""
        html = resp.text
    except Exception as e:
        print("    warning: ar5iv 요청 실패 (" + arxiv_id + "): " + str(e))
        return [], ""

    # 1) Affiliation 파싱
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

    # 2) Introduction 파싱
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


def detect_institution_from_list(institution_list):
    """
    기관 목록에서 VVIP_LABS / TOP_INSTITUTIONS 매칭.
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
# 🛠️ 공통 유틸리티
# ════════════════════════════════════════════════════

def sanitize_for_hugo(text):
    if not text:
        return ""
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"**\1**", text, flags=re.MULTILINE)
    return text


def sanitize_title(title):
    return re.sub(r"\{.*?\}", "", title).replace('"', '\\"').replace("|", "-").strip()


# ════════════════════════════════════════════════════
# 📡 데이터 수집 및 스코어링 (Core Logic)
# ════════════════════════════════════════════════════
def fetch_papers_by_category(cat_config, cutoff):
    category = cat_config["category"]
    keywords = cat_config.get("keywords", [])
    limit = cat_config["papers_per_day"]
    is_vvip_only = cat_config.get("is_vvip_only", False)
    is_vip_author_only = cat_config.get("is_vip_author_only", False)

    # 1. 쿼리 생성 로직 통합
    if is_vip_author_only:
        # VIP 저자 검색 강화: 이름을 쿼리에 직접 포함
        author_queries = [f"au:{auth.replace(' ', '_')}" for auth in VIP_AUTHORS[:15]]
        query = f"({ ' OR '.join(author_queries) }) AND ({category})"
    elif is_vvip_only:
        # VVIP 기관 전용은 일단 해당 카테고리 전체를 넓게 가져옴
        query = f"({category})"
    else:
        # 일반 키워드 매칭
        terms = [f"(ti:{kw} OR abs:{kw})" for kw in keywords]
        query = "(" + " OR ".join(terms) + ") AND (" + category + ")"

    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": 200 if (is_vvip_only or is_vip_author_only) else 100
    }
    
    try:
        resp = requests.get("https://export.arxiv.org/api/query", params=params, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"arXiv API Error: {e}")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.content)
    pre_candidates = []

    for entry in root.findall("atom:entry", ns):
        # 기본 정보 추출
        published_el = entry.find("atom:published", ns)
        published = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
        if published < cutoff: continue

        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        
        # 2. 저자 매칭 및 기본 스코어링
        matched_vips = detect_vip_author(authors)
        is_vip_author = len(matched_vips) > 0
        
        # 저자 전용 모드인데 해당 저자가 없으면 필터링
        if is_vip_author_only and not is_vip_author:
            continue

        kw_score = flexible_keyword_match(title + " " + summary, keywords) if keywords else 0
        
        # 스코어 계산 (VIP 저자에게 매우 높은 가중치)
        score = kw_score * 10
        if is_vip_author: score += 5000 
        if any(x in (title + summary).lower() for x in ["github.com", "code available"]): 
            score += 50

        paper_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
        pre_candidates.append({
            "id": paper_id, "title": title, "summary": summary, "authors": authors,
            "matched_vips": matched_vips, "score": score,
            "abs_url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}"
        })

    # 3. 상위 후보에 대해 상세 정보(기관/Intro) 파싱 및 최종 필터링
    pre_candidates.sort(key=lambda x: x["score"], reverse=True)
    final_candidates = []
    
    # 상위 20개 정도만 ar5iv 확인 (성능 및 매너 대기)
    for paper in pre_candidates[:20]:
        raw_inst, intro = fetch_affiliation_and_intro(paper["id"])
        inst_name, is_vvip_lab = detect_institution_from_list(raw_inst)
        
        # VVIP 기관 전용 모드일 때의 필터링 (기관이 없으면 텍스트에서라도 찾음)
        if is_vvip_only:
            inst_in_text = any(lab.lower() in (paper["title"] + paper["summary"]).lower() for lab in VVIP_LABS)
            if not (is_vvip_lab or inst_in_text):
                continue
        
        # 데이터 업데이트
        paper.update({
            "institution": inst_name, 
            "is_vvip": is_vvip_lab, 
            "intro": intro
        })
        final_candidates.append(paper)
        
        if len(final_candidates) >= limit: break
        time.sleep(1.2) 

    return final_candidates

# review_paper_with_cache 등 나머지 함수는 논리적 흐름이 맞으므로 그대로 유지 가능합니다.

# ════════════════════════════════════════════════════
# 🧠 AI 리뷰 생성
# ════════════════════════════════════════════════════

def review_paper_with_cache(paper, category_id, client):
    domain_guide = DOMAIN_GUIDES.get(category_id, "일반적인 AI 기술 분석에 집중하세요.")

    inst_info = "기관: " + paper["institution"] if paper["institution"] else "기관 정보 없음"
    if paper["is_vvip"]:
        inst_info += " (업계 최고 권위 연구소)"
    
    vip_info = ""
    if paper.get("matched_vips"):
        vip_info = f"\n[Special Note] This paper is authored by: {', '.join(paper['matched_vips'])}"
        
    abstract_text = paper["summary"]
    intro_text = paper.get("intro", "")
    intro_section = "\nIntroduction (요약):\n" + intro_text if intro_text else ""

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
                                + "Abstract:\n" + abstract_text
                                + intro_section + "\n\n리뷰 시작:"
                            ),
                        },
                    ],
                }
            ],
        )
        return sanitize_for_hugo(message.content[0].text)
    except Exception as e:
        print("  Claude API 에러: " + str(e))
        return "리뷰 생성 실패"
# ════════════════════════════════════════════════════
# 📝 카테고리별 요약 생성
# ════════════════════════════════════════════════════

CATEGORY_SUMMARY_PROMPT = """당신은 AI 연구를 일반 독자에게 쉽게 전달하는 과학 커뮤니케이터입니다.

아래는 오늘 [{category_name}] 분야에서 주목할 논문들입니다.
이 논문들을 바탕으로, 전문가가 아닌 독자도 이해할 수 있는 오늘의 핵심 인사이트를 구어체로 작성해주세요.

작성 규칙:
- 마치 친한 선배가 "오늘 이런 연구들이 나왔는데 말이야~" 하고 설명해주는 톤
- 전문 용어는 반드시 쉬운 말로 풀어서 설명
- 각 논문을 개별 나열하지 말고, 오늘의 공통 흐름을 하나의 이야기로 엮어서 설명
- **3~5문장으로 짧고 임팩트 있게** 작성
- "오늘은", "이번에", "흥미롭게도" 같은 자연스러운 연결어 사용
- 마지막 문장은 이 흐름이 왜 중요한지 한 줄 전망으로 마무리
- # 헤더 절대 사용 금지, **볼드**는 핵심 키워드에만 최소한으로 사용

논문 목록:
{papers_text}

오늘의 핵심 인사이트 (3~5문장):"""


def generate_category_summary(cat_name, papers, client):
    """카테고리 내 논문들을 바탕으로 독자 친화적 요약 생성 (3~5문장)"""
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
            max_tokens=512,  # 짧은 요약이므로 512로 충분
            messages=[{"role": "user", "content": prompt}],
        )
        return sanitize_for_hugo(message.content[0].text)
    except Exception as e:
        print(f"  카테고리 요약 생성 실패 ({cat_name}): {e}")
        return ""

# ════════════════════════════════════════════════════
# 💾 저장
# ════════════════════════════════════════════════════

def save_daily_digest(date_str, sections, reviews):
    today_kst = datetime.now(KST).strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in sections.values())

    cat_names = [cat["name"].split(" ")[-1] for cat in CONFIG["categories"] if sections.get(cat["name"])]
    cat_str = " · ".join(cat_names)
    summary_text = cat_str + " 분야 유망 논문 " + str(total) + "편 | " + MODEL_NAME + " 자동 분석"

    toc_rows = []
    idx = 1
    for cat_name, papers in sections.items():
        for p in papers:
            t = p["title"] # if len(p["title"]) > 55 else p["title"]
            anchor = f"paper{idx}"
            toc_rows.append(f"| {idx} | {cat_name} | [{t.replace('|', '-') }](#{anchor}) |")
            # toc_rows.append("| " + str(idx) + " | " + cat_name + " | " + t.replace("|", "-") + " |")
            idx += 1
    toc_str = (
        '<div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">\n\n'
        "| # | 분야 | 제목 |\n|---|------|------|\n" 
        + "\n".join(toc_rows) + 
        '\n\n</div>'
    )
    body_parts = []
    idx = 1
    for cat_name, papers in sections.items():
        if not papers:
            continue
        body_parts.append(f"\n---\n\n**{cat_name}**\n")

        # ✅ 카테고리 요약을 논문 목록 바로 앞에 삽입
        summary = category_summaries.get(cat_name, "")
        if summary:
            body_parts.append(f"\n> 💡 {summary}\n")  # blockquote로 시각적으로 구분

        for p, r in zip(papers, reviews[cat_name]):
            anchor = f"paper{idx}"
            body_parts.append(f'\n<a id="{anchor}"></a>\n**{idx}. {sanitize_title(p["title"])}**\n')
            body_parts.append(
                f"\n**저자**: {', '.join(p['authors'][:3])}"
                f" | [원문]({p['abs_url']}) | [PDF]({p['pdf_url']})\n\n{r}\n"
            )
            idx += 1

    ai_notice = "\n\n---\n\n*본 리포트의 논문 리뷰는 Anthropic의 **" + MODEL_NAME + "** 모델을 사용하여 자동 생성되었습니다.*"

    content = (
        '---\n'
        'title: "논문 Daily Digest ' + today_kst + ' (' + str(total) + '편)"\n'
        'date: ' + date_str + 'T00:00:00+09:00\n'
        'draft: false\n'
        'summary: "' + summary_text + '"\n'
        'tags: ["Daily", "AI", "Research"]\n'
        '---\n\n'
        '**목차**\n\n'
        + toc_str + '\n\n'
        + "".join(body_parts)
        + ai_notice + "\n"
    )
    
    # [수정] 파일 저장 경로 로직: 중복 방지 번호 추가
    base_dir = Path("content/post")
    post_dir = base_dir / f"{date_str}-digest"
    
    # 만약 오늘 이미 생성된 폴더가 있다면 번호를 붙임
    counter = 0
    final_post_dir = post_dir
    while final_post_dir.exists():
        counter += 1
        final_post_dir = base_dir / f"{date_str}-digest_{counter}"
    
    final_post_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일 저장
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
    reviewed_ids = set(json.loads(history_path.read_text())) if history_path.exists() else set()

    sections = {}
    reviews_dict = {}
    category_summaries = {}  # ✅ 추가

    for cat_config in CONFIG["categories"]:
        name = cat_config["name"]
        print("\n[" + name + "] 검색 중...")

        all_papers = fetch_papers_by_category(cat_config, cutoff)
        new_papers = [p for p in all_papers if p["id"] not in reviewed_ids]

        sections[name] = []
        reviews_dict[name] = []

        for paper in new_papers:
            print("  리뷰 생성: " + paper["title"][:55] + "...")
            review = review_paper_with_cache(paper, cat_config["category"], client)
            sections[name].append(paper)
            reviews_dict[name].append(review)
            reviewed_ids.add(paper["id"])
            time.sleep(1)

        # ✅ 개별 논문 리뷰 완료 후 카테고리 요약 생성
        if sections[name]:
            print(f"  카테고리 요약 생성 중: {name}")
            category_summaries[name] = generate_category_summary(name, sections[name], client)
        else:
            category_summaries[name] = ""
            
    total = sum(len(v) for v in sections.values())
    if total > 0:
        date_str = now_kst.strftime("%Y-%m-%d")
        save_daily_digest(date_str, sections, reviews_dict, category_summaries)
        history_path.write_text(json.dumps(list(reviewed_ids), indent=2))
        print("\n완료! 총 " + str(total) + "편 처리.")
    else:
        print("\n오늘 업데이트할 새 논문이 없습니다.")


if __name__ == "__main__":
    main()
