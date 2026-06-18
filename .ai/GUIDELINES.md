# AI Development Guidelines

Project-specific conventions for AI-assisted development. Read this before generating code or tests.

## Project Overview

Discord bot running on Raspberry Pi 4 (arm64) in Docker. Commands use `!` prefix.
New features are added as cogs in `bot/cogs/`. SQLite database at `/data/markov.db` is shared between cogs.

## Tech Stack

- Python 3.9 — see version constraints below
- discord.py 2.x (>=2.4.0, <3.0)
- SQLite for persistence (`/data/markov.db`)
- pytest for testing
- Docker + GitHub Actions CI/CD (linux/amd64 + linux/arm64)

## Python Version

Minimum is **Python 3.9**. Do not use syntax introduced in later versions:

| Avoid | Use instead |
|-------|-------------|
| `int \| None` | `Optional[int]` from `typing` |
| `str \| int` | `Union[str, int]` from `typing` |

Built-in generics like `list[str]`, `dict[str, int]` are fine — PEP 585 landed in 3.9.

## Adding a New Cog

1. Create `bot/cogs/{name}.py` with a class extending `commands.Cog`
2. Add `{name}` to `config.yml` under `cogs.cogs`
3. End the file with `async def setup(bot): await bot.add_cog(YourCog(bot))`

## Code Conventions

- No comments unless the WHY is non-obvious
- Blocking calls (SQLite queries, heavy computation) must use `run_in_executor` to avoid blocking the Discord event loop
- All data is channel-specific — always filter queries by `channel_id`
- When posting user-generated content, always pass `allowed_mentions=discord.AllowedMentions.none()` to prevent unintended pings

## Testing Conventions

- Framework: **pytest**
- Test files: `tests/test_{cogname}.py`
- Shared fixtures and test data: `tests/conftest.py`
- For cogs that use SQLite: patch `DB_PATH` using `monkeypatch` and use `tmp_path` for an isolated temporary database
- Test data must be **completely unrelated to the real project** — use fictional names (alice, bob), generic terms, and arbitrary IDs
- Group related tests in classes: `class TestFeatureName`

### DB test fixture pattern

```python
# tests/conftest.py
@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("bot.cogs.your_cog.DB_PATH", str(db_path))
    conn = sqlite3.connect(str(db_path))
    # create schema + insert test data
    conn.commit()
    conn.close()
    yield  # tmp_path cleans up automatically
```

## CI/CD

- Push to `dev` → builds `:dev` image, runs tests first
- GitHub Release → builds `:latest` image
- Tests must pass before Docker build proceeds
