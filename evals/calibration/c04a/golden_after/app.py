from collections.abc import Callable, Iterable


def convert_records(
    records: Iterable[str],
    encode: Callable[[str], bytes],
) -> list[bytes]:
    return [encode(record) for record in records]
