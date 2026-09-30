"""Client for the Reachy Mini motion generator: a text prompt in, a playable motion out."""

from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Literal

from reachy_animation import Clip

Effort = Literal["low", "medium", "high"]
"""Which planner writes the motion: ``low`` 0.8B (fastest), ``medium`` 4B, ``high`` 27B (best)."""

DEFAULT_URL = "http://localhost:8000"


class MotionGeneratorError(RuntimeError):
    """The server could not be reached, or it rejected the request."""


@dataclass(frozen=True)
class Plan:
    """What the planner decided, before any motion is generated (``MotionGenerator.sparse``)."""

    prompt: str
    idea: str
    """One sentence describing the motion."""
    recipe: str
    """The motion script the keyframes were expanded from."""
    keyframes: list[list[dict[str, float]]]
    """One keyframe list per variation. Every keyframe has ``t`` (s), ``earR earL pitch roll yaw body`` (deg),
    ``z`` (mm) and ``energy`` (deg RMS of the fast detail the motion model adds), every 0.25 s."""
    durations_s: list[float]
    timing_ms: dict[str, int] = field(default_factory=dict)


class MotionGenerator:
    """A motion generator server.

    ``url`` defaults to the ``REACHY_MOTION_API`` environment variable, then ``http://localhost:8000``.
    ``effort`` sets the default planner for every call; each call can override it.
    """

    def __init__(self, url: str | None = None, effort: Effort | None = None, timeout_s: float = 60.0) -> None:
        self.url = (url or os.environ.get("REACHY_MOTION_API") or DEFAULT_URL).rstrip("/")
        self.effort = effort
        self.timeout_s = timeout_s

    def dense(self, prompt: str, effort: Effort | None = None, seed: int | None = None) -> Clip:
        """Generate one motion for ``prompt``, ready for ``Animator.play``.

        ``seed=None`` picks a new one each call, so the same prompt varies; pass a seed to repeat a result.
        """
        return self.dense_many(prompt, 1, effort, seed)[0]

    def dense_many(self, prompt: str, n: int, effort: Effort | None = None, seed: int | None = None) -> list[Clip]:
        """Generate ``n`` variations of one motion (same plan, different amplitude, tempo and detail)."""
        r = self._post("/generate-dense", prompt, n, effort, seed)
        return [Clip.load({**move, "description": prompt}) for move in r["moves"]]

    def sparse(self, prompt: str, n: int = 1, effort: Effort | None = None, seed: int | None = None) -> Plan:
        """Only plan the motion: the recipe and its keyframes, without running the motion model (faster)."""
        r = self._post("/generate-sparse", prompt, n, effort, seed)
        return Plan(
            prompt=prompt,
            idea=r.get("idea", ""),
            recipe=r["recipe"],
            keyframes=[p["keys"] for p in r["plans"]],
            durations_s=r["durations_s"],
            timing_ms=r.get("timing_ms", {}),
        )

    def _post(self, path: str, prompt: str, n: int, effort: Effort | None, seed: int | None) -> dict[str, Any]:
        body: dict[str, Any] = {"prompt": prompt, "n": n, "seed": random.randrange(2**31) if seed is None else seed}
        if effort or self.effort:
            body["effort"] = effort or self.effort
        request = urllib.request.Request(
            self.url + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                result: dict[str, Any] = json.load(response)
                return result
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except (ValueError, AttributeError):
                pass
            raise MotionGeneratorError(f"{self.url}{path} returned {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            reason = getattr(e, "reason", e)
            raise MotionGeneratorError(f"cannot reach the motion generator at {self.url} ({reason})") from None
