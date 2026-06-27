import sqlite3
import random
import re
import datetime
from typing import Optional
import discord
from discord.ext import commands

_DISCORD_EPOCH_MS = 1420070400000


def _snowflake_to_dt(snowflake_id: int) -> datetime.datetime:
    ms = (snowflake_id >> 22) + _DISCORD_EPOCH_MS
    return datetime.datetime.fromtimestamp(ms / 1000)


def _format_dt(dt: datetime.datetime) -> str:
    return f"{dt.day}.{dt.month}.{dt.year} klo {dt.strftime('%H:%M')}"

DB_PATH = "/data/rankaisija.db"
MENTION_RE = re.compile(r'<@!?(\d+)>')


class RandomMsg(commands.Cog, name="random_msg"):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _build_regex(term: str) -> re.Pattern:
        starts_wild = term.startswith('*')
        ends_wild = term.endswith('*')
        stripped = term.strip('*')
        parts = [re.escape(p) for p in term.split('*')]
        core = r'\w*'.join(parts)
        first_char = stripped[:1]
        last_char = stripped[-1:]
        prefix = '' if starts_wild else (r'\b' if first_char and (first_char.isalnum() or first_char == '_') else '')
        suffix = '' if ends_wild else (r'\b' if last_char and (last_char.isalnum() or last_char == '_') else '')
        return re.compile(rf'{prefix}{core}{suffix}', re.IGNORECASE)

    def _sanitize_mentions(self, content: str, channel_id: int) -> str:
        def replace(match):
            user_id = int(match.group(1))
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute(
                "SELECT username FROM messages WHERE user_id = ? AND channel_id = ? LIMIT 1",
                (user_id, channel_id),
            ).fetchone()
            conn.close()
            return f'@{row[0]}' if row else f'@{user_id}'
        return MENTION_RE.sub(replace, content)

    def _resolve_user_id(self, target: str, channel_id: int) -> Optional[int]:
        conn = sqlite3.connect(DB_PATH)
        nick_row = conn.execute(
            "SELECT username FROM nicknames WHERE channel_id = ? AND LOWER(nickname) = LOWER(?)",
            (channel_id, target),
        ).fetchone()
        username = nick_row[0] if nick_row else target
        user_row = conn.execute(
            "SELECT user_id FROM messages WHERE channel_id = ? AND LOWER(username) = LOWER(?) LIMIT 1",
            (channel_id, username),
        ).fetchone()
        conn.close()
        return user_row[0] if user_row else None

    def _fetch_random(self, channel_id: int, search_term: str = None):
        conn = sqlite3.connect(DB_PATH)

        if search_term is None:
            row = conn.execute(
                "SELECT id, content, username FROM messages WHERE channel_id = ? ORDER BY RANDOM() LIMIT 1",
                (channel_id,),
            ).fetchone()
        elif search_term.startswith('@'):
            target = search_term[1:]
            user_id = self._resolve_user_id(target, channel_id)
            if user_id is None:
                conn.close()
                return None
            rows = conn.execute(
                "SELECT id, content, username FROM messages WHERE channel_id = ? AND content LIKE ?",
                (channel_id, f'%<@{user_id}>%'),
            ).fetchall()
            row = random.choice(rows) if rows else None
        else:
            sql_like = '%' + search_term.replace('*', '%') + '%'
            pattern = self._build_regex(search_term)
            rows = conn.execute(
                "SELECT id, content, username FROM messages WHERE channel_id = ? AND LOWER(content) LIKE LOWER(?)",
                (channel_id, sql_like),
            ).fetchall()
            matches = [(i, c, u) for i, c, u in rows if pattern.search(c)]
            row = random.choice(matches) if matches else None

        if row is None:
            conn.close()
            return None

        msg_id, content, username = row
        nick_row = conn.execute(
            "SELECT nickname FROM nicknames WHERE channel_id = ? AND LOWER(username) = LOWER(?) LIMIT 1",
            (channel_id, username),
        ).fetchone()
        conn.close()

        display_name = nick_row[0] if nick_row else username
        content = self._sanitize_mentions(content, channel_id)
        timestamp = _format_dt(_snowflake_to_dt(msg_id))
        return content, display_name, timestamp

    @commands.command(name="random")
    async def random_msg(self, context, *, search_term: str = None):
        loop = context.bot.loop
        result = await loop.run_in_executor(
            None, lambda: self._fetch_random(context.channel.id, search_term)
        )

        if result is None:
            if search_term:
                await context.send(f"Ei löydy viestejä hakusanalla `{search_term}`.")
            else:
                await context.send("Ei viestejä kanavalla.")
            return

        content, display_name, timestamp = result
        await context.send(
            f"**{display_name}:** {content}\n-# {timestamp}",
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot):
    await bot.add_cog(RandomMsg(bot))
