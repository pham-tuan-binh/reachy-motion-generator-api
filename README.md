# reachy-motion-generator-api

Turn any text into a Reachy Mini motion. Type "sneezing" or "a cat stalking prey" and get a motion you can play with
[reachy-animation](https://github.com/pham-tuan-binh/reachy-animation).

```bash
pip install git+https://github.com/pham-tuan-binh/reachy-motion-generator-api
```

```python
from reachy_animation import Animator, to_target
from reachy_motion_generator_api import MotionGenerator

gen = MotionGenerator("http://localhost:8001")          # the motion generator server

animator = Animator()
animator.on_pose(lambda pose: robot.set_target(*to_target(pose)))
animator.start()

animator.play(gen.dense("sneezing. You build up and then sneeze loudly."))
```

`dense` waits for the motion (about 0.2–0.8 s) and returns a `Clip`. To keep the robot moving while it waits, give
`play` a function instead, so the request runs in the background:

```python
from functools import partial
animator.play(partial(gen.dense, "startled. A door slams behind you."))
```

## Calls

| call | returns |
|---|---|
| `gen.dense(prompt)` | one `Clip`, ready for `Animator.play` |
| `gen.dense_many(prompt, n)` | `n` variations of the same motion |
| `gen.sparse(prompt)` | a `Plan`: the motion's `idea`, its `recipe` and `keyframes` (faster: no motion is generated) |

Every call takes `effort` and `seed`:

| | |
|---|---|
| `effort="low"` | fastest (~0.15 s) |
| `effort="medium"` | balanced (~0.3 s) |
| `effort="high"` | best motion (~0.8 s), the server's default |
| `seed=None` | a new variation each call (default) |
| `seed=7` | the same result every time |

Set the default once with `MotionGenerator(url, effort="low")`. The URL can also come from the `REACHY_MOTION_API`
environment variable. Errors raise `MotionGeneratorError` with the server's message.

Prompts work best as a word plus one sentence of context: `"proud. You finally solved the puzzle."`

## The server

This is only the client. The motion generator runs on a GPU and serves `POST /generate-dense` and
`POST /generate-sparse`; its models are on Hugging Face:
[27B](https://huggingface.co/binhpham/reachy-mini-motion-planner-27b) (`high`),
[4B](https://huggingface.co/binhpham/reachy-mini-motion-planner-4b) (`medium`),
[0.8B](https://huggingface.co/binhpham/reachy-mini-motion-planner-0.8b) (`low`).

If the server runs on another machine, a Reachy Mini Lite's daemon already uses port 8000 on your computer, so tunnel
the server to another port: `ssh -N -L 8001:localhost:8000 <gpu-machine>`.

## Example

[`examples/robot.py`](examples/robot.py): type prompts in the terminal and the robot performs them.

```bash
uv run --with reachy-mini examples/robot.py --api http://localhost:8001
```

## Develop

```bash
uv sync
uv run pytest && uv run ruff check . && uv run mypy src
```
