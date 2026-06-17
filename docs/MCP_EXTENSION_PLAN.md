# MCP Extension Plan

Model Context Protocol (MCP)은 AI 에이전트(Owner 및 Worker)가 외부 도구(파일 시스템, Git, 데이터베이스 등)에 통제된 상태로 안전하게 접근할 수 있도록 설계된 개방형 통신 프로토콜입니다.

본 설계 문서는 실제 외부 프로세스를 호출하지 않는 **V1.5의 MCP Registry, Permission Guard, Audit Log, Dry-Run 규격**을 기술합니다.

---

## 1. 아키텍처 아웃라인 (Architectural Outline)

최종 상태와 제어권은 언제나 **FastAPI Dev Server**가 보유합니다. MCP Server는 단순한 자원 접근 래퍼(Wrapper)로 가동되며, 모든 요청은 Permission Guard와 Audit Log를 거치게 됩니다.

```text
エージェント (Agent)
  -> Stdio / HTTP를 통해 MCP Call 전송
  -> MCP Permission Guard (app/mcp/permissions.py)
  -> 통과 여부 검사 (allowed_tools, required_roles, allowed_roots)
  -> Audit Log 기록 (app/mcp/audit_log.py)
  -> [Dry-Run] Planned Action JSON 반환
  -> [Live] 실제 로컬 Tool 실행 (V2 예정)
```

---

## 2. MCP Registry 설계

MCP 서버 설정 규격은 `MCPServerConfig` 스키마로 표현되며, 각 도구 그룹별로 격리된 권한 세트를 정의합니다.

### 2.1. Server Config 필드 명세
* `name`: MCP 서버 이름 (예: `filesystem`, `git`, `sqlite`)
* `command`: 실행할 프로세스 바이너리 경로 목록
* `args`: 실행 시 주입할 커맨드 인수
* `allowed_tools`: 에이전트가 호출할 수 있도록 명시적으로 허용된 도구 목록
* `required_roles`: 각 도구별로 필요한 최소 보안 역할 매핑 (`tool_name` -> `role`)
* `allowed_roots`: 접근이 허용된 물리 파일 시스템의 최상위 디렉토리 목록
* `approval_required_tools`: 실행 시 반드시 오너/사용자의 수동 결재(approval)가 필요한 도구 목록
* `timeout_seconds`: 도구 실행 타임아웃 기본값 (기본 30초)

---

## 3. MCP Permission Guard & Role 범위

에이전트 역할에 따른 보안 레벨 계층 구조를 정의합니다:

```text
readonly (읽기 전용) < worker (작업 수행) < owner (기획 및 리뷰) < admin (시스템 관리)
```

### 3.1. Role별 호출 가능 범위
* **`readonly`**:
  - `allowed_tools`: `read_file`, `git.diff`, `db.select`
  - `allowed_roots`: 읽기 권한이 부여된 workspace 폴더
* **`worker`**:
  - `allowed_tools`: `write_file`, `create_file`, `git.commit`, `git.push`, `artifact.upload`
  - `allowed_roots`: 특정 태스크에 lease된 임시 `workspaces/{project_id}/` 경로로 제한
* **`owner`**:
  - `allowed_tools`: `task.create`, `task.assign`, `approval.request`, `git.merge`
  - `allowed_roots`: 프로젝트 전체 작업 공간
* **`admin`**:
  - `allowed_tools`: 모든 도구 포함 및 시스템 마이그레이션, 서버 배포 툴 실행 가능

---

## 4. Allowed Roots 및 경로 격리 (Path Confinement)

* **허용 경로 규격**: `allowed_roots` 리스트 내의 경로 하위에 있는 파일/디렉토리만 제어하도록 가둡니다.
* **보안 필터**: 상위 디렉토리 참조 패턴(`../`, `..\\`)이나 절대 경로 우회를 방지하기 위해, 모든 타겟 경로는 `Path.resolve()`를 수행한 뒤 허용 경로의 하위 디렉토리인지를 명확하게 대조·검증합니다.
* **차단 대상**: 루트 디렉토리(`/`, `C:\`), 홈 디렉토리(`~/`), 시스템 폴더, `.env`, `.git/config`, `secrets/` 등은 어떠한 경우에도 도구 접근이 차단됩니다.

---

## 5. MCP Dry-Run Mode 규격

실제 디스크 파괴나 잘못된 Git Push를 예방하기 위해 V1.5 수준에서는 모든 승인 필요 도구 및 검증에 **Dry-Run Mode**를 기본 적용합니다.

* **요청/응답 JSON 규격**:
  - 에이전트가 `tools/call`을 수행하면, Permission Guard가 `is_allowed=True`와 함께 `dry_run_action` 상세 구조를 반환합니다.
  - 실제 실행을 우회하고 "실행할 계획인 세부 커맨드라인 및 타겟 변경점"을 JSON 포맷으로 사전에 확인하게 만듭니다.
* **응답 예시**:
  ```json
  {
    "is_allowed": true,
    "reason": "Permissions valid. Tool runs in dry-run mode.",
    "approval_required": true,
    "dry_run_action": {
      "tool": "git.commit",
      "args": {
        "message": "Task 12: Implement player speed update",
        "files": ["src/player.py"]
      }
    }
  }
  ```

---

## 6. MCP Audit Log 설계

모든 MCP 도구 호출은 `mcp_tool_call_logs` 테이블 또는 로컬 audit 파일에 누적 기록됩니다.
* **로그 필드**:
  - `timestamp`: 호출 시간
  - `agent_id`: 호출자 ID
  - `role`: 에이전트의 권한 등급
  - `server_name` / `tool_name`: 호출한 대상
  - `arguments`: 입력 변수 목록 (민감한 secret은 마스킹 처리)
  - `allowed`: 허용 여부
  - `executed`: 실제 실행 여부 (V1.5는 항상 False 또는 dry_run 기록)
  - `reason`: 허용/거절 사유
