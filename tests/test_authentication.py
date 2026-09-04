from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QDialog, QInputDialog, QLineEdit, QMessageBox

from mypackage import start


@pytest.mark.parametrize(
    ("dialog_result", "expected_accepted"),
    [(QDialog.DialogCode.Accepted, True), (QDialog.DialogCode.Rejected, False)],
)
def test_prompt_for_key_uses_dialog_instance_in_password_mode(
    qt_application, monkeypatch, dialog_result, expected_accepted
):
    dialog = QInputDialog()
    dialog.setTextValue("stayup")
    dialog.exec = Mock(return_value=dialog_result)
    monkeypatch.setattr(start, "QInputDialog", lambda: dialog)
    try:
        user_key, accepted = start._prompt_for_key("Authentication", "Enter key")

        assert user_key == "stayup"
        assert accepted is expected_accepted
        assert dialog.windowTitle() == "Authentication"
        assert dialog.labelText() == "Enter key"
        assert dialog.textEchoMode() == QLineEdit.EchoMode.Password
        dialog.exec.assert_called_once_with()
    finally:
        dialog.deleteLater()
        qt_application.processEvents()


@pytest.fixture
def authentication_dialogs(qt_application, monkeypatch):
    messages = []
    dialogs = []

    def create_message_box():
        dialog = QMessageBox()
        dialog.exec = Mock(side_effect=lambda: messages.append(dialog.text()) or 0)
        dialogs.append(dialog)
        return dialog

    # Replace only this module's factory; other tests keep the real Qt classes.
    message_boxes = Mock(side_effect=create_message_box)
    message_boxes.Icon = QMessageBox.Icon
    message_boxes.StandardButton = QMessageBox.StandardButton
    message_boxes.information = Mock(
        side_effect=lambda _parent, _title, text: messages.append(text)
    )
    message_boxes.warning = Mock()
    message_boxes.critical = Mock()
    monkeypatch.setattr(start, "QMessageBox", message_boxes)
    monkeypatch.setattr(start, "apply_modern_style", lambda: None)
    monkeypatch.setattr(start, "get_preferred_device", lambda: "cpu")
    yield {"warning": message_boxes.warning, "messages": messages}
    for dialog in dialogs:
        dialog.deleteLater()
    qt_application.processEvents()


@pytest.mark.parametrize("authenticate", [start.authenticate, start.authenticate_basic])
def test_empty_confirmation_can_retry_without_consuming_attempts(
    monkeypatch, authentication_dialogs, authenticate
):
    answers = [("", True)] * 4 + [
        ("wrong-1", True),
        ("", True),
        ("wrong-2", True),
        (start.VALID_KEY, True),
    ]
    prompt = Mock(side_effect=answers)
    monkeypatch.setattr(start, "_prompt_for_key", prompt)

    assert authenticate() is True
    assert prompt.call_count == len(answers)
    empty_warnings = [
        call for call in authentication_dialogs["warning"].call_args_list
        if call.args[1] == "인증 키 입력"
    ]
    assert len(empty_warnings) == 5


@pytest.mark.parametrize("authenticate", [start.authenticate, start.authenticate_basic])
def test_explicit_cancel_still_exits(monkeypatch, authentication_dialogs, authenticate):
    prompt = Mock(return_value=("", False))
    monkeypatch.setattr(start, "_prompt_for_key", prompt)

    with pytest.raises(SystemExit):
        authenticate()
    assert prompt.call_count == 1


@pytest.mark.parametrize("authenticate", [start.authenticate, start.authenticate_basic])
def test_three_incorrect_keys_still_exit(
    monkeypatch, authentication_dialogs, authenticate
):
    prompt = Mock(return_value=("incorrect-key", True))
    monkeypatch.setattr(start, "_prompt_for_key", prompt)

    with pytest.raises(SystemExit):
        authenticate()
    assert prompt.call_count == start.MAX_ATTEMPTS


@pytest.mark.parametrize("authenticate", [start.authenticate, start.authenticate_basic])
@pytest.mark.parametrize("selected_device", ["cuda", "mps", "cpu"])
def test_success_dialog_preserves_current_version_and_selected_device(
    monkeypatch, authentication_dialogs, authenticate, selected_device
):
    monkeypatch.setattr(start, "_prompt_for_key", lambda *args: (start.VALID_KEY, True))
    monkeypatch.setattr(start, "get_preferred_device", lambda: selected_device)

    assert authenticate() is True

    assert len(authentication_dialogs["messages"]) == 1
    message = authentication_dialogs["messages"][0]
    assert start.CURRENT_RELEASE.display_version in message
    assert start.get_startup_device_message(selected_device) in message
