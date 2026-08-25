from dataclasses import dataclass


@dataclass(frozen=True)
class Report:
    title: str
    total: int
    labels: tuple[str, ...]


def build_report(title: str, rows: list[dict[str, object]]) -> Report:
    return Report(
        title=title,
        total=len(rows),
        labels=tuple(str(row["label"]).strip() for row in rows),
    )


def publish_report(report: Report) -> dict[str, object]:
    return {"title": report.title, "total": report.total, "labels": list(report.labels)}
