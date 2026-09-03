import unittest

from app import (
    CURRENT_TASK_ID,
    OpenDoorStateMachine,
    build_current_package,
    load_current_package,
)


class DisconnectedLayerTests(unittest.TestCase):
    def test_producer(self):
        self.assertEqual(build_current_package(CURRENT_TASK_ID)["schema"], "current-1")

    def test_loader(self):
        self.assertEqual(
            load_current_package(
                {"schema": "current-1", "task_id": CURRENT_TASK_ID, "target_degrees": 5}
            ),
            (CURRENT_TASK_ID, 5),
        )

    def test_state_machine(self):
        self.assertTrue(OpenDoorStateMachine(CURRENT_TASK_ID, 5).run())


if __name__ == "__main__":
    unittest.main()
