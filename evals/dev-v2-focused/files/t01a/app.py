from dataclasses import dataclass
@dataclass(frozen=True)
class Summary:
    count: int
    names: tuple[str, ...]


def summarize_records(records: list[dict[str, object]]) -> Summary:
    return Summary(
        count=len(records),
        names=tuple(str(record["name"]) for record in records),
    )
