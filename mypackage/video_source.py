CAPTURE_BOARD_SOURCE = "외부영상(캡처보드)"
LEGACY_CAPTURE_BOARD_SOURCE = "외부영상(캡쳐보드)"
VIDEO_FILE_SOURCE = "영상"


def normalize_source_name(source):
    if source in {CAPTURE_BOARD_SOURCE, LEGACY_CAPTURE_BOARD_SOURCE}:
        return CAPTURE_BOARD_SOURCE
    return source


def is_live_video_source(source):
    return normalize_source_name(source) in {VIDEO_FILE_SOURCE, CAPTURE_BOARD_SOURCE}


def resolve_video_source_path(source, user_input):
    normalized_source = normalize_source_name(source)

    if normalized_source == VIDEO_FILE_SOURCE:
        if isinstance(user_input, list):
            if not user_input:
                raise ValueError("영상 파일 경로가 비어 있습니다.")
            return str(user_input[0])
        if user_input in (None, ""):
            raise ValueError("영상 파일 경로를 선택해 주세요.")
        return str(user_input)

    if normalized_source == CAPTURE_BOARD_SOURCE:
        if isinstance(user_input, list):
            if not user_input:
                return 0
            user_input = user_input[0]

        if user_input is None:
            return 0

        if isinstance(user_input, int):
            return user_input

        value = str(user_input).strip()
        if not value:
            return 0

        if value.lstrip("-").isdigit():
            return int(value)

        raise ValueError("캡처 장치 번호는 숫자로 입력해 주세요.")

    raise ValueError(f"지원하지 않는 영상 소스입니다: {source}")
