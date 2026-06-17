# Server Configuration Decisions

이 문서는 `SERVER_CONFIGURATION.md`의 서버 구성안 중 사용자가 직접 결정해야
하는 항목과, v1 진행을 위해 임시 추천값으로 둘 수 있는 항목을 분리한다.

현재 원칙:

- 원격 작업은 하지 않는다.
- 코드는 수정하지 않는다.
- 결정 전까지는 보수적인 추천값을 문서상의 기본값으로 둔다.
- 실제 배포, systemd 활성화, 공개 네트워크 노출, 유료 모델 변경 전에는
  사용자의 명시 결정을 받는다.

## 현재 사용자 방향

2026-06-14 기준 사용자 방향:

- v1은 초기 버전이므로 당장 병렬 개발 서버를 구현하지는 않는다.
- 나중에 같이 작업할 사람들이 들어와 여러 서버가 동시에 개발할 수 있도록
  확장 가능성은 설계에 남긴다.
- i5-12400 / RTX 3060 컴퓨터를 Test Runner 머신으로 붙일 예정이다.
- worker들은 따로 관리하기 편하게 서비스/프로세스 단위로 분리한다.
- 외부에서도 접속할 수 있게 설계한다.
- DB는 추천대로 v1에서 SQLite를 사용한다.
- API Worker는 우선 OpenAI-compatible API를 사용한다.
- Claude CLI 등 다른 CLI worker 가능성은 열어둔다.
- Test Runner는 별도 테스트 머신을 전제로 설계한다.
- 백업 주기와 보관 기간은 추천안으로 시작하고, 프로젝트 중요도에 따라
  나중에 줄이거나 늘린다.
- systemd와 Codex CLI Owner 호출 방식은 쉬운 설명을 보고 최종 구현 방식을
  정한다.
- 새 프로젝트 생성은 Owner 자연어 대화로 진행한다.
- 프로젝트 타입은 Owner가 자동 추정하고 애매할 때만 질문한다.
- 새 프로젝트는 Discord channel/thread와 서버 Project record를 자동 생성한다.
- GitHub private repo/template/workspace 생성은 `#approval-inbox` 승인 후
  서버가 자동 실행한다.
- 진짜 프로젝트는 GitHub private repo, 임시/테스트 프로젝트는 local bare repo를
  기본으로 한다.
- Template은 타입별 template과 공통 `.ai-company/` 폴더를 함께 사용한다.
- 앞으로는 추천 기본값 묶음을 제안하고, 사용자가 수정할 것만 말하는 방식으로
  결정한다. 위험한 결정만 별도로 묻는다.
- `#approval-inbox`는 결재함처럼 사용한다. 사용자는 버튼보다 Owner와의 자연어
  대화로 "좋아 진행해", "보류", "수정해"처럼 결재할 수 있고, 버튼은 보조
  수단으로 둔다.
- 결재 기준은 고정 목록이 아니라 Owner 판단 기반 decision gate로 둔다. 위험,
  비용, 보안, 외부 공개, 되돌리기 어려움, main/release 영향, 방향 변경, 애매한
  의도가 있으면 Owner가 멈추고 묻는다.
- Discord Bot은 main server에서 FastAPI와 별도 프로세스/서비스로 둔다.
- Discord Bot은 DB에 직접 접근하지 않고 FastAPI API만 사용한다.
- Artifact는 server로 업로드하고 프로젝트별로 분리 저장한다.
- GitHub 자동 repo 생성 인증은 우선 GitHub CLI 로그인 방식을 추천한다.
- 사람의 기본 운영 인터페이스는 Discord 자연어 대화이므로, 별도 public HTTPS
  UI/API는 필요할 때 추가한다. raw `:8080` 공개는 금지한다.
- Worker Registry와 Discord/approval/artifact/memory 최소 schema는 v1에 설계해
  두고, 여러 서버/친구 컴퓨터/테스트 머신 확장 가능성을 남긴다.
- main server 사양은 Intel Core i5-14600KF, NVIDIA RTX 4070, 32 GB DDR5 RAM이다.
  v1에서는 우선 control-plane 안정성을 우선하고, RTX 4070은 나중에 별도
  local LLM/GPU worker로 붙일 수 있는 확장 자원으로 둔다.

