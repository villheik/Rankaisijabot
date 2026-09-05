import random
import sqlite3
import yaml
from discord.ext import commands
from bot.db import DB_PATH

with open("casino.yml", encoding="UTF-8") as f:
    _CONFIG = yaml.safe_load(f)

_STARTING_BALANCE = _CONFIG["starting_balance"]
_LOAN_MAX = _CONFIG["loan"]["max_amount"]
_LOAN_INTEREST = _CONFIG["loan"]["interest_rate"]
_LUCK_MAX = _CONFIG["luck"]["max_level"]
_LUCK_COST_BASE = _CONFIG["luck"]["cost_base"]
_AUTO_COLLECT_THRESHOLD = _CONFIG["auto_collect_threshold"]
_SYMBOLS = _CONFIG["symbols"]

_NORMAL_SYMBOLS = [s for s in _SYMBOLS if not s.get("last_reel_only")]
_LUCK_SYMBOLS = [s for s in _SYMBOLS if s.get("lucky") or s.get("bomb")]


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


def _spin(luck=0):
    def ew(s):
        return max(0.0, s["weight"] + luck * s.get("luck_weight_scale", 0))

    normal_weights = [ew(s) for s in _NORMAL_SYMBOLS]
    all_weights = [ew(s) for s in _SYMBOLS]
    reels = [random.choices(_NORMAL_SYMBOLS, weights=normal_weights, k=3) for _ in range(2)]
    reels.append(random.choices(_SYMBOLS, weights=all_weights, k=3))
    return reels


def _has_bomb(grid):
    return any(grid[reel][row].get("bomb") for reel in range(3) for row in range(3))


def _check_line(grid, payline):
    s1 = grid[payline[0][0]][payline[0][1]]
    s2 = grid[payline[1][0]][payline[1][1]]
    s3 = grid[payline[2][0]][payline[2][1]]

    # 3oaK
    if s1["name"] == s2["name"] == s3["name"]:
        return s1.get("payout", 0)

    # 2+wild: tähti viimeisenä (reel 2), kaksi samaa edessä, ei cherry-symboli
    if s3.get("wild") and s1["name"] == s2["name"] and not s1.get("cherry"):
        return s1.get("two_plus_wild_payout", 0)

    # Kirsikka/mansikka — luetaan vasemmalta oikealle
    if s1.get("cherry"):
        if s2.get("cherry"):
            # 3 kirsikkaa jo käsitelty 3oaK:ssa
            if s3.get("cherry_sub"):
                return s1["payout"]                      # 2 kirsikka + mansikka
            return s1["partial_payouts"].get(2, 0)       # 2 kirsikka + muu
        return s1["partial_payouts"].get(1, 0)           # 1 kirsikka

    # Mansikka yksin (s1 ei ole kirsikka)
    if s3.get("cherry_sub"):
        return s3["payout"]

    # Lucky symbol partial (s1 on luck-symboli, ei 3oaK tai wild-combo)
    if s1.get("lucky"):
        if s2.get("name") == s1["name"]:
            return s1.get("partial_payouts", {}).get(2, 0)
        return s1.get("partial_payouts", {}).get(1, 0)

    return 0


def _calculate_winnings(grid, per_line_bet):
    line_wins = [
        per_line_bet * _check_line(grid, line)
        for line in _PAYLINES
    ]
    winning = [w for w in line_wins if w > 0]
    if not winning:
        return 0, []
    total = sum(winning)
    winning_lines = [i + 1 for i, w in enumerate(line_wins) if w > 0]
    return total, winning_lines


