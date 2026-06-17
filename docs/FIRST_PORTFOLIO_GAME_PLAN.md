# First Portfolio Game Plan: Neon Survival Prototype

이 문서는 AI Game Company Server의 첫 번째 실전 프로젝트이자 포트폴리오용 게임인 **Neon Survival Prototype**의 개발 계획서입니다. 이 프로젝트는 인공지능 에이전트들(Owner, Worker)이 태스크 단위 협업을 통해 하나의 완성도 높은 게임을 빌드하고 검증해 나가는 과정을 투명하게 증명하는 쇼케이스입니다.

---

## 1. 게임 개요 (Game Overview)

* **게임명**: Neon Survival Prototype (최종 권장명)
* **장르**: 2D 탑다운 서바이벌 미니 게임 (2D Top-Down Survival Mini Game)
* **컨셉**: 어두운 네온 스타일 공간에서 무한히 몰려드는 붉은 적들을 피하며 60초 동안 생존하는 단순하고 몰입감 높은 액션 아케이드 데모.
* **조작법**: 
  - `W`, `A`, `S`, `D`: 플레이어 이동
  - `Space`: 게임 오버 시 재시작
* **목표**: 60초 생존 성공. 적과의 충돌을 피하며 생존한 시간과 충돌 횟수를 바탕으로 최종 스코어를 산출.

---

## 2. 핵심 플레이 루프 (Core Play Loop)

```text
[게임 시작] -> [PLAYING 상태] -> [플레이어 WASD 이동 및 적 회피] -> [적 스폰 및 플레이어 유도 이동]
                   ^                                                    |
                   |                                                    v
             [Space 키 입력] <--------- [GAME OVER 상태] <-------- [충돌로 체력 0 도달]
```

---

## 3. MVP 범위 (Minimum Viable Product Scope)

### 포함 사항 (In-Scope)
* **기본 프레임워크**: Python 3.12 및 Pygame 라이브러리.
* **플레이어 제어**: 화면 경계 밖으로 나갈 수 없는 WASD 기반 이동 메커니즘.
* **적 생성**: 주기적으로 화면 바깥(Off-screen) 랜덤 위치에서 스폰되어 플레이어 방향으로 가속 추적하는 적 무리.
* **충돌 및 체력**: 플레이어와 적의 충돌 감지(AABB Bounding Box Rects), 충돌 시 체력(Health) 감소, 체력이 0 이하가 될 시 즉각 게임 오버 상태로 전환.
* **게임 상태 제어**: PLAYING 상태와 GAME_OVER 상태 구분 및 스페이스바 입력 시 모든 점수/상태 리셋 후 재시작.
* **네온 UI 오버레이**: 폰트를 활용한 실시간 생존 시간(초) 및 스코어 렌더링.
* **자동 스모크 테스트**: 실제 게임 렌더링 창을 띄우지 않아도 되는 Headless dummy video driver 기반 100프레임 실행 후 스크린샷 캡처 및 자동 종료 스크립트.

---

## 4. 하지 않을 것 (Out-of-Scope)
* **무기 발사 및 전투 기능**: 적을 총으로 쏘거나 파괴하는 기능 제외 (생존 회피에 집중).
* **아이템 및 파워업 시스템**: 속도 증가, 무적 등 아이템 수집 기능 배제.
* **사운드 효과 및 배경음악**: 오디오 디바이스 의존성을 줄이고 Headless 테스트 용이성을 위해 제외.
* **화려한 스프라이트 리소스 사용**: 별도의 이미지 로딩 실패 리스크를 없애기 위해 Pygame 도형 그리기(Draw) 명령어로 도형 렌더링 처리.
* **다양한 적 패턴**: 직선 유도 방식 이외의 복잡한 AI 패턴 제외.

---

## 5. 기술 스택 (Tech Stack)
* **언어**: Python 3.12
* **라이브러리**: Pygame-ce (또는 표준 pygame)
* **테스트**: Python 내장 `unittest` 프레임워크
* **CI/CD 검증**: Headless 가상 환경 검증 (`SDL_VIDEODRIVER=dummy` 환경변수 주입 필수)

---

## 6. 저장소 구조 (Repository Structure)

에이전트가 코드를 관리하기 위해 구성할 최종 Repository 디렉토리 구조입니다.

