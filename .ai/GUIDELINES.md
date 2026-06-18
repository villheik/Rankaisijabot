# AI Development Guidelines

Project-specific conventions for AI-assisted development. Read this before generating code or tests.

---

## Codebase Overview

```
bot/
    __main__.py       — entry point, sets up intents and loads cogs
    rankaisija.py     — Bot subclass, handles cog loading
    constants.py      — reads config.yml via YAMLGetter, exposes typed config classes
    log.py            — logging setup
    cogs/             — one file per feature group
config.yml            — bot configuration (token via env var, cog list, feature settings)
tests/
    conftest.py       — shared pytest fixtures and test data
    test_*.py         — test files per cog
.ai/
    GUIDELINES.md     — this file
```

## Configuration System

Settings live in `config.yml`. The `!ENV` tag reads environment variables at runtime:

```yaml
bot:
    token: !ENV "BOT_TOKEN"   # reads $BOT_TOKEN from environment
    prefix: "!"
```

`bot/constants.py` exposes config as typed Python classes using `YAMLGetter`:

```python
class Bot(metaclass=YAMLGetter):
    section = "bot"
    prefix: str
    token: str
```

To add a new config section:
1. Add it to `config.yml`
2. Add a corresponding class in `constants.py`
3. Import and use via `constants.YourClass.your_value`

## Adding a New Cog

1. Create `bot/cogs/{name}.py`:

```python
from discord.ext import commands

class MyCog(commands.Cog, name="{name}"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mycommand")
    async def my_command(self, context, *, arg: str = None):
        await context.send("response")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

2. Add `{name}` to `config.yml` under `cogs.cogs`

The bot loads all cogs listed in `config.yml` — no other registration needed.

## Python Version

Minimum is **Python 3.9** (matches Dockerfile). Do not use syntax from later versions:

| Avoid (3.10+) | Use instead (3.9 compatible) |
|---------------|------------------------------|
| `int \| None` | `Optional[int]` from `typing` |
| `str \| int`  | `Union[str, int]` from `typing` |

Built-in generics `list[str]`, `dict[str, int]`, `tuple[...]` are fine — these landed in 3.9.

## Blocking Operations

Discord runs on an async event loop. Any blocking call (SQLite query, HTTP request, heavy computation) must be offloaded with `run_in_executor` to prevent blocking the event loop:

```python
loop = context.bot.loop
result = await loop.run_in_executor(None, lambda: blocking_function())
```

Symptoms of a missing `run_in_executor`: log warning "heartbeat blocked for more than 10 seconds".

## GDPR

The bot stores Discord message content and usernames in SQLite for Markov and random search features. This is personal data under GDPR.

Default assumption: data originates from Discord, where users have already accepted Discord's own privacy policy. If someone imports data from an external source, the GDPR implications may differ and should be assessed separately.

Practical mitigations already in place:
- Data is stored locally on a private server, not shared with third parties
- `DELETE FROM messages WHERE username = ?` removes a user's data on request
- `allowed_mentions=discord.AllowedMentions.none()` prevents unintended pings when posting stored content

If the bot is deployed in a non-private or commercial context, a proper GDPR assessment is recommended.

## SQLite

All cogs that need persistence share `/data/markov.db`. The path is defined as a module-level constant `DB_PATH` in each cog that uses it:

```python
DB_PATH = "/data/markov.db"
```

Always open and close a new connection per operation — do not keep long-lived connections.

All queries must filter by `channel_id` — data is channel-specific.

## Posting User Content

When posting content originally written by users, always suppress Discord pings:

```python
await context.send(content, allowed_mentions=discord.AllowedMentions.none())
```

## Code Conventions

- No comments unless the WHY is non-obvious
- Keep cogs self-contained — minimal cross-cog dependencies
- Use `context.bot.loop` for the event loop inside commands, `asyncio.get_event_loop()` in tasks

## Testing Conventions

- Framework: **pytest**
- Test files: `tests/test_{cogname}.py`
- Shared fixtures and test data: `tests/conftest.py`
- For cogs that use SQLite: patch `DB_PATH` using `monkeypatch`, use `tmp_path` for an isolated database
- Test data must be **completely unrelated to the real project** — use fictional names (alice, bob), generic terms, arbitrary IDs
- Group related tests in classes: `class TestFeatureName`
- Run tests: `pytest tests/ -v`

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

## CI/CD Pipeline

- Push to `dev` branch → runs tests → if passing, builds and pushes `:dev` image to ghcr.io
- Publish a GitHub Release → builds and pushes `:latest` image
- Images are multi-platform: `linux/amd64` + `linux/arm64` (Raspberry Pi)
- Bot token is **never** baked into the image — passed at container runtime via `-e BOT_TOKEN=...`
