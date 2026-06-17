import aiohttp
import yfinance as yf
from discord.ext import commands

allowedCurrencies = ["EUR", "USD"]
COINGECKO_IDS = {"BTC": "bitcoin", "ETH": "ethereum"}
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


class Stock(commands.Cog, name="stock"):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_crypto_price(self, context, coin: str, currency: str):
        if currency.upper() not in allowedCurrencies:
            await context.send(f"Unsupported currency: {currency}. Use EUR or USD.")
            return

        coin_id = COINGECKO_IDS[coin.upper()]
        params = f"?ids={coin_id}&vs_currencies={currency.lower()}"

        async with aiohttp.ClientSession() as session:
            raw_response = await session.get(COINGECKO_URL + params)
            response = await raw_response.json()
            price = response[coin_id][currency.lower()]
            await context.send(f"{coin.upper()} price is: {price} {currency.upper()}")

    @commands.command(name="btc")
    async def btc(self, context, currency=None):
        if currency is None:
            currency = "USD"
        await self.fetch_crypto_price(context, "BTC", currency)

    @commands.command(name="eth")
    async def eth(self, context, currency=None):
        if currency is None:
            currency = "USD"
        await self.fetch_crypto_price(context, "ETH", currency)

    async def resolve_ticker(self, query: str, session: aiohttp.ClientSession) -> str:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=1&newsCount=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return query
            data = await resp.json(content_type=None)
        quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
        if quotes:
            return quotes[0]["symbol"]
        return query

    @commands.command(name="price")
    async def price(self, context, *, stock=None):
        if stock is None:
            await context.send("No stock specified. Usage: `!price <ticker or name>`")
            return

        async with aiohttp.ClientSession() as session:
            try:
                info = yf.Ticker(stock).info
                if not info.get("symbol"):
                    raise ValueError("Not found")
            except Exception:
                ticker = await self.resolve_ticker(stock, session)
                try:
                    info = yf.Ticker(ticker).info
                except Exception:
                    await context.send(f"Could not find stock `{stock}`.")
                    return

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            name = info.get("shortName") or info.get("longName", stock)
            currency = info.get("currency", "")
            await context.send(f"{name} ({info.get('symbol', stock)}): {price} {currency}")



async def setup(bot):
    await bot.add_cog(Stock(bot))
