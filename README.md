# AI-page

AI 객체 탐지 및 SuperClaude 프레임워크 통합 프로젝트

## 프로젝트 개요

이 저장소는 두 개의 주요 프로젝트를 포함합니다:

1. **AI 객체 탐지 애플리케이션** - YOLO와 PySide6를 사용한 Python 기반 객체 탐지 GUI 애플리케이션
2. **SuperClaude 프레임워크** - Claude Code용 특화 페르소나와 MCP 통합을 제공하는 명령 프레임워크 확장

## 주요 기능

### AI 탐지 앱 (`/mypackage/`)
- **실시간 객체 탐지**: YOLO 모델을 사용한 사람 및 차량 탐지
- **GUI 인터페이스**: PySide6 기반 사용자 친화적 인터페이스
- **성능 모니터링**: FPS 표시 및 실시간 성능 추적
- **알림 시스템**: 탐지 시 오디오 알림 기능
- **인증 시스템**: 키 기반 접근 제어 (인증키: "stayup")
- **GPS/매핑 기능**: 위치 기반 서비스 통합

### SuperClaude 프레임워크 (`/superclaude/`)
- **계층적 명령 시스템**: 16개의 특화된 명령 제공
- **페르소나 시스템**: AI 동작 패턴 특화
- **MCP 서버 통합**: Model Context Protocol 서버 연동
- **명령 라우팅 및 오케스트레이션**: 지능형 작업 관리

## 설치 및 실행

### 필수 요구사항
- Python 3.8+
- PyTorch
- PySide6
- Ultralytics YOLO

### AI 탐지 애플리케이션 실행
```bash
# 메인 AI 탐지 GUI 실행
python AI-detection.py

# 또는
python mypackage/start.py
```

### SuperClaude 프레임워크 설치
```bash
# 프레임워크 설치
cd superclaude
pip install -e .

# SuperClaude 명령 실행
SuperClaude
```

## 프로젝트 구조

```
AI-page/
├── mypackage/              # AI 객체 탐지 애플리케이션
│   ├── start.py           # 인증 시스템 및 진입점
│   ├── gui.py             # 메인 애플리케이션 로직
│   ├── ex_gui.py          # Qt Designer 생성 UI 파일
│   ├── check_version.py   # 버전 확인 시스템
│   └── gps2.py           # GPS/매핑 기능
├── superclaude/           # SuperClaude 프레임워크
│   ├── SuperClaude/Core/  # 9개 마크다운 설정 파일
│   ├── SuperClaude/Commands/ # 16개 특화 명령
│   └── pyproject.toml     # 빌드 설정
├── CLAUDE.md             # Claude Code 가이던스
└── README.md             # 이 파일
```

## 주요 특징

### 보안 및 인증
- 하드코딩된 인증 키 시스템 (개선 권장)
- 최대 3회 인증 시도 제한
- GUI 기반 입력 다이얼로그

### YOLO 통합 패턴
- 실시간 비디오 처리
- 구성 가능한 탐지 클래스 (사람, 차량)
- 성능 모니터링 (FPS 표시)
- 오디오 알림이 있는 알림 시스템

### 프레임워크 확장 패턴
- 마크다운 기반 설정 파일
- 특화된 AI 동작을 위한 페르소나 시스템
- MCP 서버 통합
- 명령 라우팅 및 오케스트레이션

## 개발 노트

- AI 탐지 앱은 최적의 YOLO 성능을 위해 GPU 지원이 필요합니다
- 인증은 현재 하드코딩되어 있으며 보안 개선이 고려되어야 합니다
- SuperClaude 프레임워크는 독립형 애플리케이션이 아닌 개발 도구 확장으로 설계되었습니다
- 버전 관리는 AI 탐지 앱에 대해 GitHub 호스팅 JSON 파일을 통해 구현됩니다

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 링크

- **GitHub Pages**: https://muyeongkim.github.io/AI-page/