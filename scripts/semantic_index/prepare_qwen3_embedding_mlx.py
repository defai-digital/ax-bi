#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Prepare Qwen3-Embedding-0.6B MLX artifacts for ax-engine."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_OUTPUT = "models/qwen3-embedding-0.6b-mlx"


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command and stream output."""

    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, check=check, text=True)  # noqa: S603


def _ax_engine_bench_path() -> str | None:
    """Return the ax-engine-bench executable path."""

    found = shutil.which("ax-engine-bench")
    if found:
        return found
    try:
        import ax_engine
    except ImportError:
        return None
    bundled = Path(ax_engine.__file__).resolve().parent / "_bin" / "ax-engine-bench"
    return str(bundled) if bundled.exists() else None


def _try_ax_engine_download(model_id: str, output_dir: Path) -> bool:
    """Try ax-engine download before falling back to MLX conversion."""

    ax_engine = shutil.which("ax-engine")
    if not ax_engine:
        return False

    command = [
        ax_engine,
        "download",
        model_id,
        "--dest",
        str(output_dir),
        "--json",
    ]
    print("+ " + " ".join(command), flush=True)
    result = subprocess.run(command, text=True)  # noqa: S603
    return result.returncode == 0


def prepare_model(model_id: str, output_dir: Path, q_bits: int) -> dict[str, str]:
    """Download or convert a Qwen embedding model into an AX-ready MLX directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = output_dir / "model-manifest.json"
    if manifest.exists():
        return {
            "status": "exists",
            "model_id": model_id,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
        }

    if not _try_ax_engine_download(model_id, output_dir):
        mlx_convert = shutil.which("mlx_lm.convert")
        if not mlx_convert:
            raise RuntimeError(
                "mlx_lm.convert is required because this ax-engine version "
                "does not manage embedding model downloads"
            )
        _run(
            [
                mlx_convert,
                "--hf-path",
                model_id,
                "--mlx-path",
                str(output_dir),
                "-q",
                "--q-bits",
                str(q_bits),
            ]
        )

    bench = _ax_engine_bench_path()
    if bench:
        _run([bench, "generate-manifest", str(output_dir)])

    return {
        "status": "prepared",
        "model_id": model_id,
        "output_dir": str(output_dir),
        "manifest": str(manifest),
    }


def main() -> int:
    """Run the model preparation command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    parser.add_argument("--q-bits", type=int, default=8)
    args = parser.parse_args()

    result = prepare_model(args.model_id, Path(args.output_dir), args.q_bits)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
