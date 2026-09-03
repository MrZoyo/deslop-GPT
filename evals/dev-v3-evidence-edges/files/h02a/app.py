import json


def build_assets(config_path):
    config = json.loads(config_path.read_text())
    source_path = config_path.parent / config["source"]
    output_path = config_path.parent / config["output"]
    source = json.loads(source_path.read_text())
    compiled = {
        "joint": source["joint"],
        "collision": source["collision"],
    }
    output_path.write_text(json.dumps(compiled, sort_keys=True))
    return compiled
