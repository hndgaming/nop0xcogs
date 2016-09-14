import os
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils.dataIO import fileIO
from .utils import checks



class games:

    def __init__(self, bot):
        self.bot = bot
        self.games = fileIO("data/games/games.json", "load")

    @commands.group(pass_context=True)
    async def game(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @game.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def add(self, short:str, name:str):
        """Add a game to the list"""
        if name not in self.games:
            self.games[short] = {}
            self.games[short]["name"] = name
            self.games[short]["short"] = short
            fileIO("data/games/games.json", "save", self.games)
            await self.bot.say("Game has been added!")
        else:
            await self.bot.say("This Game already exists!")
    @game.command()
    async def list(self):
        """List all supported games"""
        msg = ""
        msg += "__**HND Supported Games**__\n\n"
        for game in self.games:
            msg += self.games[game]["short"] + " - " + self.games[game]["name"] + "\n"
        await self.bot.say(msg)

    @game.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def remove(self, short: str, name: str):
        """Add a game to the list"""
        if short in self.games:
            del self.games[short]
            fileIO("data/games/games.json", "save", self.games)
            await self.bot.say("Game has been removed!")
        else:
            await self.bot.say("This Game does not exist!")

def check_folders():
    if not os.path.exists("data/games"):
        print("Creating data/games folder...")
        os.makedirs("data/games")

def check_files():
    f = "data/games/games.json"
    if not fileIO(f, "check"):
        print("Creating empty games.json...")
        fileIO(f, "save", {})

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(games(bot))
