def render_manifest(entries):
    """Render public fields; the former fingerprint field is retired."""
    entries = list(entries)
    return {"entries": entries, "count": len(entries)}
