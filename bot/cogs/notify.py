from __future__ import annotations
import sqlite3
import datetime
from discord.ext import commands, tasks
from bot.db import DB_PATH


def _parse_remind_at(args: tuple, now: datetime.datetime | None = None) -> tuple[datetime.datetime, str] | None:
    if now is None:
        now = datetime.datetime.now().astimezone()
    local_tz = now.tzinfo
    now_utc = now.astimezone(datetime.timezone.utc)

    def make_utc(d: datetime.date, t: datetime.time) -> datetime.datetime:
        return datetime.datetime.combine(d, t).replace(tzinfo=local_tz).astimezone(datetime.timezone.utc)

    def parse_time(s: str) -> datetime.time | None:
        try:
            return datetime.datetime.strptime(s, "%H:%M").time()
        except ValueError:
            return None

    def parse_date(s: str) -> datetime.date | None:
        s = s.rstrip(".")
        for fmt in ("%d.%m.%Y", "%d.%m"):
            try:
                d = datetime.datetime.strptime(s, fmt).date()
                if fmt == "%d.%m":
                    d = d.replace(year=now.year)
                return d
            except ValueError:
                continue
        return None

    # <time> <message>
    if len(args) >= 2 and (t := parse_time(args[0])):
        dt = make_utc(now.date(), t)
        if dt <= now_utc:
            dt += datetime.timedelta(days=1)
        return dt, " ".join(args[1:])

    # tomorrow <time> <message>
    if len(args) >= 3 and args[0].lower() == "tomorrow":
        if t := parse_time(args[1]):
            return make_utc(now.date() + datetime.timedelta(days=1), t), " ".join(args[2:])

    # <date> <time> <message>
    if len(args) >= 3 and (d := parse_date(args[0])) and (t := parse_time(args[1])):
        return make_utc(d, t), " ".join(args[2:])

    return None


class Notify(commands.Cog, name="reminders"):
    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = sqlite3.connect(DB_PATH)
        due = conn.execute(
            "SELECT id, user_id, channel_id, message FROM notify_reminders WHERE remind_at <= ?",
            (now_utc,),
        ).fetchall()
        for row_id, user_id, channel_id, message in due:
            conn.execute("DELETE FROM notify_reminders WHERE id = ?", (row_id,))
            conn.commit()
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(f"<@{user_id}> {message}")
        conn.close()

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @commands.command(name="notify", aliases=["remind"])
    async def notify(self, context, *args):
        """Aseta muistutus.

        Muodot:
        !notify 13:30 <viesti>           – seuraavan kerran kun kello on 13:30
        !notify tomorrow 13:30 <viesti>  – huomenna klo 13:30
        !notify 24.7. 13:30 <viesti>     – tiettynä päivämääränä
        !notify 24.7.2026 13:30 <viesti> – tiettynä päivämääränä (eksplisiittinen vuosi)
        """
        result = _parse_remind_at(args)
        if result is None:
            await context.send("Käyttö: `!notify [tomorrow|päivämäärä] <HH:MM> <viesti>`")
            return
        remind_at_utc, message = result
        if not message.strip():
            await context.send("Anna myös muistutusviesti.")
            return
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO notify_reminders (user_id, channel_id, remind_at, message) VALUES (?, ?, ?, ?)",
            (context.author.id, context.channel.id, remind_at_utc.isoformat(), message),
        )
        conn.commit()
        conn.close()
        local_dt = remind_at_utc.astimezone()
        when = f"{local_dt.day}.{local_dt.month}.{local_dt.year} klo {local_dt.strftime('%H:%M')}"
        await context.send(f"Muistutan sinua {when}.")


async def setup(bot):
    await bot.add_cog(Notify(bot))
