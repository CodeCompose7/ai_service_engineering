# 변경 이력

이 프로젝트의 모든 주요 변경사항은 이 파일에 기록됩니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따르며,
이 프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 준수합니다.

이 저장소는 공통 선행 VOD 과정 "AI 서비스 엔지니어링"의 강의 문서와 예제 코드입니다.
버전은 섹션 단위로 올라가며, 1.0.0은 전 과정(S1~S5, 32단위)의 완성을 뜻합니다.

## 1.1.0 - 2026-06-13

전 과정 완성 후 첫 정비. S3 LangGraph 예제·문서를 다듬고 표기를 통일했습니다.

### 변경됨 1.1.0

- S3 lec05·06·07 예제 코드 포매팅 정리 — `acompletion` 호출, 조건 엣지, 메시지
  구성 등을 멀티라인으로 펴고 주석을 정렬. 동작은 그대로

### 수정됨 1.1.0

- S3 lec07 문서 실행 출력 갱신 — plan-execute를 4단계 → 5단계 실제 출력으로,
  reflection은 `MAX_ROUNDS`(2)에 닿아 멈추는 실제 흐름과 docstring·테스트까지
  더해진 최종 코드로 교체
- 표기 통일 — S4 lec03 `부작용` → `부수효과`, S4 lec07 `카나리` → `Canary`

### 문서 1.1.0

- S3 lec06에 `graph.py` 워크스루(§7.1) 신설 — 순차 루프 + 분기 그래프의
  self-drawn mermaid와 실행 출력을 싣고, 기존 `briefing.py` 설명을 §7.2로 정리

## 1.0.0 - 2026-06-11

전 과정 완성. 5개 섹션 / 32단위 / 480분(8시간). 전체 점검으로 문서와 코드를 맞췄습니다.

### 변경됨 1.0.0

- **캡스톤을 S5에 병합** — 별도 단원 대신 S5 lec02 통합 웹 서비스가 end-to-end 데모를
  겸한다. 플랜 총량을 505분/33단위 → 480분/32단위로 정합

### 수정됨 1.0.0

- **전체 점검 — 문서·코드 교차 검증** (5개 섹션 병렬 리뷰)
  - 잔존 참조 제거: `panel.py`가 삭제된 `EvalHarness`를 가리키던 곳, S4 lec03의
    LangGraph 체크포인트 참조를 `S3 lec05·06`으로 명시, mermaid 노드 `lec02 acomplete`
    → `S3 acomplete`
  - 전방 참조 정정: S2 lec05·lec06이 lec07 지표를 `Recall@k`로 가리키던 것을
    `Hit Rate@k`로 (lec07 헤드라인 지표와 일치)
  - 사실 정정: S3 lec01의 `minimax-m3:cloud` "로컬" → "Ollama"(둘 다 Ollama Cloud),
    "LiteLLM이 검색어를 고르는" → "모델이", 시계 prose 시각 일치, S3 `fc.py`의 약한
    모델 처리 참조 `lec07` → `S4`
  - S5 lec02 배포 노트 정정 — `rag.pdf`가 출하되고 `open_index`가 비면 다시 채우므로
    배포 컨테이너에서 RAG는 돌고, 첫 요청의 인덱스 콜드 스타트가 실제 비용임을 기술
  - `benchmark.py` 도크스트링 "한 청크만 붙인다" → "이웃과 함께 붙인다"(이웃 확장 반영)
- **시간 재배분 정합** — S1 개요표(lec06~09)·S5 분량을 헤더·플랜과 일치

### 문서 1.0.0

- `vod_plan.md` 전체 점검 — 32단위 단위명이 빌드된 S1~S5 lec 제목과 전부 일치 확인,
  캡스톤 병합 후 잔재(흐름줄·폴더 목록) 정리
- 강의 문서 문체 규칙(`.claude/CLAUDE.md`) — 합니다체, 번호 제목, mermaid radius,
  과한 강조·이모지 금지
- 자동 메모리(`memory/`) — 시간 재배분 시 내용 보존·숫자만 변경 원칙

## 0.5.0 - 2026-06-10

S5 — 서빙 & 배포 (통합 데모 겸 캡스톤). 만든 것을 API로 감싸 웹 서비스로 내보냅니다.

### 추가됨 0.5.0

- **lec01 — FastAPI 서빙 + 스트리밍** : `server.py` lifespan으로 모델 준비,
  `/generate`(한 번에)·`/generate/stream`(StreamingResponse로 토큰), Pydantic 입력
  검증(422)·모델 실패 502, `GET /` 브라우저 테스트 페이지(마크다운 렌더링)
- **lec02 — 통합 웹 서비스 (채팅 + 관리자)** : `assistant.py`가 S2 RAG + S4 가드(주입·
  검열·PII) + S4 관찰(Trace)을 한 파이프라인으로 조합. `app.py` 한 서버가 채팅
  페이지와 관리자 페이지(관찰 대시보드·하네스 토글)를 함께 제공
  - `/chat/stream` 스트리밍 채팅 + 마크다운 렌더, `/api/metrics`·`/api/settings`
  - `Dockerfile`로 배포 이미지, 운영자 키 vs BYOK 키 전략

