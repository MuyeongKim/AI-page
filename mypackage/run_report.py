"""Save a completed detection run's settings and outcome beside its results."""

import json
import os
from pathlib import Path
from uuid import uuid4


def write_run_report(output_folder, report):
    """Atomically publish UTF-8 JSON; leave existing results intact on failure."""
    folder = Path(output_folder)
    destination = folder / "run_summary.json"
    temporary = folder / f".run_summary.{uuid4().hex}.tmp"
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(
                {"schema_version": 1, **report},
                stream,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return str(destination.resolve())
