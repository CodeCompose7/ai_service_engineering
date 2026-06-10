# lec05 — 운영 신뢰성: 비용·레이트리밋·회복력

> - S4 개요: [docs/section4/README.md](../README.md)
> - 분량 20분
> - 산출물: 운영 신뢰성 모듈

## 1. 목표

"동작하는" 에이전트를 "출하 가능한" 시스템으로 끌어올리는 운영 층을 만듭니다. 토큰·비용 예산, 재시도·백오프·타임아웃, 폴백 체인, 프롬프트 캐싱으로 비용과 한계와 실패를 견디게 합니다.

```mermaid
flowchart LR
  L4["lec04<br/>주입 방어"] --> L5["lec05<br/>운영 신뢰성"] --> L6["lec06<br/>평가·검증"]
  classDef default rx:8,ry:8;
  classDef now fill:#eaf2ff,stroke:#4a78c0;
  class L5 now;
```

## 2. 운영 신뢰성이란

데모에서 한 번 도는 것과, 수천 명이 동시에 쓰는 서비스로 사는 것은 다릅니다. 모델 호출은 돈이 들고, 레이트리밋에 걸리고, 가끔 실패하고, 느려집니다. 운영 신뢰성은 이 현실을 견디는 층입니다. 모델 호출 둘레에 두릅니다.

- 비용: 토큰을 누적해 예산을 넘으면 막습니다. 폭주를 막는 안전판입니다.
- 한계: 레이트리밋(429)에 걸리면 잠깐 쉬었다 다시 시도합니다.
- 실패: 한 모델이 안 되면 다른 모델로 넘어갑니다.
- 지연: 너무 느리면 끊습니다.

여기서는 패턴을 손으로 짜 봅니다. 실전에서는 이 호출이 LiteLLM이고, LiteLLM이 `num_retries`·`fallbacks`·`timeout`을 내장 지원합니다. 직접 짜 보면 그 내장 기능이 무엇을 하는지 또렷해집니다.

## 3. 비용·토큰 예산

토큰은 곧 돈입니다. 에이전트가 루프를 돌며 호출을 거듭하면 비용이 새기 쉽습니다. 그래서 예산을 두고, 쓴 만큼 누적해 한도를 넘으면 막습니다.

```python
class Budget:
    def charge(self, tokens):
        if self.spent + tokens > self.limit:
            raise BudgetError(...)
        self.spent += tokens
```

한도 1000에서 400씩 쓰면 두 번은 통과하고 세 번째(800+400)는 막힙니다. 폭주하는 에이전트가 돈을 무한정 태우지 못하게 하는 안전판입니다.

## 4. 재시도·백오프·타임아웃

레이트리밋(429)이나 일시적 오류는 잠깐 뒤 다시 하면 대개 됩니다. 그런데 바로 다시 때리면 서버를 더 밀어붙입니다. 그래서 쉬는 간격을 지수로 늘립니다. 이것이 백오프입니다. 그리고 무한정 기다리지 않게 타임아웃으로 끊습니다.

```mermaid
flowchart TD
  C["호출"] --> T{"성공?"}
  T -->|"예"| OK["결과"]
  T -->|"일시적 실패<br/>429·타임아웃"| M{"시도 남음?"}
  M -->|"예"| W["백오프 대기<br/>0.05 → 0.10 → 0.20s"] --> C
  M -->|"아니오"| FAIL["실패 올림"]
  classDef default rx:8,ry:8;
```

```python
async def with_retry(call, max_attempts=4, base_delay=0.05):
    for attempt in range(max_attempts):
        try:
            return await call()
        except (RateLimitError, TimeoutError):
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(base_delay * (2 ** attempt))
```

대기 간격이 0.05, 0.10, 0.20초로 두 배씩 늡니다. 영구적 오류(스키마 오류 같은)는 재시도해도 소용없으니, 재시도는 일시적 오류에만 겁니다.

## 5. 폴백 체인

한 모델이나 프로바이더가 죽어도 서비스는 살아 있어야 합니다. 그래서 후보를 줄로 세워, 앞이 실패하면 다음으로 넘어갑니다.

