import sqlite3
import markovify
import discord
from discord.ext import commands

DB_PATH = "/data/markov.db"


class Markov(commands.Cog, name="markov"):
    def __init__(self, bot):
        self.bot = bot
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                username TEXT,
                content TEXT,
                channel_id INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                channel_id INTEGER PRIMARY KEY,
                last_message_id INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nicknames (
                nickname TEXT,
                username TEXT,
                PRIMARY KEY (nickname, username)
            )
        """)
        conn.commit()
        conn.close()

    def _resolve_usernames(self, target: str) -> list[str]:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT username FROM nicknames WHERE LOWER(nickname) = LOWER(?)", (target,)
        ).fetchall()
        conn.close()
        if rows:
            return [row[0] for row in rows]
        return [target]

    @commands.command(name="train")
    async def train(self, context):
        if context.author.id != context.guild.owner_id:
            await context.send("Vain serverin omistaja voi ajaa tämän komennon.")
            return

        channel = context.channel
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT last_message_id FROM meta WHERE channel_id = ?", (channel.id,)
        ).fetchone()
        last_message_id = row[0] if row else None
        conn.close()

        after = discord.Object(id=last_message_id) if last_message_id else None
        status_msg = await context.send("Haetaan viestejä...")

        count = 0
        newest_id = last_message_id
        conn = sqlite3.connect(DB_PATH)

        async for message in channel.history(limit=None, after=after, oldest_first=True):
            if message.author.bot or not message.content.strip():
                continue
            conn.execute(
                "INSERT OR IGNORE INTO messages (id, user_id, username, content, channel_id) VALUES (?, ?, ?, ?, ?)",
                (message.id, message.author.id, message.author.display_name, message.content, channel.id),
            )
            newest_id = message.id
            count += 1
            if count % 1000 == 0:
                conn.commit()
                await status_msg.edit(content=f"Haetaan viestejä... ({count} haettu)")

        if newest_id:
            conn.execute(
                "INSERT OR REPLACE INTO meta (channel_id, last_message_id) VALUES (?, ?)",
                (channel.id, newest_id),
            )
        conn.commit()
        conn.close()

        await status_msg.edit(content=f"Valmis! {count} uutta viestiä tallennettu.")

    @commands.command(name="nickname")
    @commands.has_permissions(administrator=True)
    async def nickname(self, context, username: str, nickname: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO nicknames (nickname, username) VALUES (?, ?)",
            (nickname, username),
        )
        conn.commit()
        conn.close()
        await context.send(f"`{username}` yhdistetty nicknameen `{nickname}`.")

    @commands.command(name="mimic")
    async def mimic(self, context, *, target=None):
        if target is None:
            await context.send("Käyttö: `!mimic <käyttäjänimi tai nickname>`")
            return

        usernames = self._resolve_usernames(target)
        placeholders = ",".join("?" * len(usernames))

        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            f"SELECT content FROM messages WHERE channel_id = ? AND LOWER(username) IN ({placeholders})",
            (context.channel.id, *[u.lower() for u in usernames]),
        ).fetchall()
        conn.close()

        messages = [row[0] for row in rows]

        if len(messages) < 10:
            await context.send(f"Liian vähän viestejä kohteelle `{target}` (minimi 10).")
            return

        model = markovify.NewlineText("\n".join(messages))
        result = model.make_sentence(tries=100)

        if result is None:
            await context.send(f"Ei pystytty generoimaan tekstiä kohteelle `{target}`.")
            return

        display = target if len(usernames) == 1 else f"{target} ({', '.join(usernames)})"
        await context.send(f"**{display}:** {result}")


async def setup(bot):
    await bot.add_cog(Markov(bot))
