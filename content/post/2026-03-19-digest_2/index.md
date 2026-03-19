---
title: "논문 Daily Digest 2026년 03월 19일 (4편)"
date: 2026-03-19T00:00:00+09:00
draft: false
summary: "Summarization · Long-horizon · Memory 분야 유망 논문 4편 | Haiku 자동 분석"
tags: ["Daily", "AI", "Research"]
---

**목차**

<div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">

| # | 분야 | 제목 |
|---|------|------|
| 1 | 💬 Dialogue Summarization | [PACE-RAG: Patient-Aware Contextual and Evidence-based Policy RAG for Clinical Drug Recommendation](#paper1) |
| 2 | 🔄 Long-horizon | [From Isolated Scoring to Collaborative Ranking: A Comparison-Native Framework for LLM-Based Paper Evaluation](#paper2) |
| 3 | 🧠 Lifelong & Long-range Memory | [TDAD: Test-Driven Agentic Development - Reducing Code Regressions in AI Coding Agents via Graph-Based Impact Analysis](#paper3) |
| 4 | 🧠 Lifelong & Long-range Memory | [Procedural Generation of Algorithm Discovery Tasks in Machine Learning](#paper4) |

</div>


---

**💬 Dialogue Summarization**

<a id="paper1"></a>
**1. PACE-RAG: Patient-Aware Contextual and Evidence-based Policy RAG for Clinical Drug Recommendation**

**저자**: Chaeyoung Huh, Hyunmin Hwang, Jung Hwan Shin | [원문](https://arxiv.org/abs/2603.17356v1) | [PDF](https://arxiv.org/pdf/2603.17356v1)

**한 줄 요약**: 환자 맥락과 유사 사례의 처방 패턴을 합성하여 개인화된 임상 의약품 추천을 실현하는 RAG 프레임워크.

**Background**: 임상 의약품 추천은 단순한 의학 지식 검색을 넘어 개별 환자의 복잡한 임상 신호와 실제 처방 관행을 통합해야 하는 과제를 안고 있다. 기존 LLM은 광범위한 의료 지식을 보유하지만 처방 뉘앙스를 포착하지 못하며, 표준 RAG 방식의 가이드라인 기반 검색은 일반화되어 있고 유사 환자 검색은 다수 패턴을 단순 복제하여 개인의 임상 특수성을 반영하지 못한다.

**핵심 아이디어**

- **구조적 차별점**: PACE-RAG는 임상 신호에 맞춤화된 처방 패턴 분석 메커니즘을 도입하여, 단순 유사도 기반 검색에서 벗어나 실제 임상 결정의 근거가 되는 환자-특이적 맥락 신호를 학습한다. 이 접근법은 guideline과 similar-patient 전략을 계층적으로 통합하되, 특정 임상 신호에 반응하는 처방 패턴의 분포를 직접 모델링함으로써 소수 집단이나 비전형적 사례에서도 적절한 추천을 생성할 수 있다.

- **직관적 비유**: 의사가 환자를 진찰할 때 교과서(가이드라인)를 참고하되, 자신의 경험 속 유사한 환자들이 그 증상에 어떻게 반응했는지 기억하며 최종 진단을 내리는 것과 같다. PACE-RAG는 이 두 정보원을 동시에 활용하되, 각 환자의 고유한 임상 신호(예: 파킨슨병의 진행 단계, 동반 질환)에 따라 검색된 유사 사례의 가중치를 동적으로 조정한다.

**왜 중요한가**: 임상 의약품 추천은 오진과 부작용이 직결되는 고위험 의료 행위이며, 개인화된 정확한 추천을 제공하는 것은 환자 안전과 치료 효과성 향상에 필수적이다. 이 연구는 LLM 기반 임상 의사결정 지원 시스템의 실용화를 앞당기며, 특히 복잡한 질환 관리에서 데이터 기반 개인화의 한계를 극복하는 중요한 시도로 평가된다.

**Research Questions**

*Q1: 개별 환자의 임상 맥락을 어떻게 정량화하고 처방 패턴 검색에 반영할 것인가?* A1: PACE-RAG는 환자의 임상 신호(증상, 질병 진행도, 동반질환 등)를 벡터화하여 임상적으로 유사한 사례를 검색하되, 각 검색된 사례의 처방 패턴이 현재 환자의 신호에 얼마나 적절한지 재점수화하는 context-aware reranking을 적용한다.

*Q2: 파킨슨병 환자군과 MIMIC-IV 벤치마크에서 제안 방법이 기존 RAG 및 LLM 베이스라인과 정량적으로 얼마나 개선되는가?* A2: 파킨슨병 코호트에서 F1 80.84%, MIMIC-IV에서 F1 47.22%를 달성하여 state-of-the-art 성능을 입증했으며, 이는 비맥락화 검색(guideline-only) 대비 현저한 개선을 보여준다.

*Q3: 생성된 추천이 임상적으로 신뢰할 수 있고 해석 가능한가?* A3: PACE-RAG는 최종 의약품 추천과 함께 선택된 유사 환자 사례와 해당 임상 신호를 명시적으로 제시하는 explainable clinical summary를 생성하므로, 의료진이 모델의 판단 근거를 검토하고 검증할 수 있다.

**실험 결과**: 파킨슨병 환자 기반 dataset에서 Llama-3.1-8B 및 Qwen-3.1-8B 모델 대비 F1 80.84% 달성. MIMIC-IV 벤치마크(다중 질환, 다중 약물 추천)에서 F1 47.22%로 기존 RAG 베이스라인 및 순수 LLM 프롬프팅 방식을 우월. ablation study를 통해 patient context 모듈과 pattern retrieval 메커니즘의 각각 기여도 검증됨.

**한계**: 연구는 파킨슨병과 MIMIC-IV라는 제한된 도메인에서만 평가되었으며, 다른 만성질환군에 대한 일반화 가능성 미검증. 임상 신호의 정의와 가중치 설정이 질환별로 수동 조정이 필요한 점은 확장성을 제한한다. 또한 검색 데이터베이스(유사 환자 기록)의 질과 규모에 강하게 의존하므로, 희귀질환이나 데이터 부족 환경에서 성능 저하 가능성이 있다.

**재현성**: 코드 공개: **O** (GitHub 링크 제공) | Llama-3.1-8B, Qwen-3.1-8B (8B 규모 오픈 모델) 기반이며 MIMIC-IV는 요청 기반 접근 필요. 파킨슨병 cohort 데이터는 기관 데이터이므로 완전 재현은 제한될 수 있으나, 코드와 알고리즘 설명을 통해 다른 임상 데이터셋에 적용 가능한 구조로 설계됨.

---

**🔄 Long-horizon**

<a id="paper2"></a>
**2. From Isolated Scoring to Collaborative Ranking: A Comparison-Native Framework for LLM-Based Paper Evaluation**

**저자**: Pujun Zheng, Jiacheng Yao, Jinquan Zheng | [원문](https://arxiv.org/abs/2603.17588v1) | [PDF](https://arxiv.org/pdf/2603.17588v1)

**한 줄 요약**: LLM의 논문 평가를 절대 점수에서 상대 비교 기반 랭킹으로 전환하여 일반화 능력 강화.

**Background**: 기존 LLM 기반 논문 평가는 각 논문에 독립적으로 절대 점수를 할당하는데, 컨퍼런스마다 평가 기준과 점수 스케일이 상이하여 모델이 맥락 특화적 규칙에 과적합되기 쉽다. 이는 학술적 판단력의 전이 가능성을 심각하게 제한한다. 상대적 품질 판단은 절대 점수 편향을 원천 차단할 수 있지만, 기존 연구는 이 접근법을 체계적으로 탐구하지 못했다.

**핵심 아이디어**

- **구조적 차별점**: CNPE는 데이터 구성부터 모델 학습까지 비교 신호를 통합한다. 그래프 기반 유사도 랭킹 알고리즘으로 정보성 높은 논문 쌍을 샘플링하고, 비교 기반 보상으로 감독 학습과 강화학습을 수행한 후, 추론 시 페어와이즈 비교를 통해 전역 상대 랭킹을 도출한다.

- **직관적 비유**: 절대 점수는 마치 고정된 기준으로 각 학생을 평가하는 것처럼 스케일 편향에 취약하지만, 비교 기반 평가는 "논문 A가 B보다 나은가?"라는 상대적 질문에만 답하므로 평가 기준의 변화에 더 견고하다. 여러 쌍의 비교 결과를 모으면 절대적 순위보다 더 안정적인 상대 순위가 도출된다.

**왜 중요한가**: 학술 출판 생태계에서 자동 리뷰는 상이한 평가 환경 간 일관성이 생명이므로, 맥락 독립적 판단 능력은 실제 배포 가능성을 획기적으로 높인다. 이는 LLM 기반 과학 평가의 신뢰성 문제를 근본적으로 해결하는 패러다임 전환이다.

**Research Questions**

*Q1: 절대 점수 대비 상대 비교가 평가 일반화 능력을 얼마나 개선하는가?* A1: 보이지 않은 5개 데이터셋에서 평균 21.8% 상대 개선율 달성, DeepReview-14B 대비 우수한 일반화.

*Q2: 어떤 논문 쌍 샘플링 전략이 학습 효율을 극대화하는가?* A2: 그래프 기반 유사도 랭킹이 무작위 샘플링보다 더 판별력 높은 쌍을 선정, 모델의 구분 능력 향상.

*Q3: 감독 학습과 강화학습의 결합이 비교 기반 학습에서 필수적인가?* A3: 두 방식의 상승 효과가 확인되어 비교 신호의 활용을 극대화.

**실험 결과**: ArXiv, OpenReview 등 학술 논문 데이터를 기반으로 학습하고, 이전에 본 적 없는 5개 평가 데이터셋에서 검증. DeepReview-14B를 baseline으로 설정했을 때 21.8% 상대 개선, Spearman 상관계수 및 NDCG 메트릭에서 일관된 우수성. 특히 도메인 시프트가 큰 시나리오에서 절대 점수 모델의 성능 저하는 급격한 반면, CNPE는 상대적으로 견고함을 입증.

**한계**: 페어와이즈 비교로 인한 추론 복잡도 증가(기존보다 다중 비교 필요), 대규모 논문 컬렉션에서의 계산 오버헤드 미분석. 또한 비교 기반 보상 설계 및 강화학습 수렴 안정성에 대한 이론적 보장 부재.

**재현성**: 코드 공개: O | GitHub 링크 제공, 데이터셋 규모·특성(ArXiv, OpenReview 등) 명시되나 전체 컴퓨팅 자원 상세 정보(GPU 메모리, 학습 시간)는 보충 자료 확인 필요.

---

**🧠 Lifelong & Long-range Memory**

<a id="paper3"></a>
**3. TDAD: Test-Driven Agentic Development - Reducing Code Regressions in AI Coding Agents via Graph-Based Impact Analysis**

**저자**: Pepe Alonso | [원문](https://arxiv.org/abs/2603.17973v1) | [PDF](https://arxiv.org/pdf/2603.17973v1)

**한 줄 요약**: AST 기반 코드-테스트 그래프와 impact analysis로 AI 코딩 에이전트의 회귀 버그 70% 감소.

**Background**: AI 코딩 에이전트는 소프트웨어 버그 해결에 효과적이지만, 기존 테스트를 깨뜨리는 회귀(regression) 문제를 빈번히 야기한다. 현존 벤치마크(SWE-bench 등)는 해결율에만 집중하며, 회귀 동작은 체계적으로 평가되지 않았다. 이는 프로덕션 환경에서 진정한 코드 품질 평가를 어렵게 만드는 근본적 공백이다.

**핵심 아이디어**

- **구조적 차별점**: TDAD는 AST 파싱을 통해 코드와 테스트 간 의존성 그래프를 구축한 후, weighted impact analysis로 변경된 코드가 영향을 미칠 가능성이 높은 테스트를 사전에 식별한다. 기존 방식이 "무엇을 고쳐야 하는가"에만 집중했다면, 이 논문은 "고침으로써 어떤 테스트가 깨질 수 있는가"를 먼저 감지하는 proactive 접근을 취한다.

- **직관적 비유**: 의사가 진료 후 처방전을 내기 전에, 그 약이 환자의 다른 장기에 미칠 부작용을 먼저 파악하는 것과 같다. TDAD는 에이전트가 코드를 수정하기 전에 "영향받을 테스트 범위"를 사전에 제시해 더 신중한 수정을 유도한다.

**왜 중요한가**: 회귀 제거는 단순한 품질 지표를 넘어 AI 에이전트의 실제 배포 가능성을 결정하는 요소다. 논문이 드러낸 핵심 통찰—"작은 모델은 절차적 지시(TDD 하라)보다 문맥 정보(어떤 테스트를 확인할지)를 더 효과적으로 활용한다"—는 향후 에이전트 프롬프트 엔지니어링과 tool design의 방향을 재정의한다.

**Research Questions**

*Q1: AI 에이전트가 도입하는 회귀를 체계적으로 감지하고 예방할 수 있는가?* A1: AST 기반 code-test 그래프 구축과 weighted impact analysis를 통해 회귀 가능성이 높은 테스트를 사전에 식별하고, 에이전트가 이를 검증하도록 유도해 회귀를 70% 감소시켰다.

*Q2: TDD 프롬프팅과 contextual 정보 제공 중 어느 것이 작은 모델의 성능을 더 높이는가?* A2: 실험 결과 TDD prompting만으로는 오히려 회귀를 9.94%로 증가시켰으나, 검증할 테스트 목록을 명시하는 contextual 정보 제공이 훨씬 효과적이었다. 이는 작은 모델이 "무엇을 해야 하는가"보다 "어디를 봐야 하는가"를 더 잘 따른다는 의미다.

*Q3: auto-improvement 루프로 확장 시 얼마나 강건한가?* A3: 10개 인스턴스 부분집합에서 자동 개선 루프를 적용했을 때 해결율이 12%에서 60%로 상승했으나, 회귀는 0%로 유지되었다. 다만 이는 제한된 규모의 실험이므로, 더 큰 스케일에서의 안정성은 추가 검증이 필요하다.

**실험 결과**: Qwen3-Coder 30B(100 인스턴스)와 Qwen3.5-35B-A3B(25 인스턴스)에서 SWE-bench Verified로 평가했다. **핵심 성과**: (1) 테스트 레벨 회귀 6.08%→1.82%(70% 감소), (2) 해결율 24%→32%, (3) TDD prompting만 사용 시 회귀율 9.94%로 역효과, (4) auto-improvement 루프에서 해결율 12%→60%(0% 회귀). 이는 GraphRAG workflow가 실질적 영향을 미친다는 증거다.

**한계**: (1) Qwen 모델만 테스트되어, 다른 규모/아키텍처 에이전트에 일반화 가능성 미확인, (2) 25개 인스턴스만으로 auto-improvement 검증하여 통계적 유의성 부족, (3) AST 기반 impact analysis의 정확도가 코드 복잡도에 따라 어떻게 변하는지 미분석, (4) 의존성 그래프 구축 시 동적 코드(reflection, 동적 import)는 포착하지 못할 가능성.

**재현성**: 코드 공개: **O** (GitHub 링크 제공) | qwen-coder 30B 및 35B 모델 필요, 100~25개 인스턴스로 실험 가능, 계산 자원 구체 명시 없음(공개 링크에서 확인 필요).

<a id="paper4"></a>
**4. Procedural Generation of Algorithm Discovery Tasks in Machine Learning**

**저자**: Alexander D. Goldie, Zilin Wang, Adrian Hayler | [원문](https://arxiv.org/abs/2603.17863v1) | [PDF](https://arxiv.org/pdf/2603.17863v1)

**한 줄 요약**: 절차적 생성으로 수백만 개 ML 알고리즘 발견 태스크를 자동 생성하는 벤치마크.

**Background**: 머신러닝 알고리즘 자동 발견(Algorithm Discovery)은 새로운 옵티마이저나 손실함수 개발을 가속화할 수 있는 유망한 분야이나, 기존 벤치마크는 데이터 오염, 포화된 문제, 평가 방법론의 부재 등으로 체계적 발전이 제한되어 왔다. 강화학습의 절차적 생성 성공에 영감받아, 이 연구는 대규모의 다양한 난이도 태스크 생성 체계를 제시한다.

**핵심 아이디어**

- **구조적 차별점**: DiscoGen은 소수의 설정 파라미터로 수백만 개의 서로 다른 ML 태스크를 절차적으로 생성한다. 기존 정적 벤치마크와 달리, 태스크 분포의 제어 가능성과 확장성을 확보하며, DiscoBench라는 고정된 평가 부분집합으로 공정한 비교를 보장한다.

- **직관적 비유**: 마치 게임 엔진이 무한한 맵을 절차적으로 생성하는 것처럼, DiscoGen은 설정만 조정하면 새로운 최적화 또는 분류 태스크를 계속 만들어낸다. 이를 통해 알고리즘 발견 에이전트(ADA)가 다양한 환경에 일반화되는지 검증할 수 있다.

**왜 중요한가**: 알고리즘 자동 발견이 실질적인 breakthrough를 가능하려면 충분하고 신뢰할 수 있는 태스크 집합이 필수인데, DiscoGen은 이를 해결함으로써 이 분야의 과학적 진전을 가속화한다. 강화학습 커뮤니티의 벤치마킹 성숙도를 ML 알고리즘 발견 영역으로 확대하는 전환점이 될 수 있다.

**Research Questions**

*Q1: 절차적 생성으로 얼마나 다양하고 의미 있는 태스크를 확보할 수 있는가?* A1: 수백만 개의 태스크를 여러 ML 분야(RL 옵티마이저, 이미지 분류 손실함수 등)에서 생성하며, 난이도와 복잡도를 조절 가능한 파라미터로 제어한다.

*Q2: DiscoBench라는 고정 부분집합이 정말 공정한 평가를 보장하는가?* A2: 논문은 데이터 오염 방지와 포화 문제 제거를 명시하지만, 실제 부분집합의 대표성과 난이도 분포에 대한 상세 통계는 제시되지 않았다.

*Q3: 절차적 생성 태스크에서 학습한 ADA가 실제 새로운 알고리즘 설계에 적용되는가?* A3: Prompt 최적화 실험을 제시하나, 실제 미발견 알고리즘의 발견이나 기존 방법 개선 사례는 제한적이다.

**실험 결과**: 코드 및 벤치마크는 공개되었으나, 논문에 명시된 정량 결과가 제한적이다. Prompt 최적화 실험에서 ADA의 성능 향상을 보였으나, Baseline 대비 수치(예: 수렴 속도, 최종 성능 비율)와 통계적 유의성이 부족하다. 여러 ML 분야(RL, 이미지 분류)에서의 교차 분야 일반화 성능 평가도 상세하지 않다.

**한계**: (1) DiscoBench 부분집합이 전체 DiscoGen의 대표성을 어느 정도 담보하는지 불명확하다. (2) 절차적 생성이 실제로 의미 있는 새로운 알고리즘을 발견하는 데 얼마나 효과적인지 증거가 부족하다. (3) ADA 학습에 필요한 컴퓨팅 비용과 확장성 한계에 대한 논의가 결여되어 있다.

**재현성**: 코드 공개: O | GitHub 저장소 제공(https://github.com/AlexGoldie/discogen). 단, 대규모 태스크 생성과 ADA 훈련에 필요한 GPU/메모리 사양, 훈련 시간, 하이퍼파라미터 상세 정보는 논문에서 명확히 제시되지 않아 재현의 난이도가 있을 수 있다.


---

*본 리포트의 논문 리뷰는 Anthropic의 **Haiku** 모델을 사용하여 자동 생성되었습니다.*
