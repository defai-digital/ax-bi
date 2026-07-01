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
"""Host-side ax-engine embedding HTTP proxy for AX-BI Docker."""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any

DEFAULT_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_DIMENSIONS = 1024
DEFAULT_INSTRUCTION = (
    "Given a BI analytics question, retrieve relevant datasets, columns, "
    "metrics, and dashboard examples."
)


class AxEngineEmbeddingRuntime:
    """Lazy ax-engine embedding runtime."""

    def __init__(self, model_dir: Path, max_length: int) -> None:
        self.model_dir = model_dir
        self.max_length = max_length
        self._lock = Lock()
        self._session: Any | None = None
        self._tokenizer: Any | None = None

    def _ensure_loaded(self) -> tuple[Any, Any]:
        """Load ax-engine and tokenizer once."""

        with self._lock:
            if self._session is None or self._tokenizer is None:
                from ax_engine import Session
                from transformers import AutoTokenizer

                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_dir,
                    padding_side="left",
                )
                self._session = Session(
                    mlx=True,
                    mlx_model_artifacts_dir=str(self.model_dir),
                )
        return self._session, self._tokenizer

    def _tokenize(self, text: str, tokenizer: Any) -> list[int]:
        """Tokenize one request text for Qwen3-Embedding."""

        encoded = tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            add_special_tokens=True,
        )
        token_ids = list(encoded.input_ids)
        eos_token_id = getattr(tokenizer, "eos_token_id", None)
        if eos_token_id is not None and token_ids and token_ids[-1] != eos_token_id:
            token_ids.append(eos_token_id)
        return token_ids

    def embed(
        self,
        texts: list[str],
        *,
        is_query: bool,
        instruction: str,
    ) -> list[list[float]]:
        """Embed text with ax-engine."""

        session, tokenizer = self._ensure_loaded()
        input_texts = [
            f"Instruct: {instruction}\nQuery: {text}" if is_query else text
            for text in texts
        ]
        batch_token_ids = [self._tokenize(text, tokenizer) for text in input_texts]
        array = session.embed_batch_array(
            batch_token_ids,
            pooling="last",
            normalize=True,
        )
        return array.tolist()


class EmbeddingHandler(BaseHTTPRequestHandler):
    """HTTP handler for embedding requests."""

    runtime: AxEngineEmbeddingRuntime
    model_name: str
    dimensions: int

    def do_GET(self) -> None:  # noqa: N802
        """Return health and model metadata."""

        if self.path != "/health":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_json(
            {
                "status": "ok",
                "model": self.model_name,
                "dimensions": self.dimensions,
            }
        )

    def do_POST(self) -> None:  # noqa: N802
        """Embed a batch of texts."""

        if self.path != "/embed":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            texts = payload.get("texts")
            if not isinstance(texts, list) or not all(
                isinstance(text, str) for text in texts
            ):
                raise ValueError("texts must be a list of strings")
            instruction = payload.get("instruction") or DEFAULT_INSTRUCTION
            if not isinstance(instruction, str):
                raise ValueError("instruction must be a string")
            embeddings = self.runtime.embed(
                texts,
                is_query=payload.get("is_query") is True,
                instruction=instruction,
            )
            self._send_json(
                {
                    "model": self.model_name,
                    "dimensions": self.dimensions,
                    "embeddings": embeddings,
                }
            )
        except Exception as ex:  # pylint: disable=broad-except
            self.send_error(HTTPStatus.BAD_REQUEST, str(ex))

    def log_message(self, format: str, *args: Any) -> None:
        """Write access logs to stderr."""

        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _send_json(self, payload: dict[str, Any]) -> None:
        """Send a JSON response."""

        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    """Run the embedding proxy."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--max-length", type=int, default=8192)
    args = parser.parse_args()

    handler = EmbeddingHandler
    handler.runtime = AxEngineEmbeddingRuntime(Path(args.model_dir), args.max_length)
    handler.model_name = args.model_name
    handler.dimensions = args.dimensions

    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving ax-engine embeddings at http://{args.host}:{args.port}/embed")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
