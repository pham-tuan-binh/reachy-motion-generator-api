"""Type a prompt, Reachy Mini performs it. The robot keeps breathing while each motion is generated.

uv run --with reachy-mini examples/robot.py --api http://localhost:8001 [--effort low|medium|high]
"""

import argparse
import logging
import sys
from functools import partial

from reachy_animation import Animator, to_target
from reachy_mini import ReachyMini

from reachy_motion_generator_api import MotionGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--api", default=None, help="server URL (default: $REACHY_MOTION_API or http://localhost:8000)"
    )
    parser.add_argument("--effort", choices=["low", "medium", "high"], default="medium")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")  # the animator logs failed requests here
    gen = MotionGenerator(args.api, effort=args.effort)

    with ReachyMini(media_backend="no_media") as robot:
        animator = Animator()
        animator.on_pose(lambda pose: robot.set_target(*to_target(pose)))
        animator.start()
        print("Type a prompt and press enter (ctrl-D to quit).")
        for line in sys.stdin:
            if line.strip():
                animator.play(partial(gen.dense, line.strip()))  # generated in the background, then crossfades in
        animator.close()


if __name__ == "__main__":
    main()
