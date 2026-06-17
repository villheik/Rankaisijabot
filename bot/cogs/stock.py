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

    @commands.command(name="price")
    async def price(self, context, stock=None):
        if stock == None:
            await context.send(
                "No stock specified. Specify a stock by using '!price <stock>"
            )
            return

        try:
            result = yf.Ticker(stock).info
            price = result.get("currentPrice") or result.get("regularMarketPrice")
            name = result.get("shortName") or result.get("longName", stock)
            currency = result.get("currency", "")
            await context.send(f"{name} ({result['symbol']}): {price} {currency}")
        except Exception as e:
            await context.send(f"Could not find stock {stock}.")
            return



async def setup(bot):
    await bot.add_cog(Stock(bot))
