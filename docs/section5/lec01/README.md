# lec01 — FastAPI 서빙 + 스트리밍

> - S5 개요: [docs/section5/README.md](../README.md)
> - 분량 25분
> - 산출물: 추론 API 서버

## 1. 목표

S1~S4에서 만든 기능을 FastAPI로 감싸 API로 내보냅니다. lifespan으로 자원을 띄우고, /generate 엔드포인트로 요청을 받고, 입력을 검증하고 에러를 처리하며, StreamingResponse로 토큰을 흘려보냅니다.
