from dataclasses import dataclass


@dataclass(frozen=True)
class ReportOptions:
    display_label: str


def parse_report_options(mapping):
    return ReportOptions(display_label=mapping["display_label"])
