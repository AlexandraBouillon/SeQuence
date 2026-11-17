# Install SeQUeNCe in a new project

You are setting up **SeQUeNCe** (Simulator of QUantum Network Communication) in a **new project**. Install only. Do not implement MUERP, routing algorithms, or NetSquid.

Official sources (use these; do not invent flags):

- Repo: https://github.com/sequence-toolbox/SeQUeNCe
- Docs: https://sequence-rtd-tutorial.readthedocs.io/latest/about/requirements/prerequisite.html
- PyPI package name: `sequence` (import as `sequence`)
- Requires **Python 3.12 or later** (PyPI: `>=3.12,<3.15`)

This is the ANL/toolbox quantum-network simulator, not some other `sequence` library. After install, `import sequence as sq` must work.

---

## Before you start — ask, then wait

Ask these questions and **stop**. Do not create directories, venvs, or run `pip` until the human answers.

1. **Where** should the new project live? (absolute path)
2. **Install mode?**
   - **A — user:** `pip install sequence` (default; enough to *use* the API)
   - **B — editable:** clone the GitHub repo and `pip install --editable .` (only if we will change SeQUeNCe internals)
3. **Environment?** `venv` (default on this Mac), `conda`, or `uv`
4. Is **Python 3.12+** already installed, and which binary? (`python3.12`, `python3`, Homebrew, etc.)

If they say “just go” and do not answer, use:

- Path: `Research/Yiming/sequence_sim/` under the Broome repo
- Mode **A**
- `venv`
- Prefer `python3.12`; if missing, locate 3.12–3.14 and report it. **Do not** install on 3.11 or older.

---

## Rules

- One step at a time. If a step fails, **stop**, paste the error, and wait.
- Isolated environment only. Never `pip install sequence` into system Python.
- Do not upgrade pip globally. Do not use `sudo`.
- Do not clone SeQUeNCe unless mode **B** was chosen.
- Do not run the full tutorial notebook unless the smoke test passes.
- After success, write a short `README.md` in the project with how to activate the env and the one-liner that proved the import.

---

## Step 1 — Check Python

```bash
python3.12 --version
```

If that fails, try `python3 --version`. Require 3.12, 3.13, or 3.14. If none, stop and tell the human to install Python 3.12.

---

## Step 2 — Create the project directory

```bash
mkdir -p /ABSOLUTE/PATH/TO/PROJECT
cd /ABSOLUTE/PATH/TO/PROJECT
```

Project should be empty of a competing Python env. If the path already has a `.venv` or `SeQUeNCe/` clone, stop and ask.

---

## Step 3 — Create and activate the environment

**venv (default):**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
which python
```

Confirm `which python` is inside `.venv`.

**conda** (only if chosen):

```bash
conda create -n sequence python=3.12 -y
conda activate sequence
python --version
```

**uv** (only if chosen): follow the SeQUeNCe README uv path; do not mix uv with a pip venv in the same directory.

---

## Step 4 — Install SeQUeNCe

**Mode A (user):**

```bash
python -m pip install --upgrade pip
python -m pip install sequence
```

**Mode B (editable):**

```bash
git clone https://github.com/sequence-toolbox/SeQUeNCe.git
cd SeQUeNCe
python -m pip install --upgrade pip
python -m pip install --editable . --config-settings editable_mode=strict
```

Stay in the venv. If pip tries to pull a package that is not the ANL simulator, stop.

Expected transitive deps (installed automatically; do not pip-install them one-by-one unless the resolver fails): `numpy`, `scipy`, `networkx`, `pandas`, `matplotlib`, `qutip`, `stim`, and others from `pyproject.toml`.

---

## Step 5 — Smoke test the import

From the **project root** (mode A) or anywhere with the venv on (mode B):

```bash
python -c "import sequence as sq; print('sequence', getattr(sq, '__version__', 'ok'))"
```

Must print without traceback. If `ModuleNotFoundError` or you got a different `sequence` package, stop.

---

## Step 6 — Smoke test a timeline

Write `smoke_test.py` in the project root (not inside the cloned repo’s tests unless mode B and you are running theirs):

```python
import sequence as sq

tl = sq.Timeline(1e12)
tl.show_progress = False
tl.init()
tl.run()
print("timeline ran")
```

Run:

```bash
python smoke_test.py
```

Expect `timeline ran` and exit 0. If `Timeline` is missing or the API changed, stop and quote the error; check https://sequence-rtd-tutorial.readthedocs.io/ rather than guessing a new API.

---

## Step 7 — Optional two-node check (only if Step 6 passed)

If `generate-topology` is on PATH (installed with the package):

```bash
generate-topology linear 2 --memory-size 1 --output two_node.json --directory .
```

Do **not** invent CLI flags. If the command is missing, skip this step and note it. Do not debug a full entanglement request unless the human asks; install is done.

---

## Step 8 — Record what you did

In the project `README.md`, list:

- Absolute project path
- Python version
- Mode A or B
- How to activate (`.venv` or conda env name)
- The import one-liner and that `smoke_test.py` passed
- `pip show sequence` name, version, and home page

Also paste `pip show sequence` in the chat.

---

## Done when

- [ ] Questions in “Before you start” were asked (or defaults used because they said “just go”)
- [ ] Python 3.12–3.14 in an isolated env
- [ ] `import sequence as sq` works
- [ ] `smoke_test.py` runs
- [ ] README records activate + versions

Stop there. Do not start MUERP graphs, Algorithms 1–4, or NetSquid.
