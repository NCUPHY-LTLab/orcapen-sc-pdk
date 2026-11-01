from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sync_qmd_notebooks", ROOT / "scripts/sync_qmd_notebooks.py"
)
SYNC = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(SYNC)


def notebook(*, name="python3", display="Python 3", language="python", path=None, code="x = 1"):
    kernelspec = {"name": name, "display_name": display, "language": language}
    if path is not None:
        kernelspec["path"] = path
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": kernelspec},
        "cells": [
            {
                "id": "code-1",
                "cell_type": "code",
                "metadata": {"tags": []},
                "source": code,
                "execution_count": None,
                "outputs": [],
            }
        ],
    }


class NotebookPairMetadataTests(unittest.TestCase):
    def test_standard_python_kernel_is_portable(self):
        first = SYNC._normalized_inputs(
            notebook(
                display="Python 3 (ipykernel)", path="/private/.venv/share/jupyter/kernels/python3"
            ),
            "first",
        )
        second = SYNC._normalized_inputs(notebook(), "second")
        self.assertEqual(first, second)
        self.assertEqual(
            first["metadata"]["kernelspec"],
            {"name": "python3", "display_name": "Python 3", "language": "python"},
        )

    def test_custom_kernel_label_is_preserved_but_path_is_not(self):
        rendered = SYNC._normalized_inputs(
            notebook(
                name="custom", display="Lab Quantum", language="python", path="/machine/kernel"
            ),
            "rendered",
        )
        self.assertEqual(
            rendered["metadata"]["kernelspec"],
            {"name": "custom", "display_name": "Lab Quantum", "language": "python"},
        )

    def test_name_language_and_code_changes_still_fail_comparison(self):
        baseline = SYNC._normalized_inputs(notebook(), "baseline")
        for changed in (
            notebook(name="other"),
            notebook(language="javascript"),
            notebook(code="x = 2"),
        ):
            with self.subTest(changed=changed):
                self.assertNotEqual(SYNC._normalized_inputs(changed, "changed"), baseline)

    def test_validation_only_does_not_mutate_candidate_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src"
            output = root / "out"
            source.mkdir()
            output.mkdir()
            (source / "sample.qmd").write_text("```{python}\n#| id: code-1\nx = 1\n```\n")
            candidate = output / "sample.ipynb"
            candidate.write_text(
                json.dumps(
                    notebook(display="Python 3 (ipykernel)", path="/machine/kernel"), indent=1
                )
                + "\n"
            )
            before = candidate.read_bytes()
            with patch.object(SYNC, "_render_qmd", return_value=notebook()):
                with patch("sys.argv", ["sync_qmd_notebooks.py", str(source), str(output)]):
                    self.assertEqual(SYNC.main(), 0)
            self.assertEqual(candidate.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
