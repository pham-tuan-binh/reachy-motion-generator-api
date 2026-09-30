# Writing prompts

The planner reads your prompt and decides how Reachy Mini's head, antennas and body should move. It was trained on
prompts like these, so this shape works best:

```
<what to express>. <one sentence of context, usually starting with "You">
```

```
sneezing. You build up and then sneeze loudly.
heartbroken. You just got terrible news.
a cat stalking prey. You crouch low and freeze.
curious. Something catches your eye on your left.
```

## Rules of thumb

1. **Say what to express, not how to move.** "proud. You finally solved the puzzle." works better than "raise your
   head 20 degrees". The planner knows how an emotion looks on this body; that is its job.
2. **Keep it short: a label plus one sentence.** Training prompts are ~13 words. A long paragraph makes the planner
   about twice as slow and the motion is no richer.
3. **A bare word is fine** ("sleepy", "dancing"), but the context sentence gives the motion a situation to act out.
4. **Use intensity words to scale the motion.** "slightly", "a little", "extremely", "utterly" change how big and
   energetic the motion is.
5. **Directions are the robot's own**, as if you were the robot: "on your left" is the robot's left. Use
   `effort="high"` when direction matters: the smaller planners often ignore left vs right.
6. **One moment per prompt.** Motions are usually 3–8 s. A two-step story ("surprised, then happy. A noise startles
   you, then you see it is your friend.") works, but for anything longer, generate one clip per beat and queue them
   (`animator.play(clip, queue=True)`).
7. **Asking for a duration only nudges it.** "for about 15 seconds" gives ~7–8 s, not 15. Queue clips, or use
   `dense_many` for variations, to fill longer stretches.
8. **Stay within what the robot has:** a head that tilts, turns, nods and rises; two antennas ("ears"); a rotating
   body. There are no arms, legs, face or voice. "waving hello" becomes a head-and-ears greeting.
9. **English only**, up to 500 characters.

## Measured

Median over 6 samples on an RTX PRO 6000 server, using the `sparse` plans:

| prompt | effect |
|---|---|
| "slightly …" vs "extremely …" | pitch range 7° → 12–16°, energy 1.5–1.8 → 6 (`medium` and `high`) |
| "on your left" vs "on your right" | `high`: head turns +27° vs −25° (correct). `medium`: +27° for both (direction ignored) |
| no duration vs "for about 15 seconds" | 4.3 → 7.7 s (`medium`), 5.8 → 7.5 s (`high`) |
| one feeling vs a two-step story | 2.7–2.9 s → 3.5–3.8 s, one or two more segments |
| word + context vs a long paragraph | `high` planner 561 → 1030 ms, motion 3.2 → 3.9 s |
| bare word vs word + context | both valid on the first try in every test (192 requests over all three efforts) |

## Choosing `effort`

| | use it for |
|---|---|
| `low` (0.8B, ~0.15 s) | quick, single-feeling reactions: happy, startled, cowering |
| `medium` (4B, ~0.3 s) | most prompts; the best balance |
| `high` (27B, ~0.8 s) | directions, multi-step stories, build-up-and-release events (sneezes, jumps), subtle or unusual prompts |
