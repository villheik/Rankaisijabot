import os, sys, discord, platform, random, aiohttp, json
import yfinance as yf
from discord.ext import commands

allowedCurrencies = ['EUR', 'USD']
allowedCoins = ['BTC', 'ETH']

class Stock(commands.Cog, name="stock"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="btc")
    async def btc(self, context, currency=None):
        if (currency==None):
            currency="USD"

        url = coinbaseUrl("btc", currency)
        if (url == None):
            await context.send("Unsupported currency: " + currency)
            return
        # Async HTTP request
        async with aiohttp.ClientSession() as session:
            raw_response = await session.get(url)
            response = await raw_response.text()
            response = json.loads(response)

            result=f"Bitcoin price is: {response['data']['amount']} " + currency 

            await context.send(result)
    
    @commands.command(name="eth")
    async def eth(self, context, currency=None):
        if (currency==None):
            currency="USD"

        url = coinbaseUrl("eth", currency)
        if (url == None):
            await context.send("Unsupported currency: " + currency)
            return
        # Async HTTP request
        async with aiohttp.ClientSession() as session:
            raw_response = await session.get(url)
            response = await raw_response.text()
            response = json.loads(response)

            result=f"Ethereum price is: {response['data']['amount']} " + currency 

            await context.send(result)

    @commands.command(name="price")
    async def price(self, context, stock=None):
        if (stock==None):
            await context.send("No stock specified. Specify a stock by using '!price <stock>")
            return

        try:
            result = yf.Ticker(stock).info
            await context.send(f"{result['shortName']} ({result['symbol']}): ask: {result['ask']} bid: {result['bid']} {result['currency']}")
        except:
            await context.send(f"Could not find stock {stock}.")
            return
        

def coinbaseUrl(coin, currency):
    try:
        if (coin.upper() in allowedCoins and currency.upper() in allowedCurrencies):
            return "https://api.coinbase.com/v2/prices/" + coin.upper() + "-" + currency.upper() + "/buy"
    except:
        return None
    return None

async def setup(bot):
    await bot.add_cog(Stock(bot))