## 반드시 사용자 결정이 필요한 항목

아래 항목은 운영 방식, 비용, 보안, 확장성에 직접 영향을 준다. 로컬 문서
작업은 추천값으로 진행할 수 있지만, 실제 always-on 운영이나 원격 배포 전에
사용자 결정이 필요하다.

### 1. v1 Workspace Worker 수

1. 추천안

   v1 초기에는 프로젝트당 workspace-mutating `Workspace Worker`를 동시에
   1개만 둔다. 다만 설계는 나중에 여러 친구/여러 서버가 동시에 작업할 수
   있도록 확장 지점을 남긴다.

   API Worker는 여러 개를 둘 수 있지만, 같은 game workspace를 직접 수정하는
   worker는 v1 초기에는 1개만 실행한다.

2. 장점

   - 현재 구현의 `workspace_path` 1개 모델과 잘 맞는다.
   - git 충돌, dirty workspace, merge 중 동시 수정 위험이 작다.
   - systemd timer 구성도 단순하다.
   - 실패 원인을 추적하기 쉽다.

3. 단점

   - 작업 처리량이 낮다.
   - 여러 code task를 동시에 실행하기 어렵다.
   - 큰 게임 프로젝트에서는 병목이 될 수 있다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: v1 초기에는 1개로 시작하고, 병렬 worker는 확장 가능성만
   남긴다.

5. 내가 답해야 하는 질문

   병렬 작업이 필요해질 때 worker별 workspace/worktree 모델로 확장할까요,
   아니면 그 시점에 Postgres/분산 큐까지 함께 전환할까요?

### 2. Project Workspace 배치

1. 추천안

   v1 초기에는 프로젝트별 기본 workspace를 1개만 둔다.

   ```text
   <HOME_DIR>/game-workspaces/{project}
   ```

   단, 별도 테스트 머신과 미래 병렬 작업을 위해 worker별 workspace 구조를
   설계상 확장 대상으로 둔다.

   미래 확장 예:

   ```text
   <HOME_DIR>/game-workspaces/{project}/main
   ```

   단, 별도 테스트 머신과 미래 병렬 작업을 위해 worker별 workspace 구조를
   설계상 확장 대상으로 둔다.

   미래 확장 예:

   ```text
   <HOME_DIR>/game-workspaces/{project}/main
   <HOME_DIR>/game-workspaces/{project}/workers/{worker_id}
   <HOME_DIR>/game-workspaces/{project}/test-runners/{machine_id}
   ```

2. 장점

   - 현재 DB의 `projects.workspace_path`와 바로 맞는다.
   - 구현 변경 없이 운영 가능하다.
   - 디스크 사용량이 작고 구조가 단순하다.
   - Owner merge가 같은 workspace에서 바로 동작한다.

3. 단점

   - worker 병렬 실행에 약하다.
   - 테스트 러너와 코드 worker가 같은 workspace를 공유하면 순서 제어가 필요하다.
   - 장기적으로 GPU worker나 별도 테스트 머신을 붙일 때 확장 모델을 다시
     설계해야 한다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: v1 초기에는 프로젝트별 기본 workspace 1개, 병렬/테스트
   머신은 worker별 workspace로 확장 가능하게 설계한다.

5. 내가 답해야 하는 질문

   12400/3060 테스트 머신의 workspace 경로는 어떤 OS와 기본 경로로 둘까요?

### 3. Main Server와 Worker 배치

1. 추천안

   FastAPI/SQLite/Owner adapter는 main server에 둔다. Worker들은 관리하기
   쉽도록 별도 프로세스/서비스 단위로 나눈다.

   v1 초기에는 일부 worker가 main server에서 실행될 수 있지만, Test Runner는
   12400/3060 테스트 머신을 전제로 분리 설계한다.

2. 장점

   - FastAPI 서버와 worker 장애를 분리해서 볼 수 있다.
   - worker별 enable/disable, 로그, 재시작 관리가 쉬워진다.
   - 테스트 머신을 빨리 붙일 수 있다.
   - 현재 구현과 가장 잘 맞는다.

