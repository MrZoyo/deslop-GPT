import csv
import hashlib
import io
import re


def _validate_item(item, quantity):
    if not isinstance(item, str) or not item.strip() or "\n" in item or "\r" in item:
        raise ValueError("invalid item")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        raise ValueError("invalid quantity")
    return {"item": item, "quantity": quantity}


def _number(value):
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError("invalid stored quantity")
    return int(value)


def _receipt(text):
    raw = text.encode("utf-8")
    return (len(raw), hashlib.sha256(raw).hexdigest())


def _verify_receipt(text, receipt):
    if _receipt(text) != receipt:
        raise ValueError("receipt mismatch")


def encode_item(item, quantity):
    _validate_item(item, quantity)
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="").writerow(["stock-v2", item, quantity])
    text = output.getvalue()
    receipt = _receipt(text)
    _verify_receipt(text, receipt)
    return text


def _read_old_row(row):
    return _validate_item(row[2], _number(row[1]))


def decode_item(text):
    if not isinstance(text, str):
        raise ValueError("record must be text")
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as exc:
        raise ValueError("invalid CSV") from exc
    if len(rows) != 1 or len(rows[0]) != 3:
        raise ValueError("invalid record shape")
    row = rows[0]
    if row[0] == "stock-v1":
        return _read_old_row(row)
    if row[0] != "stock-v2":
        raise ValueError("unsupported record version")
    return _validate_item(row[1], _number(row[2]))
