# Task 004: Engine — World grid & movement (pure Python)

## Description
The 10×10 overworld: deterministic generation from a seed, visible monsters and
treasure at random tiles, a town tile, and step-based movement.

## Files
- `engine/world.py` (create)
- `tests/test_world.py` (create)

## Requirements
1. `World.generate(seed, cfg, cleared)`: builds a `grid_size`×`grid_size` map from
   `random.Random(seed)`. Places: one town tile, `monster_count` monsters, `treasure_count`
   treasures — at distinct random tiles, skipping any coord in `cleared`. Player starts
   at a fixed open tile (e.g. center or 0,0 if open).
2. Tile model: each cell has a type ("empty"/"town"/"monster"/"treasure") + optional payload.
3. `move(direction)` → returns a result: `moved`, `blocked` (out of bounds),
   `monster` (with which monster), `town`, or `treasure` (with reward). Player position updates on `moved`/onto-tile.
4. `cleared` coords (defeated monsters / opened treasure) are not re-placed.
5. Deterministic + pure Python. Commented.

## Acceptance Criteria
- [ ] `pytest tests/test_world.py` passes.
- [ ] Same seed → identical map; coords in `cleared` are absent.
- [ ] Moving off the edge returns `blocked`; stepping onto a monster tile returns `monster`.
- [ ] Map has exactly one town, `monster_count` monsters, `treasure_count` treasures (minus cleared).

## Dependencies
- Task 003

## Commit Message
feat(engine): 10x10 world grid with seeded generation and movement