```mermaid
flowchart LR
  C["호출"] --> A["모델 A"]
  A -->|"실패"| B["모델 B"]
  B -->|"실패"| D["모델 C"]
  A -->|"성공"| OK["결과"]
  B -->|"성공"| OK
  D -->|"성공"| OK
  D -->|"실패"| FAIL["모두 실패"]
  classDef default rx:8,ry:8;
```

재시도가 같은 모델을 다시 부르는 것이라면, 폴백은 아예 다른 모델로 바꾸는 것입니다. 둘을 겹쳐 쓰기도 합니다. 한 모델에 몇 번 재시도하고, 그래도 안 되면 다음 모델로 폴백합니다.

## 6. 프롬프트 캐싱

같은 시스템 프롬프트나 큰 지식을 매 호출 새로 보내면, 그 토큰값을 매번 냅니다. 프로바이더는 안정적인 앞부분을 캐시해 두고, 다음 호출에서 그 부분을 싸게(캐시된 토큰은 훨씬 저렴) 재사용합니다. 비용과 지연이 같이 줄어듭니다.

```mermaid
flowchart LR
  P["안정적 앞부분<br/>시스템·지식 (캐시됨)"] --> M["모델"]
  Q["바뀌는 뒷부분<br/>질문"] --> M
  classDef default rx:8,ry:8;
  classDef cached fill:#eaf2ff,stroke:#4a78c0;
  class P cached;
```

핵심은 순서입니다. 안정적인 것(시스템·지식)을 앞에, 매번 바뀌는 것(질문)을 뒤에 둬야 앞부분이 캐시로 재사용됩니다. lec01에서 순서를 모델 주목도 때문에 다뤘다면, 여기서는 캐시 때문에 다시 중요해집니다. Anthropic·OpenAI·Gemini가 지원하고 LiteLLM으로 켭니다.

## 7. 운영 신뢰성을 하네스로 엮기

reliability.py가 패턴을 따로 보였다면, [reliable_agent.py](../../../src/section4/lec05/reliable_agent.py)는 모델 호출 둘레에 그것들을 한 흐름으로 두릅니다. `ask` 한 번에 예산을 차감하고, 폴백 체인을 도는데, 각 후보는 재시도와 타임아웃으로 감쌉니다. 예산을 넘으면 모델을 부르지도 않습니다.

```mermaid
flowchart TD
  ASK["ask(messages)"] --> BUD{"예산 안?"}
  BUD -->|"초과"| REF["거부 (모델 안 부름)"]
  BUD -->|"통과"| M1["주모델<br/>재시도 + 타임아웃"]
  M1 -->|"성공"| OK["응답"]
  M1 -->|"실패"| M2["보조모델<br/>재시도 + 타임아웃"]
  M2 -->|"성공"| OK
  M2 -->|"실패"| FAIL["모든 후보 실패"]
  classDef default rx:8,ry:8;
```

코드 구조는 비용 게이트와 폴백 체인입니다. 체인의 각 후보를 `with_retry`와 `with_timeout`으로 감쌉니다.

```mermaid
flowchart TB
  ASK["ReliableAgent.ask"]
  ASK --> BUD["Budget.charge<br/>비용 게이트"]
  ASK --> CHAIN["폴백 체인 (models)"]
  CHAIN --> RT["with_retry<br/>지수 백오프"]
  CHAIN --> TO["with_timeout"]
  RT --> MODEL["모델 호출 (acomplete 등)"]
  classDef default rx:8,ry:8;
```

```bash
uv run python src/section4/lec05/reliable_agent.py
```

```text
=== 정상 (예산 충분, 1차 성공) ===
  답: RAG는 언어 모델이 답하기 전에 외부에서 관련 정보를 검색해 ...
  트레이스: ['예산 25토큰 차감 (남은 9975)', '주모델 성공']

=== 1차 다운 → 폴백 ===
  답: RAG는 LLM이 외부 지식에서 관련 정보를 검색해 더 정확히 답하도록 ...
  트레이스: ['예산 25토큰 차감 (남은 9975)', '주모델 재시도 1 (0.05s, 과부하 429)', '주모델 실패 → 폴백 (과부하 429)', '보조모델 성공']

=== 예산 초과 (한도 5토큰) ===
  답: 예산을 초과해 요청을 거부합니다.
  트레이스: ['예산 초과 → 거부 (예산 초과: 0 + 25 > 5)']
```

