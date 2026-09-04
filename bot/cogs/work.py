import datetime
import sqlite3
import yaml
from discord.ext import commands, tasks
from bot.db import DB_PATH

with open("work.yml", encoding="UTF-8") as f:
    _CONFIG = yaml.safe_load(f)

_MIN_HOURS = _CONFIG["work"]["min_hours"]
_XP_LEVEL_MULTIPLIER = _CONFIG["work"]["xp_level_multiplier"]
_LEVELS = _CONFIG["levels"]
_MAX_LEVEL = len(_LEVELS) + 1
_JOBS = {j["name"]: j for j in _CONFIG["jobs"]}

_XP_THRESHOLDS = []
_cumulative = 0
for _lvl in _LEVELS:
    _cumulative += _lvl["xp_required"]
    _XP_THRESHOLDS.append(_cumulative)



def _level_from_xp(xp: float) -> int:
    level = 1
    for i, threshold in enumerate(_XP_THRESHOLDS):
        if xp >= threshold:
            level = i + 2
        else:
            break
    return min(level, _MAX_LEVEL)


def _multiplier(level: int) -> int:
    return 2 ** (level - 1)


def _actual_hours(base_hours: float, level: int) -> float:
    return max(_MIN_HOURS, base_hours / _multiplier(level))


def _fmt_duration(hours: float) -> str:
    if hours < 1 / 60:
        return f"{int(hours * 3600)}s"
    if hours < 1:
        return f"{round(hours * 60)}min"
    h = int(hours)
    m = int((hours - h) * 60)
    if m == 0:
        return f"{h}h"
    return f"{h}h {m}min"


