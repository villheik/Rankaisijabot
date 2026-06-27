import sqlite3
import aiohttp
from typing import Optional
import discord
from discord.ext import commands

DB_PATH = "/data/rankaisija.db"
GITHUB_REPO = "villheik/Rankaisijabot"


class Release(commands.Cog, name="release"):
    def __init__(self, bot):
        self.bot = bot
        self._checked = False
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS release_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _get(self, key: str) -> Optional[str]:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT value FROM release_config WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _set(self, key: str, value: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO release_config (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
        conn.close()

    async def _fetch_latest_release(self) -> Optional[dict]:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"Accept": "application/vnd.github+json"}) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    def _format_announcement(self, release: dict) -> str:
        tag = release["tag_name"]
        name = release.get("name") or tag
        body = (release.get("body") or "").strip()
        url = release["html_url"]

        msg = f"**{name}**"
        if body:
            msg += f"\n{body}"
        msg += f"\n<{url}>"
        return msg

    @commands.Cog.listener()
    async def on_ready(self):
        if self._checked:
            return
        self._checked = True

        channel_id = self._get("channel_id")
        if channel_id is None:
            return

        release = await self._fetch_latest_release()
        if release is None:
            return

        tag = release["tag_name"]
        if tag == self._get("last_tag"):
            return

        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            return

        await channel.send(self._format_announcement(release))
        self._set("last_tag", tag)

    @commands.command(name="releasechannel")
    async def releasechannel(self, ctx, channel: Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        self._set("channel_id", str(target.id))
        await ctx.send(f"Release-ilmoitukset asetettu kanavalle {target.mention}.")


async def setup(bot):
    await bot.add_cog(Release(bot))
