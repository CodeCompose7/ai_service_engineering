# S3 — Agent 구성: 빌드

> 상위 계획: [docs/plan/vod_plan.md](../plan/vod_plan.md)의 S3 항목

도구를 쓰는 에이전트를 "동작하게" 만드는 빌드 레이어입니다. 모델이 스스로 도구를 부르는 function calling에서 시작해, 한 도구 에이전트, 여러 도구를 라우팅하는 멀티툴 에이전트로 넓히고, LangGraph로 분기·루프가 있는 흐름까지 만듭니다. 마지막으로 같은 에이전트를 클라우드와 로컬 Ollama 어느 백엔드로도 돌리게 합니다.

이 섹션을 마치면 도구를 호출해 일을 처리하고, 상태와 분기를 가진 그래프로 흐름을 제어하며, 프로바이더를 바꿔 끼울 수 있는 동작하는 에이전트가 손에 들어옵니다.

## 학습 방식

S1·S2와 같습니다. 예제 코드는 이 저장소로 공유되며, devcontainer 안에서 실행해 결과를 관찰하고 핵심을 읽어 이해합니다. 손으로 바꿔보는 부분은 각 단위의 "직접 해보기"로 한정합니다.

## 관통하는 원칙

모든 LLM 호출은 S1·S2처럼 LiteLLM을 경유합니다. function calling도 `litellm.completion`의 tool 인자로 두어, 클라우드와 로컬을 같은 코드로 오갑니다.

로컬 Ollama 실행에는 갈래가 있습니다. tool calling을 지원하는 모델은 그대로 도구를 부르고, 지원하지 않는 모델은 JSON 모드로 폴백해 같은 결과를 냅니다. 이 폴백이 provider-agnostic 에이전트의 핵심입니다.

```mermaid
flowchart LR
  CALL["에이전트 호출"] --> LL["LiteLLM"]
  LL --> CLOUD["클라우드<br/>tool calling"]
  LL --> OLL["Ollama<br/>tool calling 또는 JSON 폴백"]
  classDef default rx:8,ry:8;
```

## 단위 구성

| 단위 | 분 | 주제 | 산출물 |
| --- | --- | --- | --- |
| [lec01](lec01/README.md) | 24 | function calling 원리 | 단일 tool 호출 |
| [lec02](lec02/README.md) | 18 | 단일 도구 에이전트 | 동작 에이전트 |
| [lec03](lec03/README.md) | 27 | multi-tool agent | 멀티툴 에이전트 |
| [lec04](lec04/README.md) | 22 | LangGraph 기초 | 최소 그래프 |
| [lec05](lec05/README.md) | 28 | LangGraph 실전 | 자동화 그래프 |
| [lec06](lec06/README.md) | 19 | provider-agnostic 에이전트 | 클라우드·Ollama 양쪽 동작 |

합계 138분, 6단위입니다.

## 흐름

도구를 부르는 한 번의 호출에서 시작해 점점 넓힙니다. function calling 원리를 익히고, 한 도구로 end-to-end 에이전트를 만들고, 여러 도구를 라우팅합니다. 그다음 LangGraph로 상태·분기·루프가 있는 흐름을 짜고, 마지막으로 백엔드를 바꿔 끼웁니다.

```mermaid
flowchart LR
  L1["lec01<br/>function calling"] --> L2["lec02<br/>단일 도구"] --> L3["lec03<br/>멀티툴"] --> L4["lec04<br/>LangGraph 기초"] --> L5["lec05<br/>LangGraph 실전"] --> L6["lec06<br/>provider-agnostic"]
  classDef default rx:8,ry:8;
```

## 코드와 테스트

공유되는 예제 코드는 [src/section3](../../src/section3)에, 테스트는 [tests/section3](../../tests/section3)에 같은 `lecNN` 구조로 들어 있습니다. 이 저장소를 받아 devcontainer 안에서 그대로 실행하는 것이 기본이고, 손으로 바꿔보는 부분은 각 단위의 "직접 해보기"로 한정합니다.
