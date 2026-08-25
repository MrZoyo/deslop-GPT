import unittest

from app import build_main_parser, build_standalone_parser


class ParserTests(unittest.TestCase):
    def test_both_entrypoints_have_the_same_conversion_options(self):
        arguments = ["--frame-rate", "24", "--workers", "3", "--include-sidecars"]
        main = vars(build_main_parser().parse_args(arguments))
        standalone = vars(build_standalone_parser().parse_args(arguments))
        self.assertEqual(main, standalone)


if __name__ == "__main__":
    unittest.main()
