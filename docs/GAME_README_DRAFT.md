# Neon Survival Prototype (Game README Draft)

이 문서는 Neon Survival Prototype 게임 프로젝트가 생성될 때 최상위 경로에 위치할 `README.md` 파일의 초안입니다.

---

# Neon Survival Prototype

[![Engine](https://img.shields.io/badge/Engine-Pygame--ce-blueviolet)](https://github.com/pygame-community/pygame-ce)
[![Build Status](https://img.shields.io/badge/Build-Headless--Verified-success)](#)
[![AI Managed](https://img.shields.io/badge/AI--Game--Company-Managed-blue)](https://github.com/powerpunch080403/ai-game-company-server)

## 🌌 한 줄 소개 (Introduction)
**Neon Survival Prototype**은 어두운 그리드 공간 속에서 다가오는 붉은색 네온 적 오브젝트들을 회피하며 60초 동안 생존하는 탑다운 2D 미니 서바이벌 게임 프로토타입입니다.

> [!IMPORTANT]
> 이 프로젝트는 **AI Game Company Server**의 완전 자율적 에이전트 협업 파이프라인(Owner & Worker)을 통해 100% 개발되고 테스트 러너의 검증을 거쳐 빌드된 포트폴리오용 데모입니다.

---

## 🕹️ 조작 방법 (Controls)
* **`W` / `A` / `S` / `D`**: 플레이어 캐릭터 (Cyan Neon Circle) 상/하/좌/우 이동
* **`Space`**: 게임 오버(체력 0 도달) 시 게임 리셋 및 재시작
* **`Esc` / `창 닫기`**: 게임 종료

---

## 🚀 실행 방법 (How to Run)

### 1. 요구사항 설치
Python 3.12+ 및 Pygame 설치가 필요합니다.
```bash
pip install -r requirements.txt
```

### 2. 게임 실행
```bash
python -m src.game.main
```

---

## 🧪 테스트 방법 (How to Test)

### 1. 단위 테스트 실행
```bash
python -m unittest discover -s tests
```

### 2. 가상 헤드리스 스모크 테스트 (CI/CD 환경)
실제 디스플레이 장치가 없는 Headless 환경(서버/컨테이너 등)에서는 가상 비디오 드라이버를 로드하여 100프레임 동안 게임 루프를 돌린 후 렌더링 화면을 스크린샷 아티팩트로 저장하고 정상 종료합니다.
```bash
# Windows
$env:SDL_VIDEODRIVER="dummy"
python scripts/smoke_check.py

# Linux / macOS
SDL_VIDEODRIVER=dummy python scripts/smoke_check.py
```
* 검증 완료 후 `.game-company/artifacts/screenshot.png` 파일이 생성됩니다.

---

## 🏗️ Built with AI Game Company Server

이 프로젝트는 단순히 코드를 실행하는 게임이 아니라, **AI Game Company Server의 수많은 보안 가드와 파이프라인 정책을 완전히 통과했음을 증명하는 E2E 검증 결과물**입니다. 개발 시 다음 핵심 서버 기능들이 유기적으로 활용되고 테스트되었습니다:

1. **에픽 및 작업 계층 관리 (Hierarchy Management)**:
   * 전체 게임 구조가 `Project -> Epic -> SubEpic -> Task` 구조에 맵핑되어 데이터베이스에 사전 등록되고 관리되었습니다.
2. **에이전트 작업 유효성 검사 (Owner Task Planning Validator)**:
   * 작업 배포 전 `goal`, `role`, `branch`, `estimated_minutes` 및 필수 제출 증적(evidence) 목록이 올바른지 사전 검증을 통과했습니다.
3. **가두리 격리 브랜치 개발 (Workspace Worker Branch Flow)**:
   * 작업자들이 메인 브랜치를 직접 건드리지 않고, Lease 받은 `worker/*` 개발 격리 브랜치에서 단위 커밋과 푸시를 통해서만 코드를 기여하도록 강제되었습니다.
4. **품질 검증 테스트 러너 (Test Runner Validation)**:
   * `.game-company/test_runner.json` 설정 파일에 기반해 가상 환경 setup, pytest를 사용한 test, 그리고 dummy video driver 기반의 headless smoke 테스트 단계를 순차 완수했습니다.
5. **엄격한 병합 차단 정책 (Merge Review Policy)**:
   * 일부러 테스트를 실패시키거나 증적 로그를 누락시킨 브랜치(`worker/merge-policy-challenge`)를 제출하여, 서버의 `eval_merge_policy`가 이를 감지하고 안전하게 병합을 차단·반려(Block)하는 오작동 복원력이 테스트되었습니다.
6. **디스코드 자연어 승인 결재 (Discord Natural-Language Approval)**:
   * 릴리즈 후보(RC) 브랜치 병합 시, 디스코드 채널로 결재 알림을 보내고 사용자의 한국어 의사결정("좋아 진행해", "승인")을 해석하여 자동으로 최종 병합을 처리하는 흐름을 검증했습니다.
7. **아티팩트 분류 및 보존 주기 제어 (Artifact Cleanup & Safety Guard)**:
   * 스크린샷 및 로그를 스트리밍하여 서버에 안전하게 보존하고, `release_or_milestone=1` 지정 아티팩트는 삭제에서 제외시키는 안전한 아티팩트 정리 주기(`cleanup_artifacts.py`)를 가동했습니다.
8. **컨텍스트 연속성 보존 (Memory Refs & History Summaries)**:
   * 작업 시 이전 태스크들의 개발 기록 요약본과 `project_rules`, `coding_rules` 기억 지시자가 콘텍스트에 바인딩되어 모델의 추론 일관성을 유지했습니다.

---

### 개발사 소개
* **AI Game Company System**: Autonomous Software Engine for Game Development and Lifecycle Management.
* **Server Repository**: [ai-game-company-server](https://github.com/powerpunch080403/ai-game-company-server)
