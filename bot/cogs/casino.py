import random
import datetime
import sqlite3
import yaml
from discord.ext import commands, tasks
from bot.db import DB_PATH

with open("casino.yml", encoding="UTF-8") as f:
    _CONFIG = yaml.safe_load(f)

_STARTING_BALANCE = _CONFIG["starting_balance"]
_LOAN_MAX = _CONFIG["loan"]["max_amount"]
_LOAN_INTEREST = _CONFIG["loan"]["interest_rate"]
_SYMBOLS = _CONFIG["symbols"]
_WEIGHTS = [s["weight"] for s in _SYMBOLS]
_JOBS = {j["name"]: j for j in _CONFIG["jobs"]}
_PARTIAL_SYMBOLS = [s for s in _SYMBOLS if s.get("partial_payouts")]

def _fmt_duration(hours):
    if hours < 1:
        return f"{int(hours * 60)}min"
    return f"{int(hours)}h"


_WORK_HELP = "Ansaitse kolikoita töitä tekemällä.\n\nTyölajit:\n" + "\n".join(
    f"  !work {j['name']:<12} — {j['payout']} \U0001fa99 (cooldown {_fmt_duration(j['cooldown_hours'])})"
    for j in _CONFIG["jobs"]
)


# grid[reel][row], reel=0..2 (vasen→oikea), row=0..2 (ylä→ala)
# Linjojen järjestys alkuperäisen Tuplapotin mukaan:
# 1=keskirivi, 2=alariivi, 3=yläriivi, 4=diag ↗, 5=diag ↘
_ROW_LABEL = ["3️⃣", "1️⃣", "2️⃣"]  # rivin emoji-numero (ylä=L3, keski=L1, ala=L2)
_LINE_DESC = {1: "keskirivi", 2: "alarivi", 3: "ylärivi", 4: "↗", 5: "↘"}
_PAYLINES = [
    [(0, 1), (1, 1), (2, 1)],  # linja 1: keskirivi
    [(0, 2), (1, 2), (2, 2)],  # linja 2: alariivi
    [(0, 0), (1, 0), (2, 0)],  # linja 3: yläriivi
    [(0, 2), (1, 1), (2, 0)],  # linja 4: diagonaali ↗
    [(0, 0), (1, 1), (2, 2)],  # linja 5: diagonaali ↘
]


def _spin():
    # Palauttaa grid[reel][row] — jokainen ruutu pyörähtää erikseen
    return [random.choices(_SYMBOLS, weights=_WEIGHTS, k=3) for _ in range(3)]


def _check_line(grid, payline):
    symbols = [grid[reel][row] for reel, row in payline]
    non_wilds = [s for s in symbols if not s.get("wild")]

    # 3-of-a-kind (wilit korvaavat)
    if not non_wilds:
        return symbols[0]["payout"]
    if len(set(s["name"] for s in non_wilds)) == 1:
        return non_wilds[0]["payout"]

    # Osittaisvoitot (vain oikeat symbolit, ei wiliä) — kirsikka ennen mansikkaa
    for sym in _PARTIAL_SYMBOLS:
        count = sum(1 for s in symbols if s["name"] == sym["name"])
        payout = sym["partial_payouts"].get(count)
        if payout:
            return payout

    return 0


def _calculate_winnings(grid, per_line_bet):
    line_wins = [
        per_line_bet * _check_line(grid, line)
        for line in _PAYLINES
    ]
    winning = [w for w in line_wins if w > 0]
    if not winning:
        return 0, []
    # Suurin voitto × voittavien linjojen määrä
    total = max(winning) * len(winning)
    winning_lines = [i + 1 for i, w in enumerate(line_wins) if w > 0]
    return total, winning_lines


