import aiohttp
import discord
import json
import requests
from discord.ext import commands
from cogs.utils import checks
import pycountry
import re

class dictionary:

    def __init__(self, bot):
        self.bot = bot

    def remove_tags(text, lol):
        TAG_RE = re.compile(r'<[^>]+>')
        return TAG_RE.sub('', lol)

        return cleantext
    @commands.command(pass_context=True, no_pm=True)
    async def dict(self, ctx, word: str, number: int = 1):
        """Example: -location GB"""
        url = "https://owlbot.info/api/v1/dictionary/" + word
        try:
            async with aiohttp.get(url) as r:
                data = await r.json()
        except:
            await self.bot.say("error")
        msg = ""
        if (len(data)>0):
            if number > 1:
                try:
                    msg += "\n**" + word + "**\n"
                    msg += "\n**Entry #" + str(number) + " of " + str(len(data))+ "**" + "\n"
                    msg += "\n*Type*: " + str(data[number-1]['type'])+ "\n" + "\n*Definition*: " + self.remove_tags(str(data[number - 1]['defenition']))+ "\n" + "\n*Example*: " + str(data[number - 1]['example'])
                    await self.bot.say(msg)
                except:
                    await self.bot.say("I was not able to fetch your definition. Did you use the right number?")
            else:
                msg += "\n**" + word + "**\n"
                msg += "\n**Entry #" + str(1) + " of " + str(len(data)) + "**" + "\n"
                msg += "\n*Type*: " + str(data[0]['type'])+ "\n" + "\n*Definition*: " + self.remove_tags(str(data[0]['defenition']))+ "\n" + "\n*Example*: " + str(data[0]['example'])
                await self.bot.say(msg)
        else:
            await self.bot.say("I was not able to find a dictionary entry for you. Sorry :(")


def setup(bot):
    bot.add_cog(dictionary(bot))
