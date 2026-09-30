"""The client against a local stand-in for the motion generator server."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import numpy as np
import pytest
from reachy_animation import Clip

from reachy_motion_generator_api import Generation, MotionGenerator, MotionGeneratorError, Plan

REQUESTS: list[dict[str, Any]] = []


def move(frames: int, pitch: float) -> dict[str, Any]:
    c, s = np.cos(pitch), np.sin(pitch)
    head = [[c, 0.0, s, 0.0], [0.0, 1.0, 0.0, 0.0], [-s, 0.0, c, 0.01], [0.0, 0.0, 0.0, 1.0]]
    return {
        "description": "x",
        "time": [i / 25 for i in range(frames)],
        "set_target_data": [{"head": head, "antennas": [-0.2, 0.2], "body_yaw": 0.0}] * frames,
    }


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        REQUESTS.append({"path": self.path, **body})
        if body.get("effort") == "medium" and body["prompt"] == "unloaded":
            self._send(422, {"detail": "effort 'medium' not loaded; available: ['high']"})
        elif self.path == "/generate-dense":
            self._send(
                200,
                {
                    "prompt": body["prompt"],
                    "effort": body.get("effort", "high"),
                    "idea": "i",
                    "recipe": "go 1 e=20",
                    "moves": [move(50, 0.1 * (k + 1)) for k in range(body["n"])],
                    "durations_s": [2.0] * body["n"],
                    "timing_ms": {"total": 1},
                },
            )
        elif self.path == "/generate-sparse":
            keys = [
                {"t": 0.0, "earR": 15, "earL": 15, "pitch": 0, "roll": 0, "yaw": 0, "z": 3, "body": 0, "energy": 0.5}
            ]
            self._send(
                200,
                {
                    "prompt": body["prompt"],
                    "idea": "i",
                    "recipe": "go 1 e=20",
                    "plans": [{"duration": 1.0, "keys": keys}],
                    "durations_s": [1.0],
                    "timing_ms": {"planner": 1, "total": 1},
                },
            )
        else:
            self._send(404, {"detail": "Not Found"})

    def _send(self, code: int, obj: dict[str, Any]) -> None:
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def server() -> Iterator[str]:
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    REQUESTS.clear()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_dense_returns_a_playable_clip(server: str) -> None:
    clip = MotionGenerator(server).dense("sneezing.", effort="low", seed=3)
    assert isinstance(clip, Clip) and clip.name == "sneezing."
    assert clip.duration == pytest.approx(49 / 25) and clip.fps == pytest.approx(25)
    assert clip.sample(1.0)[4] == pytest.approx(0.1)  # pitch from the head matrix
    assert REQUESTS[-1] == {"path": "/generate-dense", "prompt": "sneezing.", "n": 1, "seed": 3, "effort": "low"}


def test_dense_many_and_default_effort(server: str) -> None:
    clips = MotionGenerator(server, effort="high").dense_many("nodding.", 3)
    assert [round(float(c.sample(0.5)[4]), 2) for c in clips] == [0.1, 0.2, 0.3]
    assert REQUESTS[-1]["effort"] == "high" and isinstance(REQUESTS[-1]["seed"], int)


def test_sparse_returns_the_plan(server: str) -> None:
    plan = MotionGenerator(server).sparse("heartbroken.")
    assert isinstance(plan, Plan) and plan.recipe == "go 1 e=20" and plan.keyframes[0][0]["earR"] == 15
    assert "effort" not in REQUESTS[-1]  # the server's default


def test_errors_are_readable(server: str) -> None:
    with pytest.raises(MotionGeneratorError, match="not loaded"):
        MotionGenerator(server).dense("unloaded", effort="medium")
    with pytest.raises(MotionGeneratorError, match="cannot reach"):
        MotionGenerator("http://127.0.0.1:9", timeout_s=2).dense("x")


def test_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REACHY_MOTION_API", "http://example:1234/")
    assert MotionGenerator().url == "http://example:1234"


def test_generate_returns_metadata_and_passes_retry_options(server: str) -> None:
    g = MotionGenerator(server).generate("proud.", n=2, effort="medium", retries=0, batched_retries=True)
    assert isinstance(g, Generation) and len(g.clips) == 2 and g.recipe == "go 1 e=20" and g.effort == "medium"
    assert REQUESTS[-1]["retries"] == 0 and REQUESTS[-1]["batched_retries"] is True
    MotionGenerator(server).dense("proud.")
    assert "retries" not in REQUESTS[-1] and "batched_retries" not in REQUESTS[-1]  # server defaults
