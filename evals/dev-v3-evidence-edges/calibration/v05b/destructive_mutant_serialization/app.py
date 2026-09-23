import hashlib
import json


def render_manifest(entries):
    manifest = {"entries": list(entries), "count": len(entries)}
    manifest["fingerprint"] = hashlib.sha256(json.dumps(manifest["entries"]).encode()).hexdigest()
    return manifest
