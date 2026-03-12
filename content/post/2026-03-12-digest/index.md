---
title: "논문 Daily Digest 2026년 03월 12일 (1편)"
date: 2026-03-12T00:00:00Z
draft: false
tags: ["Daily", "AI", "Robotics", "Memory"]
summary: "Self-Evolving, Memory, Robotics, Reasoning 분야 유망 논문 1편"
---

## 목차

| # | 분야 | 제목 |
|---|------|------|
| 1 | ⏳ Advanced Reasoning (Long-Think) | Stop the Flip-Flop: Context-Preserving Verification for... |


---

## ⏳ Advanced Reasoning (Long-Think)

### 1. Stop the Flip-Flop: Context-Preserving Verification for Fast Revocable Diffusion Decoding

**저자**: Yanzheng Xiang, Lan Wei, Yizhen Yao 외 | [원문](https://arxiv.org/abs/2602.06161v1) | [PDF](https://arxiv.org/pdf/2602.06161v1) | 
**한 줄 요약**: 확산모델 병렬디코딩의 토큰 진동 문제 해결

**핵심 아이디어**:
- 기존 검증 방식은 토큰이 마스킹→복원을 반복하는 flip-flop 진동을 유발하여 추론 효율을 저하시킴
- COVER는 KV 캐시 오버라이드를 통해 검증과 드래프팅을 단일 forward pass에서 수행하며, leave-one-out 검증 시 문맥 정보를 보존함
- 불확실성, 하류 영향도, 캐시 드리프트를 종합한 안정성 인식 점수로 검증 대상 시드를 우선순위화함

**왜 중요한가**:
- 확산 언어모델의 병렬 디코딩 속도를 품질 손실 없이 실질적으로 향상시킴
- 불필요한 재검증 사이클을 대폭 감소시켜 revision budget을 효율적으로 활용함
- LLM 추론 가속화라는 실용적 문제에 대해 즉시 적용 가능한 해결책을 제시함

**Research Questions**:

*Q1: 기존 revocable decoding의 flip-flop 진동이 왜 발생하며 어떤 문제를 야기하는가?*
A1: 토큰 재마스킹 시 문맥 정보가 손실되어 병렬 드래프팅의 조건화가 약화되고, 동일 토큰의 반복적 마스킹-복원 사이클이 revision budget을 낭비함.

*Q2: COVER는 어떻게 문맥 보존과 효율적 검증을 동시에 달성하는가?*
A2: KV 캐시 오버라이드로 두 가지 attention view를 구성하여 시드 위치는 검증용으로 마스킹하면서도 다른 쿼리에는 캐시된 key-value를 주입하고, 대각 보정으로 self-leakage를 방지함.

