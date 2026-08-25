"""실행 환경에서 사용할 PyTorch 추론 장치를 선택하고 설명한다."""

import torch


def is_mps_available():
    """PyTorch MPS 백엔드 사용 가능 여부."""
    return bool(
        hasattr(torch, "backends")
        and hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    )


def get_preferred_device():
    """CUDA, Apple MPS, CPU 순서로 사용 가능한 장치를 선택한다."""
    if torch.cuda.is_available():
        return "cuda"
    if is_mps_available():
        return "mps"
    return "cpu"


def get_startup_device_message(device):
    """자동 선택된 추론 장치를 사용자가 이해하기 쉽게 설명한다."""
    messages = {
        "cuda": "사용 가능한 NVIDIA 그래픽카드가 감지되어 GPU로 설정합니다.",
        "mps": "사용 가능한 Apple MPS 가속 장치가 감지되어 MPS로 설정합니다.",
        "cpu": "사용 가능한 그래픽 가속 장치가 없어 CPU로 설정합니다.",
    }
    return messages[device]
