"""Type a prompt, Reachy Mini performs it. The robot keeps breathing while each motion is generated.

uv run --with reachy-mini examples/robot.py --api http://localhost:8001 [--effort low|medium|high]

At the prompt:
  <text>               generate and play (the planner's idea, recipe and timing are printed)
  Enter                replay the last motion
  /again               a new variation of the last prompt
  /many 3              3 variations of the last prompt, played one after another
  /plan <text>         only plan it: print the idea, recipe and keyframes, without moving
  /low /medium /high   switch planner (0.8B fastest, 4B, 27B best)
  /stop                back to idle          /quit (or Ctrl-D)
"""

import argparse
import logging
import sys
import threading

from reachy_animation import Animator, Clip, to_target
from reachy_mini import ReachyMini

from reachy_motion_generator_api import Generation, MotionGenerator, MotionGeneratorError


def show(g: Generation) -> None:
    t = g.timing_ms
    print(
        f"\n  {g.idea}\n  {g.recipe}\n  {len(g.clips)} x {g.clips[0].duration:.1f} s, made in {t.get('total')} ms "
        f"(planner {t.get('planner')}, motion {t.get('generator')}) by {g.effort}\n> ",
        end="",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--api", default=None, help="server URL (default: $REACHY_MOTION_API or http://localhost:8000)"
    )
    parser.add_argument("--effort", choices=["low", "medium", "high"], default="medium")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")  # the animator logs failed requests here
    gen = MotionGenerator(args.api, effort=args.effort)
    last: dict[str, object] = {"prompt": None, "clip": None}

    def generate(prompt: str) -> Clip:
        """Runs on the animator's background thread; the robot keeps breathing meanwhile."""
        g = gen.generate(prompt)
        show(g)
        last.update(prompt=prompt, clip=g.clips[0])
        return g.clips[0]

    def many(prompt: str, n: int) -> None:
        try:
            g = gen.generate(prompt, n)
        except MotionGeneratorError as e:
            print(e)
            return
        show(g)
        for i, clip in enumerate(g.clips):
            animator.play(clip, queue=i > 0)  # the first replaces what is playing, the rest follow

    with ReachyMini(media_backend="no_media") as robot:
        animator = Animator()
        animator.on_pose(lambda pose: robot.set_target(*to_target(pose)))
        animator.start()
        print(__doc__.split("At the prompt:")[1].rstrip() + "\n\n> ", end="", flush=True)
        for raw in sys.stdin:
            line = raw.strip()
            cmd, _, rest = line.partition(" ")
            if cmd in ("/quit", "/exit"):
                break
            elif cmd in ("/low", "/medium", "/high"):
                gen.effort = cmd[1:]  # type: ignore[assignment]
                print(f"  effort: {gen.effort}")
            elif cmd == "/stop":
                animator.stop()
            elif cmd == "/plan" and rest:
                try:
                    p = gen.sparse(rest)
                    print(
                        f"  {p.idea}\n  {p.recipe}\n  {len(p.keyframes[0])} keyframes, {p.durations_s[0]:.1f} s, "
                        f"planned in {p.timing_ms.get('planner')} ms"
                    )
                except MotionGeneratorError as e:
                    print(e)
            elif cmd == "/many" and last["prompt"]:
                threading.Thread(target=many, args=(last["prompt"], int(rest or 3)), daemon=True).start()
            elif cmd == "/again" and last["prompt"]:
                animator.play(lambda: generate(str(last["prompt"])))
            elif line == "" and last["clip"] is not None:
                animator.play(last["clip"])  # type: ignore[arg-type]
            elif line and not line.startswith("/"):
                animator.play(lambda p=line: generate(p))  # type: ignore[misc]
            elif line:
                print("  commands: /again /many N /plan <text> /low /medium /high /stop /quit")
            print("> ", end="", flush=True)
        animator.close()


if __name__ == "__main__":
    main()
