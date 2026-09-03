import unittest

from app import parse_task


class TaskParserTests(unittest.TestCase):
    def test_explicit_current_component_package(self):
        task = parse_task({"component_package": "outputs/current-grasp-ready"})
        self.assertEqual(task.component_package, "outputs/current-grasp-ready")


if __name__ == "__main__":
    unittest.main()