```text
neon-survival-prototype/
│
├── src/                          # 게임 로직 소스 코드
│   ├── game/
│   │   ├── __init__.py
│   │   ├── main.py               # 메인 게임 루프 및 초기화
│   │   ├── player.py             # 플레이어 클래스 (이동, 경계 처리)
│   │   ├── enemy.py              # 적 클래스
│   │   ├── collision.py          # 충돌 감지 유틸리티
│   │   ├── ui.py                 # 텍스트, 상태 오버레이 렌더러
│   │   └── settings.py           # 화면 해상도, 속도, 스폰 시간 등 설정값
│   └── __init__.py
│
├── tests/                        # 자동화 단위 테스트
│   ├── test_player.py            # 플레이어 이동/경계 유닛 테스트
│   └── test_collision.py         # 충돌 판정 유닛 테스트
│
├── scripts/                      # 자동화 스모크 테스트 스크립트
│   └── smoke_check.py            # Headless 100프레임 기동 후 스크린샷 저장
│
├── assets/                       # 기획 리소스 및 폰트 파일
│   └── README.md
│
├── docs/                         # 기획/설계 및 에이전트 개발 기록
│   └── DEVELOPMENT_LOG.md
│
├── .game-company/                # AI Game Company Server 검증 설정
│   ├── project.json              # 프로젝트 설정 메타
│   └── test_runner.json          # Test Runner 빌드/테스트 스키마
│
├── README.md                     # 포트폴리오 겸 설치 설명서
└── requirements.txt              # 의존성 정의 파일 (pygame)
```

---

## 7. 개발 순서 (Development Sequence)

[templates/task_packs/pygame_survival_v1.json](file:///C:/Users/user2/.gemini/antigravity/scratch/ai-game-company-server/templates/task_packs/pygame_survival_v1.json) 스키마를 기준으로 작업이 진행됩니다.

1. **Project Bootstrap**: 워크스페이스 구조 생성, .gitignore 및 `.game-company/` 파일 구성.
2. **Basic Game Loop**: `main.py` 중심의 기본 pygame 초기화 및 빈 화면 렌더링 루프 가동.
3. **Player Movement**: `player.py` 구현, 키보드 입력 핸들러 및 화면 이탈 방지 경계 검사 구현.
4. **Enemy Spawn**: `enemy.py` 및 스폰 주기 관리, 플레이어로의 가속 추격 로직 구현.
5. **Collision & Health**: 충돌 이벤트 연계, 플레이어 체력 하락 및 체력 0 도달 시 사망 판정.
6. **Score & Time UI**: 생존 시간, 스코어 계산 및 Pygame Font 렌더링 시스템 구현.
7. **Game Over & Restart**: PLAYING / GAME_OVER 상태 제어 및 space 키를 통한 리셋 제어.
8. **Smoke Test Artifact**: `scripts/smoke_check.py` 구현, 스크린샷 아티팩트 자동 저장 기능 구축.
9. **Portfolio README**: 종합 설명서 작성 및 최종 README 갱신.

---

## 8. Test Runner Evidence & Artifact 기준

* **Test Runner Evidence**: 모든 코드 변경 브랜치는 반드시 로컬 유닛 테스트 통과 증적(`test.log`)을 포함해야 하며, `test_runner.json` 설정에 따라 실행 결과가 100% 성공이어야 머지가 허용됩니다.
* **Artifact**: 
  - `smoke_check.py`가 저장한 `screenshot.png` 파일이 정상 존재해야 하며, 손상되지 않은 이미지 포맷이어야 합니다.
  - 빌드 및 실행 중 출력되는 `stderr` 로그에 비정상적인 Warning 또는 Exception이 없어야 합니다.
* **Merge / Retry 기준**:
  - `eval_merge_policy`에 의해, 테스트가 깨지거나 필요한 Evidence(log 파일 등)가 유실되었을 경우 머지가 차단되며 해당 에이전트 브랜치는 반려(Rejected) 처리 후 다시 Lease를 받아 재작업(Retry)해야 합니다.

---

## 9. 포트폴리오에서 보여줄 핵심 포인트

* **자율 협업의 시각화**: 기획자(Owner)가 기획 문서를 토대로 태스크 팩을 쪼개 올리면, 여러 Worker가 브랜치를 나눠 규칙적으로 단위 코드를 빌드하고, 테스트를 통과시킨 후 안전하게 승인 합의를 거쳐 메인 브랜치에 점진적으로 합산하는 파이프라인의 안전성을 보여줍니다.
* **엄격한 품질 보증**: Headless 환경에서 Pygame의 스크린샷과 로그 파일을 아티팩트로 추출하고, 병합 전 Merge Policy로 사전 승인 제약을 판단하는 자동 보증 메커니즘을 증명합니다.