3. 단점

   - 서비스 파일과 설정 파일 수가 늘어난다.
   - worker가 분리될수록 네트워크/API token 관리가 중요해진다.
   - SQLite v1 구조에서는 높은 병렬 worker에 한계가 있다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: worker들은 따로 관리하기 편하게 분리한다.

5. 내가 답해야 하는 질문

   각 worker 서비스를 수동 실행부터 시작할까요, 아니면 worker별 systemd
   timer까지 v1 안에서 만들까요?

### 4. systemd Always-On 구현 시점

1. 추천안

   systemd는 Linux에서 프로그램을 서비스처럼 관리해주는 기본 관리자다.
   사용자가 말한 것처럼 main computer가 켜질 때 서버도 자동으로 켜지게
   만들 수 있다. 서버가 죽으면 다시 시작하게 만들 수도 있다.

   추천은 두 단계다:

   - v1: FastAPI main server는 systemd로 자동 시작한다.
   - v1 이후 또는 명시 승인 후: worker들은 worker별 timer/service로 켠다.

2. 장점

   - main computer 재부팅 후 서버를 수동으로 켤 필요가 줄어든다.
   - 서버 죽음에 자동 복구를 붙일 수 있다.
   - worker를 API/Workspace/Test Runner별로 따로 관리할 수 있다.

3. 단점

   - 잘못 설정하면 부팅 때 문제가 반복될 수 있다.
   - worker까지 자동 실행하면 API 비용이나 git 작업이 예상보다 많이 돌 수 있다.
   - unit/timer 파일 관리가 추가된다.

4. 지금 결정 필요 여부

   부분 결정 필요. FastAPI 자동 시작은 v1에 넣는 쪽을 추천한다. worker 자동
   실행은 별도 확인 후 켜는 쪽을 추천한다.

5. 내가 답해야 하는 질문

   FastAPI main server 자동 시작용 systemd service는 v1에서 만들고, worker
   timers는 나중에 따로 켜는 방식으로 갈까요?

### 5. 외부 접속 범위

1. 추천안

   외부에서도 접속할 수 있게 설계한다. 단, raw `:8080` 공개 노출은 피하고
   HTTPS reverse proxy 뒤에 둔다. Tailscale은 관리자/복구 경로로 계속 유지한다.

2. 장점

   - 외부 PC나 모바일 환경에서도 접근할 수 있다.
   - 나중에 대시보드나 webhook을 붙이기 쉽다.
   - Tailscale은 admin backdoor로 남겨 복구가 쉽다.

3. 단점

   - TLS, 도메인, reverse proxy, rate limit 등 보안 설계가 필요하다.
   - API token 유출 위험을 더 진지하게 다뤄야 한다.
   - 공개 인터넷에 노출되면 로그/모니터링 필요성이 커진다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: 외부 접속을 고려한다. 구현 전에는 도메인, HTTPS 방식,
   인증 강도를 다시 결정해야 한다.

5. 내가 답해야 하는 질문

   사용할 도메인과 HTTPS 방식은 무엇으로 할까요? 예: Cloudflare Tunnel,
   Caddy/Nginx reverse proxy, Tailscale Funnel 등.

### 6. SQLite 유지와 Postgres 전환 시점

1. 추천안

   v1은 SQLite를 계속 쓴다. Postgres는 다중 서버 worker, 높은 동시성,
   원격 DB 백업/관측, 웹 UI가 필요해지는 v1.5 이후에 검토한다.

2. 장점

   - 현재 구현과 테스트를 그대로 활용할 수 있다.
   - 백업과 복구가 단순하다.
   - 운영해야 할 서비스 수가 적다.
   - v1 목표인 작은 자동화 loop에 충분하다.

3. 단점

   - 다중 writer와 높은 병렬성에 약하다.
   - 원격 worker가 많아질수록 큐 DB로는 한계가 생길 수 있다.
   - 운영 관측과 권한 분리가 Postgres보다 약하다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: v1은 SQLite를 유지한다. Postgres는 병렬 worker/다중 서버
   요구가 커질 때 검토한다.

