import unittest

from app import pack_samples, read_full_action


class PackedActionTests(unittest.TestCase):
    def test_each_sample_references_the_full_episode_action(self):
        blob, records = pack_samples([0, 1, 2], [0.1, 0.2, 0.3])
        self.assertEqual([record["full_action_anchor_index"] for record in records], [0, 1, 2])
        for record in records:
            self.assertEqual(read_full_action(blob, record), [0.1, 0.2, 0.3])


if __name__ == "__main__":
    unittest.main()