def _db_get_xp(user_id, guild_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT xp FROM work_xp WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    conn.close()
    xp = row[0] if row else 0.0
    return xp, _level_from_xp(xp)


def _db_add_xp(user_id, guild_id, xp_gain: float):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT xp FROM work_xp WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    old_xp = row[0] if row else 0.0
    new_xp = old_xp + xp_gain
    old_level = _level_from_xp(old_xp)
    new_level = _level_from_xp(new_xp)
    conn.execute(
        "INSERT OR REPLACE INTO work_xp (user_id, guild_id, xp) VALUES (?, ?, ?)",
        (user_id, guild_id, new_xp),
    )
    conn.commit()
    conn.close()
    return new_xp, new_level, new_level > old_level


def _db_work_start(user_id, guild_id, job_name):
    job = _JOBS.get(job_name)
    if job is None:
        return "unknown", None, None

    xp, level = _db_get_xp(user_id, guild_id)
    actual = _actual_hours(job["base_hours"], level)

    if actual > 24.0:
        return "too_inexperienced", job, actual

    now = datetime.datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    active = conn.execute(
        "SELECT job, finishes_at FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()

    if active is not None:
        active_job, finishes_at_str = active
        finishes_at = datetime.datetime.fromisoformat(finishes_at_str)
        remaining = (finishes_at - now).total_seconds() / 3600
        conn.close()
        return "already_working", _JOBS.get(active_job, {"name": active_job}), remaining

    finishes_at = now + datetime.timedelta(hours=actual)
    conn.execute(
        "INSERT INTO casino_active_job (user_id, guild_id, job, finishes_at) VALUES (?, ?, ?, ?)",
        (user_id, guild_id, job_name, finishes_at.isoformat()),
    )
    conn.commit()
    conn.close()
    return "started", job, actual


def _db_work_status(user_id, guild_id):
    now = datetime.datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    active = conn.execute(
        "SELECT job, finishes_at FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    conn.close()
    if active is None:
        return "no_job", None, None
    job_name, finishes_at_str = active
    finishes_at = datetime.datetime.fromisoformat(finishes_at_str)
    if now < finishes_at:
        remaining = (finishes_at - now).total_seconds() / 3600
        return "working", job_name, remaining
    return "ready", job_name, None


def _db_work_quit(user_id, guild_id):
    conn = sqlite3.connect(DB_PATH)
    active = conn.execute(
        "SELECT job FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if active is None:
        conn.close()
        return None
    conn.execute(
        "DELETE FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    conn.commit()
    conn.close()
    return active[0]


def _db_collect_finished_jobs():
    now = datetime.datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    finished = conn.execute(
        "SELECT user_id, guild_id, job FROM casino_active_job WHERE finishes_at <= ?",
        (now.isoformat(),),
    ).fetchall()
    results = []
    for user_id, guild_id, job_name in finished:
        job = _JOBS.get(job_name)
        conn.execute(
            "DELETE FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        if not job:
            conn.commit()
            continue
        payout = job["payout"]
        row = conn.execute(
            "SELECT balance, debt FROM casino_balance WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ).fetchone()
        if row is None:
            conn.commit()
            continue
        balance, debt = row
        debt_paid = min(debt, payout)
        new_debt = debt - debt_paid
        new_balance = balance + (payout - debt_paid)
        conn.execute(
            "UPDATE casino_balance SET balance = ?, debt = ? WHERE user_id = ? AND guild_id = ?",
            (new_balance, new_debt, user_id, guild_id),
        )
        conn.commit()
        results.append((user_id, guild_id, job_name, payout, debt_paid, new_debt, new_balance))
    conn.close()
    return results


def _db_channel_get(guild_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT channel_id FROM work_allowed_channels WHERE guild_id = ?",
        (guild_id,),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def _db_channel_set(guild_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO work_allowed_channels (guild_id, channel_id) VALUES (?, ?)",
        (guild_id, channel_id),
    )
    conn.commit()
    conn.close()


def _db_channel_clear(guild_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM work_allowed_channels WHERE guild_id = ?", (guild_id,))
    conn.commit()
    conn.close()


def _db_channel_is_allowed(guild_id, channel_id):
    return _db_channel_get(guild_id) == channel_id


class _ChannelNotAllowed(commands.CheckFailure):
    pass


class Work(commands.Cog, name="work"):
    def __init__(self, bot):
        self.bot = bot
        self._job_notifier.start()

    def cog_unload(self):
        self._job_notifier.cancel()

    async def _run(self, fn, *args):
        return await self.bot.loop.run_in_executor(None, lambda: fn(*args))

    async def cog_check(self, ctx):
        if ctx.command.name == "workchannel":
            return True
        allowed = await self._run(_db_channel_is_allowed, ctx.guild.id, ctx.channel.id)
        if not allowed:
            raise _ChannelNotAllowed()
        return True

    async def cog_command_error(self, ctx, error):
        if isinstance(error, _ChannelNotAllowed):
            channel_id = await self._run(_db_channel_get, ctx.guild.id)
            if channel_id:
                await ctx.send(f"Työkomennot eivät toimi täällä. Mene: <#{channel_id}>")
            else:
                await ctx.send("Työkomennot eivät ole käytössä tällä serverillä.")

    @tasks.loop(minutes=1)
    async def _job_notifier(self):
        try:
            await self._notifier_tick()
        except Exception as e:
            self.bot.logger.error(f"work: notifier virhe: {e}", exc_info=True)

    async def _notifier_tick(self):
        finished = await self._run(_db_collect_finished_jobs)
        if not finished:
            return
        channel_cache = {}
        for user_id, guild_id, job_name, payout, debt_paid, new_debt, new_balance in finished:
            job = _JOBS.get(job_name, {})
            _, level_at_finish = _db_get_xp(user_id, guild_id)
            xp_gain = job.get("base_hours", 0) * (_XP_LEVEL_MULTIPLIER ** (level_at_finish - 1))
            new_xp, new_level, leveled_up = await self._run(_db_add_xp, user_id, guild_id, xp_gain)

            if guild_id not in channel_cache:
                channel_id = await self._run(_db_channel_get, guild_id)
                channel_cache[guild_id] = self.bot.get_channel(channel_id) if channel_id else None
            channel = channel_cache[guild_id]
            if channel is None:
                continue

            msg = f"<@{user_id}> {job.get('flavor', f'Työ {job_name} valmis.')} +{payout} \U0001fa99."
            if debt_paid > 0:
                msg += f" ({debt_paid} \U0001fa99 meni velan lyhennykseen"
                if new_debt > 0:
                    msg += f", velkaa jäljellä {new_debt} \U0001fa99"
                msg += ".)"
            msg += f" Saldo: {new_balance} \U0001fa99."
            if leveled_up:
                msg += f"\n🎉 **Nousit tasolle {new_level}!** Töiden nopeus: {_multiplier(new_level)}×"
            await channel.send(msg)

    @_job_notifier.before_loop
    async def _before_notifier(self):
        await self.bot.wait_until_ready()

    def _build_job_list(self, level: int) -> str:
        at_min = [j for j in _CONFIG["jobs"] if _actual_hours(j["base_hours"], level) <= _MIN_HOURS]
        best_min = max(at_min, key=lambda j: j["payout"]) if at_min else None

        lines = []
        for job in _CONFIG["jobs"]:
            actual = _actual_hours(job["base_hours"], level)
            if actual <= _MIN_HOURS:
                if job is not best_min:
                    continue
            available = actual <= 24.0
            icon = "✅" if available else "🔒"
            lines.append(
                f"{icon} `{job['name']:<12}` {_fmt_duration(actual):<10} {job['payout']:>9} \U0001fa99"
            )
        return "\n".join(lines)

    @commands.command(name="workchannel")
    @commands.has_permissions(manage_guild=True)
    async def workchannel(self, ctx):
        current = await self._run(_db_channel_get, ctx.guild.id)
        if current == ctx.channel.id:
            await self._run(_db_channel_clear, ctx.guild.id)
            await ctx.send("Työkanava poistettu. Työkomennot ovat nyt estetty kaikkialla.")
        else:
            await self._run(_db_channel_set, ctx.guild.id, ctx.channel.id)
            await ctx.send(f"Työkanava asetettu: {ctx.channel.mention}")

    @commands.command(name="level", aliases=["rank"])
    async def level(self, ctx):
        xp, level = await self._run(_db_get_xp, ctx.author.id, ctx.guild.id)
        mult = _multiplier(level)
        if level < _MAX_LEVEL:
            xp_needed = _XP_THRESHOLDS[level - 1] - xp
            next_info = f"Seuraavaan tasoon: **{xp_needed:.1f} XP**"
        else:
            next_info = "**Maksimitaso saavutettu.**"
        await ctx.send(
            f"**{ctx.author.display_name}** — Taso **{level}** ({mult}×)\n{next_info}"
        )

    @commands.command(name="worklist")
    async def worklist(self, ctx):
        xp, level = await self._run(_db_get_xp, ctx.author.id, ctx.guild.id)
        mult = _multiplier(level)
        if level < _MAX_LEVEL:
            threshold_idx = level - 1
            xp_needed = _XP_THRESHOLDS[threshold_idx] - xp
            next_info = f" · {xp_needed:.1f} XP seuraavaan tasoon"
        else:
            next_info = " · MAX"
        header = f"**Taso {level} ({mult}×)**{next_info}\n"
        await ctx.send(header + self._build_job_list(level))

    @commands.command(name="work")
    async def work(self, ctx, job: str = None):
        if job is not None:
            job = next((k for k in _JOBS if k.lower() == job.lower()), job)

        if job == "quit":
            quit_job = await self._run(_db_work_quit, ctx.author.id, ctx.guild.id)
            if quit_job is None:
                await ctx.send("Et ole töissä.")
            else:
                job_cfg = _JOBS.get(quit_job, {})
                await ctx.send(
                    f"Lähdit töistä (**{job_cfg.get('name', quit_job)}**) ilman palkkaa."
                )
            return

        if job is not None and job not in _JOBS:
            await ctx.send("Tuntematon työlaji. Katso `!worklist`.")
            return

        if job is not None:
            status, job_data, value = await self._run(
                _db_work_start, ctx.author.id, ctx.guild.id, job
            )
            if status == "unknown":
                await ctx.send("Tuntematon työlaji.")
            elif status == "too_inexperienced":
                _, level = await self._run(_db_get_xp, ctx.author.id, ctx.guild.id)
                await ctx.send(
                    f"Olet liian kokematon. **{job}** kestäisi sinulta {_fmt_duration(value)} "
                    f"(taso {level}, {_multiplier(level)}×)."
                )
            elif status == "already_working":
                await ctx.send(
                    f"Olet jo töissä (**{job_data.get('name', '?')}**). "
                    f"Valmistuu {_fmt_duration(value)} päästä."
                )
            else:
                await ctx.send(
                    f"Lähdit töihin: **{job}**. Valmistuu {_fmt_duration(value)} päästä."
                )
            return

        status, job_name, value = await self._run(_db_work_status, ctx.author.id, ctx.guild.id)
        if status == "working":
            await ctx.send(
                f"Olet töissä (**{job_name}**). Valmistuu {_fmt_duration(value)} päästä."
            )
        elif status == "ready":
            await ctx.send(f"Työ (**{job_name}**) on valmis — palkka maksetaan hetken kuluttua.")
        else:
            xp, level = await self._run(_db_get_xp, ctx.author.id, ctx.guild.id)
            mult = _multiplier(level)
            if level < _MAX_LEVEL:
                xp_needed = _XP_THRESHOLDS[level - 1] - xp
                next_info = f" · {xp_needed:.1f} XP seuraavaan tasoon"
            else:
                next_info = " · MAX"
            header = f"**Taso {level} ({mult}×)**{next_info}\n"
            await ctx.send(header + self._build_job_list(level))


async def setup(bot):
    await bot.add_cog(Work(bot))
