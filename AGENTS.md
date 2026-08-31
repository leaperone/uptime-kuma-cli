# Project: uptime-kuma-cli

CLI tool for managing Uptime Kuma monitors, built with typer + rich + uptime-kuma-api.

## Tech Stack

- Python >= 3.13
- Package manager: uv
- CLI framework: typer
- Output formatting: rich
- API client: uptime-kuma-api

## Project Structure

- `main.py` - All CLI commands (info, list, get, add, edit, delete, pause, resume)
- `pyproject.toml` - Project config and dependencies
- `.github/workflows/publish.yml` - GitHub Actions for PyPI publishing

## Publishing

Uses PyPI Trusted Publishers (no token needed in CI).

### Release process

1. Update version in `pyproject.toml`
2. Commit and push
3. Create a GitHub Release: `gh release create v<version>`
4. GitHub Actions automatically builds and publishes to PyPI

### Manual publish

```bash
source .env && uv publish --token "$UV_PUBLISH_TOKEN"
```

## Links

- GitHub: https://github.com/leaperone/uptime-kuma-cli
- PyPI: https://pypi.org/project/uptime-kuma-cli/
