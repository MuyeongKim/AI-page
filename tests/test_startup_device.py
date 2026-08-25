import importlib
import importlib.util
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mypackage import gui, start
from mypackage.version import CURRENT_RELEASE

DEVICE_SPEC = importlib.util.find_spec("mypackage.device")


def test_startup_device_module_exists():
    assert DEVICE_SPEC is not None


if DEVICE_SPEC is not None:
    device = importlib.import_module("mypackage.device")


@pytest.fixture(scope="session")
def qapp():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.mark.parametrize(
    ("cuda_available", "mps_available", "expected"),
    [
        (True, True, "cuda"),
        (False, True, "mps"),
        (False, False, "cpu"),
    ],
)
def test_preferred_device_uses_cuda_then_mps_then_cpu(
    monkeypatch, cuda_available, mps_available, expected
):
    monkeypatch.setattr(device.torch.cuda, "is_available", lambda: cuda_available)
    monkeypatch.setattr(device, "is_mps_available", lambda: mps_available)

    assert device.get_preferred_device() == expected


@pytest.mark.parametrize(
    ("selected_device", "expected_words"),
    [
        ("cuda", ("NVIDIA", "GPU로 설정합니다")),
        ("mps", ("Apple", "MPS로 설정합니다")),
        ("cpu", ("가속 장치가 없어", "CPU로 설정합니다")),
    ],
)
def test_startup_device_message_explains_the_selected_device(
    selected_device, expected_words
):
    message = device.get_startup_device_message(selected_device)

    assert all(word in message for word in expected_words)


def test_authentication_success_message_combines_version_and_device_result():
    message = start.build_authentication_success_message("cuda")

    assert CURRENT_RELEASE.display_version in message
    assert f"{CURRENT_RELEASE.display_version}를 실행합니다" in message
    assert "인증 성공" in message
    assert device.get_startup_device_message("cuda") in message


@pytest.mark.parametrize(
    ("preferred_device", "expected_label"),
    [("cuda", "GPU"), ("mps", "MPS"), ("cpu", "CPU")],
)
def test_main_window_preselects_the_detected_device(
    qapp, monkeypatch, preferred_device, expected_label
):
    monkeypatch.setattr(gui, "get_preferred_device", lambda: preferred_device)
    monkeypatch.setattr(gui.MemoryMonitor, "log_memory_usage", lambda *_args: None)

    window = gui.Ui_MainWindow()
    try:
        assert window.device == preferred_device
        assert window.comboBox_device.currentText() == expected_label
    finally:
        window._closing_without_confirmation = True
        window.close()
        window.deleteLater()
        qapp.processEvents()
