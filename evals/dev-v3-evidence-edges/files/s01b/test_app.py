import unittest

from app import migrate_episode


class MigrationTests(unittest.TestCase):
    def test_current_schema_is_already_current(self):
        self.assertEqual(
            migrate_episode({"schema": "2.0", "frames": ["a"]}),
            {"schema": "2.0", "frames": ["a"]},
        )


if __name__ == "__main__":
    unittest.main()