읽어낼 점입니다.

- 예산이 모델 앞에 섭니다. 한도를 넘으면 모델을 부르지도 않고 거부합니다. 에이전트를 켜둔 채 두면 비용이 폭주하는 사고를 여기서 막습니다.
- 1차 모델이 과부하여도 재시도 뒤 폴백으로 보조 모델이 받아, 서비스가 죽지 않습니다. 트레이스가 운영 흐름을 그대로 보입니다.
- 여기 예산은 우리가 센 토큰 추정입니다. 실전에서는 응답의 실제 사용량이나 누적 청구액으로도 재고, 요청별·사용자별·일별로 한도를 둡니다.
- 이것이 lec02~04의 하네스가 모델을 부르던 그 자리를, 비용·실패·지연에 견디게 감싼 모습입니다.

## 8. 여러 하네스에 공통 관심사 더하기

하네스를 여럿 만들면(비속어 감지·요약·번역 등) 예산 같은 공통 관심사를 모두에 더하고 싶어집니다. 클래스마다 찾아가 박을 수는 없습니다. 세 방법을 견줍니다.

상속으로 부모에 예산을 두는 방법입니다.

```python
class BaseHarness:
    def __init__(self, budget):
        self.budget = budget
    async def _call(self, messages):
        self.budget.charge(_cost(messages))
        return await acomplete(messages)

class SummarizeHarness(BaseHarness):   # _call을 물려받아 쓴다
    ...
```

각 하네스를 감싸는 래퍼를 따로 두는 방법입니다.

```python
class BudgetedSummarize:               # SummarizeHarness를 감싼다
    def __init__(self, inner, budget):
        self.inner, self.budget = inner, budget
    async def run(self, text):         # run이라는 시그니처를 알아야 한다
        self.budget.charge(...)
        return await self.inner.run(text)
```

호출을 감싸 주입하는 방법입니다.

```python
def budgeted(call, budget):            # 호출 한 곳을 감싼다
    async def wrapped(messages):
        budget.charge(_cost(messages))
        return await call(messages)
    return wrapped

llm = budgeted(acomplete, budget)      # 한 번만
summarize = SummarizeHarness(llm)      # 같은 llm
translate = TranslateHarness(llm)      # 같은 llm — 예산을 공유
```

| 방법 | 문제 |
| --- | --- |
| 상속 (BaseHarness) | 단일 계층이라 예산·로깅·트레이싱을 같이 못 섞고 강결합입니다. 상속보다 합성입니다 |
| 각 하네스 클래스를 래핑 | 하네스마다 인터페이스(run·handle·summarize_reviews)가 달라 래퍼를 일반화 못 합니다. 게다가 예산은 호출의 관심사라 층이 틀립니다 |
| 호출 주입 (DI) | 한 곳만 두르고 모두 공유합니다. 관심사가 맞는 층에 붙습니다 |

핵심은 예산이 하네스가 아니라 호출의 관심사라는 점입니다. 모두가 지나는 호출 한 곳을 감싸고 그것을 주입하면, 하나만 감싸도 모든 하네스가 공유합니다. 하네스의 메서드 이름이 `run`이든 `handle`이든 상관없습니다. 다 같은 `llm`을 받아 부를 뿐입니다.

```mermaid
flowchart LR
  S["SummarizeHarness"] --> L["budgeted(call)<br/>예산을 호출 한 곳에"]
  T["TranslateHarness"] --> L
  L --> M["모델"]
  classDef default rx:8,ry:8;
```

[compose.py](../../../src/section4/lec05/compose.py)가 이 DI 방식을 보입니다.

```bash
uv run python src/section4/lec05/compose.py
```

```text
=== 두 하네스가 한 예산을 공유 (한도 40) ===
  SummarizeHarness: 성공 → 남은 예산 31
  TranslateHarness: 성공 → 남은 예산 23
  SummarizeHarness: 성공 → 남은 예산 14
  TranslateHarness: 성공 → 남은 예산 7
  SummarizeHarness: 거부 (예산 초과: 33 + 10 > 40)
```

