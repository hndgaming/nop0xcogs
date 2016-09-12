import os

import aiohttp
from discord import Colour
from discord.ext import commands
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from imgurpython import ImgurClient
import requests
import shutil

class logo:

    def __init__(self, bot):
        client_id = '7c25f864e1c79db'
        client_secret = '2f0e0023b46fe6c615dc73534947313177628b0b'
        self.client = ImgurClient(client_id, client_secret)
        self.bot = bot
        self.name = ""
        self.color = Colour.blue()

    @commands.command(pass_context=True, no_pm=True)
    async def logo(self, ctx, name : str = ""):
        """Example: -logo name (3 or 4 chars)"""
        offset = 10
        user = ctx.message.author
        for x in range(0, len(user.roles)):
            if (user.roles[x].name == "Veteran") | (user.roles[x].name == "Regular"):
                self.color = str(user.color)
                break
        o = 357
        if(len(name) == 3):
            font = ImageFont.truetype("spaceman.ttf", 155)
        elif(len(name) == 4):
            font = ImageFont.truetype("spaceman.ttf", 135)
        else:
            await self.bot.say("You are a retard")
            return
        img = Image.open("avabg.png")
        draw = ImageDraw.Draw(img)
        shadowcolor = "#1e2124"
        text = name
        width,height = draw.textsize(text, font=font)
        height -= 10
        x = o-width/2.0
        y = o-height/2.0
        draw.text((x - offset, y - offset), text, font=font, fill=shadowcolor)
        draw.text((x + offset, y - offset), text, font=font, fill=shadowcolor)
        draw.text((x - offset, y + offset), text, font=font, fill=shadowcolor)
        draw.text((x + offset, y + offset), text, font=font, fill=shadowcolor)
        draw.text((x, y), text, self.color, font=font)
        img.save(name+'.png', format='PNG', subsampling=0, quality=100)
        self.name = name
        await self.upload()

    async def upload(self):
        upload = self.client.upload_from_path(self.name+'.png')
        await self.bot.say(upload['link'])
        os.remove(self.name+'.png')

def check_files():
    if not os.path.isfile("avabg.png"):
        url = 'http://i.imgur.com/DqtTq42.png'
        response = requests.get(url, stream=True)
        with open('avabg.png', 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response
    if not os.path.isfile("spaceman.ttf"):
        url = 'http://www.hndgaming.com/wp-content/uploads/SPACEMAN.TTF'
        response = requests.get(url, stream=True)
        with open('spaceman.ttf', 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response
def setup(bot):
    check_files()
    bot.add_cog(logo(bot))
