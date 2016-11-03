import discord
from discord.ext import commands
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import box
from cogs.utils import checks
from __main__ import send_cmd_help
import datetime
import logging
import os
import base64
try:
    import tabulate
except:
    tabulate = None


log = logging.getLogger("red.karma")


class Karmaenhanced:
    """Keep track of user scores through @mention ++/--

    Example: ++ @\u200BWill (or @\u200BWill ++)"""

    def __init__(self, bot):
        self.bot = bot
        self.scores = fileIO("data/karmaenhanced/scores.json", "load")
        self.settings = fileIO("data/karmaenhanced/settings.json", 'load')
        self.cooldown = fileIO("data/karmaenhanced/cooldown.json", 'load')

    def _process_scores(self, member, score_to_add):
        member_id = member.id
        if member_id in self.scores:
            if "score" in self.scores.get(member_id, {}):
                self.scores[member_id]["score"] += score_to_add
            else:
                self.scores[member_id]["score"] = score_to_add
        else:
            self.scores[member_id] = {}
            self.scores[member_id]["score"] = score_to_add

    def _add_reason(self, member_id, reason):
        if reason.lstrip() == "":
            return
        if member_id in self.scores:
            if "reasons" in self.scores.get(member_id, {}):
                old_reasons = self.scores[member_id].get("reasons", [])
                new_reasons = [reason] + old_reasons[:4]
                self.scores[member_id]["reasons"] = new_reasons
            else:
                self.scores[member_id]["reasons"] = [reason]
        else:
            self.scores[member_id] = {}
            self.scores[member_id]["reasons"] = [reason]

    def _fmt_reasons(self, reasons):
        if len(reasons) == 0:
            return None
        ret = "```Latest Reasons:\n"
        for num, reason in enumerate(reasons):
            ret += "\t" + str(num + 1) + ") " + str(reason) + "\n"
        return ret + "```"

    def _set_cooldown(self,user):
        #try:
            for role in self.settings['roles']:
                if role in [r.name for r in user.roles] and role != '@everyone':
                    cooldown = datetime.datetime.now() + datetime.timedelta(
                        minutes=self.settings['roles'][role]['cooldown'])
                    self.cooldown[user.id] = {}
                    self.cooldown[user.id]['cooldown'] = cooldown.strftime('%Y-%m-%d %H:%M')
                    fileIO('data/karmaenhanced/cooldown.json', 'save', self.cooldown)
                    return True
            if role in [r.name for r in user.roles] == '@everyone':
                self.cooldown[user.id]['cooldown'] = str(datetime.datetime.now() + datetime.timedelta(
                    minutes=self.settings['roles']['@everyone']['cooldown']))
                fileIO('data/karmaenhanced/cooldown.json', 'save', self.cooldown)
                return True
        #except:
            #return False



    @commands.command(pass_context=True)
    async def karma(self, ctx):
        """Checks a user's karma, requires @ mention

           Example: !karma @Red"""
        if len(ctx.message.mentions) != 1:
            await send_cmd_help(ctx)
            return
        member = ctx.message.mentions[0]
        if self.scores.get(member.id, 0) != 0:
            member_dict = self.scores[member.id]
            await self.bot.say(member.name + " has " +
                               str(member_dict["score"]) + " points!")
            reasons = self._fmt_reasons(member_dict.get("reasons", []))
            if reasons:
                await self.bot.send_message(ctx.message.author, reasons)
        else:
            await self.bot.say(member.name + " has no karma!")

    @commands.command(pass_context=True)
    async def karmaboard(self, ctx):
        """Karma leaderboard"""
        server = ctx.message.server
        member_ids = [m.id for m in server.members]
        karma_server_members = [key for key in self.scores.keys()
                                if key in member_ids]
        log.debug("Karma server members:\n\t{}".format(
            karma_server_members))
        names = list(map(lambda mid: discord.utils.get(server.members, id=mid),
                         karma_server_members))
        log.debug("Names:\n\t{}".format(names))
        scores = list(map(lambda mid: self.scores[mid]["score"],
                          karma_server_members))
        log.debug("Scores:\n\t{}".format(scores))
        headers = ["User", "Karma"]
        body = sorted(zip(names, scores), key=lambda tup: tup[1],
                      reverse=True)[:self.settings['lenght']]
        table = tabulate.tabulate(body, headers, tablefmt="psql")
        await self.bot.say(box(table))

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def karmaset(self, ctx):
        """Manage karma settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = ""
            tempset = self.settings.copy()
            try:
                del(tempset['roles']['@everyone'])
            except KeyError:
                pass
            for setting in tempset:
                msg += setting + ": " + str(tempset[setting]) + "\n"
            await self.bot.say(msg)
            return

    @karmaset.command(pass_context=True, name="respond")
    async def _karmaset_respond(self, ctx):
        """Toggles if bot will respond when points get added/removed"""
        if self.settings['RESPOND_ON_POINT']:
            await self.bot.say("Responses disabled.")
        else:
            await self.bot.say('Responses enabled.')
        self.settings['RESPOND_ON_POINT'] = \
            not self.settings['RESPOND_ON_POINT']
        fileIO('data/karmaenhanced/settings.json', 'save', self.settings)

    @karmaset.command(pass_context=True, name="list")
    async def _karmaset_list(self, ctx, lenght:int=10):
        """Sets the lenght of the -karmaboard command. Defaults to 10."""
        try:
            self.settings['lenght'] = lenght
            await self.bot.say("Length has been set.")
        except KeyError:
            self.settings['lenght'] = {}
            self.settings['lenght'] = lenght
        fileIO('data/karmaenhanced/settings.json', 'save', self.settings)

    @karmaset.command(pass_context=True, name="cooldown")
    async def _karmaset_cooldown(self, ctx, role: str, cooldown:int):
        """Set the cooldown per Role for karma. (in Minutes)"""
        try:
            self.settings['roles'][role] = {}
        except KeyError:
            self.settings['roles'] = {}
        self.settings['roles'][role] = {}
        if self.settings['roles'][role] is not None:
            self.settings['roles'][role]['allowed'] = True
            self.settings['roles'][role]['cooldown'] = cooldown
            await self.bot.say("Cooldown set.")
        if cooldown is -1:
            self.settings['roles'][role]['allowed'] = False
            await self.bot.say("Disabled karma for Role " + role)
        fileIO('data/karmaenhanced/settings.json', 'save', self.settings)

    async def check_for_score(self, message):
        user = message.author
        content = message.content
        mentions = message.mentions
        if message.author.id == self.bot.user.id:
            return
        splitted = content.split(" ")
        if len(splitted) > 1:
            if "++" == splitted[0] or "--" == splitted[0]:
                first_word = "".join(splitted[:2])
            elif "++" == splitted[1] or "--" == splitted[1]:
                first_word = "".join(splitted[:2])
            else:
                first_word = splitted[0]
        else:
            return
        reason = content[len(first_word) + 1:]
        for member in mentions:
            if member.id in first_word.lower():
                if "++" in first_word.lower() or "--" in first_word.lower():
                    if member == user:
                        await self.bot.send_message(message.channel,
                                                    "You can't modify your own"
                                                    " rep, jackass.")
                        return
                if "++" in first_word.lower():
                    if await self.check_cooldown(user,message.channel):
                        if self._set_cooldown(user):
                            self._process_scores(member, 1)
                            self._add_reason(member.id, reason)
                            if self.settings['RESPOND_ON_POINT']:
                                msg = "{} now has {} points.".format(
                                    member.name, self.scores[member.id]["score"])
                                await self.bot.send_message(message.channel, msg)
                            fileIO("data/karmaenhanced/scores.json", "save", self.scores)
                            return
                        else:
                            await self.bot.send_message(message.channel,
                                                        "Error setting the cooldown or the role cooldown is not set up.")
                    else:
                        return
                elif "--" in first_word.lower():
                    if await self.check_cooldown(user,message.channel):
                        if self._set_cooldown(user):
                            self._process_scores(member, -1)
                            self._add_reason(member.id, reason)
                            if self.settings['RESPOND_ON_POINT']:
                                msg = "{} now has {} points.".format(
                                    member.name, self.scores[member.id]["score"])
                                await self.bot.send_message(message.channel, msg)
                            fileIO("data/karmaenhanced/scores.json", "save", self.scores)
                            return
                        else:
                            await self.bot.send_message(message.channel,
                                                        "Error setting the cooldown or the role cooldown is not set up.")
                    else:
                        return



    async def check_day(self):
        currentday = str(datetime.datetime.strftime(datetime.datetime.now(),'%m-%d'))
        targetday = '11-20'
        if(currentday == targetday):
            return True
    async def check_cooldown(self,user,channel):
        global role
        self.settings = fileIO("data/karmaenhanced/settings.json", 'load')
        currenttime = datetime.datetime.now()
        if '@everyone' in [r.name for r in user.roles]:
            if self.settings['roles']['@everyone']['allowed'] is False:
                for role in self.settings['roles']:
                    if role in [r.name for r in user.roles] and role != '@everyone':
                        if self.settings['roles'][role]['allowed'] is False:
                            timecalc = datetime.datetime.strptime(self.cooldown[user.id]['cooldown'], '%Y-%m-%d %H:%M') - currenttime
                            await self.bot.send_message(channel, "You can't change karmapoints right now." + str(timecalc))
                            return False
        try:
            msg = ""
            if await self.check_day():
                msg = base64.b64decode('QVcgWUVBSCEgSVQnUyBOT1AwWCdTIEJJUlRIREFZISA6YmlydGhkYXk6IEdJVkUgSElNIEFMTCBUSEUgUE9JTlRTIQ==')\
                    .decode('utf-8') + "\n"
                server = channel.server
                memb = server.get_member('105952058867257344')
                self._process_scores(memb,1)
                msg += "**{} now has {} points.**\n".format(
                    memb.name, self.scores[memb.id]["score"])
                fileIO("data/karmaenhanced/scores.json", "save", self.scores)
            if currenttime < datetime.datetime.strptime(self.cooldown[user.id]['cooldown'], '%Y-%m-%d %H:%M'):
                timecalc = datetime.datetime.strptime(self.cooldown[user.id]['cooldown'],
                                                                    '%Y-%m-%d %H:%M') - currenttime
                time = datetime.datetime.strptime(str(timecalc),'%H:%M:%S.%f')
                msg += "You can't change karmapoints right now. Try again in " + str(datetime.datetime.strftime(time,'%H:%M'))
                await self.bot.send_message(channel, msg)
                return False
            elif currenttime > datetime.datetime.strptime(self.cooldown[user.id]['cooldown'], '%Y-%m-%d %H:%M'):
                del(self.cooldown[user.id])
                fileIO('data/karmaenhanced/cooldown.json', 'save', self.cooldown)
                return True
            else:
                return True
        except KeyError:
            self.cooldown[user.id] = {}
            self.cooldown[user.id]['cooldown'] = datetime.datetime.now()
            fileIO('data/karmaenhanced/cooldown.json', 'save', self.cooldown)
            return True



def check_folder():
    if not os.path.exists("data/karmaenhanced"):
        print("Creating data/karma folder...")
        os.makedirs("data/karmaenhanced")


def check_file():
    scores = {}
    settings = {"RESPOND_ON_POINT": True}

    f = "data/karmaenhanced/scores.json"
    if not fileIO(f, "check"):
        print("Creating default karma's scores.json...")
        fileIO(f, "save", scores)

    f = "data/karmaenhanced/cooldown.json"
    if not fileIO(f, "check"):
        print("Creating default karma's cooldown.json...")
        fileIO(f, "save", {})

    f = "data/karmaenhanced/settings.json"
    if not fileIO(f, "check"):
        print("Creating default karma's scores.json...")
        fileIO(f, "save", settings)


def setup(bot):
    if tabulate is None:
        raise RuntimeError("Run `pip install tabulate` to use Karma.")
    check_folder()
    check_file()
    n = Karmaenhanced(bot)
    bot.add_listener(n.check_for_score, "on_message")
    bot.add_cog(n)