def _ensure_balance(conn, user_id, guild_id):
    exists = conn.execute(
        "SELECT 1 FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if exists is None:
        conn.execute(
            "INSERT INTO casino_balance (user_id, guild_id, balance, debt, pending_winnings) VALUES (?, ?, ?, 0, 0)",
            (user_id, guild_id, _STARTING_BALANCE),
        )
        conn.commit()


def _db_get_or_create(user_id, guild_id):
    conn = sqlite3.connect(DB_PATH)
    _ensure_balance(conn, user_id, guild_id)
    row = conn.execute(
        "SELECT balance, debt, pending_winnings FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    conn.close()
    return row


def _db_slot(user_id, guild_id, per_line_bet, grid):
    total_bet = per_line_bet * 5
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT balance, debt, pending_winnings FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO casino_balance (user_id, guild_id, balance, debt, pending_winnings) VALUES (?, ?, ?, 0, 0)",
            (user_id, guild_id, _STARTING_BALANCE),
        )
        conn.commit()
        balance, debt, pending = _STARTING_BALANCE, 0, 0
    else:
        balance, debt, pending = row

    if pending > 0:
        conn.close()
        return "pending", balance, pending, 0, []

    if balance < total_bet:
        conn.close()
        return "broke", balance, 0, 0, []

    winnings, winning_lines = _calculate_winnings(grid, per_line_bet)
    if winnings > 0:
        conn.execute(
            "UPDATE casino_balance SET balance = ?, pending_winnings = ? WHERE user_id = ? AND guild_id = ?",
            (balance - total_bet, winnings, user_id, guild_id),
        )
        conn.commit()
        conn.close()
        return "win", balance - total_bet, 0, winnings, winning_lines
    else:
        conn.execute(
            "UPDATE casino_balance SET balance = ? WHERE user_id = ? AND guild_id = ?",
            (balance - total_bet, user_id, guild_id),
        )
        conn.commit()
        conn.close()
        return "loss", balance - total_bet, 0, 0, []


def _db_double(user_id, guild_id, tulos):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT balance, debt, pending_winnings FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if row is None or row[2] == 0:
        conn.close()
        return "none", 0, 0
    balance, debt, pending = row
    if tulos == "win":
        doubled = pending * 2
        conn.execute(
            "UPDATE casino_balance SET pending_winnings = ? WHERE user_id = ? AND guild_id = ?",
            (doubled, user_id, guild_id),
        )
        conn.commit()
        conn.close()
        return "win", pending, doubled
    else:
        conn.execute(
            "UPDATE casino_balance SET pending_winnings = 0 WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        conn.commit()
        conn.close()
        return "loss", pending, 0


def _db_collect(user_id, guild_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT balance, debt, pending_winnings FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if row is None or row[2] == 0:
        conn.close()
        return 0, 0, 0, 0
    balance, debt, pending = row
    debt_paid = min(debt, pending)
    new_debt = debt - debt_paid
    new_balance = balance + (pending - debt_paid)
    conn.execute(
        "UPDATE casino_balance SET balance = ?, debt = ?, pending_winnings = 0 WHERE user_id = ? AND guild_id = ?",
        (new_balance, new_debt, user_id, guild_id),
    )
    conn.commit()
    conn.close()
    return pending, debt_paid, new_debt, new_balance


def _db_loan(user_id, guild_id, amount):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT balance, debt, pending_winnings FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO casino_balance (user_id, guild_id, balance, debt, pending_winnings) VALUES (?, ?, ?, 0, 0)",
            (user_id, guild_id, _STARTING_BALANCE),
        )
        conn.commit()
        balance, debt = _STARTING_BALANCE, 0
    else:
        balance, debt = row[0], row[1]

    if debt > 0:
        conn.close()
        return "existing_debt", debt, 0, 0

    interest = int(amount * _LOAN_INTEREST)
    new_debt = amount + interest
    new_balance = balance + amount
    conn.execute(
        "UPDATE casino_balance SET balance = ?, debt = ? WHERE user_id = ? AND guild_id = ?",
        (new_balance, new_debt, user_id, guild_id),
    )
    conn.commit()
    conn.close()
    return "ok", new_debt, interest, new_balance


def _db_work_start(user_id, guild_id, job):
    job_cfg = _JOBS[job]
    now = datetime.datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    _ensure_balance(conn, user_id, guild_id)

    active = conn.execute(
        "SELECT job, finishes_at FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()

    if active is not None:
        active_job, finishes_at_str = active
        finishes_at = datetime.datetime.fromisoformat(finishes_at_str)
        remaining = finishes_at - now
        hours, rem = divmod(max(0, int(remaining.total_seconds())), 3600)
        minutes = rem // 60
        conn.close()
        return "already_working", active_job, hours, minutes

    finishes_at = now + datetime.timedelta(hours=job_cfg["cooldown_hours"])
    conn.execute(
        "INSERT INTO casino_active_job (user_id, guild_id, job, finishes_at) VALUES (?, ?, ?, ?)",
        (user_id, guild_id, job, finishes_at.isoformat()),
    )
    conn.commit()
    conn.close()
    return "started", job, job_cfg["cooldown_hours"], 0


def _db_collect_finished_jobs():
    now = datetime.datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    finished = conn.execute(
        "SELECT user_id, guild_id, job FROM casino_active_job WHERE finishes_at <= ?",
        (now.isoformat(),),
    ).fetchall()
    results = []
    for user_id, guild_id, job in finished:
        job_cfg = _JOBS.get(job)
        conn.execute(
            "DELETE FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        if not job_cfg:
            conn.commit()
            continue
        payout = job_cfg["payout"]
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
        results.append((user_id, guild_id, job, payout, debt_paid, new_debt, new_balance))
    conn.close()
    return results


def _db_work_status(user_id, guild_id):
    now = datetime.datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    _ensure_balance(conn, user_id, guild_id)

    active = conn.execute(
        "SELECT job, finishes_at FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()

    if active is None:
        conn.close()
        return "no_job", None, 0, 0, 0, 0, 0

    job, finishes_at_str = active
    finishes_at = datetime.datetime.fromisoformat(finishes_at_str)

    if now < finishes_at:
        remaining = finishes_at - now
        hours, rem = divmod(int(remaining.total_seconds()), 3600)
        minutes = rem // 60
        conn.close()
        return "working", job, hours, minutes, 0, 0, 0

    # Työ valmis — kerätään palkka
    job_cfg = _JOBS.get(job)
    payout = job_cfg["payout"] if job_cfg else 0
    row = conn.execute(
        "SELECT balance, debt FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    balance, debt = row

    debt_paid = min(debt, payout)
    new_debt = debt - debt_paid
    new_balance = balance + (payout - debt_paid)

    conn.execute(
        "UPDATE casino_balance SET balance = ?, debt = ? WHERE user_id = ? AND guild_id = ?",
        (new_balance, new_debt, user_id, guild_id),
    )
    conn.execute(
        "DELETE FROM casino_active_job WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    conn.commit()
    conn.close()
    return "done", job, payout, debt_paid, new_debt, new_balance, 0


class Casino(commands.Cog, name="casino"):
    def __init__(self, bot):
        self.bot = bot
        self._job_notifier.start()

    def cog_unload(self):
        self._job_notifier.cancel()

    async def _run(self, fn, *args):
        loop = self.bot.loop
        return await loop.run_in_executor(None, lambda: fn(*args))

    @tasks.loop(minutes=1)
    async def _job_notifier(self):
        finished = await self._run(_db_collect_finished_jobs)
        if not finished:
            return
        # Luetaan ilmoituskanava release_config:sta (sama kuin f1/release käyttää)
        channel_id = await self._run(self._get_notify_channel_id)
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if channel is None:
            return
        for user_id, guild_id, job, payout, debt_paid, new_debt, new_balance in finished:
            job_cfg = _JOBS.get(job, {})
            msg = f"<@{user_id}> {job_cfg.get('flavor', f'Työ {job} valmis.')} +{payout} \U0001fa99."
            if debt_paid > 0:
                msg += f" ({debt_paid} \U0001fa99 meni velan lyhennykseen"
                if new_debt > 0:
                    msg += f", velkaa jäljellä {new_debt} \U0001fa99"
                msg += ".)"
            msg += f" Saldo: {new_balance} \U0001fa99."
            await channel.send(msg)

    @staticmethod
    def _get_notify_channel_id():
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT value FROM release_config WHERE key = 'channel_id'"
        ).fetchone()
        conn.close()
        return int(row[0]) if row else None

    @_job_notifier.before_loop
    async def _before_notifier(self):
        await self.bot.wait_until_ready()

    @commands.command(name="balance", aliases=["bal"], help="Näytä oma saldo ja velkatilanne.")
    async def balance(self, ctx):
        balance, debt, pending = await self._run(_db_get_or_create, ctx.author.id, ctx.guild.id)
        msg = f"**{ctx.author.display_name}** — {balance} \U0001fa99"
        if pending > 0:
            msg += f" | Odottaa: {pending} \U0001fa99"
        if debt > 0:
            msg += f" | Velka: {debt} \U0001fa99"
        await ctx.send(msg)

    @commands.command(
        name="slot",
        aliases=["slots"],
        help="Pyöritä slottia. Panos jaetaan tasan 5 linjalle (minimi 5 \U0001fa99).\n\nKäyttö: `!slot <panos>`",
    )
    async def slot(self, ctx, bet: str = None):
        try:
            bet_int = int(bet) if bet is not None else None
        except ValueError:
            await ctx.send("Käyttö: `!slot <panos per linja>` (5 linjaa, yhteensä panos × 5)")
            return

        if bet_int is None or bet_int < 5:
            await ctx.send("Käyttö: `!slot <panos>` (jaetaan tasan 5 linjalle, minimi 5 \U0001fa99)")
            return

        per_line_bet = bet_int // 5
        total_bet = per_line_bet * 5
        grid = _spin()
        if total_bet != bet_int:
            await ctx.send(f"Panos pyöristetty {total_bet} \U0001fa99:ään ({per_line_bet} per linja).")
        status, balance, pending, winnings, winning_lines = await self._run(
            _db_slot, ctx.author.id, ctx.guild.id, per_line_bet, grid
        )

        if status == "pending":
            await ctx.send(
                f"Sinulla on {pending} \U0001fa99 odottamassa. "
                f"Ota ulos (`!collect`) tai tuplaa (`!double kruuna/klaava`)."
            )
            return
        if status == "broke":
            await ctx.send(
                f"Ei riitä kolikoita. Saldosi on {balance} \U0001fa99 "
                f"(tarvitaan {per_line_bet * 5} \U0001fa99)."
            )
            return

        # Ruudukko omana viestinään (pelkkiä emojeja → jumbo-koko Discordissa)
        grid_rows = [
            " ".join(grid[reel][row]["emoji"] for reel in range(3))
            for row in range(3)
        ]
        await ctx.send("\n".join(grid_rows))

        if status == "win":
            lines_str = ", ".join(
                f"linja {l} {_LINE_DESC[l]}" for l in winning_lines
            )
            await ctx.send(
                f"**Voitit {winnings} \U0001fa99!** ({lines_str})\n"
                f"Tuplaa (`!double kruuna/klaava`) tai ota ulos (`!collect`)."
            )
        else:
            await ctx.send(f"Ei voittoa. Saldo: {balance} \U0001fa99.")

    @commands.command(
        name="double",
        aliases=["dbl"],
        help="Tuplaa odottavat voitot arvaamalla kruuna tai klaava.\n\nKäyttö: `!double kruuna` tai `!double klaava`",
    )
    async def double(self, ctx, valinta: str = None):
        if valinta not in ("kruuna", "klaava"):
            await ctx.send("Käyttö: `!double kruuna` tai `!double klaava`")
            return

        tulos_kolikko = random.choice(["kruuna", "klaava"])
        db_tulos = "win" if valinta == tulos_kolikko else "loss"
        status, pending, doubled = await self._run(_db_double, ctx.author.id, ctx.guild.id, db_tulos)

        if status == "none":
            await ctx.send("Ei odottavia voittoja tuplattavaksi.")
        elif status == "win":
            await ctx.send(
                f"**{tulos_kolikko.capitalize()}!** {pending} \U0001fa99 → **{doubled} \U0001fa99**. "
                f"Jatka (`!double kruuna/klaava`) tai ota ulos (`!collect`)."
            )
        else:
            await ctx.send(f"**{tulos_kolikko.capitalize()}!** Hävisit {pending} \U0001fa99.")

    @commands.command(name="collect", aliases=["take"], help="Siirrä odottavat voitot tilille.")
    async def collect(self, ctx):
        pending, debt_paid, new_debt, new_balance = await self._run(
            _db_collect, ctx.author.id, ctx.guild.id
        )

        if pending == 0:
            await ctx.send("Ei odottavia voittoja.")
            return

        msg = f"Tilitetty {pending} \U0001fa99."
        if debt_paid > 0:
            msg += f" ({debt_paid} \U0001fa99 meni velan lyhennykseen"
            if new_debt > 0:
                msg += f", velkaa jäljellä {new_debt} \U0001fa99"
            msg += ".)"
        msg += f" Saldo: {new_balance} \U0001fa99."
        await ctx.send(msg)

    @commands.command(
        name="loan",
        help=f"Ota pikavippi. {int(_LOAN_INTEREST * 100)}% korko, max {_LOAN_MAX} \U0001fa99.\n\nKäyttö: `!loan <summa>`",
    )
    async def loan(self, ctx, amount: str = None):
        try:
            amount_int = int(amount) if amount is not None else None
        except ValueError:
            await ctx.send(
                f"Käyttö: `!loan <summa>` (max {_LOAN_MAX} \U0001fa99, {int(_LOAN_INTEREST * 100)}% korko)"
            )
            return

        if amount_int is None or amount_int <= 0:
            await ctx.send(
                f"Käyttö: `!loan <summa>` (max {_LOAN_MAX} \U0001fa99, {int(_LOAN_INTEREST * 100)}% korko)"
            )
            return

        if amount_int > _LOAN_MAX:
            await ctx.send(f"Maksimi laina on {_LOAN_MAX} \U0001fa99.")
            return

        status, debt, interest, new_balance = await self._run(
            _db_loan, ctx.author.id, ctx.guild.id, amount_int
        )

        if status == "existing_debt":
            await ctx.send(f"Sinulla on jo {debt} \U0001fa99 velkaa. Maksa ensin pois.")
        else:
            await ctx.send(
                f"Pikavippi Paavo nyökkää hyväksyvästi. Sait {amount_int} \U0001fa99. "
                f"Velka: {debt} \U0001fa99 (sis. {interest} \U0001fa99 korkoa). Maksa takaisin tai muuten."
            )

    @commands.command(name="work", help=_WORK_HELP)
    async def work(self, ctx, job: str = None):
        if job is not None and job not in _JOBS:
            lines = "\n".join(
                f"  `!work {j['name']}`  — {j['payout']} \U0001fa99 ({_fmt_duration(j['cooldown_hours'])})"
                for j in _CONFIG["jobs"]
            )
            await ctx.send(f"Tuntematon työlaji. Valitse:\n{lines}")
            return

        if job is not None:
            status, active_job, hours, minutes = await self._run(
                _db_work_start, ctx.author.id, ctx.guild.id, job
            )
            if status == "already_working":
                await ctx.send(
                    f"Olet jo töissä ({active_job}). "
                    f"Valmistuu {hours}h {minutes}min päästä."
                )
            else:
                await ctx.send(
                    f"Lähdit töihin: **{job}**. "
                    f"Valmistuu {_fmt_duration(hours)} päästä. Tule hakemaan palkka sitten (`!work`)."
                )
            return

        # !work ilman argumenttia — tarkista tilanne
        status, active_job, a, b, c, d, _ = await self._run(
            _db_work_status, ctx.author.id, ctx.guild.id
        )

        if status == "no_job":
            lines = "\n".join(
                f"  `!work {j['name']}`  — {j['payout']} \U0001fa99 ({j['cooldown_hours']}h)"
                for j in _CONFIG["jobs"]
            )
            await ctx.send(f"Et ole töissä. Valitse työlaji:\n{lines}")
        elif status == "working":
            hours, minutes = a, b
            await ctx.send(f"Olet töissä ({active_job}). Valmistuu {hours}h {minutes}min päästä.")
        else:
            payout, debt_paid, new_debt, new_balance = a, b, c, d
            msg = _JOBS[active_job]["flavor"] + f" +{payout} \U0001fa99."
            if debt_paid > 0:
                msg += f" ({debt_paid} \U0001fa99 meni velan lyhennykseen"
                if new_debt > 0:
                    msg += f", velkaa jäljellä {new_debt} \U0001fa99"
                msg += ".)"
            msg += f" Saldo: {new_balance} \U0001fa99."
            await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(Casino(bot))
