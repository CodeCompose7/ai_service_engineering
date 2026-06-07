# lec04 — 단일 provider 호출

> - S1 개요: [docs/section1/README.md](../README.md)
> - 분량 12분
> - 산출물: 호출 스니펫

## 목표

첫 LLM 호출을 보냅니다. 이 단위에서 익히는 것은 다음 두 가지입니다.

- 메시지가 어떤 구조로 구성되는지 봅니다.
- 응답에서 무엇을 꺼내 쓰는지 익힙니다.

프로바이더는 기본인 Gemini 하나만 씁니다.

중요한 결정 하나를 처음부터 적용합니다. 첫 호출이라도 프로바이더 SDK를 직접 부르지 않고 LiteLLM을 경유합니다. 지금은 모델이 하나뿐이라 굳이 추상화가 필요 없어 보일 수 있지만, lec06에서 모델을 바꿀 때 코드가 아니라 문자열만 바꾸려면 시작부터 LiteLLM 위에 서 있어야 합니다.

```mermaid
flowchart LR
  ENVF[".env"] -->|"load_dotenv()"| EV["환경변수<br/>GEMINI_API_KEY"]
  MSG["messages<br/>system + user"] --> LC["litellm.completion"]
  EV --> LC
  LC --> P["gemini/... 모델"]
  P --> R["응답"]
  R --> CT["choices[0].message.content"]
  R --> US["usage (토큰 수)"]
  classDef default rx:8,ry:8;
```

## 메시지 구조

대화형 LLM API는 보통 메시지의 목록을 입력으로 받습니다. 각 메시지는 역할(`role`)과 내용(`content`)을 가집니다. 역할은 크게 셋입니다.

| 역할 | 무엇을 담나 | 언제 |
| --- | --- | --- |
| `system` | 모델에게 주는 전반적인 지시나 페르소나 | 대화 맨 앞에 한 번 |
| `user` | 사용자의 입력 | 사용자가 말할 때마다 |
| `assistant` | 모델이 이전에 한 답변 | 멀티턴에서 직전 맥락을 이어줄 때 |

단일 호출에서는 보통 `system` 하나와 `user` 하나면 충분합니다.

```mermaid
flowchart TD
  S["system<br/>지시·페르소나"] --> M["messages 목록"]
  U["user<br/>사용자 입력"] --> M
  A["assistant<br/>이전 답변 (멀티턴)"] --> M
  M --> LC["litellm.completion"]
  classDef default rx:8,ry:8;
```

## 첫 호출

아래는 공유된 예제의 핵심입니다. 직접 타이핑하기보다 저장소의 파일을 열어 함께 읽습니다. 흐름은 다음과 같습니다.

- `.env`의 키를 환경변수로 불러옵니다.
- `litellm.completion`을 부릅니다.
- 모델은 `"gemini/gemini-..."`처럼 `프로바이더/모델` 형식의 문자열로 지정합니다. 구체 모델명은 녹화 시점 최신으로 확정합니다.

```python
import os
from dotenv import load_dotenv
import litellm

load_dotenv()  # .env의 GEMINI_API_KEY를 환경변수로 로드

resp = litellm.completion(
    model="gemini/gemini-2.5-flash",  # 모델명은 녹화 시점 최신으로 확정
    messages=[
        {"role": "system", "content": "너는 간결하게 답하는 도우미야."},
        {"role": "user", "content": "한 문장으로 자기소개를 해줘."},
    ],
)

print(resp.choices[0].message.content)
```

`load_dotenv()`가 키를 환경변수로 올려두면, LiteLLM은 모델 문자열의 프로바이더 부분을 보고 알아서 `GEMINI_API_KEY`를 찾아 씁니다. 키를 코드에 넣거나 함수 인자로 넘길 필요가 없습니다.

## 응답에서 무엇을 꺼내나

LiteLLM의 응답은 OpenAI 형식을 따릅니다. 프로바이더가 무엇이든 같은 모양으로 돌려준다는 점이 LiteLLM을 쓰는 큰 이유입니다.

| 꺼낼 값 | 경로 | 무엇인가 |
| --- | --- | --- |
| 본문 텍스트 | `resp.choices[0].message.content` | 모델이 돌려준 답변 |
| 토큰 사용량 | `resp.usage` | `prompt_tokens`, `completion_tokens`, `total_tokens` |

`usage`의 입력·출력 토큰 수로 lec02에서 말한 비용 감각을 실제 숫자로 확인할 수 있습니다.

```python
print(resp.usage)  # prompt_tokens, completion_tokens, total_tokens
```

응답 객체에는 이 밖에도 종료 이유 등 여러 필드가 있습니다. 처음에는 `content`와 `usage` 두 가지만 확실히 잡아도 충분합니다.

## 자주 만나는 오류

| 증상 | 원인 | 대응 |
| --- | --- | --- |
| 인증 오류 | 키가 비어 있거나 틀림 | `.env`의 `GEMINI_API_KEY`를 다시 확인 |
| 프로바이더 판단 실패 | 모델 문자열에 접두사 누락 | `gemini/` 접두사가 붙었는지 확인 |
| 일시적 거절 | 무료 티어 호출 한도 초과 | 잠시 뒤 다시 시도 |

호출 한도로 인한 거절을 어떻게 코드로 다룰지는 뒤 섹션에서 정식으로 다룹니다.

## 실행

공유된 첫 호출 예제를 실행합니다. Gemini 키가 `.env`에 있으면 클라우드로, 없으면 예제에 표시된 대로 Ollama 모델 문자열로 바꿔 실행합니다.

```bash
uv run python src/section1/lec04/first_call.py
```

출력에서 두 가지를 확인합니다.

- 모델이 돌려준 본문 텍스트를 봅니다.
- `usage`에 찍힌 입력·출력 토큰 수를 봅니다.

lec02에서 말한 "길이가 곧 비용"이라는 감각을 여기서 실제 숫자로 봅니다.

## 정리

- 입력은 역할과 내용을 가진 메시지의 목록입니다.
- 첫 호출부터 `litellm.completion`을 쓰고, 모델은 `프로바이더/모델` 문자열로 지정합니다.
- 응답은 OpenAI 형식이라 `choices[0].message.content`와 `usage`로 본문과 토큰 수를 꺼냅니다.

## 다음 단위

[lec05 — 프롬프트 패턴](../lec05/README.md)에서 이 메시지 안에 무엇을 어떻게 담아야 원하는 출력이 나오는지 설계합니다.
