import discord
import json
import requests
from discord.ext import commands
from cogs.utils import checks
import pycountry
import re
import os
from .utils.dataIO import dataIO


class countrycode:
    def __init__(self, bot):
        self.countries = dataIO.load_json("data/countrycode/countries.json")
        self.subregions = dataIO.load_json("data/countrycode/subregions.json")
        self.bot = bot
    
    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(ban_members=True)
    async def db(self, ctx):
        """Example: -country GB"""
        server = ctx.message.server
        user = ctx.message.author
        perms = discord.Permissions.none()
        
        msg = await self.bot.say("Status: fetching countries...")
        
        for country in pycountry.countries:
            if country.name not in [r.name for r in server.roles]:
                continue
            else:
                self.countries[country.name] = {}
        dataIO.save_json("data/countrycode/countries.json", self.countries)
        
        for subdivision in pycountry.subdivisions:
            if subdivision.code not in [r.name for r in server.roles]:
                continue
            else:
                self.subregions[subdivision.code] = {}
        dataIO.save_json("data/countrycode/subregions.json", self.subregions)
        
        await self.bot.edit_message(msg, "Status: fetching countries done, fetching users...")
        
        for member in server.members:
            for country in self.countries:
                if country in [r.name for r in member.roles]:
                    self.countries[country][member.id] = {}
                else:
                    continue
            for subdivision in self.subregions:
                if subdivision in [r.name for r in member.roles]:
                    self.subregions[subdivision][member.id] = {}
                else:
                    continue
        dataIO.save_json("data/countrycode/countries.json", self.countries)
        dataIO.save_json("data/countrycode/subregions.json", self.subregions)
            
        await self.bot.edit_message(msg, "Status: fetching users done, cleaning up...")
        
        for country in self.countries:
            r = discord.utils.get(ctx.message.server.roles, name=country)
            await self.bot.delete_role(server,r)
        for subregion in self.subregions:
            r = discord.utils.get(ctx.message.server.roles, name=subregion)
            await self.bot.delete_role(server,r)
        
        await self.bot.edit_message(msg, "Status: springcleaning done, lul")

    @commands.command(pass_context=True, no_pm=True)
    async def country(self, ctx, country: str):
        """Example: -country GB"""
        server = ctx.message.server
        user = ctx.message.author
        perms = discord.Permissions.none()

        re1 = '((?:[a-z][a-z]+))'  # Word 1
        re2 = '.*?'  # Non-greedy match on filler
        re3 = '((?:[a-z][a-z]+))'  # Word 2
        rg = re.compile(re1 + re2 + re3, re.IGNORECASE | re.DOTALL)

        m = rg.search(country)
        if(country.upper() == 'NA'):
            country = 'US'
        subregionobj = None
        try:
            if m:
                word1 = m.group(1)
                countryobj = pycountry.countries.get(alpha_2=word1.upper())
                subregionobj = pycountry.subdivisions.get(code=country.upper())
            else:
                countryobj = pycountry.countries.get(alpha_2=country.upper())
        except:
            countryobj= None

        if countryobj is not None:
            #try:
            if subregionobj is not None:
                try:
                    if user.id not in self.subregions[subregionobj.code]:
                        self.subregions[subregionobj.code][user.id] = {}
                        await self.bot.say(
                            "Greetings from " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha_2.lower() + ": by " + user.mention)
                        dataIO.save_json("data/countrycode/subregions.json", self.subregions)
                    else:
                        await self.bot.say("You already set your countryorigin to that country!")
                except KeyError:
                    self.subregions[subregionobj.code] = {}
                    self.subregions[subregionobj.code][user.id] = {}
                    await self.bot.say(
                            "Greetings from " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha_2.lower() + ": by " + user.mention)
                    dataIO.save_json("data/countrycode/subregions.json", self.subregions)
            else:
                try:
                    if user.id not in self.countries[countryobj.name]:
                        self.countries[countryobj.name][user.id] = {}
                        await self.bot.say(
                            "Greetings from " + countryobj.name + " :flag_" + countryobj.alpha_2.lower() + ": by " + user.mention)
                        dataIO.save_json("data/countrycode/countries.json", self.countries)
                    else:
                        await self.bot.say("You already set your countryorigin to that country!")
                except KeyError:
                    self.countries[countryobj.name] = {}
                    self.countries[countryobj.name][user.id] = {}
                    await self.bot.say(
                            "Greetings from " + countryobj.name + " :flag_" + countryobj.alpha_2.lower() + ": by " + user.mention)
                    dataIO.save_json("data/countrycode/countries.json", self.countries)
            #except AttributeError:
                #await self.bot.say("w00ps, something went wrong! :( Please try again.")
        else:
            await self.bot.say(
                "Sorry I don't know your country! Did you use the correct ISO countrycode? \nExample: `-country GB` or `-country US-CA for california `\n <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Officially_assigned_code_elements for a list of countrycodes!")

    @commands.command(pass_context=True, no_pm=True)
    async def removecountry(self, ctx, country: str):

        server = ctx.message.server
        user = ctx.message.author
        perms = discord.Permissions.none()

        re1 = '((?:[a-z][a-z]+))'  # Word 1
        re2 = '.*?'  # Non-greedy match on filler
        re3 = '((?:[a-z][a-z]+))'  # Word 2
        rg = re.compile(re1 + re2 + re3, re.IGNORECASE | re.DOTALL)

        m = rg.search(country)
        subregionobj = None
        try:
            if m:
                word1 = m.group(1)
                countryobj = pycountry.countries.get(alpha_2=word1.upper())
                subregionobj = pycountry.subdivisions.get(code=country.upper())
            else:
                countryobj = pycountry.countries.get(alpha_2=country.upper())
        except:
            countryobj= None
        if countryobj is not None:
            if subregionobj is not None:
                try:
                    if user.id in self.subregions[subregionobj.code]:
                        del(self.subregions[subregionobj.code][user.id])
                        await self.bot.say(
                            "The boys and girls from " + countryobj.name + ": " + subregionobj.name + " will miss you " + user.mention + "! :(")
                        dataIO.save_json("data/countrycode/subregions.json", self.subregions)
                    else:
                        await self.bot.say("You already removed that country as your countryorigin!")
                except KeyError:
                    await self.bot.say("You already removed that country as your countryorigin!")
            else:
                try:
                    if user.id in self.countries[countryobj.name]:
                        del(self.countries[countryobj.name][user.id])
                        await self.bot.say(
                            "The boys and girls from " + countryobj.name + " will miss you " + user.mention + "! :(")
                        dataIO.save_json("data/countrycode/countries.json", self.countries)
                    else:
                        await self.bot.say("You already removed that country as your countryorigin!")
                except:
                    await self.bot.say("You already removed that country as your countryorigin!")
        else:
            await self.bot.say("Sorry I don't know your country! Did you use the correct ISO countrycode?\n <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Officially_assigned_code_elements for a list of countrycodes!>")


def check_folders():
    folders = ("data", "data/countrycode/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)
            
def check_files():
    if not os.path.isfile("data/countrycode/countries.json"):
        print("Creating empty countries.json...")
        dataIO.save_json("data/countrycode/countries.json", {})
    if not os.path.isfile("data/countrycode/subregions.json"):
        print("Creating empty subregions.json...")
        dataIO.save_json("data/countrycode/subregions.json", {})

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(countrycode(bot))
