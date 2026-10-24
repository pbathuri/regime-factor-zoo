# Delivery verification — 23 October 2026

The sendable files are `FINAL_WRITEUP.pdf` (six pages), its Markdown source, the three PNGs under `figures/`, and the unsent draft `DRAFT_EMAIL.md`.

## Evidence

- `test_audit.txt`: the requested conda Python command passed 13 tests.
- `test_qiskit_audit.txt`: the requested quantum virtualenv command passed 5 tests.
- `run_report.txt`: fresh `run.py` output, including the retained Gaussian CVaR single-shot miss.
- `scale_sweep_rerun.json`: a full fresh sweep, with only its output path redirected. It is byte-identical to `data/scale_sweep.json`.
- `sweep_comparison.json`: no differing JSON leaves.
- `protected_files_sha256.json`: pre-work SHA-256 values for all four original data JSONs, both tests, and the three Big Red output files. All nine still match.
- `final_checks.json`: all 25 numerical table rows matched their source values at displayed precision; the 7/20 sample-target comparison was independently recomputed.
- All prose numbers were reviewed against JSON, source, or the fresh report by an independent read-only agent. The survival factor was corrected from the existing note's rounded value to 0.9055.
- Both plotting scripts passed Python compilation/AST checks and executed successfully. This folder has no configured lint/typecheck pipeline; ruff, flake8, pyflakes and mypy are absent from the conda environment. No dependencies were installed.
- All three final figures and all six final PDF pages passed visual inspection. The visual verdict is in `.omx/state/final-writeup/ralph-progress.json`.

## Files changed or added

- Added `FINAL_WRITEUP.md`, `FINAL_WRITEUP.pdf`, and `DRAFT_EMAIL.md`.
- Updated `plot_scale.py`: explicit units, dated source captions, simulator labels, CZ-count axis, single-shot markers, and a shared figure-save helper.
- Regenerated `figures/scaling_methods.png` and `figures/scaling_details.png`.
- Added `plot_panel.py` and its sole output, `figures/panel_cvar.png`.
- Added this verification directory and the visual-verdict record. No audited estimator, data file, test or original `.out`/`.err` file was modified. No message was sent.

## Reproduce without modifying the saved data

Run from the Quantum Extension directory. Cache and temporary paths are kept inside this directory.

```sh
mkdir -p .cache/matplotlib .cache/tmp .cache/texmf-var .cache/texmf-config
PYTHONDONTWRITEBYTECODE=1 /opt/miniconda3/bin/python3 test_audit.py
PYTHONDONTWRITEBYTECODE=1 ~/Desktop/quantum/.venv/bin/python test_qiskit_audit.py
PYTHONDONTWRITEBYTECODE=1 ~/Desktop/quantum/.venv/bin/python - <<'PY'
from pathlib import Path
import scale_sweep
scale_sweep.OUT = Path('verification/scale_sweep_rerun.json').resolve()
scale_sweep.main()
assert scale_sweep.OUT.read_bytes() == Path('data/scale_sweep.json').read_bytes()
PY
PYTHONDONTWRITEBYTECODE=1 XDG_CACHE_HOME="$PWD/.cache" MPLCONFIGDIR="$PWD/.cache/matplotlib" /opt/miniconda3/bin/python3 plot_scale.py
PYTHONDONTWRITEBYTECODE=1 XDG_CACHE_HOME="$PWD/.cache" MPLCONFIGDIR="$PWD/.cache/matplotlib" /opt/miniconda3/bin/python3 plot_panel.py
```

The installed TeX format was older than its support files. Building a private format fixed PDF generation without changing the TeX installation:

```sh
PATH="/Users/prady/Library/TinyTeX/bin/universal-darwin:$PATH" TMPDIR="$PWD/.cache/tmp" XDG_CACHE_HOME="$PWD/.cache" TEXMFVAR="$PWD/.cache/texmf-var" TEXMFCONFIG="$PWD/.cache/texmf-config" /Users/prady/Library/TinyTeX/bin/universal-darwin/fmtutil-user --byfmt xelatex
TMPDIR="$PWD/.cache/tmp" XDG_CACHE_HOME="$PWD/.cache" TEXMFVAR="$PWD/.cache/texmf-var" TEXMFCONFIG="$PWD/.cache/texmf-config" pandoc FINAL_WRITEUP.md --pdf-engine=/Users/prady/Library/TinyTeX/bin/universal-darwin/xelatex -o FINAL_WRITEUP.pdf
```

## Limits retained in the write-up

The bars apply to an ideal encoded expectation, not population risk or noisy hardware. Big Red results agree at reporting precision, with a maximum numeric JSON difference of 1.3322676295501878e-15 rather than literal identity. Empirical target conventions, missing delisting returns, unmatched sample windows, and firm–regime pair counts are explicit. No interval-arithmetic certificate or new Evans-function method is claimed.
