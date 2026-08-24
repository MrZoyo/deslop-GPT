import unittest

from app import format_user, render_user


class UserRenderingTests(unittest.TestCase):
    def test_public_wrapper_renders_user(self):
        self.assertEqual(format_user("Ada"), "User: Ada")

    def test_renderer_output_is_stable(self):
        self.assertEqual(render_user("Ada"), "User: Ada")

    def test_wrapper_is_callable(self):
        self.assertTrue(callable(format_user))
