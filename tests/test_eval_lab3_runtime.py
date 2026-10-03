import importlib.util
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvalLab3RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validate = load_module("eval_validate", "eval/envbuild/validate.py")
        cls.grade = load_module("eval_grade", "eval/grader/grade.py")

    def test_real_entrypoints_use_qualified_kit_launch(self):
        self.assertEqual(self.validate._LAB3_APP_KWARGS, {"headless": False, "visualizer": ["kit"]})
        self.assertEqual(
            self.grade._lab3_app_kwargs(enable_cameras=False),
            {"headless": False, "enable_cameras": False, "visualizer": ["kit"]},
        )
        self.assertTrue(self.grade._lab3_app_kwargs(enable_cameras=True)["enable_cameras"])

    def test_validation_subprocess_preserves_only_gpu_library_path(self):
        old_library_path = os.environ.get("LD_LIBRARY_PATH")
        old_sentinel = os.environ.get("EMBODIEDSWE_TEST_SENTINEL")
        try:
            os.environ["LD_LIBRARY_PATH"] = "/.singularity.d/libs"
            os.environ["EMBODIEDSWE_TEST_SENTINEL"] = "do-not-copy"
            env = self.validate._validation_subprocess_env(Path("/bench"))
        finally:
            if old_library_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_library_path
            if old_sentinel is None:
                os.environ.pop("EMBODIEDSWE_TEST_SENTINEL", None)
            else:
                os.environ["EMBODIEDSWE_TEST_SENTINEL"] = old_sentinel

        self.assertEqual(env["LD_LIBRARY_PATH"], "/.singularity.d/libs")
        self.assertEqual(env["PYTHONPATH"], "/bench")
        self.assertNotIn("EMBODIEDSWE_TEST_SENTINEL", env)


if __name__ == "__main__":
    unittest.main()
