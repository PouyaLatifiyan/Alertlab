# ALERT Lab implementation and validation

The app uses the authors' authoritative 13-page manuscript, mathematical supplement, and Python package. The standalone PDF texts match the corresponding PDFs inside the source package. The app links the supplied originals and bundles the reference Python, frozen data, and bibliographies.

| Source | SHA-256 |
| --- | --- |
| Manuscript | 7f82dd82187d7fe553a9b4086fa7d2bf7a83f2c858c46a08840aa213f2fccdfc |
| Supplement | 416e97777e42ae6b35b2e8a97956d72c451600974ab7d2f9edb7eb6f16985204 |
| Source package | da32f5cb63c5c8e5b843cc44ebcc3d38b9104ab3fb979acb5fdfb3ed5ec4a1ba |

- [Manuscript](https://chatgpt.com/library?file_id=libfile_0ad9e78f860c81918f0715a7e1b34996&account_id=personal)
- [Supplement](https://chatgpt.com/library?file_id=libfile_9c41be4a08fc81919d5e5cfa96e1bea9&account_id=personal)
- [Source package](https://chatgpt.com/library?file_id=libfile_44f1f4edfbe881918d00eb6aaaf62824&account_id=personal)

## Numerical verification

- The TypeScript tests compare the four score recursions to Python epoch by epoch, verify Clopper–Pearson against SciPy including all-event and zero-event endpoints, and reproduce all 144 frozen selector lookups. Deterministic physical draws compare benchmark crossing, opportunity and hazard outputs directly against Python.
- The full frozen benchmark was rerun in an isolated copy. The configuration, coordinate and paired intervals, thresholds, Pareto table, and decision table were byte-identical. Eight class-envelope fields differed by at most 1.12×10⁻¹⁶. The finite stopping tables were byte-identical.
- The provided Python benchmark, decision, coupled-selection and field tests passed. The original independent verifier checked 432 marginal intervals, 144 decisions and 36 class-envelope rows. The occupancy LP agreed with the rational optimum at all five budgets.
- Delay summaries regenerate held-out post-onset, premature and silent outcomes using the original generator and frozen thresholds. Actionable counts plus missed-window counts equal untreated crossing counts in all 144 scenario, monitor and threshold combinations.
- The browser tests serve the actual production build from a project subpath without an SPA history fallback. They exercise direct routes and refreshes, WebGL and chart synchronization, scenario persistence and parameter changes, both data upload formats and malformed input, model-worker results, benchmark decisions and abstention, and mobile and desktop rendering. Desktop and mobile screenshots were inspected.

## Evidence boundaries

- Benchmark recommendations are confidence-qualified decisions over the evaluated candidates under the specified calibration, observations, deadlines, response dynamics and deterministic resource assumptions. State slots count persistent numerical slots under the package's convention. A slot count carries no hardware latency or energy guarantee.
- The physical class envelope applies under the manuscript's model and independence assumptions and at or below the associated false-alert cap. The exact three-epoch causal optimum applies to the explicitly specified observation and policy class.
- The simulated navigation scenarios are exploratory and treat the error limit as a navigation-integrity event. The jamming quality proxy is illustrative. Demonstrations do not estimate event probabilities. Replicated browser trials have model-conditional bounds and use controlled pseudorandom simulations. Neither result establishes deployed RF, navigation, or closed-loop hardware performance.
- TEXBAT and Beihang evidence shows replay-specific timing and discrepancies. The upstream archives were not reacquired for this implementation. The original Python record checks ran against the bundled outputs. No observed action outcomes establish field safety. The Beihang AR alarm remains a reported value from the supplied paper.
- Generic imports use declared units and complete missions. Response labels can be supplied for complex policies independently of the browser's single-action opportunity calculation. Missing safety labels stay unidentified. The app does not infer counterfactual hazard from untreated trajectories.
- The online regret tab shows frozen common-law program outputs. Run the supplied Python program for new transport or capacity models.
- Deployment was validated with a local static server. A public GitHub repository and URL were not created in this session.