5. 내가 답해야 하는 질문

   SQLite를 v1 전체에서 계속 쓰고, Postgres 전환은 v1.5 이후 병렬 worker가
   필요해질 때 고려해도 될까요?

### 7. Codex CLI Owner 호출 방식

1. 추천안

   v1에서는 `/owner/runs`가 prompt 파일을 만들고, `GAME_COMPANY_OWNER_COMMAND`가
   `{prompt_file}`과 `{run_dir}`를 받아 Codex CLI를 on-demand로 호출한다.
   항상 켜진 Owner loop는 두지 않는다.

   쉽게 말하면:

   - 서버가 "기획서/업무지시서" 파일을 만든다.
   - Codex CLI를 한 번 실행해서 그 파일을 읽게 한다.
   - Codex CLI가 낸 답을 서버가 저장한다.
   - 사람이 보고 승인할 것은 승인한다.

   Owner는 계속 떠 있는 직원이라기보다, 필요할 때 불러서 판단을 맡기는
   비싼 기획/검토 담당자에 가깝다.

2. 장점

   - Owner 호출 비용과 위험을 사람이 통제할 수 있다.
   - dry-run과 실제 실행을 분리하기 쉽다.
   - Owner 결과가 `owner_runs` DB와 run directory에 남는다.
   - 현재 구현의 command adapter와 맞는다.

3. 단점

   - 완전 자동 기획 loop는 아직 아니다.
   - Codex CLI 인증/세션/권한 모델을 별도로 검증해야 한다.
   - CLI flag가 바뀌면 command 값을 업데이트해야 한다.

4. 지금 결정 필요 여부

   아직 최종 결정 전. 쉬운 시작은 prompt file on-demand 방식이다.

5. 내가 답해야 하는 질문

   일단 prompt file on-demand 방식으로 실험해보고, 불편하면 stdin/수동/별도
   Owner 프로세스로 바꾸는 흐름으로 갈까요?

### 8. API Worker와 Local LLM 범위

1. 추천안

   v1은 OpenAI-compatible API 기준으로 간다. Claude CLI 같은 다른 CLI worker를
   쓸 가능성은 열어두되, 바뀌면 그때 별도 worker adapter로 설계한다.

   로컬 LLM은 v1.5 확장으로 두되, 나중에 붙일 수 있도록 model profile의
   `base_url`은 OpenAI-compatible local endpoint를 받을 수 있게 유지한다.

   main server에 RTX 4070이 있으므로 local LLM/GPU worker 가능성은 좋다.
   다만 v1에서는 FastAPI/SQLite/Discord/Owner control-plane을 먼저 안정화하고,
   GPU worker는 별도 서비스로 붙이는 쪽을 추천한다.

2. 장점

   - 현재 API Worker 구현과 맞는다.
   - 모델 교체가 `base_url`, `model`, `api_key_env` 설정으로 끝난다.
   - v1에서 GPU 세팅과 local model 운영 부담을 피할 수 있다.
   - 비용 제어는 cheap worker model 선택으로 먼저 할 수 있다.

3. 단점

   - 외부 API 비용이 계속 발생한다.
   - 네트워크/API 장애에 의존한다.
   - 로컬 GPU를 활용한 장기 비용 절감은 늦어진다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: v1은 API 먼저. Claude CLI나 로컬 LLM으로 바뀌면 그때
   사용자가 알려준다.

5. 내가 답해야 하는 질문

   API Worker는 v1에서 OpenAI-compatible API 기준으로 갈까요, 아니면 로컬
   LLM/GPU worker도 v1 범위에 포함할까요?

### 9. Test Runner 실행 위치

1. 추천안

   v1에서는 12400/3060 별도 테스트 머신을 전제로 Test Runner를 설계한다.
   main server는 task queue and report를 관리하고, 테스트 머신은 작업을 lease해
   자체 workspace에서 build/test/run을 수행한다.

2. 장점

   - main server를 무거운 빌드/테스트 부하에서 보호한다.
   - RTX 3060이 필요한 GPU/그래픽 테스트 확장에 유리하다.
   - 실제 게임 실행 환경에 가까운 테스트를 할 수 있다.
   - 테스트 머신을 나중에 여러 대로 늘리기 쉽다.

