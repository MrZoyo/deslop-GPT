import sqlite3
import tempfile
import unittest
from pathlib import Path
from app import read_inventory, write_inventory


class InventoryDatabase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "inventory.sqlite"

    def test_save_count_and_sorted_read(self):
        self.assertEqual(write_inventory(self.path, [("washer", 7), ("bolt", 0)]), 2)
        self.assertEqual(read_inventory(self.path), [{"item": "bolt", "quantity": 0},
                                                   {"item": "washer", "quantity": 7}])

    def test_replace_current_inventory(self):
        write_inventory(self.path, [("old", 1)])
        self.assertEqual(write_inventory(self.path, [("齿轮", 2)]), 1)
        self.assertEqual(read_inventory(self.path), [{"item": "齿轮", "quantity": 2}])

    def test_empty_inventory(self):
        self.assertEqual(write_inventory(self.path, []), 0)
        self.assertEqual(read_inventory(self.path), [])

    def test_invalid_input_does_not_replace(self):
        write_inventory(self.path, [("kept", 4)])
        for rows in [[("x", -1)], [("x", True)], [("", 1)], [("x", 1), ("x", 2)]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                write_inventory(self.path, rows)
        self.assertEqual(read_inventory(self.path), [{"item": "kept", "quantity": 4}])

    def test_unknown_database_version(self):
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA user_version = 9")
        with self.assertRaises(ValueError):
            read_inventory(self.path)

    def test_corrupt_current_row(self):
        write_inventory(self.path, [("x", 2)])
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE inventory_items SET quantity = -1")
        with self.assertRaises(ValueError):
            read_inventory(self.path)


if __name__ == "__main__":
    unittest.main()
