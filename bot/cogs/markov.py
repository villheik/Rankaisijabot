import sqlite3
import datetime
import asyncio
from functools import partial
import markovify
import discord
from discord.ext import commands, tasks
from bot import constants
from bot.db import DB_PATH


class Markov(commands.Cog, name="markov"):
    def __init__(self, bot):
        self.bot = bot
        self._model_cache = {}
        self.nightly_rebuild.start()

    def cog_unload(self):
        self.nightly_rebuild.cancel()

    def _resolve_usernames(self, target: str, channel_id: int) -> list[str]:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT username FROM nicknames WHERE channel_id = ? AND LOWER(nickname) = LOWER(?)",
            (channel_id, target),
        ).fetchall()
        conn.close()
        if rows:
            return [row[0] for row in rows]
        return [target]

    def _build_model(self, channel_id: int, usernames: list[str]) -> tuple:
        placeholders = ",".join("?" * len(usernames))
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            f"SELECT content FROM messages WHERE channel_id = ? AND LOWER(username) IN ({placeholders})",
            (channel_id, *[u.lower() for u in usernames]),
        ).fetchall()
        conn.close()
        messages = [row[0] for row in rows]
        count = len(messages)
        if count < 10:
            return None, count
        state_size = 1 if count < 500 else 2 if count < 5000 else 3
        model = markovify.NewlineText("\n".join(messages), state_size=state_size)
        return model, count

    async def _build_nickname_cache(self, loop):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT DISTINCT channel_id, nickname FROM nicknames").fetchall()
        conn.close()

        for channel_id, nickname in rows:
            cache_key = (channel_id, nickname.lower())
            if cache_key in self._model_cache:
                continue
            usernames = self._resolve_usernames(nickname, channel_id)
            if len(usernames) == 1:
                user_key = (channel_id, usernames[0].lower())
                if user_key in self._model_cache:
                    self._model_cache[cache_key] = self._model_cache[user_key]
            else:
                try:
                    model, _ = await loop.run_in_executor(
                        None, partial(self._build_model, channel_id, usernames)
                    )
                    if model:
                        self._model_cache[cache_key] = model
                except Exception as e:
                    self.bot.logger.error(f"markov: nickname rebuild epäonnistui {channel_id}/{nickname}: {e}")

    @tasks.loop(time=datetime.time(hour=constants.Markov.rebuild_hour, minute=0))
    async def nightly_rebuild(self):
        self.bot.logger.info("markov: aloitetaan yöllinen rebuild")
        self._model_cache.clear()

        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT DISTINCT channel_id, username FROM messages").fetchall()
        conn.close()

        loop = asyncio.get_running_loop()
        built = 0
        for channel_id, username in rows:
            try:
                model, count = await loop.run_in_executor(
                    None, partial(self._build_model, channel_id, [username])
                )
                if model:
                    self._model_cache[(channel_id, username.lower())] = model
                    built += 1
            except Exception as e:
                self.bot.logger.error(f"markov: rebuild epäonnistui {channel_id}/{username}: {e}")

        await self._build_nickname_cache(loop)
        self.bot.logger.info(f"markov: rebuild valmis, {built}/{len(rows)} mallia rakennettu")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.content.strip():
            return
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO messages (id, user_id, username, content, channel_id) VALUES (?, ?, ?, ?, ?)",
            (message.id, message.author.id, message.author.display_name, message.content, message.channel.id),
        )
        conn.commit()
        conn.close()

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

        await status_msg.edit(content=f"Valmis! {count} uutta viestiä tallennettu. Rakennetaan mallit...")

        self._model_cache.clear()
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT DISTINCT channel_id, username FROM messages").fetchall()
        conn.close()

        loop = asyncio.get_running_loop()
        built = 0
        for ch_id, username in rows:
            try:
                model, msg_count = await loop.run_in_executor(
                    None, partial(self._build_model, ch_id, [username])
                )
                if model:
                    self._model_cache[(ch_id, username.lower())] = model
                    built += 1
            except Exception as e:
                self.bot.logger.error(f"markov: train rebuild epäonnistui {ch_id}/{username}: {e}")

        await self._build_nickname_cache(loop)
        await status_msg.edit(content=f"Valmis! {count} uutta viestiä tallennettu. {built} mallia rakennettu.")

    @commands.command(name="nickname")
    async def nickname(self, context, username: str, nickname: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO nicknames (channel_id, nickname, username) VALUES (?, ?, ?)",
            (context.channel.id, nickname, username),
        )
        conn.commit()
        conn.close()
        await context.send(f"`{username}` yhdistetty nicknameen `{nickname}`.")

    async def _get_model(self, context, target: str):
        usernames = self._resolve_usernames(target, context.channel.id)
        cache_key = (context.channel.id, target.lower())
        loop = context.bot.loop

        if cache_key not in self._model_cache:
            self.bot.logger.info(f"mimic: cache miss '{target}', rakennetaan malli")
            model, count = await loop.run_in_executor(
                None, partial(self._build_model, context.channel.id, usernames)
            )
            if model is None:
                self.bot.logger.warning(f"mimic: liian vähän viestejä kohteelle '{target}' kanavalla {context.channel.id} ({count} viestiä)")
                await context.send(f"Liian vähän viestejä kohteelle `{target}` (minimi 10).")
                return None, None, usernames
            self._model_cache[cache_key] = model
            self.bot.logger.info(f"mimic: malli rakennettu ({count} viestiä)")
        else:
            self.bot.logger.info(f"mimic: cache hit '{target}'")

        return self._model_cache[cache_key], loop, usernames

    async def _mimic(self, context, target: str, min_words: int = None):
        model, loop, usernames = await self._get_model(context, target)
        if model is None:
            return

        kwargs = {"tries": 200}
        if min_words:
            kwargs["min_words"] = min_words

        result = await loop.run_in_executor(None, partial(model.make_sentence, **kwargs))

        if result is None:
            self.bot.logger.warning(f"mimic: make_sentence palautti None kohteelle '{target}' (min_words={min_words})")
            await context.send(f"Ei pystytty generoimaan tekstiä kohteelle `{target}`.")
            return

        display = target if len(usernames) == 1 else f"{target} ({', '.join(usernames)})"
        await context.send(f"**{display}:** {result}")

    @commands.command(name="mimic")
    async def mimic(self, context, *, target=None):
        if target is None:
            await context.send("Käyttö: `!mimic <käyttäjänimi tai nickname>`")
            return
        await self._mimic(context, target)

    @commands.command(name="mimiclong")
    async def mimiclong(self, context, *, target=None):
        if target is None:
            await context.send("Käyttö: `!mimiclong <käyttäjänimi tai nickname>`")
            return
        await self._mimic(context, target, min_words=6)


async def setup(bot):
    await bot.add_cog(Markov(bot))