def _ensure_balance(conn, user_id, guild_id):
    exists = conn.execute(
        "SELECT 1 FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if exists is None:
        conn.execute(
            "INSERT INTO casino_balance (user_id, guild_id, balance, debt, pending_winnings, luck) VALUES (?, ?, ?, 0, 0, 0)",
            (user_id, guild_id, _STARTING_BALANCE),
        )
        conn.commit()


def _db_get_or_create(user_id, guild_id):
    conn = sqlite3.connect(DB_PATH)
    _ensure_balance(conn, user_id, guild_id)
    row = conn.execute(
        "SELECT balance, debt, pending_winnings, luck FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    conn.close()
    return row


def _db_slot(user_id, guild_id, per_line_bet):
    total_bet = per_line_bet * 5
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT balance, debt, pending_winnings, luck FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO casino_balance (user_id, guild_id, balance, debt, pending_winnings, luck) VALUES (?, ?, ?, 0, 0, 0)",
            (user_id, guild_id, _STARTING_BALANCE),
        )
        conn.commit()
        balance, debt, pending, luck = _STARTING_BALANCE, 0, 0, 0
    else:
        balance, debt, pending, luck = row

    if pending > 0:
        conn.close()
        return "pending", balance, pending, 0, [], None

    if balance < total_bet:
        conn.close()
        return "broke", balance, 0, 0, [], None

    grid = _spin(luck)

    if _has_bomb(grid):
        conn.execute(
            "UPDATE casino_balance SET balance = ? WHERE user_id = ? AND guild_id = ?",
            (balance - total_bet, user_id, guild_id),
        )
        conn.commit()
        conn.close()
        return "bomb", balance - total_bet, 0, 0, [], grid

    winnings, winning_lines = _calculate_winnings(grid, per_line_bet)

    if winnings > 0:
        conn.execute(
            "UPDATE casino_balance SET balance = ?, pending_winnings = ? WHERE user_id = ? AND guild_id = ?",
            (balance - total_bet, winnings, user_id, guild_id),
        )
        conn.commit()
        conn.close()
        return "win", balance - total_bet, 0, winnings, winning_lines, grid

    conn.execute(
        "UPDATE casino_balance SET balance = ? WHERE user_id = ? AND guild_id = ?",
        (balance - total_bet, user_id, guild_id),
    )
    conn.commit()
    conn.close()
    return "loss", balance - total_bet, 0, 0, [], grid


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
            "INSERT INTO casino_balance (user_id, guild_id, balance, debt, pending_winnings, luck) VALUES (?, ?, ?, 0, 0, 0)",
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


def _db_buyluck(user_id, guild_id):
    conn = sqlite3.connect(DB_PATH)
    _ensure_balance(conn, user_id, guild_id)
    row = conn.execute(
        "SELECT balance, luck FROM casino_balance WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    balance, luck = row

    if luck >= _LUCK_MAX:
        conn.close()
        return "max", luck, 0, balance

    next_level = luck + 1
    cost = _LUCK_COST_BASE * next_level ** 2

    if balance < cost:
        conn.close()
        return "broke", luck, cost, balance

    new_balance = balance - cost
    conn.execute(
        "UPDATE casino_balance SET balance = ?, luck = ? WHERE user_id = ? AND guild_id = ?",
        (new_balance, next_level, user_id, guild_id),
    )
    conn.commit()
    conn.close()
    return "ok", next_level, cost, new_balance


class _ChannelNotAllowed(commands.CheckFailure):
    pass


def _db_channel_get(guild_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT channel_id FROM casino_allowed_channels WHERE guild_id = ?",
        (guild_id,),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def _db_channel_set(guild_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO casino_allowed_channels (guild_id, channel_id) VALUES (?, ?)",
        (guild_id, channel_id),
    )
    conn.commit()
    conn.close()


def _db_channel_clear(guild_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM casino_allowed_channels WHERE guild_id = ?", (guild_id,))
    conn.commit()
    conn.close()


def _db_channel_is_allowed(guild_id, channel_id):
    return _db_channel_get(guild_id) == channel_id


def _db_work_channel_get(guild_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT channel_id FROM work_allowed_channels WHERE guild_id = ?",
        (guild_id,),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def _luck_symbol_desc(weight):
    if weight < 0.5:
        return "ei vielä näy"
    if weight < 3:
        return "erittäin harvinainen"
    if weight < 8:
        return "harvinainen"
    return "näkyy silloin tällöin"


class Casino(commands.Cog, name="casino"):
    def __init__(self, bot):
        self.bot = bot

    async def _run(self, fn, *args):
        loop = self.bot.loop
        return await loop.run_in_executor(None, lambda: fn(*args))

    async def cog_check(self, ctx):
        if ctx.command.name == "casinochannel":
            return True
        if ctx.command.name in ("balance", "bal"):
            casino_ok = await self._run(_db_channel_is_allowed, ctx.guild.id, ctx.channel.id)
            work_ok = await self._run(
                lambda: _db_work_channel_get(ctx.guild.id) == ctx.channel.id
            )
            if not (casino_ok or work_ok):
                raise _ChannelNotAllowed()
            return True
        allowed = await self._run(_db_channel_is_allowed, ctx.guild.id, ctx.channel.id)
        if not allowed:
            raise _ChannelNotAllowed()
        return True

    async def cog_command_error(self, ctx, error):
        if isinstance(error, _ChannelNotAllowed):
            channel_id = await self._run(_db_channel_get, ctx.guild.id)
            if channel_id:
                await ctx.send(f"Kasino on kiinni. Mene uhkapelaamaan: <#{channel_id}>")
            else:
                await ctx.send("Kasino on kiinni.")

    @commands.command(name="casinochannel", help="Aseta/poista tämä kanava kasino-kanavaksi. Vaatii manage_guild.")
    @commands.has_permissions(manage_guild=True)
    async def casinochannel(self, ctx):
        current = await self._run(_db_channel_get, ctx.guild.id)
        if current == ctx.channel.id:
            await self._run(_db_channel_clear, ctx.guild.id)
            await ctx.send("Kasino-kanava poistettu. Kasino on nyt estetty kaikkialla.")
        else:
            await self._run(_db_channel_set, ctx.guild.id, ctx.channel.id)
            await ctx.send(f"Kasino-kanava asetettu: {ctx.channel.mention}")

    @commands.command(name="balance", aliases=["bal"], help="Näytä oma saldo ja velkatilanne.")
    async def balance(self, ctx):
        balance, debt, pending, luck = await self._run(_db_get_or_create, ctx.author.id, ctx.guild.id)
        msg = f"**{ctx.author.display_name}** — {balance} \U0001fa99"
        if luck > 0:
            msg += f" | Luck: {luck}"
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
        if total_bet != bet_int:
            await ctx.send(f"Panos pyöristetty {total_bet} \U0001fa99:ään ({per_line_bet} per linja).")

        status, balance, pending, winnings, winning_lines, grid = await self._run(
            _db_slot, ctx.author.id, ctx.guild.id, per_line_bet
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

        grid_rows = [
            " ".join(grid[reel][row]["emoji"] for reel in range(3))
            for row in range(3)
        ]
        await ctx.send("\n".join(grid_rows))

        if status == "bomb":
            await ctx.send(f"💣 Pommi! Ei voittoa. Saldo: {balance} \U0001fa99.")
        elif status == "win":
            lines_str = ", ".join(f"linja {l} {_LINE_DESC[l]}" for l in winning_lines)
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

    @commands.command(name="luck", help="Näytä luck-tasosi ja sen vaikutus.")
    async def luck_cmd(self, ctx):
        balance, debt, pending, luck = await self._run(_db_get_or_create, ctx.author.id, ctx.guild.id)
        next_cost = _LUCK_COST_BASE * (luck + 1) ** 2 if luck < _LUCK_MAX else None

        lines = [f"**Luck-taso: {luck}/{_LUCK_MAX}**\n"]
        for s in _LUCK_SYMBOLS:
            weight = luck * s.get("luck_weight_scale", 0)
            desc = _luck_symbol_desc(weight)
            lines.append(f"{s['emoji']} {s['name']} — paino {weight:.1f} ({desc})")

        if next_cost is not None:
            lines.append(f"\nSeuraava taso ({luck + 1}): {next_cost} \U0001fa99 | `!buyluck`")
        else:
            lines.append("\nMaksimitaso saavutettu!")

        await ctx.send("\n".join(lines))

    @commands.command(name="buyluck", help="Osta seuraava luck-taso.")
    async def buyluck(self, ctx):
        status, luck, cost, balance = await self._run(_db_buyluck, ctx.author.id, ctx.guild.id)

        if status == "max":
            await ctx.send(f"Olet jo maksimitasolla ({luck}). Ei korkeammalle päästä.")
        elif status == "broke":
            await ctx.send(
                f"Ei riitä. Tason {luck + 1} hinta on {cost} \U0001fa99, "
                f"saldosi on {balance} \U0001fa99."
            )
        else:
            await ctx.send(
                f"Luck nostettu tasolle **{luck}**! (−{cost} \U0001fa99) "
                f"Saldo: {balance} \U0001fa99."
            )


async def setup(bot):
    await bot.add_cog(Casino(bot))
