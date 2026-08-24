import unittest

from app import render_user


class UserRenderingTests(unittest.TestCase):
    def test_renderer_output_is_stable(self):
        self.assertEqual(render_user("Ada"), "User: Ada")
