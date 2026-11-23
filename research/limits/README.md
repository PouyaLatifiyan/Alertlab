# Exact decision frontier

Run `python limits/oracle.py` from the manuscript directory. The standard-library calculation writes the three CSVs as exact rational numbers. With NumPy and Matplotlib installed it also regenerates `causal_frontier.pdf`. All calculations are deterministic.

The code first enumerates 676 prefix-free stopping trees through epoch three, computes the randomized upper hull in rational arithmetic, then checks each hull segment with a separate finite-horizon Bellman support-function calculation. For every reported budget it also computes the fractional likelihood-ratio full-history upper bound and asserts candidate power ≤ exact admissible power ≤ relaxed power. In this specified mission timely action succeeds with independent probability 9/10. Optimal hazard is therefore exactly one minus 9/10 times optimal timely power. The enumeration uses the same observation channel and no advance knowledge of the mode for every policy.
