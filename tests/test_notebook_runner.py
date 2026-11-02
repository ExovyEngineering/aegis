"""Optional Jupyter orchestration checks use fake clients, never real kernels."""
import json
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat", reason="Optional notebook tools are not installed")
nbclient = pytest.importorskip("nbclient", reason="Optional notebook tools are not installed")
jupyter_client = pytest.importorskip("jupyter_client", reason="Optional notebook tools are not installed")
from jupyter_client import kernelspec

from scripts import execute_notebooks as runner


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "A B"
    (root / "notebooks").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "reports").mkdir()
    (root / "requirements-lock.txt").write_bytes(b"numpy==tested\r\n")
    (root / "requirements-notebooks.txt").write_bytes(b"nbformat==tested\r\n")
    (root / "data/aegis.sqlite").write_bytes(b"preserve operator database")
    (root / "data/aegis.sqlite-wal").write_bytes(b"preserve uncheckpointed work")
    name = runner.NOTEBOOKS[0]
    source = root / "notebooks" / name
    notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("answer = 2 + 2\nanswer")])
    nbformat.write(notebook, source)
    monkeypatch.delenv("AEGIS_NOTEBOOK_RAW_DIR", raising=False)
    monkeypatch.setenv("AEGIS_DB_PATH", str(root / "data/aegis.sqlite"))
    monkeypatch.setenv("AEGIS_REHEARSAL_ID", "inherited-owner-profile")
    monkeypatch.setenv("AEGIS_OFFLINE_DEMO", "0")
    monkeypatch.setenv("AEGIS_DATA_DIR", str(root / "private-originals"))
    # Package-version reporting is independent from these orchestration tests.
    monkeypatch.setattr(runner, "version", lambda package: "test-optional-version")
    return root, name, source


def clients(monkeypatch, mode="success", export_error=False):
    captured = {"managers": [], "execute": [], "client_options": []}

    class KernelSpecManager:
        def __init__(self, **kwargs):
            captured["spec_options"] = kwargs

    class KernelManager:
        def __init__(self, **kwargs):
            self.options = kwargs
            self.has_kernel = False
            self.shutdown_calls = []
            self.cleanup_calls = 0
            captured["managers"].append(self)

        def shutdown_kernel(self, now=False):
            self.shutdown_calls.append(now)
            self.has_kernel = False

        def cleanup_resources(self):
            self.cleanup_calls += 1

    class NotebookClient:
        def __init__(self, notebook, km, **kwargs):
            self.notebook, self.km = notebook, km
            captured["client_options"].append(kwargs)

        def execute(self, **kwargs):
            captured["execute"].append(kwargs)
            # Simulate a started externally supplied manager, including a cell
            # failure before normal client cleanup can complete.
            self.km.has_kernel = True
            cell = self.notebook.cells[0]
            cell.execution_count = 1
            if mode in {"cell_failure", "error_output"}:
                cell.outputs = [nbformat.v4.new_output("error", ename="ValueError",
                    evalue="original cell failure", traceback=["ValueError: original cell failure"])]
                if mode == "cell_failure":
                    raise ValueError("original cell failure")
            else:
                cell.outputs = [nbformat.v4.new_output("stream", name="stdout", text="recomputed answer: 4\n")]
            return self.notebook

    def export(notebook, source, destination):
        if export_error:
            raise OSError("preview export failed")
        destination.write_text("<!doctype html><title>Actual captured outputs</title>", encoding="utf-8")

    monkeypatch.setattr(nbclient, "NotebookClient", NotebookClient)
    monkeypatch.setattr(jupyter_client, "KernelManager", KernelManager)
    monkeypatch.setattr(kernelspec, "KernelSpecManager", KernelSpecManager)
    monkeypatch.setattr(runner, "export_html", export)
    return captured


def assert_cleaned(captured):
    manager = captured["managers"][0]
    assert manager.has_kernel is False
    assert manager.shutdown_calls == [True]
    assert manager.cleanup_calls >= 1


def test_success_uses_exact_local_python_and_keeps_outputs_separate(project, monkeypatch):
    root, name, source = project
    original = source.read_bytes()
    captured = clients(monkeypatch)
    result = runner.execute(names=(name,), root=root, timeout=30)
    assert result["passed"] is True and result["operator_preserved"] is True
    assert result["notebooks"][0]["status"] == "passed"
    assert result["notebooks"][0]["executed_code_cells"] == 1
    assert source.read_bytes() == original
    executed = nbformat.read(root / "reports/notebooks" / name, as_version=4)
    assert executed.cells[0].outputs[0].text == "recomputed answer: 4\n"
    kernel_files = list((root / "reports/notebook_executions").glob("*/kernels/*/kernel.json"))
    assert len(kernel_files) == 1
    kernel = json.loads(kernel_files[0].read_text())
    assert kernel["argv"] == [runner.sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    executed_options = captured["execute"][0]
    assert executed_options["cwd"] == str(root)
    assert not any(key in executed_options["env"] for key in
                   ("AEGIS_DB_PATH", "AEGIS_REHEARSAL_ID", "AEGIS_OFFLINE_DEMO", "AEGIS_DATA_DIR", "AEGIS_NOTEBOOK_RAW_DIR"))
    assert captured["client_options"][0]["allow_errors"] is False
    assert_cleaned(captured)
    assert (root / "data/aegis.sqlite").read_bytes() == b"preserve operator database"
    assert (root / "data/aegis.sqlite-wal").read_bytes() == b"preserve uncheckpointed work"


def test_cell_failure_and_export_failure_preserve_the_original_error_and_outputs(project, monkeypatch):
    root, name, source = project
    original = source.read_bytes()
    captured = clients(monkeypatch, mode="cell_failure", export_error=True)
    result = runner.execute(names=(name,), root=root)
    assert result["passed"] is False and result["operator_preserved"] is True
    assert "original cell failure" in result["error"]
    assert "preview export failed" not in result["error"]
    entry = result["notebooks"][0]
    assert entry["status"] == "failed" and "original cell failure" in entry["error"]
    assert "preview export failed" in entry["html_export_error"]
    executed = nbformat.read(root / "reports/notebooks" / name, as_version=4)
    assert executed.cells[0].outputs[0].output_type == "error"
    assert executed.cells[0].outputs[0].evalue == "original cell failure"
    assert source.read_bytes() == original
    assert json.loads((root / "reports/notebook_execution.json").read_text())["passed"] is False
    assert_cleaned(captured)


def test_html_failure_after_successful_cells_is_reported_as_incomplete_publication(project, monkeypatch):
    root, name, source = project
    captured = clients(monkeypatch, export_error=True)
    result = runner.execute(names=(name,), root=root, update_notebooks=True)
    assert result["passed"] is False and "preview export failed" in result["error"]
    entry = result["notebooks"][0]
    assert entry["status"] == "failed" and entry["executed_code_cells"] == 1
    assert "preview export failed" in entry["html_export_error"]
    # An incomplete publication must not replace the maintained notebook source.
    assert nbformat.read(source, as_version=4).cells[0].execution_count is None
    assert nbformat.read(root / "reports/notebooks" / name, as_version=4).cells[0].execution_count == 1
    assert_cleaned(captured)


def test_returned_error_output_cannot_be_counted_as_a_successful_execution(project, monkeypatch):
    root, name, _ = project
    captured = clients(monkeypatch, mode="error_output")
    result = runner.execute(names=(name,), root=root)
    assert result["passed"] is False and "execution error" in result["error"]
    assert result["notebooks"][0]["status"] == "failed"
    assert_cleaned(captured)
