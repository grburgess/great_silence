# Perf pass (Jul 2026)

- Pre-existing logic gap: same-star colonization by two civs never triggers encounters via the _scan_for_encounters path (single-civ_id find_territory_overlaps always returns []). Fixing it would add RNG draws and change seeded results; needs a deliberate decision.
