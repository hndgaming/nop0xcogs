import discord
import json
import requests
from discord.ext import commands
from cogs.utils import checks
import pycountry
import re
import os
import datetime
import pandas as pd
import plotly.plotly as py
from imgurpython import ImgurClient
import csv
from .utils.dataIO import dataIO

class location:

    def __init__(self, bot):
        self.countries = dataIO.load_json("data/countrycode/countries.json")
        self.subregions = dataIO.load_json("data/countrycode/subregions.json")
        self.cooldown = datetime.datetime.now()
        self.lastlink = ""
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def locate(self, ctx, user: discord.Member):
        """Example: -locate @Nop0x
            Requires Mention or Name"""
        msg = user.name + " has the following countries set: ```"
        self.countries = dataIO.load_json("data/countrycode/countries.json")
        self.subregions = dataIO.load_json("data/countrycode/subregions.json")
        for country in self.countries:
            if user.id in self.countries[country]:
                msg += "•" + country + "\n"
        msg += "```"
        if msg == user.name + " has the following countries set: ``````":
            await self.bot.say(user.name + " has no country set :(")
            return
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def location(self, ctx, country: str):
        """Example: -location GB"""
        self.countries = dataIO.load_json("data/countrycode/countries.json")
        self.subregions = dataIO.load_json("data/countrycode/subregions.json")
        
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
            countryobj = None
        easter = "shithole";

        if countryobj is not None:
            if subregionobj is not None:
                msg = "Members from " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha_2.lower() + ": ```"
                try:
                    for member in server.members:
                        if member.id in self.subregions[subregionobj.code]:
                            msg = msg + "\n• " + member.name
                    msg = msg + "```"
                    if msg != "Members from " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha_2.lower().lower() + ": ``````":
                        await self.bot.send_message(user,msg)
                    else:
                        await self.bot.say(
                            "No one found in " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha_2.lower().lower() + ": :(")
                except:
                    await self.bot.say(
                            "No one found in " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha2.lower().lower() + ": :(")
            else:
                msg = "Members from " + countryobj.name + " :flag_"+ countryobj.alpha_2.lower() +": ```"
                try:
                    for member in server.members:
                        if member.id in self.countries[countryobj.name]:
                            msg = msg + "\n• " + member.name
                    msg = msg + "```"
                    if msg != "Members from " + countryobj.name + " :flag_"+ countryobj.alpha_2.lower() +": ``````":
                        await self.bot.send_message(user,msg)
                    else:
                        await self.bot.say("No one found in " + countryobj.name + " :flag_"+ countryobj.alpha_2.lower() +": :(")
                except:
                    await self.bot.say("No one found in " + countryobj.name + " :flag_"+ countryobj.alpha_2.lower() +": :(")
        else:
            if country.lower() == easter:
                msg = "All members for SHITHOLE :poop: : \n```•SpiritoftheWest#4290```"
                await self.bot.say(msg)
            else:
                await self.bot.say("Sorry I don't know your country! Did you use the correct ISO countrycode? \nExample: `-location GB`")
                
    @commands.command(pass_context=True, no_pm=True)
    async def map(self, ctx):
        if(datetime.datetime.now() < self.cooldown):
            await self.bot.say("The holy map of awesomness: " + self.lastlink)
            return
        msg = await self.bot.say("Looking up where HND members are from...")
        with open("data/countrycode/countries.csv", 'w') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            templist2 = ["code", "count"]
            wr.writerow(templist2)
            with open('data/countrycode/countries.json') as json_data:
                d = json.load(json_data)
                total = len(d)
                i=0
                for country in d:
                    await self.bot.edit_message(msg, "Looking up where HND members are from: " + str(i) + "/" + str(total))
                    con = pycountry.countries.get(name=country)
                    count = len(d[country])
                    i += 1
                    if count != 0:
                        templist=[con.alpha_3,count]
                        wr.writerow(templist)
        
        df = pd.read_csv('data/countrycode/countries.csv')
        client_id = '7c25f864e1c79db'
        client_secret = '2f0e0023b46fe6c615dc73534947313177628b0b'
        client = ImgurClient(client_id, client_secret)
        
        data = [ dict(
                type = 'choropleth',
                locations = df['code'],
                z = df['count'],
                autocolorscale = True,
                reversescale = False,
                marker = dict(
                    line = dict (
                        color = 'rgb(180,180,180)',
                        width = 0.5
                    ) ),
                colorbar = dict(),
              ) ]
        
        layout = dict(
            title = 'HND World Map',
            geo = dict(
                showframe = False,
                showcoastlines = True,
            )
        )
        await self.bot.edit_message(msg, "Generating heatmap...")
        fig = dict( data=data, layout=layout )
        py.image.save_as(fig, filename='worldmap.png', scale=2, width=1920, height = 1080)
        upload = client.upload_from_path('worldmap.png')
        await self.bot.say("The holy map of awesomness: " + upload['link'])
        self.lastlink = upload['link']
        self.cooldown = datetime.datetime.now() + datetime.timedelta(hours=1)
        
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
    bot.add_cog(location(bot))