두 하네스가 같은 예산을 공유합니다. 번갈아 돌리면 한 예산이 둘에 걸쳐 줄고, 다 떨어지면 다음 호출이 거부됩니다. 어느 하네스 클래스도 예산을 모릅니다. 예산은 주입된 호출에만 있습니다. 실전에서는 이 공유 호출 층이 LiteLLM Router이고, budgets·fallbacks·retries를 거기 설정하면 모든 하네스가 받습니다.

## 9. 예제 코드가 하는 일 및 결과

[reliability.py](../../../src/section4/lec05/reliability.py)는 네 패턴을 가짜 호출로 결정적으로 보입니다. 레이트리밋을 일부러 일으킬 수 없으니, 모사한 실패로 메커니즘을 드러냅니다.

```mermaid
flowchart TB
  MAIN["main()"]
  MAIN --> B["Budget<br/>charge · remaining"]
  MAIN --> R["with_retry<br/>지수 백오프"]
  MAIN --> F["with_fallback<br/>폴백 체인"]
  MAIN --> T["with_timeout<br/>asyncio.wait_for"]
  classDef default rx:8,ry:8;
```

```bash
uv run python src/section4/lec05/reliability.py
```

```text
=== 비용·토큰 예산 (한도 1000) ===
  +400 토큰 → 남은 예산 600
  +400 토큰 → 남은 예산 200
  +400 토큰 → 예산 초과: 800 + 400 > 1000

=== 재시도·백오프 (429 두 번 뒤 성공) ===
  1번째 실패(429 Too Many Requests) → 0.05s 대기 후 재시도
  2번째 실패(429 Too Many Requests) → 0.10s 대기 후 재시도
  결과: 성공 (총 3회 시도)

=== 폴백 체인 (앞 모델 실패 → 다음) ===
  후보 0 실패(모델 A 과부하) → 다음으로
  결과: 모델 B 응답

=== 타임아웃 (0.1s 한도) ===
  0.1s 초과 → TimeoutError로 끊음
```

읽어낼 점입니다.

- 예산은 누적 한도입니다. 800을 쓴 뒤 400을 더 쓰려 하면 막힙니다. 비용이 새기 전에 멈춥니다.
- 재시도는 백오프와 함께 갑니다. 대기가 0.05, 0.10초로 두 배씩 늘어, 서버를 몰아붙이지 않으면서 일시적 실패를 넘깁니다. 두 번 실패해도 세 번째에 성공합니다.
- 폴백은 다른 후보로 넘어갑니다. 모델 A가 과부하여도 모델 B가 받아 서비스가 죽지 않습니다.
- 타임아웃은 무한정 기다리지 않게 끊습니다. 느린 호출 하나가 전체를 잡아먹지 않게 합니다.

## 10. 정리

- 운영 신뢰성은 비용·한계·실패·지연을 견디는 층입니다. 모델 호출 둘레에 두릅니다.
- 비용은 토큰 예산으로 막고, 일시적 실패는 지수 백오프 재시도로 넘기고, 모델이 죽으면 폴백 체인으로 잇고, 느리면 타임아웃으로 끊습니다.
- 프롬프트 캐싱은 안정적인 앞부분을 재사용해 비용·지연을 줄입니다. 안정적인 것을 앞에 두는 순서가 관건입니다.
- 손으로 짜 본 이 패턴들을 실전에서는 LiteLLM이 `num_retries`·`fallbacks`·`timeout`으로 내장 지원합니다.
- reliable_agent.py가 이 패턴들을 하네스로 엮습니다. 예산을 모델 앞에 세우고, 폴백 체인의 각 후보를 재시도·타임아웃으로 감쌉니다. 운영 신뢰성은 모델 호출을 감싸는 하네스의 운영 층입니다.
- 여러 하네스에 공통 관심사를 더할 때는 클래스를 손대거나 상속하지 않고, 호출 한 곳을 감싸 주입(DI)합니다. 관심사는 그게 속한 층에 붙입니다.
