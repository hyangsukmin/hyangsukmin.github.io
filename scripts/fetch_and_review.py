import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any

import anthropic

KST = timezone(timedelta(hours=9))

# Anthropic model names are kept from the original script.
MODEL_NAME = "Haiku"
MODEL_API = {"Haiku": "claude-haiku-4-5-20251001", "Sonnet": "claude-sonnet-4-6"}

# =============================================================================
# Search intent vocabulary
# =============================================================================

AGENT_ANCHORS = [
    "LLM agent",
    "LLM agents",
    "language agent",
    "language agents",
    "AI agent",
    "AI agents",
    "autonomous agent",
    "autonomous agents",
    "agentic",
    "tool-use agent",
    "tool-using agent",
    "web agent",
    "software agent",
]

MEMORY_TARGETS = [
    "agent memory",
    "LLM agent memory",
    "language agent memory",
    "memory-augmented agent",
    "memory-augmented agents",
    "long-term memory",
    "long term memory",
    "persistent memory",
    "episodic memory",
    "experience memory",
    "memory system",
    "memory bank",
    "memory module",
    "memory retrieval",
    "memory update",
    "memory management",
    "memory consolidation",
]

MEMORY_RELIABILITY_TARGETS = [
    "memory reliability",
    "reliable memory",
    "memory hallucination",
    "memory conflict",
    "memory contamination",
    "memory poisoning",
    "stale memory",
    "outdated memory",
    "irrelevant memory",
    "selective forgetting",
    "memory forgetting",
    "memory robustness",
    "memory faithfulness",
    "memory grounding",
    "memory evaluation",
    "memory benchmark",
]

LONG_HORIZON_TARGETS = [
    "long-horizon",
    "long horizon",
    "long-horizon agent",
    "long-horizon agents",
    "long-horizon task",
    "long-horizon tasks",
    "long-term planning",
    "extended horizon",
    "multi-step task",
    "multi-step tasks",
    "multi-step reasoning",
    "multi-step decision making",
    "task success",
]

EVALUATION_TARGETS = [
    "agent evaluation",
    "LLM agent evaluation",
    "language agent evaluation",
    "agent benchmark",
    "agent benchmarking",
    "benchmark",
    "evaluation suite",
    "reliability evaluation",
    "robustness evaluation",
    "failure analysis",
    "failure attribution",
    "error attribution",
    "failure diagnosis",
    "fault localization",
]

EXPERIENCE_ADAPTATION_TARGETS = [
    "experience-based adaptation",
    "experience driven adaptation",
    "experience-driven learning",
    "experience replay",
    "learning from mistakes",
    "trial and error",
    "self-improving agent",
    "self-improving agents",
    "self-evolving agent",
    "self-evolving agents",
    "reflection",
    "self-reflection",
    "reflexion",
    "lifelong learning",
    "continual learning",
    "online learning",
]

EMBODIED_ANCHORS = [
    "embodied agent",
    "embodied agents",
    "embodied AI",
    "embodied intelligence",
    "robotic agent",
    "robotic agents",
    "robot learning",
    "robot manipulation",
    "vision-language-action",
    "vision language action",
    "VLA",
    "VLA model",
    "VLA models",
    "navigation",
]

ACTION_GROUNDING_TARGETS = [
    "action grounding",
    "grounded action",
    "action faithfulness",
    "memory-grounded action",
    "evidence-grounded action",
    "tool use",
    "tool-use",
    "planning",
    "execution",
    "environment adaptation",
    "world model",
]

# Terms that often retrieve irrelevant systems papers when they appear without
# LLM/agent anchors. They are used only as mild penalties, not hard exclusions.
NOISE_TERMS = [
    "gpu memory",
    "cache memory",
    "memory bandwidth",
    "memory hierarchy",
    "hardware memory",
    "human memory",
    "working memory in humans",
]

KEYWORD_SYNONYMS = {
    "llm": [
        "large language model",
        "large language models",
        "language model",
        "language models",
        "gpt",
        "transformer",
    ],
    "agent": [
        "agents",
        "agentic",
        "autonomous agent",
        "autonomous agents",
        "language agent",
        "language agents",
        "LLM agent",
        "LLM agents",
    ],
    "memory": [
        "memories",
        "memorization",
        "memorize",
        "memory bank",
        "memory module",
        "memory system",
    ],
    "dynamic memory": [
        "adaptive memory",
        "evolving memory",
        "updatable memory",
        "memory update",
        "memory updating",
        "memory management",
    ],
    "memory-augmented agents": [
        "memory augmented agents",
        "memory-augmented agent",
        "memory augmented agent",
        "agents with memory",
        "LLM agents with memory",
        "memory-based agents",
    ],
    "agent memory": [
        "memory for agents",
        "agentic memory",
        "LLM agent memory",
        "language agent memory",
        "memory module for agents",
    ],
    "memory reliability": [
        "reliable memory",
        "memory robustness",
        "memory faithfulness",
        "memory grounding",
        "trustworthy memory",
    ],
    "memory retrieval": [
        "retrieval memory",
        "memory recall",
        "retrieve memory",
        "retrieving memories",
        "episodic retrieval",
    ],
    "memory utilization": [
        "memory use",
        "memory usage",
        "using memory",
        "utilizing memory",
        "memory grounding",
    ],
    "memory interference": [
        "irrelevant memory",
        "outdated memory",
        "stale memory",
        "memory conflict",
        "memory contamination",
        "negative transfer",
    ],
    "long-term memory": [
        "long term memory",
        "persistent memory",
        "long-range memory",
        "long range memory",
    ],
    "episodic memory": [
        "episodic",
        "episode memory",
        "experience memory",
        "experience replay",
        "trajectory memory",
    ],
    "long-horizon": [
        "long horizon",
        "long-term planning",
        "extended horizon",
        "multi-step",
        "multi step",
        "long-duration",
        "long duration",
    ],
    "long-horizon agents": [
        "long horizon agents",
        "long-horizon agent",
        "long horizon agent",
        "long-term agents",
        "long-running agents",
    ],
    "agent evaluation": [
        "agent benchmark",
        "agent benchmarking",
        "LLM agent evaluation",
        "language agent evaluation",
        "evaluation of agents",
    ],
    "agent reliability": [
        "reliable agents",
        "trustworthy agents",
        "robust agents",
        "agent robustness",
        "agent trustworthiness",
    ],
    "failure attribution": [
        "failure analysis",
        "error attribution",
        "error analysis",
        "failure diagnosis",
        "fault localization",
    ],
    "action faithfulness": [
        "faithful action",
        "grounded action",
        "action grounding",
        "memory-grounded action",
        "evidence-grounded action",
    ],
    "experience-based adaptation": [
        "experience based adaptation",
        "experience-driven adaptation",
        "experience driven adaptation",
        "adaptive agents",
        "adaptation from experience",
    ],
    "lifelong learning": [
        "lifelong",
        "life-long learning",
        "perpetual learning",
        "continual learning",
        "online learning",
    ],
    "self-evolving agents": [
        "self evolving agents",
        "self-evolution",
        "self-evolved",
        "self-improving agents",
        "self improving agents",
    ],
    "self-reflection": [
        "self reflect",
        "self-reflect",
        "self-reflecting",
        "reflection",
        "reflexion",
        "verbal reflection",
    ],
    "embodied AI": [
        "embodied intelligence",
        "embodied agent",
        "embodied agents",
        "physical AI",
        "robotic agent",
    ],
    "embodied agent memory": [
        "embodied memory",
        "memory for embodied agents",
        "robot memory",
        "robotic memory",
        "memory in embodied agents",
    ],
    "vision-language-action": [
        "VLA",
        "VLA model",
        "vision language action",
        "vision-language-action model",
        "vision-language-action models",
    ],
    "robot manipulation": [
        "manipulation",
        "robotic manipulation",
        "grasping",
        "dexterous manipulation",
    ],
    "benchmark": [
        "benchmarks",
        "benchmarking",
        "evaluation suite",
        "leaderboard",
    ],
}

