# S1 — LLM을 서비스로

> 상위 계획: [docs/plan/vod_plan.md](../plan/vod_plan.md)의 S1 항목

멀티 프로바이더 호출부터 신뢰할 수 있는 구조화 출력까지, 서비스 소비자 관점의 기본기를 다룹니다. 모델을 직접 만들지 않고, 이미 있는 모델을 호출해 서비스의 한 부품으로 쓰는 감각을 잡는 것이 이 섹션의 목표입니다.

이 섹션을 마치면 클라우드 모델과 로컬 Ollama 모델을 같은 코드로 부르고, 출력이 깨질 때 이를 검증·교정하는 작은 함수까지 손에 들어옵니다.

## 학습 방식

이 과정은 코드를 한 줄씩 따라 치는 방식이 아닙니다. 예제 코드는 이 저장소로 공유되며, 여러분은 그 코드를 devcontainer 안에서 실행해 결과를 관찰하고, 핵심 부분을 읽어 이해합니다. AI 시대에 보일러플레이트를 손으로 옮겨 적는 데 시간을 쓸 이유는 없습니다.

대신 정말 의미가 있는 몇 군데만 직접 손봅니다. 자기 키를 넣는 일, 프롬프트를 바꿔 출력이 어떻게 달라지는지 보는 일, 스키마에 필드를 더해보는 일 같은 것입니다. 각 단위 문서에는 실행하는 방법과 무엇을 관찰할지가 적혀 있고, 직접 만져볼 부분은 "직접 해보기"로 표시합니다.

```bash
# 예: 한 단위의 예제 실행 (devcontainer 터미널에서)
uv run python src/section1/lec04/first_call.py
```

## 관통하는 원칙

S1의 모든 예제는 LiteLLM을 경유합니다. 첫 호출부터 프로바이더별 SDK를 직접 부르지 않고 `litellm.completion` 하나로 시작합니다. 그래야 뒤에서 모델을 바꿀 때 코드가 아니라 문자열만 바뀝니다. 이 결정이 lec04부터 lec09까지를 하나로 꿰는 축입니다.

임베딩만 예외입니다. S1에서는 임베딩을 다루지 않으므로 이 예외는 S2에서 처음 등장합니다.

```mermaid
flowchart LR
  APP["호출 코드"] --> W["chat 래퍼"]
  W --> LL["LiteLLM"]
  LL --> G["Gemini · 권장"]
  LL --> O["OpenAI · 보조"]
  LL --> C["Claude · 보조"]
  LL --> OL["Ollama · 로컬"]
  classDef default rx:8,ry:8;
```

## 단위 구성

| 단위 | 분 | 주제 | 산출물 |
| --- | --- | --- | --- |
| [lec01](lec01/README.md) | 17 | 환경 셋업 | 동작하는 개발 컨테이너 |
| [lec02](lec02/README.md) | 21 | LLM 멘탈 모델 | 개념 |
| [lec03](lec03/README.md) | 13 | 샘플링 파라미터 | 비교 스크립트 |
| [lec04](lec04/README.md) | 16 | 단일 provider 호출 | 호출 스니펫 |
| [lec05](lec05/README.md) | 13 | 프롬프트 패턴 | 프롬프트 템플릿 |
| [lec06](lec06/README.md) | 8 | LiteLLM 멀티 프로바이더 | 멀티 프로바이더 래퍼 |
| [lec07](lec07/README.md) | 8 | Ollama 로컬 | 로컬 호출 예제 |
| [lec08](lec08/README.md) | 19 | 구조화 출력 1 | Pydantic 모델 |
| [lec09](lec09/README.md) | 19 | 구조화 출력 2 | 안전한 추출 함수 |

합계 134분, 9단위입니다.

## 흐름

앞의 세 단위는 손을 풀고 머릿속 모델을 세우는 구간입니다. lec01에서 환경을 맞추고, lec02에서 LLM을 어떻게 바라볼지, lec03에서 출력을 어디까지 흔들 수 있는지 감을 잡습니다.

lec04부터 실제 호출이 시작됩니다. 단일 모델 호출(lec04)에서 출발해 프롬프트를 설계하고(lec05), 같은 코드로 프로바이더를 바꾼 다음(lec06) lec07에서 로컬 모델까지 끌어옵니다. 마지막 두 단위는 자연어 응답을 프로그램이 믿고 쓸 수 있는 구조화 데이터로 바꾸는 방법입니다. lec08에서 함정을 보고, lec09에서 instructor로 해결합니다.

```mermaid
flowchart TD
  subgraph G0["손풀기 · 멘탈 모델"]
    L1["lec01<br/>환경 셋업"] --> L2["lec02<br/>LLM 멘탈 모델"] --> L3["lec03<br/>샘플링 파라미터"]
  end
  subgraph G1["호출"]
    L4["lec04<br/>단일 호출"] --> L5["lec05<br/>프롬프트 패턴"] --> L6["lec06<br/>멀티 프로바이더"] --> L7["lec07<br/>Ollama 로컬"]
  end
  subgraph G2["구조화 출력"]
    L8["lec08<br/>JSON 함정"] --> L9["lec09<br/>instructor"]
  end
  L3 --> L4
  L7 --> L8
  classDef default rx:8,ry:8;
```

## 코드와 테스트

공유되는 예제 코드는 [src/section1](../../src/section1)에, 테스트는 [tests/section1](../../tests/section1)에 같은 `lecNN` 구조로 들어 있습니다. 이 저장소를 받아 devcontainer 안에서 그대로 실행하는 것이 기본이고, 손으로 바꿔보는 부분은 각 단위의 "직접 해보기"로 한정합니다.
