# Contributing / Wspolpraca

**EN:** Contributions welcome. Open an issue to discuss before submitting large PRs.

**PL:** Zapraszamy do wspolpracy. Otworz issue przed zgloszeniem duzych PR.

## Development Setup / Konfiguracja deweloperska

```bash
git clone https://github.com/parapet-ai/parapet.git
cd parapet
python3 -m venv .venv && source .venv/bin/activate
pip install -r agent/requirements.txt
pip install -r web-ui/requirements.txt
```

## Running Tests / Uruchamianie testow

```bash
# Unit tests
python3 -m pytest tests/ -v

# PowerShell integration tests (Windows)
pwsh -File tests/test-ssdlc.ps1
```

## Code Style / Styl kodu

- Python: follow PEP 8
- PowerShell: use `Set-StrictMode -Version Latest`
- Security-sensitive code must include inline threat comments

## License / Licencja

By contributing, you agree your code will be licensed under the MIT License. See [LICENSE](LICENSE).
