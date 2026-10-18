"""Save a completed detection run's settings and outcome beside its results."""

import json
import os
from pathlib import Path
from uuid import uuid4


def write_run_report(output_folder, report):
    """Atomically publish UTF-8 JSON; leave existing results intact on failure."""
    return write_json_file(Path(output_folder) / "run_summary.json", {"schema_version": 1, **report})


def write_json_file(destination, document):
    """Publish a local JSON document without replacing the previous file on failure."""
    destination = Path(destination)
    temporary = destination.with_name(f".{destination.stem}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(
                document,
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


def write_bytes_file(destination, data):
    """Publish encoded local output atomically, retaining an existing file on failure."""
    destination = Path(destination)
    temporary = destination.with_name(f".{destination.stem}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return str(destination.resolve())
