"""애플리케이션의 로컬 버전과 GUI 변경 이력을 관리한다.

``latest_version.json``은 배포 서버에서 읽는 원격 최신 버전 피드이고,
이 모듈은 현재 소스 코드에 포함된 로컬 버전 정보의 단일 원본이다.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ChangelogSection:
    """GUI에 표시할 날짜별 변경 사항."""

    date: str
    title: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class ReleaseInfo:
    """현재 애플리케이션 릴리스의 구조화된 정보."""

    version: str
    release_date: str
    changelog: tuple[ChangelogSection, ...]

    @property
    def display_version(self) -> str:
        return f"V{self.version}"

    @property
    def window_title(self) -> str:
        return f"AI 객체 탐지 프로그램 {self.display_version} With Stay Up"


CURRENT_RELEASE = ReleaseInfo(
    version="26.0905",
    release_date="2026-09-05",
    changelog=(
        ChangelogSection(
            date="2026.09.05",
            title="V26.0905 결과 보호와 사용성 개선",
            items=(
                "동시 실행의 사진·영상 저장 충돌 방지와 불완전한 원본 복사본 정리",
                "Esc 취소·단계별 진행·경과시간 표시 및 휠에 의한 설정 변경 방지",
                "하단 실행·상태 고정, 옵션 이름·글씨·장치 전환 표시 개선",
                "작업 결과 탭에 전체 오류 보관, 저장 폴더 열기와 원본·탐지본 비교 추가",
                "GPS 백그라운드 분석·취소 안내, 전체 위치 범위와 사진 파일명 표시",
                "빈 인증 입력 재입력과 온라인 공지 링크 열기 개선",
                "웹 관리자 편집 충돌 방지, 모바일 줄바꿈과 현재 GUI 소개 보완",
            ),
        ),
        ChangelogSection(
            date="2026.08.25",
            title="V26.08.25 시작 환경 자동 설정",
            items=(
                "인증 성공 안내에 앱 버전과 자동 감지된 추론 장치를 함께 표시",
                "CUDA·Apple MPS·CPU 순서로 사용 가능한 장치를 판정해 GUI 선택값에 반영",
                "탐지 완료 후 결과 폴더를 GUI에서 바로 열 수 있는 버튼 추가",
                "인증 키 입력 다이얼로그의 PySide6 호환성과 비밀번호 입력 표시 안정화",
            ),
        ),
        ChangelogSection(
            date="2026.08.17",
            title="V26.08.17 운영 안전성 개선",
            items=(
                "사진 처리를 완료·부분 완료·실패·취소 상태와 성공·실패 수로 구분",
                "영상 보고값·재생 시각을 교차 확인하고 불확실한 입력은 검증된 결과를 부분 완료로 보존",
                "캡처보드 읽기 종료를 정상 완료가 아닌 연결 끊김으로 표시",
                "미리보기를 최신 프레임 1장·20fps로 표시해 GUI 프레임 누적 방지",
                "버전·창 제목·GUI 변경 이력을 단일 원본으로 통합하고 불일치 검증 추가",
                "랜딩페이지 관리자 공지와 GUI 온라인 소식을 공통 피드로 연동",
            ),
        ),
        ChangelogSection(
            date="2026.08.08",
            title="안정성 및 사용성 개선",
            items=(
                "현재 추론 결과를 직접 저장해 이전 실행의 동명 사진 결과 재사용 방지",
                "영상 임시 저장·프레임 검증·원자적 전환과 취소·오류 정리 보완",
                "작업 스레드 종료까지 진행 상태 유지 및 실행 중 입력 잠금",
                "탐지 대상 선택, 실제 기본값 표시, 반응형 스크롤과 접근성 보완",
                "GPS 개인정보 안내, 비정상 EXIF 격리 및 생성 지도 Git 제외",
                "README·라이선스 고지·결과 무결성 회귀 테스트 최신화",
            ),
        ),
        ChangelogSection(
            date="2026.04.09",
            title="V26.04.09 릴리스",
            items=(
                "Yolo V26 모델 선택 항목 추가",
                "모던 GUI 스타일 및 사용자 문구 정리",
                "결과 표시 흐름, 실행 진입점과 버전 확인 보완",
            ),
        ),
    ),
)

# 기존 import 경로와 외부 코드의 호환성을 위한 파생 상수이다.
CURRENT_VERSION = CURRENT_RELEASE.version


def format_gui_changelog(release: ReleaseInfo = CURRENT_RELEASE) -> str:
    """구조화된 릴리스 정보를 GUI용 일반 텍스트로 변환한다."""
    lines = [f"현재 버전 {release.display_version}"]

    for section in release.changelog:
        lines.extend(("", f"[{section.date} {section.title}]"))
        lines.extend(f"- {item}" for item in section.items)

    return "\n".join(lines)


def release_feed_mismatches(
    feed: Mapping[str, object],
    release: ReleaseInfo = CURRENT_RELEASE,
) -> tuple[str, ...]:
    """원격 배포 피드와 로컬 릴리스 메타데이터의 불일치 목록을 반환한다.

    이 검증은 릴리스 준비와 테스트에서 사용한다. 실행 중 최신 버전 확인은
    로컬보다 높은 원격 버전을 정상적으로 안내해야 하므로 이 함수를 호출하지 않는다.
    """
    expected_fields = {
        "version": release.version,
        "release_date": release.release_date,
    }
    mismatches = []

    for field, expected in expected_fields.items():
        actual = feed.get(field)
        if actual != expected:
            mismatches.append(f"{field}: 로컬={expected!r}, 원격 피드={actual!r}")

    return tuple(mismatches)


def assert_release_feed_matches_local(
    feed: Mapping[str, object],
    release: ReleaseInfo = CURRENT_RELEASE,
) -> None:
    """릴리스 피드가 로컬 버전과 다르면 명확한 오류를 발생시킨다."""
    mismatches = release_feed_mismatches(feed, release)
    if mismatches:
        details = "; ".join(mismatches)
        raise ValueError(f"로컬 버전과 latest_version.json이 일치하지 않습니다: {details}")
