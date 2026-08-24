from collections.abc import Callable, Iterable


def convert_records(
    records: Iterable[str],
    encode: Callable[[str], bytes],
    continue_on_error: bool = True,
    fail_fast: bool = False,
) -> list[bytes]:
    """Production conversion stops at the first failed record."""
    converted: list[bytes] = []
    errors: list[Exception] = []
    for record in records:
        try:
            converted.append(encode(record))
        except Exception as error:
            errors.append(error)
            if fail_fast:
                raise
            if continue_on_error:
                continue
            raise
    if errors:
        raise RuntimeError(f"{len(errors)} record(s) failed") from errors[0]
    return converted
