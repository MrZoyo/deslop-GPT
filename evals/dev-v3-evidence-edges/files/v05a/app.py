import hashlib
import json


def render_manifest(entries):
    manifest = {"entries": list(entries), "count": len(entries)}
    manifest["fingerprint"] = _fingerprint(manifest["entries"])
    return manifest


def _fingerprint(entries):
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def verify_manifest(manifest):
    return _fingerprint(manifest["entries"]) == manifest["fingerprint"]
