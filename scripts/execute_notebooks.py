"""Execute the maintained notebooks with this exact Python and save real outputs.

Install requirements-notebooks.txt first. The notebooks independently copy their
analysis inputs; no operator database or published scientific report is rewritten.
"""
from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timezone
import hashlib
import html
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote, urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.notebook_support import local_path, operator_fingerprints

NOTEBOOKS = ("00_Start_Here_and_Coverage.ipynb", "01_Preprocessing_and_Integration.ipynb",
             "02_Modeling_and_Evaluation.ipynb", "03_Scenario_Analysis.ipynb")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_digest(notebook):
    cells = [{"cell_type": cell["cell_type"], "source": cell["source"]} for cell in notebook["cells"]]
    return hashlib.sha256(json.dumps(cells, sort_keys=True).encode("utf-8")).hexdigest()


def export_html(notebook, source, destination):
    from nbconvert import HTMLExporter
    exporter = HTMLExporter(template_name="classic", embed_images=True, mathjax_url="")
    body, _ = exporter.from_notebook_node(notebook)
    # These previews contain tables and embedded PNGs, with no interactive widget
    # dependency. Removing exporter scripts/CDN assets makes reading them offline.
    body = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", body, flags=re.I)
    body = re.sub(r"<link\b[^>]*href=[\"']https?://[^\"']+[\"'][^>]*>", "", body, flags=re.I)

    def rewrite(match):
        target = match.group(2)
        parsed = urlsplit(html.unescape(target))
        if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
            return match.group(0)
        resolved = (source.parent / unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(ROOT):
            return match.group(0)
        relative = os.path.relpath(resolved, destination.parent).replace(os.sep, "/")
        if parsed.fragment:
            relative += "#" + parsed.fragment
        return "href=" + match.group(1) + html.escape(relative, quote=True) + match.group(1)

    body = re.sub(r"href=([\"'])([^\"']+)\1", rewrite, body)
    destination.write_text(body, encoding="utf-8")


def write_index(folder, results, raw_mode):
    rows = []
    for row in results:
        name = Path(row["notebook"]).stem
        rows.append(f'<li><a href="{html.escape(name)}.html">{html.escape(name.replace("_", " "))}</a> '
                    f'— {html.escape(row["status"])}; {row.get("code_cells", 0)} code cells '
                    f'(<a href="{html.escape(name)}.ipynb">executed notebook</a>)</li>')
    body = ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>AEGIS executed analysis notebooks</title><style>body{font:17px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#193b2e}li{margin:18px 0}a{color:#176044}code{overflow-wrap:anywhere}</style>"
            "<h1>AEGIS — executed analysis notebooks</h1>"
            f"<p>Profile: {'original-source reconstruction' if raw_mode else 'bundled-source snapshots'}. "
            "These are read-only HTML previews of real notebook execution, including code, tables and figures. "
            "Open the .ipynb files with a Python 3.13 Jupyter kernel to run them again.</p><ol>" + "".join(rows) + "</ol>"
            "<p>Run outputs are isolated. Raw files are required only for the explicit original-source profile. "
            "Logistics and cargo replay are simulated; model validation remains retrospective. "
            "Kiro non-use is disclosed separately in the final submission guide.</p></html>")
    (folder / "index.html").write_text(body, encoding="utf-8")


def execute(names=NOTEBOOKS, raw_dir=None, update_notebooks=False, timeout=900, root=ROOT):
    try:
        import nbformat
        from nbclient import NotebookClient
        from jupyter_client import KernelManager
        from jupyter_client.kernelspec import KernelSpecManager
    except ImportError as error:
        raise RuntimeError("Install optional tools first: python -m pip install -r requirements-notebooks.txt") from error
    root = Path(root).resolve()
    if any(name not in NOTEBOOKS for name in names):
        raise ValueError("Select only a maintained notebook filename")
    raw_value = raw_dir or os.environ.get("AEGIS_NOTEBOOK_RAW_DIR")
    if raw_value and not Path(raw_value).is_dir():
        raise FileNotFoundError(f"Original raw-data directory unavailable: {raw_value}")
    raw_mode = bool(raw_value)
    profile = "raw" if raw_mode else "bundled"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + profile
    scratch = local_path(root, "reports/notebook_executions/" + run_id)
    scratch.mkdir(parents=True, exist_ok=False)
    output = local_path(root, "reports/notebooks" + ("/raw" if raw_mode else ""))
    output.mkdir(parents=True, exist_ok=True)
    kernel_name = "aegis-repro-" + uuid.uuid4().hex
    kernels = scratch / "kernels"
    spec = kernels / kernel_name
    spec.mkdir(parents=True)
    (spec / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "AEGIS exact reproduction Python", "language": "python"}), encoding="utf-8")
    manager = KernelSpecManager(kernel_dirs=[str(kernels)], ensure_native_kernel=False)
    before = operator_fingerprints(root)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "profile": profile,
              "passed": False, "python": sys.version, "python_executable": sys.executable,
              "raw_data_requested": raw_mode, "original_raws_bundled": False,
              "requirements_lock_sha256": sha256(root / "requirements-lock.txt"),
              "optional_requirements_sha256": sha256(root / "requirements-notebooks.txt"),
              "versions": {name: version(name) for name in ("nbformat", "nbclient", "ipykernel", "nbconvert", "jupyterlab", "numpy", "pandas", "scikit-learn", "ortools")},
              "notebooks": [], "operator_before": before,
              "note": "Real kernel execution. Numeric reproducibility assertions run inside notebooks; timestamps, copied paths, UUIDs and execution timings are not fixed scientific results."}
    try:
        for name in names:
            source = root / "notebooks" / name
            notebook = nbformat.read(source, as_version=4)
            nbformat.validate(notebook)
            source_digest = code_digest(notebook)
            for cell in notebook.cells:
                if cell.cell_type == "code":
                    cell.outputs = []
                    cell.execution_count = None
            started = time.monotonic()
            entry = {"notebook": name, "source_code_sha256": source_digest, "status": "running",
                     "code_cells": sum(cell.cell_type == "code" for cell in notebook.cells)}
            print("Executing " + name, flush=True)
            km = KernelManager(kernel_name=kernel_name, kernel_spec_manager=manager,
                               connection_file=str(scratch / (Path(name).stem + "-connection.json")))
            environment = dict(os.environ)
            for key in ("AEGIS_DB_PATH", "AEGIS_REHEARSAL_ID", "AEGIS_OFFLINE_DEMO", "AEGIS_DATA_DIR"):
                environment.pop(key, None)
            environment.update(PYTHONHASHSEED="0", JUPYTER_CONFIG_DIR=str(scratch / "config"),
                               JUPYTER_DATA_DIR=str(scratch / "jupyter-data"),
                               JUPYTER_RUNTIME_DIR=str(scratch / "runtime"),
                               IPYTHONDIR=str(scratch / "ipython"), MPLCONFIGDIR=str(scratch / "matplotlib"))
            if raw_value:
                environment["AEGIS_NOTEBOOK_RAW_DIR"] = str(Path(raw_value).resolve())
            else:
                environment.pop("AEGIS_NOTEBOOK_RAW_DIR", None)
            client = None
            try:
                client = NotebookClient(notebook, km=km, timeout=timeout, allow_errors=False,
                                        record_timing=True, store_widget_state=False,
                                        resources={"metadata": {"path": str(root)}})
                client.execute(cwd=str(root), env=environment, cleanup_kc=True)
                errors = [item for cell in notebook.cells if cell.cell_type == "code"
                          for item in cell.outputs if item.output_type == "error"]
                if errors:
                    raise RuntimeError("Notebook contains an execution error")
                entry["status"] = "passed"
            except Exception as error:
                entry["status"] = "failed"
                entry["error"] = f"{type(error).__name__}: {error}"
                raise
            finally:
                # NBClient can register its exit callback before startup fails.
                # We own cleanup even for that partial-startup case.
                if client is not None:
                    callback = getattr(client, "_cleanup_kernel", None)
                    if callback is not None:
                        atexit.unregister(callback)
                    channels = getattr(client, "kc", None)
                    if channels is not None:
                        channels.stop_channels()
                # An explicitly supplied kernel manager belongs to this runner,
                # so NBClient does not automatically own its shutdown.
                if km.has_kernel:
                    km.shutdown_kernel(now=True)
                km.cleanup_resources()
                entry["duration_seconds"] = round(time.monotonic() - started, 3)
                target = output / name
                nbformat.write(notebook, target)
                entry["executed_notebook_sha256"] = sha256(target)
                entry["executed_code_cells"] = sum(cell.cell_type == "code" and cell.execution_count is not None for cell in notebook.cells)
                report["notebooks"].append(entry)
                try:
                    export_html(notebook, source, target.with_suffix(".html"))
                    entry["html_sha256"] = sha256(target.with_suffix(".html"))
                except Exception as export_error:
                    entry["html_export_error"] = f"{type(export_error).__name__}: {export_error}"
                    if entry["status"] == "passed":
                        entry["status"] = "failed"
                        raise
            if update_notebooks and not raw_mode:
                nbformat.write(notebook, source)
        report["passed"] = all(row["status"] == "passed" for row in report["notebooks"])
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        report["operator_after"] = operator_fingerprints(root)
        report["operator_preserved"] = report["operator_after"] == before
        report["passed"] = report["passed"] and report["operator_preserved"]
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_index(output, report["notebooks"], raw_mode)
        filename = "notebook_raw_execution.json" if raw_mode else "notebook_execution.json"
        (root / "reports" / filename).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (output / "execution_summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", action="append", choices=NOTEBOOKS, help="Select notebook(s); default runs all four")
    parser.add_argument("--raw-data-dir", type=Path, help="Explicit original-source replay; requires provenance-matched raw files")
    parser.add_argument("--update-notebooks", action="store_true", help="Save successful bundled execution outputs in notebooks/ as well")
    parser.add_argument("--timeout", type=int, default=900, help="Per-cell timeout in seconds")
    args = parser.parse_args()
    try:
        result = execute(args.notebook or NOTEBOOKS, args.raw_data_dir, args.update_notebooks, args.timeout)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Notebook reproduction failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"passed": result["passed"], "profile": result["profile"],
                      "notebooks": [{"name": item["notebook"], "status": item["status"]} for item in result["notebooks"]],
                      "operator_preserved": result["operator_preserved"], "error": result.get("error")}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
