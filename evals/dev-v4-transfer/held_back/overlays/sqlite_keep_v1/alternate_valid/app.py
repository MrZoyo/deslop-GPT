import sqlite3


def _checked(rows):
    result = []
    seen = set()
    for item, quantity in rows:
        if not isinstance(item, str) or not item.strip() or item in seen:
            raise ValueError("invalid or duplicate item")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise ValueError("invalid quantity")
        seen.add(item)
        result.append({"item": item, "quantity": quantity})
    result.sort(key=lambda entry: entry["item"])
    return result


def write_inventory(path, items):
    rows = _checked(list(items))
    with sqlite3.connect(path) as db:
        if db.execute("PRAGMA user_version").fetchone()[0] not in (0, 2):
            raise ValueError("unsupported write version")
        db.execute("CREATE TABLE IF NOT EXISTS inventory_items (item TEXT PRIMARY KEY, quantity INTEGER NOT NULL)")
        db.execute("DELETE FROM inventory_items")
        db.executemany("INSERT INTO inventory_items VALUES (?, ?)",
                       [(entry["item"], entry["quantity"]) for entry in rows])
        db.execute("PRAGMA user_version = 2")
    return len(rows)


def read_inventory(path):
    try:
        with sqlite3.connect(path) as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 1:
                raw = db.execute("SELECT name, units FROM stock").fetchall()
                if any(not isinstance(count, str) or not count.isascii() or not count.isdecimal() for _, count in raw):
                    raise ValueError("invalid legacy quantity")
                return _checked((name, int(count)) for name, count in raw)
            if version != 2:
                raise ValueError("unsupported database version")
            return _checked(db.execute("SELECT item, quantity FROM inventory_items").fetchall())
    except (sqlite3.DatabaseError, TypeError, OverflowError) as exc:
        raise ValueError("corrupt inventory") from exc
