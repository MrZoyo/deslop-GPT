from dataclasses import dataclass


@dataclass(frozen=True)
class Report:
    title: str
    total: int
    labels: tuple[str, ...]


def _coerce_label(value: object) -> str:
    return str(value).strip()


def build_report(title: str, rows: list[dict[str, object]]) -> Report:
    labels = tuple(_coerce_label(row["label"]) for row in rows)
    return Report(title=title, total=len(rows), labels=labels)


def publish_report(report: Report) -> dict[str, object]:
    return {"title": report.title, "total": report.total, "labels": list(report.labels)}
