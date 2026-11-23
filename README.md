# ALERT Lab

ALERT Lab is a static research application for **A Unified Mathematical Framework for Evaluating Detection Reliability, Alert Timeliness, and Safety in Dynamical Systems**, by Pouya Latifiyan and Yanhong Kou. It evaluates existing monitor–response policies across complete missions. It reports feasible, infeasible and unresolved candidates against explicit mission budgets.

## Run and test

Install Node.js 24 and run:

```sh
npm ci
npm run dev
npm test
PAGES_BASE=/alert-integrity-framework/ npm run build
npx playwright install --with-deps chromium
npm run test:browser
```

For an existing Chromium executable, set `CHROMIUM_PATH` when running the browser tests. To serve the included project-subpath build locally, run `node scripts/serve-production.mjs` and open [the local project entry point](http://127.0.0.1:4173/alert-integrity-framework/). For a root-hosted build run `npm run build` and `npm run preview`.

## Publish on GitHub Pages

1. Create a **new** repository named `alert-integrity-framework`. Use an eligible repository visibility for your GitHub plan. Do not use your personal site repository.
2. On GitHub, open **Settings → Pages → Build and deployment** and select **GitHub Actions** as the source.
3. From this project's extracted directory, initialize and push the source. Replace OWNER with your GitHub username.

```sh
git init -b main
git add .
git commit -m "Build ALERT Lab research application"
git remote add origin https://github.com/OWNER/alert-integrity-framework.git
git push -u origin main
```

4. Open **Actions → Test and deploy ALERT Lab to GitHub Pages**. After deployment succeeds, use the workflow's deployment URL. For a project site the default is `https://OWNER.github.io/alert-integrity-framework/`. Check `/simulator/` and `/evaluation/` by pasting them into a fresh browser tab and refreshing.
5. If Pages is enabled after the first push, rerun the workflow from the Actions tab. Each known route has its own static entry point, and the production base path comes from the Pages configuration.

[GitHub Pages custom-workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## Reproduce the data

Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0 and Matplotlib 3.10.8 reproduce the supplied numerical workflow. Use an isolated environment and run from the repository root.

```sh
python -m pip install -r requirements-research.txt
python research/bench/run.py
python research/bench/envelope.py
python research/bench/compare_selection.py
python research/limits/oracle.py
python research/analysis/verify.py
python scripts/export_paper.py
python scripts/export_delays.py
python scripts/reference_fixture.py
npm test
```

Run the off-browser transport and field workflows from `research/` as described in `research/analysis/validation.md`, `research/limits/README.md`, and `research/recorded/README.md`. The receiver record archives are external inputs. The browser imports recorded summaries from the frozen package. See [VALIDATION.md](VALIDATION.md) for numerical checks, limitations and the manuscript links.

## Architecture

| Module | Responsibility |
| --- | --- |
| `src/engine.ts` | Seeded trajectory and observation generation, Python-equivalent monitor scores, exploratory and benchmark response dynamics and mission outcomes |
| `src/statistics.ts` | Clopper–Pearson inversion, simultaneous-interval decision rule, feasible sets, paired excess bounds and Pareto elimination |
| `src/imports.ts` | CSV/JSON input, mapped fields, per-mission validation and paired loss aggregation |
| `src/mission.worker.ts` | Paired, replicated exploratory missions off the UI thread |
| `src/visuals.tsx` | Synchronized SVG charts, export and Three.js trajectory rendering |
| `public/data/` | Frozen paper tables, independently regenerated delay summaries and example input contracts |
| `research/` | Supplied Python and data snapshots, original recorded-data instructions, and manuscript bibliography |

The default example scenarios are lightweight measurement-level models. They represent bias, quality degradation and GNSS loss of fixes, or degraded multi-sensor navigation. Their models have no fitted receiver, 5G network, aircraft, or actuator parameters. Browser trials evaluate a specified model law and fixed protection policy. Published results use the held-out complete-mission outputs from the supplied Python source. Files are parsed in the browser and never executed. They remain in the session. Scenario settings persist locally.
