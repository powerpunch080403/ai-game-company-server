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

## 🎯 개발 목표 & 포트폴리오 설명

### AI Game Company Server의 증적
본 게임은 다음과 같은 AI 자율 개발 프로세스 하에 개발되었습니다:
1. **정형화된 태스크 팩 바인딩**: Owner 에이전트가 `pygame_survival_v1.json` 규격에 의거하여 명확한 요구사항과 성공 기준(Success Criteria)을 가진 작업들을 발행.
2. **독립적 브랜치 작업**: Worker 에이전트들이 분리된 `worker/*` 개발 브랜치를 임대(Lease)받아 독립적으로 개발 진행.
3. **헤드리스 품질 검증**: Merge가 요청되면 Test Runner가 headless 모드로 단위 테스트 및 스모크 테스트 실행 증적(`test.log`, `screenshot.png`)을 수집.
4. **결재 정책에 따른 병합**: Merge Policy 모듈이 모든 아티팩트와 성공 로그 존재 여부를 판단하여 검증 완료된 코드 브랜치만 `main`에 안전하게 병합 처리.

---

### 개발사 소개
* **AI Game Company System**: Autonomous Software Engine for Game Development and Lifecycle Management.
* **Server Repository**: [ai-game-company-server](https://github.com/powerpunch080403/ai-game-company-server)
