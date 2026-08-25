import hashlib
import json
from pathlib import Path


def freeze_jobs(root: Path, jobs: list[dict[str, object]]) -> tuple[Path, Path]:
    jobs_path = root / "jobs.jsonl"
    payload = "".join(json.dumps(job, sort_keys=True) + "\n" for job in jobs).encode()
    jobs_path.write_bytes(payload)
    manifest_path = root / "jobs.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "status": "frozen",
                "job_count": len(jobs),
                "jobs_sha256": hashlib.sha256(payload).hexdigest(),
            },
            sort_keys=True,
        )
    )
    return jobs_path, manifest_path


def load_frozen_jobs(jobs_path: Path, manifest_path: Path) -> list[dict[str, object]]:
    manifest = json.loads(manifest_path.read_text())
    payload = jobs_path.read_bytes()
    if manifest.get("status") != "frozen":
        raise ValueError("job manifest is not frozen")
    jobs = [json.loads(line) for line in payload.splitlines() if line]
    if len(jobs) != manifest.get("job_count"):
        raise ValueError("job count does not match its frozen manifest")
    return jobs
