def process(value: int) -> dict[str, object]:
    result = value * 2
    receipt = {"input": value, "output": result}
    return {"value": result, "receipt": receipt}


def validate_receipt(report: dict[str, object]) -> bool:
    receipt = report["receipt"]
    return receipt["input"] * 2 == receipt["output"] == report["value"]
