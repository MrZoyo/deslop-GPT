import argparse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame-rate", type=int, default=30)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--include-sidecars", action="store_true")
    return parser


def build_main_parser() -> argparse.ArgumentParser:
    return _build_parser()


def build_standalone_parser() -> argparse.ArgumentParser:
    return _build_parser()
