import datetime
import sqlite3
import aiohttp
from discord.ext import commands, tasks

DB_PATH = "/data/rankaisija.db"
SCHEDULE_URL = "https://api.jolpi.ca/ergast/f1/current.json?limit=100"

SESSION_NAMES = {
    "FirstPractice": "Vapaat harjoitukset 1",
    "SecondPractice": "Vapaat harjoitukset 2",
    "ThirdPractice": "Vapaat harjoitukset 3",
    "SprintShootout": "Sprint-aika-ajot",
    "Sprint": "Sprint-kilpailu",
    "Qualifying": "Aika-ajot",
    "Race": "Kilpailu",
}

ANNOUNCE_SESSIONS = {"SprintShootout", "Sprint", "Qualifying", "Race"}

WEEKDAYS_FI = ["ma", "ti", "ke", "to", "pe", "la", "su"]


def _parse_dt(date_str: str, time_str: str) -> datetime.datetime:
    return datetime.datetime.strptime(
        f"{date_str}T{time_str}", "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.timezone.utc)


def _to_local(utc_dt: datetime.datetime) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(utc_dt.timestamp())


def _format_session(key: str, utc_dt: datetime.datetime) -> str:
    local = _to_local(utc_dt)
    weekday = WEEKDAYS_FI[local.weekday()]
    name = SESSION_NAMES.get(key, key)
    return f"`{weekday} {local.day}.{local.month}. klo {local.strftime('%H:%M')}` — {name}"


def _parse_sessions(race: dict) -> list[tuple[str, datetime.datetime]]:
    sessions = []
    for key in ["FirstPractice", "SecondPractice", "SprintShootout",
                 "ThirdPractice", "Sprint", "Qualifying"]:
        if key in race:
            sessions.append((key, _parse_dt(race[key]["date"], race[key]["time"])))
    sessions.append(("Race", _parse_dt(race["date"], race["time"])))
    return sorted(sessions, key=lambda x: x[1])


def _next_race(races: list, now: datetime.datetime):
    for race in races:
        sessions = _parse_sessions(race)
        remaining = [(k, dt) for k, dt in sessions if dt > now]
        if remaining:
            return race, remaining
    return None


class F1(commands.Cog, name="f1"):
    def __init__(self, bot):
        self.bot = bot
        self._schedule_cache = None
        self._cache_date = None
        self._init_db()
        self.session_reminder.start()

    def cog_unload(self):
        self.session_reminder.cancel()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS f1_announced (
                season INTEGER,
                round INTEGER,
                session TEXT,
                PRIMARY KEY (season, round, session)
            )
        """)
        conn.commit()
        conn.close()

    async def _fetch_schedule(self) -> list:
        today = datetime.date.today()
        if self._cache_date == today and self._schedule_cache is not None:
            return self._schedule_cache
        async with aiohttp.ClientSession() as session:
            async with session.get(SCHEDULE_URL) as resp:
                data = await resp.json(content_type=None)
        races = data["MRData"]["RaceTable"]["Races"]
        self._schedule_cache = races
        self._cache_date = today
        return races

    @commands.command(name="f1")
    async def f1(self, context):
        try:
            races = await self._fetch_schedule()
        except Exception:
            await context.send("Ei saatu F1-aikataulua haettua.")
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        result = _next_race(races, now)

        if result is None:
            await context.send("Ei tulevia F1-kilpailuja tällä kaudella.")
            return

        race, remaining = result
        lines = [
            f"🏎️ **{race['raceName']}** (R{race['round']})",
            f"📍 {race['Circuit']['circuitName']}, {race['Circuit']['Location']['country']}\n",
        ]
        for key, dt in remaining:
            lines.append(_format_session(key, dt))

        await context.send("\n".join(lines))

    @tasks.loop(minutes=1)
    async def session_reminder(self):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT value FROM release_config WHERE key = 'channel_id'"
        ).fetchone()
        conn.close()

        if row is None:
            return

        channel = self.bot.get_channel(int(row[0]))
        if channel is None:
            return

        try:
            races = await self._fetch_schedule()
        except Exception:
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        result = _next_race(races, now)
        if result is None:
            return

        race, remaining = result
        season = int(race["season"])
        round_num = int(race["round"])

        for key, dt in remaining:
            if key not in ANNOUNCE_SESSIONS:
                continue

            minutes_until = (dt - now).total_seconds() / 60
            if 55 <= minutes_until <= 65:
                reminder_key = f"{key}_60"
                message = f"🏎️ **{race['raceName']}** — {SESSION_NAMES[key]} alkaa tunnin kuluttua! (klo {_to_local(dt).strftime('%H:%M')})"
            elif 4 <= minutes_until <= 6:
                reminder_key = f"{key}_5"
                message = f"🏎️ **{race['raceName']}** — {SESSION_NAMES[key]} alkaa 5 minuutin kuluttua!"
            else:
                continue

            conn = sqlite3.connect(DB_PATH)
            already = conn.execute(
                "SELECT 1 FROM f1_announced WHERE season=? AND round=? AND session=?",
                (season, round_num, reminder_key),
            ).fetchone()
            if already:
                conn.close()
                continue

            conn.execute(
                "INSERT OR IGNORE INTO f1_announced VALUES (?, ?, ?)",
                (season, round_num, reminder_key),
            )
            conn.commit()
            conn.close()

            await channel.send(message)

    @session_reminder.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(F1(bot))
