import unittest

from app import parse_task


class TaskParserTests(unittest.TestCase):
    def test_current_component_package_is_required(self):
        task = parse_task({"component_package": "outputs/current-grasp-ready"})
        self.assertEqual(task.component_package, "outputs/current-grasp-ready")
        with self.assertRaises((KeyError, ValueError, TypeError)):
            parse_task({})


if __name__ == "__main__":
    unittest.main()