### 변경됨 0.5.0

- 채팅을 비스트리밍 → 스트리밍으로(lec01 스트리밍을 통합에 적용). 입력 가드는 스트림
  전에, 출력 가드는 전체 답이 필요해 비스트리밍 길로 갈림을 명시
- 스트리밍 첫 토큰 단축 — 입력 가드 2회를 `asyncio.gather`로 병렬, gemini thinking을
  꺼(budget 0) 첫 토큰을 십몇 초 → 2초대로

## 0.4.0 - 2026-06-10

S4 — 컨텍스트 & 하네스 엔지니어링: 신뢰성. "동작하는 에이전트"를 "출하 가능한 시스템"으로.

### 추가됨 0.4.0

- **7단위 구성** : 컨텍스트 엔지니어링(토큰 예산·압축 갈래·관련도 임계값), 하네스
  엔지니어링(능력 감지·우아한 강등·보안 하네스·욕설 검열), 메모리·상태·가드레일(세션
  지속·허용 행동·PII), 프롬프트 주입 방어, 운영 신뢰성(예산·재시도·백오프·타임아웃·
  폴백·DI), 평가·검증, 관찰·운영
- **다중 에이전트 벤치마크**(lec06) — 모델 단독·RAG k=1·RAG k=3을 품질(0~5)·토큰·비용
  한 표에. 멀티 저지 패널(엄격·관대·사용자)
- **관찰 모듈**(lec07) — 구조화 로그(JSON)·트레이싱(스팬)·메트릭(p50·p95·에러율)·
  사용자별 메트릭·SLO 알림(`check_alerts`)

### 변경됨 0.4.0

- S4를 5단위 → 7단위로 확장(운영 신뢰성 신설, 평가·검증·관찰 분리)
- 평가(lec06)를 순환적 toy(지식 유무) → 다중 에이전트 벤치마크로 재구성
- 관찰(lec07)을 가짜 `sleep` → 실제 RAG 요청에 연결

## 0.3.0 - 2026-06-09

S3 — Agent 빌드. 도구를 쓰는 에이전트를 동작하게 만드는 레이어.

### 추가됨 0.3.0

- **7단위 구성** : function calling 원리(tool schema·호출 loop), 단일 도구 에이전트,
  multi-tool 라우팅, MCP로 도구 연결(`mcp_server.py`), LangGraph 기초(상태·노드·엣지·
  체크포인트), LangGraph 실전(분기·루프·병렬·재시도), 계획 수립과 자기수정
  (plan-and-execute·reflection)
- 능력 감지(`supports_function_calling`) — 미지원 모델은 JSON 모드로 폴백
- `search_wikipedia`처럼 도구 안에서 네트워크·LLM 호출이 함께 일어나는 "작은 에이전트"
- 비동기 도구 호출(한 턴의 도구들을 `asyncio.gather`로 동시 실행)

## 0.2.0 - 2026-06-08

S2 — 데이터 & RAG 코어. 데이터 처리부터 검색·평가까지 mini RAG 한 바퀴.

### 추가됨 0.2.0

- **7단위 구성** : 데이터 수집·정제(pandas), 문서 로딩(PyMuPDF, 한국어 줄바꿈·NFC
  함정), 청킹(Recursive·overlap), 임베딩(sentence-transformers `bge-m3`), 벡터DB
  Chroma(영속·메타데이터 필터), mini RAG(검색→생성→출처), 검색 평가(Hit Rate@k·MRR)
- 예제 코퍼스 `rag.pdf`(위키백과 "검색 증강 생성"), 이웃 청크 확장 검색
- 검색 평가 웹(`app.py` + `page.html`) — 청킹·임베딩 조합 비교

## 0.1.0 - 2026-06-06

S1 — LLM을 서비스로 + 개발 환경. 멀티 프로바이더 호출과 신뢰할 수 있는 출력의 기본기.

### 추가됨 0.1.0

- **개발 환경** : VSCode devcontainer(Docker·`uv`·`pyproject.toml`), `.env` 기반
  프로바이더 설정, `DEFAULT_PROVIDER`
- **LiteLLM 단일 인터페이스** : Gemini·OpenAI·Claude·Ollama를 모델 문자열 하나로 교체.
  모든 LLM 호출은 LiteLLM 경유(임베딩만 예외)
- **9단위 구성** : 환경 셋업, LLM 멘탈 모델(토큰·컨텍스트·비용), 샘플링 파라미터
  (temperature·top_p·top_k), 단일 provider 호출, 프롬프트 패턴(system/user·few-shot·
  역할·실패 교정), LiteLLM 멀티 프로바이더, Ollama 로컬, 구조화 출력 1(Pydantic),
  구조화 출력 2(instructor 검증·재시도)
- 능력별 안전 샘플링(미지원 `top_k` 드롭, `temperature` 클램프), 프로바이더 폴백 체인
