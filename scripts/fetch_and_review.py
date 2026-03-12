import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
import anthropic

KST = timezone(timedelta(hours=9))

# ════════════════════════════════════════════════════
# ✏️ [설정] 연구 카테고리 및 기관 필터링
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
    ],
    "days_back": 7, # 보통 데일리용이므로 기간을 좁혔습니다.
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
# 🤖 [프롬프트] 도메인별 특화 가이드
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
# 🛠️ 유틸리티 및 수집 로직 (기존 유지/강화)
# ════════════════════════════════════════════════════

def sanitize_for_hugo(text: str) -> str:
    if not text: return ""
    text = re.sub(r'\{\{.*?\}\}', '', text, flags=re.DOTALL)
    text = re.sub(r'^#{1,6}\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
    return text

def sanitize_title(title: str) -> str:
    return re.sub(r'\{.*?\}', '', title).replace('"', '\\"').replace("|", "-").strip()

# ════════════════════════════════════════════════════
# 📡 논문 수집 (기존 유지/점수 산정 포함)
# ════════════════════════════════════════════════════
def fetch_papers_by_category(cat_config: dict, cutoff: datetime) -> list:
    category = cat_config["category"]
    keywords = cat_config.get("keywords", [])
    limit = cat_config["papers_per_day"]

    kw_query = " OR ".join([f'all:"{kw}"' for kw in keywords])
    query = f"cat:{category} AND ({kw_query})"
    
    params = {"search_query": query, "sortBy": "submittedDate", "sortOrder": "descending", "max_results": 30}
    
    try:
        resp = requests.get("https://export.arxiv.org/api/query", params=params, timeout=60)
        resp.raise_for_status()
    except: return []

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(resp.content)
    candidates = []

    for entry in root.findall("atom:entry", ns):
        published = datetime.fromisoformat(entry.find("atom:published", ns).text.replace("Z", "+00:00"))
        if published < cutoff: continue

        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        comment = entry.find("arxiv:comment", ns)
        comment_text = comment.text if comment is not None else ""

        # ⭐️ 기관 점수제 로직
        score = 0
        is_vvip = False
        institution_found = ""

        if any(conf.lower() in comment_text.lower() for conf in TOP_CONFERENCES): score += 15
        if "github.com" in summary.lower() or "github.com" in comment_text.lower(): score += 10
        
        for inst in TOP_INSTITUTIONS:
            if inst.lower() in summary.lower() or inst.lower() in comment_text.lower():
                score += 10
                institution_found = inst
                break
        for inst in VVIP_LABS:
            if inst.lower() in summary.lower() or inst.lower() in comment_text.lower():
                score += 25
                is_vvip = True
                break

        if score < 10: continue # 낮은 점수 논문 필터링

        paper_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
        candidates.append({
            "id": paper_id, "title": title, "summary": summary,
            "authors": [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)],
            "abs_url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
            "score": score, "is_vvip": is_vvip, "institution": institution_found
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]
# ════════════════════════════════════════════════════
# 🧠 AI 리뷰 생성 (Sonnet 4.6 + Prompt Caching)
# ════════════════════════════════════════════════════

def review_paper_with_cache(paper: dict, category_id: str, client: anthropic.Anthropic) -> str:
    domain_guide = DOMAIN_GUIDES.get(category_id, "일반적인 AI 기술 분석에 집중하세요.")
    
    # AI용 맥락 정보 (결과물에는 노출 안 함)
    inst_info = f"기관: {paper['institution']}" if paper['institution'] else "기관 정보 없음"
    if paper['is_vvip']: inst_info += " (업계 최고 권위 연구소)"

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6", # Haiku 4.5 (2026 기준 명칭 대응)
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{STYLE_PROMPTS}\n\n[Domain Guide]\n{domain_guide}",
                            # ⭐️ 카테고리별 공통 지침 캐싱 (비용 절감 핵심)
                            "cache_control": {"type": "ephemeral"} 
                        },
                        {
                            "type": "text",
                            "text": f"\n\n[Input Paper Context]\n{inst_info}\nTitle: {paper['title']}\nAbstract: {paper['summary'][:2000]}\n\n리뷰 시작:"
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
# 💾 저장 및 메인 로직
# ════════════════════════════════════════════════════

def save_daily_digest(date_str: str, sections: dict, reviews: dict):
    today_kst = datetime.now(KST).strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in sections.values())

    # 목차 생성
    toc_rows = []
    idx = 1
    for cat_name, papers in sections.items():
        for p in papers:
            title = p['title'][:55] + "..." if len(p['title']) > 55 else p['title']
            toc_rows.append(f"| {idx} | {cat_name} | {title.replace('|','-')} |")
            idx += 1
    toc_str = "| # | 분야 | 제목 |\n|---|------|------|\n" + "\n".join(toc_rows)

    # 본문 생성
    body_parts = []
    idx = 1
    for cat_name, papers in sections.items():
        if not papers: continue
        body_parts.append(f"\n---\n\n**{cat_name}**\n")
        for p, r in zip(papers, reviews[cat_name]):
            body_parts.append(f"\n**{idx}. {sanitize_title(p['title'])}**\n")
            body_parts.append(f"\n**저자**: {', '.join(p['authors'][:3])} | [원문]({p['abs_url']}) | [PDF]({p['pdf_url']})\n\n{r}\n")
            idx += 1
    
    # ── 하단 고지 문구 생성 ──
    ai_model_notice = "\n\n---\n\n*본 리포트의 논문 리뷰는 Anthropic의 **Claude 4.6 Sonnet** 모델을 사용하여 자동 생성되었습니다.*"
    
    content = f"""---
title: "논문 Daily Digest {today_kst} ({total}편)"
date: {date_str}T00:00:00Z
draft: false
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
# 💾 실행 및 저장 (Main Flow)
# ════════════════════════════════════════════════════
def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key: return print("❌ API Key missing")
    
    client = anthropic.Anthropic(api_key=api_key)
    now_kst = datetime.now(KST)
    cutoff = now_kst - timedelta(days=CONFIG["days_back"])
    history_path = Path("data/reviewed_ids.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed_ids = set(json.loads(history_path.read_text())) if history_path.exists() else set()

    sections, reviews_dict = {}, {}

    for cat_config in CONFIG["categories"]:
        name = cat_config["name"]
        print(f"📡 {name} 검색 중...")
        all_papers = fetch_papers_by_category(cat_config, cutoff)
        new_papers = [p for p in all_papers if p["id"] not in reviewed_ids]
        
        sections[name], reviews_dict[name] = [], []

        for paper in new_papers:
            print(f"  📝 리뷰 생성 (Caching): {paper['title'][:50]}...")
            review = review_paper_with_cache(paper, cat_config["category"], client)
            sections[name].append(paper)
            reviews_dict[name].append(review)
            reviewed_ids.add(paper["id"])
            time.sleep(1) # API Rate Limit 방지

    if sum(len(v) for v in sections.values()) > 0:
        date_str = now_kst.strftime("%Y-%m-%d")
        save_daily_digest(date_str, sections, reviews_dict)
        history_path.write_text(json.dumps(list(reviewed_ids), indent=2))
        print("🎉 모든 작업 완료!")
    else:
        print("📭 오늘 업데이트할 새 논문이 없습니다.")

if __name__ == "__main__":
    main()
