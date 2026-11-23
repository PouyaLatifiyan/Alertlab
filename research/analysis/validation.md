# Reproduction and numerical validation

Run the following commands from the directory containing the manuscript source and the bench, case, limits, selection, and analysis directories. Standard Python 3 with NumPy, SciPy and Matplotlib is sufficient for these numerical experiments. The validation environment used Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, and Matplotlib 3.10.8.

```bash
python bench/run.py
python bench/envelope.py
python bench/test_bench.py
python limits/oracle.py
python selection/test_decision.py
python selection/apply.py --scenarios "moderate persistent"
python selection/apply.py --scenarios "moderate persistent" "brief pulse"
python case/latency_transport.py
python case/mission_mix.py
python analysis/verify.py
```

The first two commands regenerate all synthetic scenario tables. The finite-oracle calculation uses rational arithmetic. Its figure and all confidence calculations use standard floating point. The scenario study reserves .05 miscoverage jointly for its 12 regimes, three false-alarm caps, loss coordinates and declared comparisons. The separate historical margin/latency and calibration-integration studies each use their own error budget. Their reported confidence levels do not constitute simultaneous whole-paper coverage.

| Check | Method and observed result |
|---|---|
| Fresh complete rerun | Re-ran all twelve regimes and the physical class bound in an isolated directory. All six CSV tables and design.json were byte-identical to the delivered outputs. Figure binary hashes can depend on PDF timestamps. |
| Nominal bands and feasibility | Recomputed 432 marginal Clopper–Pearson intervals using direct inverse-beta formulas. Passed all 144 lookup decisions through the general selector, checking inner/outer membership, selected policy, uniqueness and excess upper bounds. All matched. |
| Paired and Pareto inference | Enumerated small multinomial outcomes for the separate discordance-rate/orientation interval in selection/; its checks passed. The scenario benchmark uses another valid construction, simultaneous binomial intervals for the two discordance cells. The serialized comparison intervals are the inputs used when reproducing the benchmark decisions. Generic Pareto elimination requires a certified feasible witness, all losses weakly better and at least one strict improvement. The four-way unconstrained operating-point frontier in bench/pareto.csv is an outer set; overlapping uncertainty retains all four at every setting. |
| Admissible physical envelope | Independently approximated the load/threshold integral by numerical quadrature at representative inputs and tested monotonicity and the unavoidable actuator-failure floor for every regime. Confirmed all 36 rows and that every issued class gap is the selected upper bound minus the lower envelope. The implementation flags a lower bound above a selected upper bound rather than reporting zero gap. These are double-precision model bounds, not validated hardware margins. |
| Exact finite oracle | Directly enumerated 676 deterministic stopping-tree policies, then evaluated the exact rational upper hull. A separately coded Bellman dual evaluated the hull supports. A third implementation in analysis/verify.py uses a primal linear program with variables for stop mass along each observable prefix, pathwise resource constraints and a healthy alarm budget. All five new LP solutions agree with the rational optima. |
| Branches and boundary conditions | Unit tests cover a wholly excluded menu, insufficient evidence, unresolved feasible rivals, strict separation, binomial endpoints, paired zero discordance, and symmetry of risk-difference intervals. The per-time scores for CUSUM, GLR and the restart portfolio are also checked against direct segment/component enumeration. |
| Cost convention | A state slot is one persistent numeric value in the specified streaming implementation. Shared sample, time counter, alarm bit, and fixed constants are excluded. Slot counts are not estimates of WCET, peak transient memory, energy, task scheduling jitter, processor utilization or qualification of the vectorized simulator on target hardware. A field selection requiring these quantities must supply independent validated limits. |
| Separate transport and mixture experiments | The transport code checks limiting two-type cases and identity of identical policies under any common coupling. mission_mix.py checks threshold identity before interpreting varying population weights as deployment of one shared frozen configuration. Neither the assumed latency shares nor the mixture fractions were inferred from the Beihang recording. |

The physical reachability bound depends on a sensor noise law independent of nuisance quantities determining the latest useful epoch. Applying it with a deadline selected from the same measurement noise, an adaptive second action, or a receiver whose observations are changed by prior control requires a different proof. The stored statistical comparisons condition on the precomputed calibration design and are valid over the new iid complete-mission draws; their nominal validity does not imply robustness to an arbitrary field population.

## Journal revision extension

Run python selection/test_coupled.py, python case/common_regret.py and python bench/threshold_sensitivity.py. The two-type witness is exactly solvable and has no seed. The sample-size analysis uses the first 500, 1500 and 5000 of the existing paired Gaussian missions and a separate .05 simultaneous error allocation over all three looks and all mission-type cells. The threshold sensitivity study uses 6000 new changed missions per scenario, seed 37601 plus the benchmark scenario index, identical physical draws at each threshold, and .05 error across its 36 marginal physical risks. It does not recertify class gaps at perturbed thresholds. Conditional mean delay uses detected post-onset paths and reports its denominator. See review/result_comparison.csv for the 24 checked frozen table hashes.
