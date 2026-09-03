from dataclasses import dataclass


@dataclass(frozen=True)
class ReportOptions:
    display_label: str = "untitled"


def parse_report_options(mapping):
    return ReportOptions(display_label=mapping.get("display_label", "untitled"))
