# SeQUeNCe install

- **Project path:** `/Users/alexandrabouillon/Documents/Quantum_Networking/SeQuEnCe`
- **Python:** 3.12.4 (`/usr/local/bin/python3.12`)
- **Install mode:** A — `pip install sequence` (user / PyPI, not editable)
- **Environment:** `.venv` in this directory

## Activate

```bash
cd /Users/alexandrabouillon/Documents/Quantum_Networking/SeQuEnCe
source .venv/bin/activate
```

## Smoke tests that passed

Import:

```bash
python -c "import sequence as sq; print('sequence', getattr(sq, '__version__', 'ok'))"
```

Timeline: `python smoke_test.py` printed `timeline ran` and exited 0.

Optional: `generate-topology linear 2 --memory-size 1 --output two_node.json --directory .` wrote `two_node.json`.

## Package

`pip show sequence`:

- **Name:** sequence
- **Version:** 1.3.1
- **Home-page:** https://github.com/sequence-toolbox/SeQUeNCe
- **Summary:** Simulator of QUantum Network Communication (SeQUeNCe)