3. 단점

   - 테스트 머신 설치/인증/네트워크 설정이 필요하다.
   - 테스트 머신별 workspace 경로 관리가 필요하다.
   - SQLite v1에서는 너무 많은 원격 worker를 동시에 붙이면 한계가 올 수 있다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: 별도 테스트 머신 전제.

5. 내가 답해야 하는 질문

   12400/3060 테스트 머신의 OS, Tailscale IP/host, 기본 workspace 경로를 무엇으로
   둘까요?

### 10. 백업 주기와 보관 기간

1. 추천안

   v1 기본 백업 정책:

   - 배포 전 수동 백업
   - 스키마 변경 전 수동 백업
   - 하루 1회 자동 백업
   - 일간 백업 7일 보관
   - 주간 백업 4주 보관

2. 장점

   - SQLite 복구 지점이 충분히 촘촘하다.
   - 디스크 사용량이 과하지 않다.
   - 운영 실수나 DB 손상에 대응하기 쉽다.

3. 단점

   - 장기 히스토리 보존에는 부족할 수 있다.
   - 백업 파일 외부 반출까지 자동화하지 않으면 서버 디스크 장애에는 약하다.
   - systemd timer나 cron 구현이 필요하다.

4. 지금 결정 필요 여부

   현재 방향 결정됨: 추천안으로 시작한다. 프로젝트/파일 중요도에 따라 나중에
   주기를 줄이거나 보관 기간을 늘린다.

5. 내가 답해야 하는 질문

   백업은 하루 1회, 일간 7일, 주간 4주 보관으로 시작할까요, 아니면 더 짧게
   또는 더 길게 가져갈까요?

## 임시 추천값으로 진행 가능한 항목

사용자가 위 질문에 답하기 전까지 문서와 로컬 설계는 아래 값으로 진행할 수
있다. 실제 원격 활성화 전에는 다시 확인한다.

| 항목 | 임시 추천값 | 실제 결정 필요 시점 |
| --- | --- | --- |
| Workspace Worker 수 | v1 초기 프로젝트당 동시 1개, 병렬 확장 여지 유지 | 병렬 worker 구현 전 |
| Workspace 배치 | 프로젝트별 기본 workspace 1개, worker별 workspace 확장 설계 | 테스트 머신/병렬 worker 구현 전 |
| Worker 배치 | worker별 프로세스/서비스 분리 | worker service 작성 전 |
| systemd | FastAPI 자동 시작 우선, worker timer는 나중 | unit/timer 파일 작성 전 |
| 외부 접속 | 공개 접속 고려, HTTPS reverse proxy 전제 | 도메인/TLS 설정 전 |
| DB | SQLite 유지 | 다중 서버/고병렬 worker 전 |
| Owner 호출 | `/owner/runs` + `{prompt_file}` on-demand로 먼저 실험 | 실제 Codex CLI 연결 전 |
| API Worker 모델 | OpenAI-compatible API | 자동 worker 실행 전 |
| Local LLM | v1.5 확장, CLI worker adapter 가능성 유지 | GPU/CLI worker 준비 전 |
| Test Runner 위치 | 12400/3060 별도 테스트 머신 전제 | runner 구현 전 |
| 백업 | 일간 7일 + 주간 4주 | backup timer 구현 전 |

## 답변 양식

결정할 때는 아래처럼 짧게 답해도 충분하다.

```text
1. workspace worker 수: v1 초기 1개, 병렬 확장 가능성 유지
2. workspace 배치: 프로젝트별 기본 1개, worker별 workspace 확장 설계
3. worker 배치: worker별 프로세스/서비스 분리
4. systemd: FastAPI 자동 시작 우선, worker timer는 나중
5. 외부 접속: 공개 접속 고려, HTTPS reverse proxy 전제
6. DB: v1 SQLite 유지
7. Codex CLI Owner: prompt_file on-demand로 먼저 실험
8. API Worker: OpenAI-compatible API v1, CLI/local LLM은 나중
9. Test Runner: 12400/3060 별도 테스트 머신 전제
10. 백업: 일간 7일, 주간 4주
```
