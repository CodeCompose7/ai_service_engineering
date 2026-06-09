# lec04 — MCP로 도구 연결

> - S3 개요: [docs/section3/README.md](../README.md)
> - 분량 20분
> - 산출물: MCP 연결 에이전트

## 1. 목표

직접 짠 도구를 넘어, MCP(Model Context Protocol) 서버에 연결해 그 서버가 제공하는 도구를 에이전트가 쓰게 합니다. 도구를 매번 손으로 만들지 않고, 표준 규격으로 도구 서버를 꽂아 쓰는 방법을 봅니다. MCP 도구도 결국 모델에는 function calling으로 노출되므로, lec01~03에서 익힌 도구 호출 위에 한 층을 더하는 셈입니다.
