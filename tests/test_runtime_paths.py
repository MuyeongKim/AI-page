from pathlib import Path

import pytest

from mypackage import gui


@pytest.mark.parametrize("model_name", ["yolo26x.pt", "yolo26n.pt"])
def test_frozen_model_beside_executable_is_found_from_another_working_directory(
    tmp_path, monkeypatch, model_name
):
    bundle = tmp_path / "프로그램"
    internal = bundle / "_internal"
    internal.mkdir(parents=True)
    model = bundle / model_name
    model.write_bytes(b"BUNDLED_WEIGHTS")
    working_directory = tmp_path / "other"
    working_directory.mkdir()
    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(gui, "PROJECT_ROOT", internal)
    monkeypatch.setattr(gui.sys, "frozen", True, raising=False)
    monkeypatch.setattr(gui.sys, "executable", str(bundle / "Application.exe"))

    assert Path(gui.resolve_model_source(model_name)) == model.resolve()
    assert list(working_directory.iterdir()) == []


def test_source_root_model_keeps_precedence_and_absolute_paths_are_preserved(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    source_root.mkdir()
    source_model = source_root / "yolo26x.pt"
    source_model.touch()
    executable_model = tmp_path / "yolo26x.pt"
    executable_model.touch()
    monkeypatch.setattr(gui, "PROJECT_ROOT", source_root)
    monkeypatch.setattr(gui.sys, "frozen", True, raising=False)
    monkeypatch.setattr(gui.sys, "executable", str(tmp_path / "App.exe"))

    assert gui.resolve_model_source("yolo26x.pt") == str(source_model)
    assert gui.resolve_model_source(str(executable_model)) == str(executable_model)


@pytest.mark.parametrize("frozen", [False, True])
def test_missing_models_keep_the_download_alias_without_starting_a_download(
    tmp_path, monkeypatch, frozen
):
    monkeypatch.setattr(gui, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(gui.sys, "frozen", frozen, raising=False)
    monkeypatch.setattr(gui.sys, "executable", str(tmp_path / "App.exe"))
    monkeypatch.setattr(gui, "YOLO", lambda *_args: pytest.fail("resolver must not load a model"))

    assert gui.resolve_model_source("yolo11n.pt") == "yolo11n.pt"
    assert list(tmp_path.iterdir()) == []


def test_source_execution_does_not_search_the_python_interpreter_directory(tmp_path, monkeypatch):
    interpreter_folder = tmp_path / "python"
    interpreter_folder.mkdir()
    (interpreter_folder / "yolo26x.pt").touch()
    monkeypatch.setattr(gui, "PROJECT_ROOT", tmp_path / "source")
    monkeypatch.setattr(gui.sys, "frozen", False, raising=False)
    monkeypatch.setattr(gui.sys, "executable", str(interpreter_folder / "python"))

    assert gui.resolve_model_source("yolo26x.pt") == "yolo26x.pt"