CONFIG = {
    "categories": [
        {
            "name": "Dynamic Memory Reliability",
            "category": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 5,
            "domain_focus": "cs.LG",
            "required_groups": [AGENT_ANCHORS, MEMORY_TARGETS],
            "optional_groups": [MEMORY_RELIABILITY_TARGETS, EVALUATION_TARGETS, EXPERIENCE_ADAPTATION_TARGETS],
            "min_optional_groups": 1,
            "strict_query_groups": [AGENT_ANCHORS, MEMORY_TARGETS, MEMORY_RELIABILITY_TARGETS],
            "relaxed_query_groups": [AGENT_ANCHORS, MEMORY_TARGETS],
        },
        {
            "name": "Long-Horizon Agents",
            "category": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 5,
            "domain_focus": "cs.AI",
            "required_groups": [AGENT_ANCHORS, LONG_HORIZON_TARGETS],
            "optional_groups": [EVALUATION_TARGETS, MEMORY_TARGETS, ACTION_GROUNDING_TARGETS],
            "min_optional_groups": 1,
            "strict_query_groups": [AGENT_ANCHORS, LONG_HORIZON_TARGETS],
            "relaxed_query_groups": [AGENT_ANCHORS],
        },
        {
            "name": "Agent Reliability and Evaluation",
            "category": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 5,
            "domain_focus": "cs.AI",
            "required_groups": [AGENT_ANCHORS, EVALUATION_TARGETS],
            "optional_groups": [MEMORY_RELIABILITY_TARGETS, LONG_HORIZON_TARGETS, ACTION_GROUNDING_TARGETS],
            "min_optional_groups": 1,
            "strict_query_groups": [AGENT_ANCHORS, EVALUATION_TARGETS],
            "relaxed_query_groups": [AGENT_ANCHORS],
        },
        {
            "name": "Experience-Based Adaptation",
            "category": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 4,
            "domain_focus": "cs.LG",
            "required_groups": [AGENT_ANCHORS, EXPERIENCE_ADAPTATION_TARGETS],
            "optional_groups": [MEMORY_TARGETS, EVALUATION_TARGETS, LONG_HORIZON_TARGETS],
            "min_optional_groups": 1,
            "strict_query_groups": [AGENT_ANCHORS, EXPERIENCE_ADAPTATION_TARGETS],
            "relaxed_query_groups": [AGENT_ANCHORS],
        },
        {
            "name": "Embodied Agent Memory",
            "category": "cat:cs.RO OR cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "papers_per_day": 4,
            "domain_focus": "cs.RO",
            "required_groups": [EMBODIED_ANCHORS],
            "optional_groups": [MEMORY_TARGETS, LONG_HORIZON_TARGETS, ACTION_GROUNDING_TARGETS, EVALUATION_TARGETS],
            "min_optional_groups": 1,
            "strict_query_groups": [EMBODIED_ANCHORS, MEMORY_TARGETS],
            "relaxed_query_groups": [EMBODIED_ANCHORS],
        },
        {
            "name": "VVIP Intelligence (Global Top Labs)",
            "category": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.RO",
            "papers_per_day": 3,
            "domain_focus": "cs.AI",
            "required_groups": [],
            "optional_groups": [AGENT_ANCHORS, MEMORY_TARGETS, LONG_HORIZON_TARGETS, EVALUATION_TARGETS],
            "min_optional_groups": 2,
            "is_vvip_only": True,
        },
        {
            "name": "VIP Authors Track",
            "category": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.RO",
            "papers_per_day": 5,
            "domain_focus": "cs.AI",
            "required_groups": [],
            "optional_groups": [AGENT_ANCHORS, MEMORY_TARGETS, LONG_HORIZON_TARGETS, EVALUATION_TARGETS],
            "min_optional_groups": 2,
            "is_vip_author_only": True,
        },
    ],
    # Daily digest라면 720일은 너무 넓습니다. 필요한 경우 365 또는 720으로 조정하세요.
    "days_back": 720,
    "review_language": "Korean",
    "review_style": "technical",
    # arXiv query가 strict해서 결과가 적을 때 relaxed query를 추가로 실행합니다.
    "min_raw_candidates_before_relax": 20,
    # 상세 affiliation 조회 전에 relevance 기준으로 볼 후보 수입니다.
    "detail_check_count_general": 40,
    "detail_check_count_vip": 80,
    # Method-to-Code Map을 위해 논문 본문에서 공개 코드 링크를 찾고,
    # GitHub 저장소가 있으면 일부 파일 경로와 내용을 리뷰 컨텍스트에 추가합니다.
    "enable_code_repo_lookup": True,
    "max_code_repos_per_paper": 2,
    "max_code_files_per_repo": 8,
    "max_code_chars_per_file": 1800,
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
- 에이전트의 자가 수정(Self-correction), 추론 루프, 계획-실행-검증 구조를 분석하세요.
- 단순 성능보다 에이전트가 오류를 어떻게 감지하고 복구하는지에 집중하세요.""",
    "cs.LG": """[Focus: Memory & Learning Efficiency]
- 정보를 어떻게 저장, 압축, 업데이트, 검색하는지 분석하세요.
- 장기 기억 유지 시 발생하는 오염, 망각, 충돌, hallucination 문제를 해결했는지 확인하세요.""",
    "cs.RO": """[Focus: Embodiment & Action]
- 고수준 언어 지시가 물리적 행동(Action)으로 변환되는 정렬 방식을 분석하세요.
- 기억, world model, sim-to-real, 환경 적응이 실제 행동 성공률에 어떻게 연결되는지 주목하세요.""",
}

# =============================================================================
# Review prompts
# =============================================================================

STYLE_PROMPTS = {
    "technical": """당신은 AI/ML 논문을 비판적으로 읽는 연구 파트너입니다.
아래 논문을 사용자가 바로 페이퍼 리뷰 노트로 쓸 수 있도록 작성하세요.

가장 중요한 원칙:
- 제공된 Title, Abstract, Paper Context, Code Repository Snapshot 안에서 확인되는 정보만 사용하세요.
- figure/table/paragraph 번호나 코드 파일 경로를 확실히 알 수 없으면 절대 지어내지 말고 "확인 불가"라고 쓰세요.
- Claim–Evidence Table은 논문 주장을 근거 위치와 연결하는 섹션입니다. 근거가 abstract/introduction 수준이면 그렇게 명시하세요.
- Method-to-Code Map은 공개 코드 링크와 저장소 스냅샷이 있을 때만 파일 경로를 연결하세요. 코드가 없거나 스냅샷에 없는 구현은 "공개 코드 기준 확인 불가"라고 쓰세요.
- 과장된 praise보다, main claim이 성립하려면 무엇이 더 필요했는지를 분명히 쓰세요.
- # 헤더는 사용하지 말고, 오직 **볼드** 헤더만 사용하세요.
- 각 bullet은 1~2문장으로 짧게 쓰세요.
- 전문 용어는 유지하되, 첫 등장 시 필요한 경우 괄호로 짧게 풀이하세요.

반드시 아래 4개 섹션만 출력하세요.

**Paper Map**
- **문제**: 이 논문이 풀려는 문제를 한 문장으로 정의하고, 기존 연구와 달라지는 지점을 함께 쓰세요.
- **방법**: 핵심 방법을 구성요소 단위로 3~5개 bullet로 분해하세요.
- **실험**: 데이터셋, baseline, evaluation metric, 비교 설정을 확인 가능한 범위에서 요약하세요.
- **핵심 결과**: 가장 중요한 결과를 2~4개 bullet로 쓰세요. 수치가 있으면 반드시 맥락과 함께 쓰고, 없으면 "수치 확인 불가"라고 쓰세요.
- **한계**: 논문 내부에서 드러난 한계와 리뷰어 관점의 한계를 구분해 쓰세요.

**Claim–Evidence Table**
| Claim | Evidence Location | Evidence Type | Strength | Caveat |
|---|---|---|---|---|
| 논문의 핵심 주장 | Table/Figure/Section/Paragraph/Abstract 중 확인 가능한 위치 | 정량 결과/ablation/분석/문제정의/사례 | Strong/Medium/Weak | 왜 충분하거나 부족한지 |

작성 규칙:
- Claim은 3~6개만 고르세요.
- Evidence Location에는 "Table 1", "Figure 3", "Section 4.2", "Abstract", "Introduction"처럼 확인 가능한 위치만 쓰세요.
- 위치가 확인되지 않으면 "확인 불가"라고 쓰고, Evidence Type과 Caveat에 이유를 쓰세요.

**Method-to-Code Map**
| Method Component | Expected Implementation | Code Location | Confidence | Note |
|---|---|---|---|---|
| 논문 방법의 구성요소 | 구현되어야 하는 함수/모듈 역할 | repo/path.py 또는 확인 불가 | High/Medium/Low/Unavailable | 연결 근거 또는 확인 불가 이유 |

작성 규칙:
- 공개 코드 링크가 없으면 첫 줄에 "공개 코드 링크 확인 불가"라고 명시하고, 방법론 기준의 expected implementation만 제시하세요.
- 공개 코드가 있더라도 저장소 스냅샷에서 확인되지 않은 파일은 추측하지 마세요.
- README, config, training, evaluation, model, data processing, retrieval/memory/agent loop 파일을 우선 연결하세요.

**Research Gap Note**
- **가정**: main claim이 성립하려면 필요한 핵심 assumptions를 2~4개 쓰세요.
- **Alternative explanation**: 실험 결과가 방법 자체가 아니라 다른 요인으로 설명될 수 있는 가능성을 2~4개 쓰세요.
- **부족한 ablation**: 추가되어야 할 ablation 또는 diagnostic experiment를 2~4개 쓰세요.
- **내가 이어서 할 질문**: 사용자가 후속 연구로 이어갈 수 있는 research question을 3~5개 쓰세요. 질문은 논문화 가능한 수준으로 구체화하세요.
"""
}

CATEGORY_SUMMARY_PROMPT = """당신은 AI 연구를 깊이 있게 전달하는 과학 커뮤니케이터입니다.

아래는 오늘 [{category_name}] 분야에서 주목할 논문들입니다.
이 논문들을 바탕으로, 오늘의 핵심 흐름을 하나의 이야기로 엮어 작성하세요.

작성 규칙:
- 친한 선배가 설명해주는 구어체 톤
- 각 논문을 개별 나열하지 말고, 오늘의 공통 테마나 흐름으로 엮을 것
- 전문 용어는 쉬운 말로 풀되, 기술적 맥락은 희석하지 말 것
- **3~5문장**, 마지막 문장은 이 흐름이 왜 중요한지 전망으로 마무리
- # 헤더 금지, **볼드**는 핵심 키워드에만 최소한으로

논문 목록:
{papers_text}

오늘의 핵심 인사이트 (3~5문장):"""

# =============================================================================
# Text matching helpers
# =============================================================================

def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2012", "-")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


def fuzzy_match(word: str, keyword: str, threshold: float = 0.84) -> bool:
    if len(keyword) <= 4:
        return word == keyword
    return SequenceMatcher(None, word, keyword).ratio() >= threshold


def expand_terms(terms: list[str]) -> list[str]:
    expanded: list[str] = []
    for term in terms:
        expanded.append(term)
        expanded.extend(KEYWORD_SYNONYMS.get(term.lower(), []))
    # preserve order, remove duplicates
    seen = set()
    out = []
    for term in expanded:
        key = term.lower()
        if key not in seen:
            out.append(term)
            seen.add(key)
    return out


def term_found(text: str, term: str) -> bool:
    text_lower = normalize_text(text)
    term_lower = normalize_text(term)

    if term_lower in text_lower:
        return True

    # Hyphen/space normalization for phrases like long-horizon / long horizon.
    if "-" in term_lower:
        if term_lower.replace("-", " ") in text_lower:
            return True
    if " " in term_lower:
        if term_lower.replace(" ", "-") in text_lower:
            return True

    # Fuzzy match only for single-token terms.
    if " " not in term_lower and "-" not in term_lower:
        words = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text_lower)
        return any(fuzzy_match(word, term_lower) for word in words)

    return False


def matched_terms(text: str, terms: list[str]) -> list[str]:
    expanded = expand_terms(terms)
    matches = []
    for term in expanded:
        if term_found(text, term):
            matches.append(term)
    return list(dict.fromkeys(matches))


def group_match_count(text: str, groups: list[list[str]]) -> int:
    return sum(1 for group in groups if matched_terms(text, group))


def detect_vip_author(paper_authors: list[str]) -> list[str]:
    found_authors = []
    for paper_auth in paper_authors:
        for vip_auth in VIP_AUTHORS:
            if vip_auth.lower() in paper_auth.lower():
                found_authors.append(vip_auth)
    return sorted(set(found_authors))


# =============================================================================
# Paper/code context helpers for review grounding
# =============================================================================

CODE_HOST_PATTERNS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "huggingface.co",
    "paperswithcode.com",
)

CODE_EXTENSIONS = (
    ".py", ".md", ".yaml", ".yml", ".json", ".toml", ".sh",
    ".js", ".ts", ".ipynb", ".txt",
)

CODE_PATH_KEYWORDS = {
    "readme": 8,
    "model": 7,
    "agent": 7,
    "memory": 7,
    "retriev": 7,
    "planner": 7,
    "plan": 5,
    "reflect": 6,
    "train": 6,
    "eval": 6,
    "benchmark": 6,
    "experiment": 5,
    "dataset": 5,
    "data": 4,
    "inference": 5,
    "generate": 4,
    "run": 4,
    "main": 4,
    "config": 3,
    "src/": 2,
}


def extract_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = re.findall(r"https?://[^\s<>'\"\\)\\]\\}]+", text)
    cleaned = []
    for url in urls:
        url = url.rstrip(".,;:)]}'\"")
        if url and url not in cleaned:
            cleaned.append(url)
    return cleaned


def extract_code_urls(text: str) -> list[str]:
    urls = extract_urls(text)
    code_urls = []
    for url in urls:
        url_lower = url.lower()
        if any(host in url_lower for host in CODE_HOST_PATTERNS):
            code_urls.append(url)
    return list(dict.fromkeys(code_urls))


def parse_github_repo_url(url: str) -> tuple[str, str] | None:
    match = re.search(r"github\.com/([^/\s?#]+)/([^/\s?#]+)", url, flags=re.IGNORECASE)
    if not match:
        return None
    owner = match.group(1)
    repo = match.group(2).replace(".git", "").strip("/")
    if not owner or not repo:
        return None
    return owner, repo


def github_headers() -> dict[str, str]:
    headers = {"User-Agent": "daily-digest-paper-review-bot/1.0"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def score_code_path(path: str) -> int:
    lower = path.lower()
    score = 0
    for keyword, weight in CODE_PATH_KEYWORDS.items():
        if keyword in lower:
            score += weight
    if lower.endswith("readme.md"):
        score += 10
    if lower.startswith((".github/", "docs/", "assets/", "figures/", "images/")):
        score -= 6
    if "test" in lower or "example" in lower:
        score -= 2
    return score


def clean_code_snippet(text: str, max_chars: int) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text[:max_chars].strip()


def fetch_github_repo_snapshot(repo_url: str) -> str:
    parsed = parse_github_repo_url(repo_url)
    if not parsed:
        return ""
    owner, repo = parsed
    headers = github_headers()

    try:
        repo_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
            timeout=15,
        )
        if repo_resp.status_code != 200:
            return f"[GitHub repo] {owner}/{repo}: metadata 조회 실패(status={repo_resp.status_code})"
        repo_meta = repo_resp.json()
        default_branch = repo_meta.get("default_branch") or "main"

        tree_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers=headers,
            timeout=20,
        )
        if tree_resp.status_code != 200:
            return f"[GitHub repo] {owner}/{repo}: file tree 조회 실패(status={tree_resp.status_code})"

        tree = tree_resp.json().get("tree", [])
        candidate_files = []
        for item in tree:
            path = item.get("path", "")
            if item.get("type") != "blob":
                continue
            if not path.lower().endswith(CODE_EXTENSIONS):
                continue
            if item.get("size", 0) > 300_000:
                continue
            score = score_code_path(path)
            if score <= 0:
                continue
            candidate_files.append((score, path))

        candidate_files.sort(key=lambda x: (-x[0], x[1]))
        selected_paths = [path for _, path in candidate_files[:CONFIG["max_code_files_per_repo"]]]

        parts = [
            f"[GitHub repo] {owner}/{repo}",
            f"Default branch: {default_branch}",
            "Selected files:",
        ]
        parts.extend(f"- {path}" for path in selected_paths)

        for path in selected_paths:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{path}"
            raw_resp = requests.get(raw_url, headers=headers, timeout=20)
            if raw_resp.status_code != 200:
                continue
            snippet = clean_code_snippet(raw_resp.text, CONFIG["max_code_chars_per_file"])
            if snippet:
                parts.append(f"\n--- FILE: {path} ---\n{snippet}")

        return "\n".join(parts)
    except Exception as e:
        return f"[GitHub repo] {owner}/{repo}: 조회 실패({e})"


def build_code_context(code_urls: list[str]) -> str:
    if not code_urls or not CONFIG.get("enable_code_repo_lookup", True):
        return ""

    github_repos = []
    for url in code_urls:
        parsed = parse_github_repo_url(url)
        if parsed and parsed not in github_repos:
            github_repos.append(parsed)

    if not github_repos:
        return "\n".join(f"- {url}" for url in code_urls)

    contexts = []
    max_repos = CONFIG.get("max_code_repos_per_paper", 2)
    for owner, repo in github_repos[:max_repos]:
        contexts.append(fetch_github_repo_snapshot(f"https://github.com/{owner}/{repo}"))
        time.sleep(0.5)
    return "\n\n".join(c for c in contexts if c)


def strip_html_to_text(html: str) -> str:
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_relevant_paper_context(clean_text: str, max_chars: int = 24000) -> str:
    """Collect broad paper snippets useful for paper map and claim-evidence review."""
    if not clean_text:
        return ""

    patterns = [
        r"\babstract\b",
        r"\bintroduction\b",
        r"\bmethod\b",
        r"\bapproach\b",
        r"\balgorithm\b",
        r"\bexperiment",
        r"\bresult",
        r"\bablation\b",
        r"\banalysis\b",
        r"\blimitation",
        r"\bconclusion\b",
        r"\btable\s+\d+",
        r"\bfigure\s+\d+",
    ]

    windows = []
    lower = clean_text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, lower):
            start = max(0, match.start() - 1200)
            end = min(len(clean_text), match.end() + 2200)
            snippet = clean_text[start:end].strip()
            if snippet:
                windows.append(snippet)
            if len(windows) >= 16:
                break

    # Always include the beginning because title/abstract often appear there.
    windows.insert(0, clean_text[:4000])

    merged = []
    seen = set()
    total = 0
    for snippet in windows:
        key = snippet[:300]
        if key in seen:
            continue
        seen.add(key)
        block = snippet.strip()
        if not block:
            continue
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining > 800:
                merged.append(block[:remaining])
            break
        merged.append(block)
        total += len(block)

    return "\n\n---\n\n".join(merged).strip()


# =============================================================================
# arXiv query builder
# =============================================================================

def arxiv_quote(term: str) -> str:
    """Quote multi-token arXiv query terms safely."""
    term = term.strip().replace('"', "")
    # arXiv accepts phrase queries as field:"multi word phrase".
    if re.search(r"\s", term):
        return f'"{term}"'
    return term


def field_query(field: str, term: str) -> str:
    return f"{field}:{arxiv_quote(term)}"


def title_abs_any(terms: list[str], max_terms: int = 18) -> str:
    """Build (ti:... OR abs:...) for a controlled number of high-value terms."""
    terms = list(dict.fromkeys(terms))[:max_terms]
    chunks = []
    for term in terms:
        chunks.append(field_query("ti", term))
        chunks.append(field_query("abs", term))
    return "(" + " OR ".join(chunks) + ")"


def build_structured_query(category: str, groups: list[list[str]]) -> str:
    """AND across concept groups, OR within each group."""
    group_queries = [title_abs_any(group) for group in groups if group]
    if group_queries:
        return "(" + " AND ".join(group_queries) + f") AND ({category})"
    return f"({category})"


def build_vvip_query(category: str) -> str:
    lab_queries = [field_query("abs", lab) for lab in VVIP_LABS] + [field_query("ti", lab) for lab in VVIP_LABS]
    return "(" + " OR ".join(lab_queries) + f") AND ({category})"


def build_vip_author_query(category: str) -> str:
    # arXiv author search is not perfect for all names, but phrase form is safer than unquoted spaces.
    author_queries = [field_query("au", author) for author in VIP_AUTHORS]
    return "(" + " OR ".join(author_queries) + f") AND ({category})"

# =============================================================================
# Affiliation / intro enrichment
# =============================================================================

def canonical_arxiv_id(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id)


def fetch_affiliations_from_s2(arxiv_id: str) -> list[str]:
    """Fetch affiliations from Semantic Scholar. Returns [] on any failure."""
    arxiv_id = canonical_arxiv_id(arxiv_id)
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
    params = {"fields": "authors.affiliations,authors.name"}
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=12,
            headers={"User-Agent": "daily-digest-bot/1.0"},
        )
        if resp.status_code == 429:
            print("    [S2] rate limit — 60초 대기")
            time.sleep(60)
            resp = requests.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
        affiliations = []
        for author in data.get("authors", []):
            for aff in author.get("affiliations", []) or []:
                if aff and aff not in affiliations:
                    affiliations.append(aff)
        return affiliations
    except Exception as e:
        print(f"    [S2] 요청 실패 ({arxiv_id}): {e}")
        return []


def fetch_affiliation_and_intro_ar5iv(arxiv_id: str, max_context_chars: int = 24000) -> tuple[list[str], str, list[str]]:
    """Fallback parser for affiliation + paper context + public code links from ar5iv HTML."""
    arxiv_id = canonical_arxiv_id(arxiv_id)
    url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return [], "", []
        html = resp.text
    except Exception as e:
        print(f"    [ar5iv] 요청 실패 ({arxiv_id}): {e}")
        return [], "", []

    code_urls = extract_code_urls(html)

    aff_pattern = re.compile(
        r'<(?:span|div)[^>]*?class="[^"]*(?:ltx_role_affiliation|ltx_affiliation)[^"]*"[^>]*?>'
        r"(.*?)</(?:span|div)>",
        re.IGNORECASE | re.DOTALL,
    )
    institutions = []
    for raw in aff_pattern.findall(html):
        clean_aff = re.sub(r"<[^>]+>", " ", raw)
        clean_aff = re.sub(r"\s+", " ", clean_aff).strip()
        clean_aff = re.sub(r"^\d+\s*", "", clean_aff).strip()
        if clean_aff and clean_aff not in institutions and len(clean_aff) > 3:
            institutions.append(clean_aff)

    clean_text = strip_html_to_text(html)
    paper_context = extract_relevant_paper_context(clean_text, max_chars=max_context_chars)

    return institutions, paper_context, code_urls


def get_affiliations_with_fallback(arxiv_id: str) -> tuple[list[str], str, list[str]]:
    s2_affiliations = fetch_affiliations_from_s2(arxiv_id)
    time.sleep(0.5)
    ar5iv_affiliations, paper_context, code_urls = fetch_affiliation_and_intro_ar5iv(arxiv_id)
    affiliations = s2_affiliations if s2_affiliations else ar5iv_affiliations
    return affiliations, paper_context, code_urls


def detect_institution_from_list(institution_list: list[str]) -> tuple[str, bool]:
    joined = " ".join(institution_list).lower()
    for inst in VVIP_LABS:
        if inst.lower() in joined:
            return inst, True
    for inst in TOP_INSTITUTIONS:
        if inst.lower() in joined:
            return inst, False
    return "", False


def detect_vvip_from_abstract(title: str, summary: str) -> tuple[str, bool]:
    text = normalize_text(title + " " + summary)
    for lab in VVIP_LABS:
        if lab.lower() in text:
            return lab, True
    return "", False

# =============================================================================
# arXiv collection
# =============================================================================

def parse_arxiv_entries(xml_content: bytes, ns: dict[str, str]) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_content)
    entries = []
    for entry in root.findall("atom:entry", ns):
        published_el = entry.find("atom:published", ns)
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        id_el = entry.find("atom:id", ns)
        if published_el is None or title_el is None or summary_el is None or id_el is None:
            continue

        published = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
        title = (title_el.text or "").strip().replace("\n", " ")
        summary = (summary_el.text or "").strip().replace("\n", " ")
        authors = []
        for a in entry.findall("atom:author", ns):
            name_el = a.find("atom:name", ns)
            if name_el is not None and name_el.text:
                authors.append(name_el.text)
        paper_id = id_el.text.split("/abs/")[-1]

        inline_affiliations = []
        for author in entry.findall("atom:author", ns):
            aff = author.find("atom:affiliation", ns)
            if aff is not None and aff.text:
                inline_affiliations.append(aff.text)

        canonical_id = canonical_arxiv_id(paper_id)
        entries.append({
            "id": canonical_id,
            "raw_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "published": published,
            "inline_affiliations": inline_affiliations,
            "abs_url": f"https://arxiv.org/abs/{canonical_id}",
            "pdf_url": f"https://arxiv.org/pdf/{canonical_id}",
        })
    return entries


def fetch_arxiv_paginated(
    query: str,
    cutoff: datetime,
    max_per_page: int = 200,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """Collect arXiv papers until cutoff using submittedDate descending order."""
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    all_entries = []
    seen_ids = set()

    for page in range(max_pages):
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": page * max_per_page,
            "max_results": max_per_page,
        }
        try:
            resp = requests.get("https://export.arxiv.org/api/query", params=params, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"    [arXiv] 페이지 {page} 요청 실패: {e}")
            break

        try:
            entries = parse_arxiv_entries(resp.content, ns)
        except Exception as e:
            print(f"    [arXiv] XML 파싱 실패: {e}")
            break

        if not entries:
            print(f"    [arXiv] 페이지 {page}: 결과 없음, 중단")
            break

        reached_cutoff = False
        added = 0
        for item in entries:
            if item["published"] < cutoff:
                reached_cutoff = True
                break
            if item["id"] not in seen_ids:
                all_entries.append(item)
                seen_ids.add(item["id"])
                added += 1

        print(f"    [arXiv] 페이지 {page}: {len(entries)}건 조회, {added}건 추가, 누적 {len(all_entries)}건")

        if reached_cutoff:
            print(f"    [arXiv] cutoff({cutoff.date()}) 도달, 수집 중단")
            break

        time.sleep(3)

    return all_entries

# =============================================================================
# Relevance filtering and scoring
# =============================================================================

def compute_relevance(paper: dict[str, Any], cat_config: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    title = paper.get("title", "")
    summary = paper.get("summary", "")
    text = title + " " + summary

    required_groups = cat_config.get("required_groups", [])
    optional_groups = cat_config.get("optional_groups", [])

    required_hits = []
    optional_hits = []

    for idx, group in enumerate(required_groups):
        hits = matched_terms(text, group)
        if hits:
            required_hits.append({"group": idx, "terms": hits[:5]})

    for idx, group in enumerate(optional_groups):
        hits = matched_terms(text, group)
        if hits:
            optional_hits.append({"group": idx, "terms": hits[:5]})

    required_count = len(required_hits)
    optional_count = len(optional_hits)

    score = 0
    score += required_count * 120
    score += optional_count * 45

    title_text = title.lower()
    # Title matches are more meaningful than abstract-only matches.
    for group in required_groups:
        if matched_terms(title_text, group):
            score += 35
    for group in optional_groups:
        if matched_terms(title_text, group):
            score += 15

    # Strong exact signals.
    strong_signals = [
        "llm agent memory",
        "language agent memory",
        "agent memory",
        "memory benchmark",
        "memory evaluation",
        "long-horizon agent",
        "agent reliability",
        "memory hallucination",
        "memory poisoning",
        "selective forgetting",
    ]
    score += 30 * sum(1 for term in strong_signals if term_found(text, term))

    # Institution/author/code/recentness bonuses should never dominate relevance.
    if paper.get("matched_vips"):
        score += 30

    _, is_vvip_text = detect_vvip_from_abstract(title, summary)
    if is_vvip_text:
        score += 20

    if any(x in normalize_text(text) for x in ["github.com", "code available", "code is available"]):
        score += 10

    days_old = (datetime.now(KST) - paper["published"]).days
    if days_old <= 7:
        score += 20
    elif days_old <= 30:
        score += 10

    noise_hits = matched_terms(text, NOISE_TERMS)
    if noise_hits:
        score -= 40

    debug = {
        "required_count": required_count,
        "optional_count": optional_count,
        "required_hits": required_hits,
        "optional_hits": optional_hits,
        "noise_hits": noise_hits,
        "score": score,
    }
    return score, debug


def passes_relevance_gate(paper: dict[str, Any], cat_config: dict[str, Any]) -> bool:
    """Hard gate: all required groups + enough optional groups must match."""
    required_groups = cat_config.get("required_groups", [])
    optional_groups = cat_config.get("optional_groups", [])
    min_optional_groups = cat_config.get("min_optional_groups", 0)

    # VVIP/VIP tracks are broad, but still require topical relevance through optional groups.
    if not required_groups:
        return group_match_count(paper["title"] + " " + paper["summary"], optional_groups) >= min_optional_groups

    text = paper["title"] + " " + paper["summary"]
    for group in required_groups:
        if not matched_terms(text, group):
            return False

    if optional_groups and group_match_count(text, optional_groups) < min_optional_groups:
        return False

    return True


def score_paper(paper: dict[str, Any], cat_config: dict[str, Any]) -> int:
    score, debug = compute_relevance(paper, cat_config)
    paper["relevance_debug"] = debug
    return score

# =============================================================================
# Paper collection by category
# =============================================================================

def fetch_raw_entries_for_category(cat_config: dict[str, Any], cutoff: datetime) -> list[dict[str, Any]]:
    category = cat_config["category"]
    is_vvip_only = cat_config.get("is_vvip_only", False)
    is_vip_author_only = cat_config.get("is_vip_author_only", False)

    if is_vip_author_only:
        query = build_vip_author_query(category)
        max_pages = 5
        print(f"    쿼리(VIP author): {query[:180]}...")
        return fetch_arxiv_paginated(query, cutoff, max_per_page=200, max_pages=max_pages)

    if is_vvip_only:
        query = build_vvip_query(category)
        max_pages = 5
        print(f"    쿼리(VVIP lab): {query[:180]}...")
        return fetch_arxiv_paginated(query, cutoff, max_per_page=200, max_pages=max_pages)

    strict_groups = cat_config.get("strict_query_groups") or cat_config.get("required_groups", [])
    relaxed_groups = cat_config.get("relaxed_query_groups") or cat_config.get("required_groups", [])[:1]

    strict_query = build_structured_query(category, strict_groups)
    print(f"    쿼리(strict): {strict_query[:220]}...")
    raw_entries = fetch_arxiv_paginated(strict_query, cutoff, max_per_page=200, max_pages=4)

    # If strict query is too narrow, add relaxed query and let Python hard gate decide.
    if len(raw_entries) < CONFIG["min_raw_candidates_before_relax"] and relaxed_groups != strict_groups:
        relaxed_query = build_structured_query(category, relaxed_groups)
        print(f"    strict 후보가 적어 relaxed query 추가: {relaxed_query[:220]}...")
        relaxed_entries = fetch_arxiv_paginated(relaxed_query, cutoff, max_per_page=200, max_pages=3)
        merged = {p["id"]: p for p in raw_entries}
        for p in relaxed_entries:
            merged.setdefault(p["id"], p)
        raw_entries = list(merged.values())

    return raw_entries


def fetch_papers_by_category(cat_config: dict[str, Any], cutoff: datetime) -> list[dict[str, Any]]:
    limit = cat_config["papers_per_day"]
    is_vvip_only = cat_config.get("is_vvip_only", False)
    is_vip_author_only = cat_config.get("is_vip_author_only", False)

    raw_entries = fetch_raw_entries_for_category(cat_config, cutoff)
    if not raw_entries:
        return []

    candidates = []
    for entry in raw_entries:
        matched_vips = detect_vip_author(entry["authors"])
        if is_vip_author_only and not matched_vips:
            continue
        entry["matched_vips"] = matched_vips

        if not passes_relevance_gate(entry, cat_config):
            continue

        entry["score"] = score_paper(entry, cat_config)
        candidates.append(entry)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    print(f"    relevance 통과 후보 {len(candidates)}건, 상위 점수: {[c['score'] for c in candidates[:5]]}")

    if not candidates:
        return []

    check_count = CONFIG["detail_check_count_vip"] if (is_vvip_only or is_vip_author_only) else CONFIG["detail_check_count_general"]
    final_candidates = []

    for paper in candidates[:check_count]:
        inst_from_text, is_vvip_text = detect_vvip_from_abstract(paper["title"], paper["summary"])
        inst_from_inline, is_vvip_inline = detect_institution_from_list(paper.get("inline_affiliations", []))

        affiliations, paper_context, ar5iv_code_urls = get_affiliations_with_fallback(paper["id"])
        inst_from_api, is_vvip_api = detect_institution_from_list(affiliations)

        if inst_from_api:
            inst_name, is_vvip = inst_from_api, is_vvip_api
        elif inst_from_inline:
            inst_name, is_vvip = inst_from_inline, is_vvip_inline
        elif inst_from_text:
            inst_name, is_vvip = inst_from_text, is_vvip_text
        else:
            inst_name, is_vvip = "", False

        if is_vvip_only and not is_vvip:
            print(f"    [VVIP 필터] 제외: {paper['title'][:70]}")
            time.sleep(0.3)
            continue

        code_urls = extract_code_urls(
            paper.get("title", "") + "\n" + paper.get("summary", "") + "\n" + paper_context
        )
        code_urls = list(dict.fromkeys(code_urls + ar5iv_code_urls))
        code_context = build_code_context(code_urls)

        paper.update({
            "institution": inst_name,
            "is_vvip": is_vvip,
            "intro": paper_context,
            "code_urls": code_urls,
            "code_context": code_context,
        })
        final_candidates.append(paper)

        matched_str = ""
        debug = paper.get("relevance_debug", {})
        if debug:
            opt_terms = []
            for item in debug.get("optional_hits", []):
                opt_terms.extend(item.get("terms", []))
            matched_str = f" | match: {', '.join(opt_terms[:4])}"

        print(f"    ✓ 선정: [{inst_name or '기관미상'}] score={paper['score']} {paper['title'][:70]}{matched_str}")

        if len(final_candidates) >= limit:
            break

        time.sleep(1.0)

    return final_candidates

# =============================================================================
# AI review generation
# =============================================================================

def review_paper_with_cache(paper: dict[str, Any], cat_config: dict[str, Any], client: anthropic.Anthropic) -> str:
    domain_focus = cat_config.get("domain_focus", "cs.AI")
    domain_guide = DOMAIN_GUIDES.get(domain_focus, "일반적인 AI 기술 분석에 집중하세요.")

    inst_info = "기관: " + paper["institution"] if paper.get("institution") else "기관 정보 없음"
    if paper.get("is_vvip"):
        inst_info += " (업계 최고 권위 연구소)"

    vip_info = ""
    if paper.get("matched_vips"):
        vip_info = f"\n[Special Note] This paper is authored by: {', '.join(paper['matched_vips'])}"

    paper_context_section = ""
    if paper.get("intro"):
        paper_context_section = "\n[Paper Context from ar5iv]\n" + paper["intro"]

    code_urls_section = ""
    if paper.get("code_urls"):
        code_urls_section = "\n[Public Code URLs]\n" + "\n".join(f"- {url}" for url in paper["code_urls"])
    else:
        code_urls_section = "\n[Public Code URLs]\n확인된 공개 코드 링크 없음"

    code_context_section = ""
    if paper.get("code_context"):
        code_context_section = "\n[Code Repository Snapshot]\n" + paper["code_context"]
    else:
        code_context_section = "\n[Code Repository Snapshot]\n확인된 저장소 스냅샷 없음"

    relevance_section = ""
    debug = paper.get("relevance_debug", {})
    if debug:
        req_terms = []
        opt_terms = []
        for item in debug.get("required_hits", []):
            req_terms.extend(item.get("terms", []))
        for item in debug.get("optional_hits", []):
            opt_terms.extend(item.get("terms", []))
        relevance_section = (
            "\n[Relevance Signals]\n"
            f"Required matches: {', '.join(req_terms[:8])}\n"
            f"Optional matches: {', '.join(opt_terms[:8])}\n"
            f"Relevance score: {paper.get('score')}\n"
        )

    try:
        message = client.messages.create(
            model=MODEL_API[MODEL_NAME],
            max_tokens=6144,
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
                                + relevance_section
                                + "Title: " + paper["title"] + "\n"
                                + "Abstract:\n" + paper["summary"]
                                + paper_context_section
                                + code_urls_section
                                + code_context_section
                                + "\n\n리뷰 시작:"
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


def generate_category_summary(cat_name: str, papers: list[dict[str, Any]], client: anthropic.Anthropic) -> str:
    if not papers:
        return ""

    papers_text = ""
    for i, p in enumerate(papers, 1):
        rel = p.get("relevance_debug", {})
        papers_text += (
            f"{i}. 제목: {p['title']}\n"
            f"   요약: {p['summary'][:350]}\n"
            f"   관련성 점수: {p.get('score')} / 매칭 정보: {rel.get('optional_hits', [])[:2]}\n\n"
        )

    prompt = CATEGORY_SUMMARY_PROMPT.format(category_name=cat_name, papers_text=papers_text)

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

# =============================================================================
# Utilities and save
# =============================================================================

def sanitize_for_hugo(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"**\1**", text, flags=re.MULTILINE)
    return text.strip()


def sanitize_title(title: str) -> str:
    return re.sub(r"\{.*?\}", "", title).replace('"', '\\"').replace("|", "-").strip()


def save_daily_digest(date_str: str, sections: dict[str, list[dict[str, Any]]], reviews: dict[str, list[str]], category_summaries: dict[str, str]) -> None:
    today_kst = datetime.now(KST).strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in sections.values())

    cat_names = [cat["name"] for cat in CONFIG["categories"] if sections.get(cat["name"])]
    summary_text = " · ".join(cat_names) + f" 분야 유망 논문 {total}편 | {MODEL_NAME} 자동 분석"

    toc_rows = []
    idx = 1
    for cat_name, papers in sections.items():
        for p in papers:
            anchor = f"paper{idx}"
            toc_rows.append(f"| {idx} | {cat_name} | [{p['title'].replace('|', '-') }](#{anchor}) |")
            idx += 1

    toc_str = (
        '<div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">\n\n'
        "| # | 분야 | 제목 |\n|---|------|------|\n"
        + "\n".join(toc_rows)
        + "\n\n</div>"
    )

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
            pub_date = p["published"].strftime("%Y-%m-%d")
            inst = p.get("institution") or "기관미상"
            rel = p.get("score", "")
            body_parts.append(f'\n<a id="{anchor}"></a>\n**{idx}. {sanitize_title(p["title"])}**\n')
            body_parts.append(
                f"\n**저자**: {', '.join(p['authors'][:3])}"
                f" | **기관**: {inst}"
                f" | **날짜**: {pub_date}"
                f" | **관련성 점수**: {rel}"
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
        'tags: ["Daily", "AI", "Research", "Agent", "Memory"]\n'
        "---\n\n"
        "**목차**\n\n"
        + toc_str + "\n\n"
        + "".join(body_parts)
        + ai_notice + "\n"
    )

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

# =============================================================================
# Main
# =============================================================================

def main() -> None:
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

    sections: dict[str, list[dict[str, Any]]] = {}
    reviews_dict: dict[str, list[str]] = {}
    category_summaries: dict[str, str] = {}

    for cat_config in CONFIG["categories"]:
        name = cat_config["name"]
        print(f"\n{'=' * 60}")
        print(f"[{name}] 수집 시작")
        print(f"{'=' * 60}")

        all_papers = fetch_papers_by_category(cat_config, cutoff)
        new_papers = [p for p in all_papers if p["id"] not in reviewed_ids]

        sections[name] = []
        reviews_dict[name] = []

        for paper in new_papers:
            print(f"  리뷰 생성: {paper['title'][:80]}...")
            review = review_paper_with_cache(paper, cat_config, client)
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
        history_path.write_text(json.dumps(sorted(reviewed_ids), indent=2), encoding="utf-8")
        print(f"\n✅ 완료! 총 {total}편 처리.")
    else:
        print("\n오늘 업데이트할 새 논문이 없습니다.")


if __name__ == "__main__":
    main()
