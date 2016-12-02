import datetime
import operator
import re
from collections import OrderedDict

import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help, settings
from collections import deque, defaultdict
from cogs.utils.chat_formatting import escape_mass_mentions, box
import os
import logging
import asyncio


class modenhanced:
    """Moderation tools."""

    def __init__(self, bot):
        self.bot = bot
        self.whitelist_list = dataIO.load_json("data/modenhanced/whitelist.json")
        self.blacklist_list = dataIO.load_json("data/modenhanced/blacklist.json")
        self.ignore_list = dataIO.load_json("data/modenhanced/ignorelist.json")
        self.filter = dataIO.load_json("data/modenhanced/filter.json")
        self.past_names = dataIO.load_json("data/modenhanced/past_names.json")
        self.mutes = dataIO.load_json("data/modenhanced/mutes.json")
        self.past_nicknames = dataIO.load_json("data/modenhanced/past_nicknames.json")
        self.warnings = dataIO.load_json("data/modenhanced/warnings.json")
        self.rules = dataIO.load_json("data/modenhanced/rules.json")
        settings = dataIO.load_json("data/modenhanced/settings.json")
        self.settings = defaultdict(lambda: default_settings.copy(), settings)
        self.cache = defaultdict(lambda: deque(maxlen=3))
        self.cases = dataIO.load_json("data/modenhanced/modlog.json")
        self.slowmode = dataIO.load_json("data/modenhanced/slowmode.json")
        self._tmp_banned_cache = []
        self.last_case = defaultdict(lambda: dict())

    @commands.group(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(administrator=True)
    async def modset(self, ctx):
        """Manages server administration settings."""
        if ctx.invoked_subcommand is None:
            server = ctx.message.server
            await send_cmd_help(ctx)
            roles = settings.get_server(server).copy()
            _settings = {**self.settings[server.id], **roles}
            msg = ("Admin role: {ADMIN_ROLE}\n"
                   "Mod role: {MOD_ROLE}\n"
                   "Mod-log: {mod-log}\n"
                   "".format(**_settings))
            await self.bot.say(box(msg))

    @modset.command(name="mutetime", pass_context=True)
    async def mutetime(self, ctx, time: str):
        """Sets the default mutetime."""
        self.settings["mutetime"] = time
        dataIO.save_json("data/modenhanced/settings.json", self.settings)
        await self.bot.say("Saved the mutetime.")

    @modset.command(name="spamdelete", pass_context=True)
    async def spamdelete(self, ctx):
        """Toggles to delete Spamesque Characters or not."""
        if (self.settings["spamdelete"]):
            self.settings["spamdelete"] = False
            dataIO.save_json("data/modenhanced/settings.json", self.settings)
            await self.bot.say("Toggled spamdelete to " + str(self.settings["spamdelete"]))
            return
        self.settings["spamdelete"] = True
        dataIO.save_json("data/modenhanced/settings.json", self.settings)
        await self.bot.say("Toggled spamdelete to " + str(self.settings["spamdelete"]))

    @modset.command(name="serverid", pass_context=True)
    async def serverid(self, ctx, id: str):
        """Sets the Serverid of this server."""
        self.settings["serverid"] = id
        dataIO.save_json("data/modenhanced/settings.json", self.settings)
        await self.bot.say("Saved the serverid.")

    @modset.command(name="addrule", pass_context=True)
    async def rulesadd(self, ctx, id: str, rule: str):
        """Add Server rules."""
        self.rules[id] = {}
        self.rules[id] = rule
        dataIO.save_json("data/modenhanced/rules.json", self.rules)
        await self.bot.say("Saved the rule.")

    @modset.command(name="adminrole", pass_context=True, no_pm=True)
    async def _modset_adminrole(self, ctx, role_name: str):
        """Sets the admin role for this server, case insensitive."""
        server = ctx.message.server
        if server.id not in settings.servers:
            await self.bot.say("Remember to set modrole too.")
        settings.set_server_admin(server, role_name)
        await self.bot.say("Admin role set to '{}'".format(role_name))

    @modset.command(name="modrole", pass_context=True, no_pm=True)
    async def _modset_modrole(self, ctx, role_name: str):
        """Sets the mod role for this server, case insensitive."""
        server = ctx.message.server
        if server.id not in settings.servers:
            await self.bot.say("Remember to set adminrole too.")
        settings.set_server_mod(server, role_name)
        await self.bot.say("Mod role set to '{}'".format(role_name))

    @modset.command(name="slowmode", pass_context=True, no_pm=True)
    async def _modset_slowmode(self, ctx):
        """Toggles Slowmode for all Chats.."""
        server = ctx.message.server
        try:
            if self.settings[server.id]["slowmode"]["enabled"]:
                self.settings[server.id]["slowmode"]["enabled"] = False
            else:
                self.settings[server.id]["slowmode"]["enabled"] = True
        except:
            self.settings[server.id] = {}
            self.settings[server.id]["slowmode"] = {}
            self.settings[server.id]["slowmode"]["enabled"] = True
        dataIO.save_json("data/modenhanced/settings.json", self.settings)
        await self.bot.say("Slowmode toggled to " + str(self.settings[server.id]["slowmode"]["enabled"]))

    @modset.command(pass_context=True, no_pm=True)
    async def modlog(self, ctx, channel: discord.Channel = None):
        """Sets a channel as mod log
        Leaving the channel parameter empty will deactivate it"""
        server = ctx.message.server
        if channel:
            self.settings[server.id]["mod-log"] = channel.id
            await self.bot.say("Mod events will be sent to {}"
                               "".format(channel.mention))
        else:
            if self.settings[server.id]["mod-log"] is None:
                await send_cmd_help(ctx)
                return
            self.settings[server.id]["mod-log"] = None
            await self.bot.say("Mod log deactivated.")
        dataIO.save_json("data/modenhanced/settings.json", self.settings)

    @modset.command(pass_context=True, no_pm=True)
    async def serverlog(self, ctx, channel: discord.Channel = None):
        """Sets a channel as mod log
        Leaving the channel parameter empty will deactivate it"""
        server = ctx.message.server
        if channel:
            self.settings[server.id]["server-log"] = channel.id
            await self.bot.say("Server events will be sent to {}"
                               "".format(channel.mention))
        else:
            if self.settings[server.id]["server-log"] is None:
                await send_cmd_help(ctx)
                return
            self.settings[server.id]["server-log"] = None
            await self.bot.say("Server log deactivated.")
        dataIO.save_json("data/modenhanced/settings.json", self.settings)

    @modset.command(name="intmodch", pass_context=True, no_pm=True)
    async def internalmodchannel(self, ctx, channel: discord.Channel = None):
        """Sets a channel as internal mod log
        Leaving the channel parameter empty will deactivate it"""
        server = ctx.message.server
        if channel:
            self.settings[server.id]["int-mod-log"] = channel.id
            await self.bot.say("Internal Mod Events will be sent to {}"
                               "".format(channel.mention))
        else:
            if self.settings[server.id]["int-mod-log"] is None:
                await send_cmd_help(ctx)
                return
            self.settings[server.id]["int-mod-log"] = None
            await self.bot.say("Mod log deactivated.")
        dataIO.save_json("data/modenhanced/settings.json", self.settings)

    @modset.command(pass_context=True, no_pm=True)
    async def banmentionspam(self, ctx, max_mentions: int = False):
        """Enables auto ban for messages mentioning X different people
        Accepted values: 5 or superior"""
        server = ctx.message.server
        if max_mentions:
            if max_mentions < 5:
                max_mentions = 5
            self.settings[server.id]["ban_mention_spam"] = max_mentions
            await self.bot.say("Autoban for mention spam enabled. "
                               "Anyone mentioning {} or more different people "
                               "in a single message will be autobanned."
                               "".format(max_mentions))
        else:
            if self.settings[server.id]["ban_mention_spam"] is False:
                await send_cmd_help(ctx)
                return
            self.settings[server.id]["ban_mention_spam"] = False
            await self.bot.say("Autoban for mention spam disabled.")
        dataIO.save_json("data/modenhanced/settings.json", self.settings)

    @modset.command(pass_context=True, no_pm=True)
    async def deleterepeats(self, ctx):
        """Enables auto deletion of repeated messages"""
        server = ctx.message.server
        if not self.settings[server.id]["delete_repeats"]:
            self.settings[server.id]["delete_repeats"] = True
            await self.bot.say("Messages repeated up to 3 times will "
                               "be deleted.")
        else:
            self.settings[server.id]["delete_repeats"] = False
            await self.bot.say("Repeated messages will be ignored.")
        dataIO.save_json("data/modenhanced/settings.json", self.settings)

    @modset.command(pass_context=True, no_pm=True)
    async def resetcases(self, ctx):
        """Resets modlog's cases"""
        server = ctx.message.server
        self.cases[server.id] = {}
        dataIO.save_json("data/modenhanced/modlog.json", self.cases)
        await self.bot.say("Cases have been reset.")

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member,reason:str):
        """Kicks user."""
        author = ctx.message.author
        server = author.server
        try:
            await self.bot.kick(user)
            data = discord.Embed(colour=discord.Colour.red())
            data.set_author(name="Moderation Log")
            data.add_field(name="Action: Kicked " + user.name + " from the server", value="Reason: " + reason)
            await self.bot.say("Done. That felt good.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    async def auto_kick(self, user: discord.Member, reason: str = ""):
        """Kicks user."""
        try:
            data = discord.Embed(colour=discord.Colour.red())
            data.set_author(name="Automatic Filter Action")
            data.add_field(name="Action: Kicked " + user.name + " from the server", value="Reason: " + reason)
            await self.bot.kick(user)
        except Exception as e:
            print(e)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.Member, reason: str, days: int = 0):
        """Bans user and deletes last X days worth of messages.
        Minimum 0 days, maximum 7. Defaults to 0."""
        author = ctx.message.author
        server = author.server
        if days < 0 or days > 7:
            await self.bot.say("Invalid days. Must be between 0 and 7.")
            return
        try:
            data = discord.Embed(colour=discord.Colour.red())
            data.set_author(name="Moderation Log")
            if user.avatar_url:
                data.set_thumbnail(url=user.avatar_url)
            data.set_image(url="http://i.imgur.com/sKkcFLw.png")
            data.add_field(name="Action: Banned " + user.name + " from the server", value="Reason: " + reason)
            self._tmp_banned_cache.append(user)
            await self.bot.ban(user, days)
            await self.appendmodlog(data, server)
            await self.bot.say("Done. It was about time.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)
        finally:
            await asyncio.sleep(1)
            self._tmp_banned_cache.remove(user)

    async def auto_ban(self, user: discord.Member, days: int = 0, reason: str = ""):
        """Bans user and deletes last X days worth of messages.
        Minimum 0 days, maximum 7. Defaults to 0."""
        server = user.server
        if days < 0 or days > 7:
            await self.bot.say("Invalid days. Must be between 0 and 7.")
            return
        try:
            data = discord.Embed(colour=discord.Colour.red())
            if user.avatar_url:
                data.set_thumbnail(url=user.avatar_url)
            data.set_author(name="Automatic Filter Action")
            data.add_field(name="Action: Banned " + user.name + " from the server", value="Reason: " + reason)
            self._tmp_banned_cache.append(user)
            await self.bot.ban(user, days)
            await self.appendmodlog(data, server)
        except Exception as e:
            print(e)
        finally:
            await asyncio.sleep(1)
            self._tmp_banned_cache.remove(user)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx, user: discord.Member, *, nickname=""):
        """Changes user's nickname
        Leaving the nickname empty will remove it."""
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(user, nickname)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I cannot do that, I lack the "
                               "\"Manage Nicknames\" permission.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def cleanup(self, ctx):
        """Deletes messages.
        cleanup messages [number]
        cleanup user [name/mention] [number]
        cleanup text \"Text here\" [number]"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @cleanup.command(pass_context=True, no_pm=True)
    async def text(self, ctx, text: str, number: int):
        """Deletes last X messages matching the specified text.
        Example:
        cleanup text \"test\" 5
        Remember to use double quotes."""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        def check(m):
            if text in m.content:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = [ctx.message]

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        logger.info("{}({}) deleted {} messages "
                    " containing '{}' in channel {}".format(author.name,
                                                            author.id, len(to_delete), text, channel.id))

        if is_bot:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @cleanup.command(pass_context=True, no_pm=True)
    async def user(self, ctx, user: discord.Member, number: int):
        """Deletes last X messages from specified user.
        Examples:
        cleanup user @\u200bTwentysix 2
        cleanup user Red 6"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        def check(m):
            if m.author == user:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = [ctx.message]

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        logger.info("{}({}) deleted {} messages "
                    " made by {}({}) in channel {}"
                    "".format(author.name, author.id, len(to_delete),
                              user.name, user.id, channel.name))

        if is_bot:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @cleanup.command(pass_context=True, no_pm=True)
    async def after(self, ctx, message_id: int):
        """Deletes all messages after specified message
        To get a message id, enable developer mode in Discord's
        settings, 'appearance' tab. Then right click a message
        and copy its id.
        """

        channel = ctx.message.channel
        author = ctx.message.author
        server = channel.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        to_delete = []

        after = await self.bot.get_message(channel, message_id)

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return
        elif not after:
            await self.bot.say("Message not found.")
            return

        async for message in self.bot.logs_from(channel, limit=2000,
                                                after=after):
            to_delete.append(message)

        logger.info("{}({}) deleted {} messages in channel {}"
                    "".format(author.name, author.id,
                              len(to_delete), channel.name))

        if is_bot:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @cleanup.command(pass_context=True, no_pm=True)
    async def messages(self, ctx, number: int):
        """Deletes last X messages.
        Example:
        cleanup messages 26"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        to_delete = []

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return

        async for message in self.bot.logs_from(channel, limit=number + 1):
            to_delete.append(message)

        logger.info("{}({}) deleted {} messages in channel {}"
                    "".format(author.name, author.id,
                              number, channel.name))

        if is_bot:
            await self.mass_purge(to_delete)
        else:
            await self.slow_deletion(to_delete)

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def blacklist(self, ctx):
        """Bans user from using the bot"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @blacklist.command(name="add")
    async def _blacklist_add(self, user: discord.Member):
        """Adds user to bot's blacklist"""
        if user.id not in self.blacklist_list:
            self.blacklist_list.append(user.id)
            dataIO.save_json("data/modenhanced/blacklist.json", self.blacklist_list)
            await self.bot.say("User has been added to blacklist.")
        else:
            await self.bot.say("User is already blacklisted.")

    @blacklist.command(name="remove")
    async def _blacklist_remove(self, user: discord.Member):
        """Removes user from bot's blacklist"""
        if user.id in self.blacklist_list:
            self.blacklist_list.remove(user.id)
            dataIO.save_json("data/modenhanced/blacklist.json", self.blacklist_list)
            await self.bot.say("User has been removed from blacklist.")
        else:
            await self.bot.say("User is not in blacklist.")

    @blacklist.command(name="clear")
    async def _blacklist_clear(self):
        """Clears the blacklist"""
        self.blacklist_list = []
        dataIO.save_json("data/modenhanced/blacklist.json", self.blacklist_list)
        await self.bot.say("Blacklist is now empty.")

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def whitelist(self, ctx):
        """Users who will be able to use the bot"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @whitelist.command(name="add")
    async def _whitelist_add(self, user: discord.Member):
        """Adds user to bot's whitelist"""
        if user.id not in self.whitelist_list:
            if not self.whitelist_list:
                msg = "\nAll users not in whitelist will be ignored (owner, admins and mods excluded)"
            else:
                msg = ""
            self.whitelist_list.append(user.id)
            dataIO.save_json("data/modenhanced/whitelist.json", self.whitelist_list)
            await self.bot.say("User has been added to whitelist." + msg)
        else:
            await self.bot.say("User is already whitelisted.")

    @whitelist.command(name="remove")
    async def _whitelist_remove(self, user: discord.Member):
        """Removes user from bot's whitelist"""
        if user.id in self.whitelist_list:
            self.whitelist_list.remove(user.id)
            dataIO.save_json("data/modenhanced/whitelist.json", self.whitelist_list)
            await self.bot.say("User has been removed from whitelist.")
        else:
            await self.bot.say("User is not in whitelist.")

    @whitelist.command(name="clear")
    async def _whitelist_clear(self):
        """Clears the whitelist"""
        self.whitelist_list = []
        dataIO.save_json("data/modenhanced/whitelist.json", self.whitelist_list)
        await self.bot.say("Whitelist is now empty.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx):
        """Adds servers/channels to ignorelist"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say(self.count_ignored())

    @ignore.command(name="channel", pass_context=True)
    async def ignore_channel(self, ctx, channel: discord.Channel = None):
        """Ignores channel
        Defaults to current one"""
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(current_ch.id)
                dataIO.save_json("data/modenhanced/ignorelist.json", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")
        else:
            if channel.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(channel.id)
                dataIO.save_json("data/modenhanced/ignorelist.json", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")

    @ignore.command(name="server", pass_context=True)
    async def ignore_server(self, ctx):
        """Ignores current server"""
        server = ctx.message.server
        if server.id not in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].append(server.id)
            dataIO.save_json("data/modenhanced/ignorelist.json", self.ignore_list)
            await self.bot.say("This server has been added to the ignore list.")
        else:
            await self.bot.say("This server is already being ignored.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx):
        """Removes servers/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say(self.count_ignored())

    @unignore.command(name="channel", pass_context=True)
    async def unignore_channel(self, ctx, channel: discord.Channel = None):
        """Removes channel from ignore list
        Defaults to current one"""
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(current_ch.id)
                dataIO.save_json("data/modenhanced/ignorelist.json", self.ignore_list)
                await self.bot.say("This channel has been removed from the ignore list.")
            else:
                await self.bot.say("This channel is not in the ignore list.")
        else:
            if channel.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(channel.id)
                dataIO.save_json("data/modenhanced/ignorelist.json", self.ignore_list)
                await self.bot.say("Channel removed from ignore list.")
            else:
                await self.bot.say("That channel is not in the ignore list.")

    @unignore.command(name="server", pass_context=True)
    async def unignore_server(self, ctx):
        """Removes current server from ignore list"""
        server = ctx.message.server
        if server.id in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].remove(server.id)
            dataIO.save_json("data/modenhanced/ignorelist.json", self.ignore_list)
            await self.bot.say("This server has been removed from the ignore list.")
        else:
            await self.bot.say("This server is not in the ignore list.")

    @commands.command(name="botswap", pass_context=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def botswap(self,ctx, member:discord.Member, channel:discord.Channel):
        await self.bot.ban(member, 0)
        data = discord.Embed(colour=discord.Colour.red())
        data.set_author(name="Update")
        data.set_image(url="http://i.imgur.com/sKkcFLw.png")
        data.add_field(name="Action: Banned D.Va from the Server.", value="There is only room for one Modbot, bitch.")
        await self.bot.send_message(channel, embed=data)

    @commands.command(name="mute", pass_context=True)
    async def manual_mute(self, ctx, member: discord.Member, duration: int, unit: str, reason: str):
        """Mutes a user for given amout of time."""
        if unit == "hours":
            try:
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    hours=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(ctx.message.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            except KeyError:
                self.mutes[member.id] = {}
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    hours=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(ctx.message.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            await self.bot.say("Muter User " + member.name + " for " + str(duration) + " " + unit + "!")
            data2 = discord.Embed(description="Mute", color=discord.Colour.red())
            data2.set_author(name="Moderation Message")
            data2.add_field(name="**This is a warning message from the " + ctx.message.server.name + " server**",
                            value="You have been temporarily muted for " + str(duration) + " " + (unit) + "\n"
                                  + "\nReason: " + reason, inline=False)
            data2.set_footer(
                text="For a complete list of " + ctx.message.server.name + " rules, please see the #intro channel")
            await self.bot.send_message(member, embed=data2)
            data = discord.Embed(colour=discord.Colour.orange())

            if member.avatar_url:
                data.set_thumbnail(url=member.avatar_url)
            data.set_author(name="Moderation Log")
            data.add_field(name="Action: Muted " + member.name + " for " + str(duration) + " " + unit + "!",
                           value="Reason: " + reason)
            await self.appendmodlog(data, member.server)

        elif unit == "minutes":
            try:
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    minutes=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(ctx.message.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            except KeyError:
                self.mutes[member.id] = {}
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    minutes=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(ctx.message.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            await self.bot.say("Muter User " + member.name + " for " + str(duration) + " " + unit + "!")
            data2 = discord.Embed(description="Mute", color=discord.Colour.red())
            data2.set_author(name="Moderation Message")
            data2.add_field(name="**This is a warning message from the " + ctx.message.server.name + " server**",
                            value="You have been temporarily muted for " + str(duration) + " " + unit + "\n"
                                  + "\nReason: " + reason, inline=False)
            data2.set_footer(
                text="For a complete list of " + ctx.message.server.name + " rules, please see the #intro channel")
            await self.bot.send_message(member, embed=data2)
            data = discord.Embed(colour=discord.Colour.orange())
            if member.avatar_url:
                data.set_thumbnail(url=member.avatar_url)
            data.set_author(name="Moderation Log")
            data.add_field(name="Action: Muted " + member.name + " for " + str(duration) + " " + unit + "!",
                           value="Reason: " + reason)
            await self.appendmodlog(data, member.server)

    async def auto_mute(self, member: discord.Member, duration: int, unit: str, reason: str):
        if unit == "hours":
            try:
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    hours=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(member.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            except KeyError:
                self.mutes[member.id] = {}
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    hours=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(member.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            data = discord.Embed(colour=discord.Colour.orange())
            data.set_author(name="Automatic filter action")
            if member.avatar_url:
                data.set_thumbnail(url=member.avatar_url)
            data.add_field(name="Action: Muted " + member.name + " for " + str(duration) + " " + unit + "!",
                           value="Reason: " + reason)
            await self.appendmodlog(data, member.server)
        elif unit == "minutes":
            try:
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    minutes=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(member.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            except KeyError:
                self.mutes[member.id] = {}
                cooldown = datetime.datetime.now() + datetime.timedelta(
                    minutes=duration)
                self.mutes[member.id]['time'] = cooldown.strftime('%Y-%m-%d %H:%M')
                self.mutes[member.id]['reason'] = reason
                dataIO.save_json("data/modenhanced/mutes.json",
                                 self.mutes)
                role = discord.utils.get(member.server.roles, name='Muted')
                await self.bot.add_roles(member, role)
            data = discord.Embed(colour=discord.Colour.orange())
            if user.avatar_url:
                data.set_thumbnail(url=user.avatar_url)
            data.set_author(name="Automatic filter action")
            data.add_field(name="Action: Muted " + member.name + " for " + str(duration) + " " + unit + "!",
                           value="Reason: " + reason)
            await self.appendmodlog(data, member.server)

    def count_ignored(self):
        msg = "```Currently ignoring:\n"
        msg += str(len(self.ignore_list["CHANNELS"])) + " channels\n"
        msg += str(len(self.ignore_list["SERVERS"])) + " servers\n```\n"
        return msg

    @commands.group(name="filter", pass_context=True, no_pm=True)
    async def _filter(self, ctx):
        """Adds/removes words from filter
        Use double quotes to add/remove sentences
        Using this command with no subcommands will send
        the list of the server's filtered words."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            server = ctx.message.server
            author = ctx.message.author
            msg = ""
            mute_filter = " "
            ban_filter = " "
            none_filter = " "
            if server.id in self.filter.keys():
                if self.filter[server.id] != []:
                    word_list = self.filter[server.id]
                    data2 = discord.Embed(color=discord.Colour.blue())
                    data2.set_author(name="Filter List")
                    for w in word_list:
                        if self.filter[server.id][w]["action"] == "mute":
                            mute_filter += w + " (Duration: " + str(self.filter[server.id][w]["duration"]) + " " + 
                                           self.filter[server.id][w]["unit"] + ") "
                            continue
                        elif self.filter[server.id][w]["action"] == "ban":
                            ban_filter += w + ", "
                            continue
                        else:
                            none_filter += w + ", "
                    data2.add_field(name="Filter Action: Mute",
                                    value=mute_filter, inline=False)
                    data2.add_field(name="Filter Action: Ban",
                                    value=ban_filter, inline=False)
                    data2.add_field(name="Filter Action: Delete",
                                    value=none_filter, inline=False)
                    await self.bot.send_message(author, embed=data2)

    @_filter.command(name="add", pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def filter_add(self, ctx, action: str, word: str, duration=0, unit="", ):
        """Adds words to the filter
        Use double quotes to add sentences
        Examples:
        filter add word1 word2 word3
        filter add \"This is a sentence\""""
        if word == ():
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        added = 0
        if server.id not in self.filter.keys():
            self.filter[server.id] = {}
        if word.lower() not in self.filter[server.id] and word != "":
            if action == 'mute':
                if (duration <= 0) or (unit == ""):
                    if (unit != "minutes") or (unit != "hours"):
                        await self.bot.say("You need to supply a valid duration for auto muting!")
                        return
            self.filter[server.id][word] = {}
            self.filter[server.id][word]["action"] = action;
            self.filter[server.id][word]["duration"] = duration;
            self.filter[server.id][word]["unit"] = unit;
            added += 1
        if added:
            dataIO.save_json("data/modenhanced/filter.json", self.filter)
            await self.bot.say("Words added to filter.")
        else:
            await self.bot.say("Words already in the filter.")

    @_filter.command(name="remove", pass_context=True)
    async def filter_remove(self, ctx, *words: str):
        """Remove words from the filter
        Use double quotes to remove sentences
        Examples:
        filter remove word1 word2 word3
        filter remove \"This is a sentence\""""
        if words == ():
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        removed = 0
        if server.id not in self.filter.keys():
            await self.bot.say("There are no filtered words in this server.")
            return
        for w in words:
            if w.lower() in self.filter[server.id]:
                del self.filter[server.id][w]
                removed += 1
        if removed:
            dataIO.save_json("data/modenhanced/filter.json", self.filter)
            await self.bot.say("Words removed from filter.")
        else:
            await self.bot.say("Those words weren't in the filter.")

    @commands.group(name="role", no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def _roles(self, ctx):
        """Adds / Removes roles from a given user."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_roles.command(name="add", pass_context=True)
    async def _rolesadd(self, ctx, user: discord.Member, role: str, reason: str="No Reason"):
        """Adds a role from a given user."""
        server = ctx.message.server
        try:
            srole = discord.utils.get(ctx.message.server.roles, name=role)
        except:
            await self.bot.say("Role not found!")
            return
        if srole not in [r for r in user.roles]:
            try:
                await self.bot.add_roles(user, srole)
                await self.bot.say("Role has been added to the user!")
                roles = [x.name for x in user.roles if x.name != "@everyone"]
                if roles:
                    roles = sorted(roles, key=[x.name for x in server.role_hierarchy
                                               if x.name != "@everyone"].index)
                    roles = ", ".join(roles)
                else:
                    roles = "None"
                data = discord.Embed(colour=discord.Colour.blue())
                data.set_author(name="Moderation Log")
                if user.avatar_url:
                    data.set_thumbnail(url=user.avatar_url)
                data.add_field(name="Action: Added Role " + srole.name + " to user " + user.name + "!",
                               value="Reason: " + reason)
                data.add_field(name="Roles", value=roles, inline=False)
                await self.appendmodlog(data, ctx.message.author.server)
            except:
                await self.bot.say("An Error occured!")
        else:
            await self.bot.say("User already got the role!")

    @_roles.command(name="remove", pass_context=True)
    async def _rolesremove(self, ctx, user: discord.Member, role: str, reason: str="No Reason"):
        """Removes a role from a given user."""
        try:
            srole = discord.utils.get(ctx.message.server.roles, name=role)
        except:
            await self.bot.say("Role not found!")
            return
        if srole in [r for r in user.roles]:
            await self.bot.remove_roles(user, srole)
            await self.bot.say("Role has been removed from the user!")
            roles = [x.name for x in user.roles if x.name != "@everyone"]
            if roles:
                roles = sorted(roles, key=[x.name for x in ctx.message.server.role_hierarchy
                                           if x.name != "@everyone"].index)
                roles = ", ".join(roles)
            else:
                roles = "None"
            data = discord.Embed(colour=discord.Colour.blue())
            if user.avatar_url:
                data.set_thumbnail(url=user.avatar_url)
            data.set_author(name="Moderation Log")
            data.add_field(name="Action: Added Role " + srole.name + " to user " + user.name + "!",
                           value="Reason: " + reason)
            data.add_field(name="Roles", value=roles, inline=False)
            await self.appendmodlog(data, ctx.message.author.server)
        else:
            await self.bot.say("User does not have the role!")

    @commands.group(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def editrole(self, ctx):
        """Edits roles settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @editrole.command(aliases=["color"], pass_context=True)
    async def colour(self, ctx, role: discord.Role, value: discord.Colour):
        """Edits a role's colour
        Use double quotes if the role contains spaces.
        Colour must be in hexadecimal format.
        \"http://www.w3schools.com/colors/colors_picker.asp\"
        Examples:
        !editrole colour \"The Transistor\" #ff0000
        !editrole colour Test #ff9900"""
        author = ctx.message.author
        try:
            await self.bot.edit_role(ctx.message.server, role, color=value)
            logger.info("{}({}) changed the colour of role '{}'".format(
                author.name, author.id, role.name))
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I need permissions to manage roles first.")
        except Exception as e:
            print(e)
            await self.bot.say("Something went wrong.")

    @editrole.command(name="name", pass_context=True)
    @checks.admin_or_permissions(administrator=True)
    async def edit_role_name(self, ctx, role: discord.Role, name: str):
        """Edits a role's name
        Use double quotes if the role or the name contain spaces.
        Examples:
        !editrole name \"The Transistor\" Test"""
        if name == "":
            await self.bot.say("Name cannot be empty.")
            return
        try:
            author = ctx.message.author
            old_name = role.name  # probably not necessary?
            await self.bot.edit_role(ctx.message.server, role, name=name)
            logger.info("{}({}) changed the name of role '{}' to '{}'".format(
                author.name, author.id, old_name, name))
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I need permissions to manage roles first.")
        except Exception as e:
            print(e)
            await self.bot.say("Something went wrong.")

    @commands.command()
    async def names(self, user: discord.Member):
        """Show previous names/nicknames of a user"""
        server = user.server
        names = self.past_names[user.id] if user.id in self.past_names else None
        try:
            nicks = self.past_nicknames[server.id][user.id]
            nicks = [escape_mass_mentions(nick) for nick in nicks]
        except:
            nicks = None
        msg = ""
        if names:
            names = [escape_mass_mentions(name) for name in names]
            msg += "**Past 20 names**:\n"
            msg += ", ".join(names)
        if nicks:
            if msg:
                msg += "\n\n"
            msg += "**Past 20 nicknames**:\n"
            msg += ", ".join(nicks)
        if msg:
            await self.bot.say(msg)
        else:
            await self.bot.say("That user doesn't have any recorded name or "
                               "nickname change.")

    @commands.command(name="warn", pass_context=True)
    async def warning(self, ctx, member: discord.Member, rulenumber: str, reason):
        try:
            points = int(self.warnings[member.id]["points"])
            points += 1
            ts = datetime.datetime.now().strftime('%Y-%m-%d')
            self.warnings[member.id]["points"] = points
            tempreason = "Rule Number " + rulenumber + "- " + reason
            try:
                self.warnings[member.id]["reasons"][ts] = self.warnings[member.id]["reasons"][ts] + ";" + tempreason
            except KeyError:
                self.warnings[member.id]["reasons"][ts] = {}
                self.warnings[member.id]["reasons"][ts] = tempreason
            data = discord.Embed(description="Warning", color=discord.Colour.blue())
            data.set_author(name="Moderation Log")
            if member.avatar_url:
                data.set_thumbnail(url=member.avatar_url)
            data.add_field(
                name="Action: Warned " + member.name + "! - Rule # " + str(rulenumber) + " - " + self.rules[rulenumber],
                value="Reason: " + reason)
            await self.appendmodlog(data, member.server)

            data2 = discord.Embed(description="Warning", color=discord.Colour.red())
            data2.set_author(name="Moderation Message")
            data2.add_field(name="**This is a warning message from the " + ctx.message.server.name + " server**",
                            value="You have received a warning point for breaking the rule: #" + str(rulenumber)
                                  + " - " + self.rules[rulenumber] + "\n"
                                + "\nReason: " + reason, inline=False)
            data2.add_field(
                name="You now have **" + str(self.warnings[member.id]["points"]) + "** warning points in total.\n",
                value="If your account reaches 3 warning points, it will be reviewed by the staff team.\n",
                inline=False)
            data2.set_footer(
                text="For a complete list of " + ctx.message.server.name + " rules, please see the #intro channel")

            await self.bot.send_message(member, embed=data2)
            print("pmed")
            await self.bot.say("User has been warned.")
            if (self.warnings[member.id]["points"] >= 3):
                data = discord.Embed(description="Warning Excess", colour=discord.Colour.red())
                if member.avatar_url:
                    name = str(member)
                    name = " ~ ".join((name, member.nick)) if member.nick else name
                    data.set_author(name=name, url=member.avatar_url)
                    data.set_thumbnail(url=member.avatar_url)
                else:
                    data.set_author(name=member.name)
                times = self.warnings[member.id]["reasons"]
                i = 1
                for time in times:
                    msg = ""
                    reasons = self.warnings[member.id]["reasons"][time].split(";")
                    msg += "Reasons: \n"
                    for temporeason in reasons:
                        msg += temporeason
                        msg += "\n"
                    data.add_field(name="Date: " + str(time), value=msg, inline=False)
                await self.appendinternal(data, member.server)
            dataIO.save_json("data/modenhanced/warnings.json", self.warnings)
        except KeyError:
            ts = datetime.datetime.now().strftime('%Y-%m-%d')
            self.warnings[member.id] = {}
            self.warnings[member.id]["points"] = 1
            self.warnings[member.id]["reasons"] = {}
            self.warnings[member.id]["reasons"][ts] = {}
            tempreason = "Rule Number " + rulenumber + "- " + reason
            self.warnings[member.id]["reasons"][ts] = reason
            data = discord.Embed(description="Warning", color=discord.Colour.red())
            if member.avatar_url:
                data.set_thumbnail(url=member.avatar_url)
            data.set_author(name="Moderation Log")
            data.add_field(name="Action: Warned " + member.name + "! - Rule # "+ str(rulenumber) + " - " + self.rules[rulenumber] , value="Reason: " + reason)
            await self.appendmodlog(data, member.server)
            await self.bot.say("User has been warned.")

            data2 = discord.Embed(description="Warning", color=discord.Colour.red())
            data2.set_author(name="Moderation Message")
            data2.add_field(name="**This is a warning message from the " + ctx.message.server.name + " server**",
                            value="You have received a warning point for breaking the rule: #" + str(rulenumber)
                                  + " - " + self.rules[rulenumber] + "\n"
                                  "\nReason: " + reason, inline=False)
            data2.add_field(
                name="You now have **" + str(self.warnings[member.id]["points"]) + "** warning points in total.\n",
                value="If your account reaches 3 warning points, it will be reviewed by the staff team.\n",
                inline=False)
            data2.set_footer(
                text="For a complete list of " + ctx.message.server.name + " rules, please see the #intro channel")

            await self.bot.send_message(member, embed=data2)
            dataIO.save_json("data/modenhanced/warnings.json", self.warnings)
            # await self.bot.send_message(ctx.message.author, "das ist ein test")

    @commands.command(name="flushwarn", pass_context=True)
    async def flush_warning(self, ctx, member: discord.Member):
        try:
            del (self.warnings[member.id])
            await self.bot.say("<insert funny toilet joke here> - done.")
        except:
            await self.bot.say("An error occured!")

    async def auto_warning(self, member: discord.Member, reason):
        try:
            points = int(self.warnings[member.id]["points"])
            points += 1
            ts = datetime.datetime.now().strftime('%Y-%m-%d')
            self.warnings[member.id]["points"] = points
            try:
                self.warnings[member.id]["reasons"][ts] = self.warnings[member.id]["reasons"][
                                                              ts] + ";" + "Automute for " + reason
            except KeyError:
                self.warnings[member.id]["reasons"][ts] = {}
                self.warnings[member.id]["reasons"][ts] = "Automute for " + reason
            data = discord.Embed(description="Warning", color=discord.Colour.blue())
            if member.avatar_url:
                data.set_thumbnail(url=member.avatar_url)
            data.set_author(name="Automatic Warning")
            data.add_field(name="Action: Warned " + member.name + "!", value="Reason: " + reason)
            await self.appendmodlog(data, member.server)

            data2 = discord.Embed(description="Warning", color=discord.Colour.red())
            data2.set_author(name="Automatic Warning")
            data2.add_field(name="**This is a warning message from the " + member.server.name + " server**",
                            value="You have received a warning point for triggering the filter."
                                  + "\n"
                                    "Reason: " + reason, inline=False)
            data2.add_field(
                name="You now have **" + str(self.warnings[member.id]["points"]) + "** warning points in total.\n",
                value="If your account reaches 3 warning points, it will be reviewed by the staff team.\n",
                inline=False)
            data2.set_footer(
                text="For a complete list of " + member.server.name + " rules, please see the #intro channel")

            await self.bot.send_message(member, embed=data2)
            # await self.bot.send_message(member,message)
            print("pmed")
            if (self.warnings[member.id]["points"] >= 3):
                data = discord.Embed(description="Warning Excess", colour=discord.Colour.red())
                if member.avatar_url:
                    name = str(member)
                    name = " ~ ".join((name, member.nick)) if member.nick else name
                    data.set_author(name=name, url=member.avatar_url)
                    data.set_thumbnail(url=member.avatar_url)
                else:
                    data.set_author(name=member.name)
                times = self.warnings[member.id]["reasons"]
                i = 1
                for time in times:
                    msg = ""
                    reasons = self.warnings[member.id]["reasons"][time].split(";")
                    msg += "Reasons: \n"
                    for temporeason in reasons:
                        msg += temporeason
                        msg += "\n"
                    data.add_field(name="Date: " + str(time), value=msg, inline=False)
                await self.appendinternal(data, member.server)
            dataIO.save_json("data/modenhanced/warnings.json", self.warnings)
        except KeyError:
            ts = datetime.datetime.now().strftime('%Y-%m-%d')
            self.warnings[member.id] = {}
            self.warnings[member.id]["points"] = 1
            self.warnings[member.id]["reasons"] = {}
            self.warnings[member.id]["reasons"][ts] = {}
            self.warnings[member.id]["reasons"][ts] = "Automute for " + reason
            data = discord.Embed(description="Warning", color=discord.Colour.red())
            data.set_author(name="Automatic Warning")
            if member.avatar_url:
                data.set_thumbnail(url=member.avatar_url)
            data.add_field(name="Action: Warned " + member.name + "!", value="Reason: " + reason)
            await self.appendmodlog(data, member.server)

            data2 = discord.Embed(description="Warning", color=discord.Colour.red())
            data2.set_author(name="Automatic Warning")
            data2.add_field(name="**This is a warning message from the " + member.server.name + " server**",
                            value="You have received a warning point for triggering the filter."
                                  + "\n"
                                    "Reason: " + reason, inline=False)
            data2.add_field(
                name="You now have **" + str(self.warnings[member.id]["points"]) + "** warning points in total.\n",
                value="If your account reaches 3 warning points, it will be reviewed by the staff team.\n",
                inline=False)
            data2.set_footer(
                text="For a complete list of " + member.server.name + " rules, please see the #intro channel")

            await self.bot.send_message(member, embed=data2)
            dataIO.save_json("data/modenhanced/warnings.json", self.warnings)
            # await self.bot.send_message(ctx.message.author, "das ist ein test")

    @commands.command(name="warnlist", pass_context=True)
    async def warninglist(self, ctx,member:discord.Member = None, limit: int = 10):
        if member == None:
            msg = ""
            highest = 0
            highestelem = None
            temp = dict(self.warnings)
            for i in range(0, limit):
                for user in temp:
                    if temp[user]["points"] > highest:
                        highestelem = user
                        highest = temp[user]["points"]
                try:
                    tempo = self.warnings[highestelem]["points"]
                    member = ctx.message.server.get_member(highestelem)
                    msg += str(member.name) + " : " + str(tempo) + "\n"
                except KeyError:
                    break
                del (temp[highestelem])
                highest = 0
                highestelem = None
                await self.bot.say(msg)
        else:
            data = discord.Embed(description="Warning List", colour=discord.Colour.red())
            if member.avatar_url:
                name = str(member)
                name = " ~ ".join((name, member.nick)) if member.nick else name
                data.set_author(name=name, url=member.avatar_url)
                data.set_thumbnail(url=member.avatar_url)
            else:
                data.set_author(name=member.name)
            times = self.warnings[member.id]["reasons"]
            for time in times:
                msg = ""
                reasons = self.warnings[member.id]["reasons"][time].split(";")
                msg += "Reasons: \n"
                for temporeason in reasons:
                    msg += temporeason
                    msg += "\n"
                data.add_field(name="Date: " + str(time), value=msg, inline=False)
            await self.bot.say(embed=data)

    async def mass_purge(self, messages):
        while messages:
            if len(messages) > 1:
                await self.bot.delete_messages(messages[:100])
                messages = messages[100:]
            else:
                await self.bot.delete_message(messages)
            await asyncio.sleep(1.5)

    async def slow_deletion(self, messages):
        for message in messages:
            try:
                await self.bot.delete_message(message)
            except:
                pass
            await asyncio.sleep(1.5)

    def is_mod_or_superior(self, message):
        user = message.author
        server = message.server
        admin_role = settings.get_server_admin(server)
        mod_role = settings.get_server_mod(server)

        if user.id == settings.owner:
            return True
        elif discord.utils.get(user.roles, name=admin_role):
            return True
        elif discord.utils.get(user.roles, name=mod_role):
            return True
        else:
            return False

    async def check_filter(self, message):
        server = message.server
        if server.id in self.filter.keys():
            for w in self.filter[server.id]:
                regex = re.compile(w)
                test = regex.match(message.content.lower())
                if re.search(regex, message.content.lower()):
                    # Something else in discord.py is throwing a 404 error
                    # after deletion
                    # try:
                    await self.bot.delete_message(message)
                    if (self.filter[server.id][w]["action"] == "mute"):
                        await self.auto_warning(message.author, "Using the blacklisted word " + w + "!")
                        await self.auto_mute(message.author,
                                             self.filter[server.id][w]["duration"],
                                             self.filter[server.id][w]["unit"],
                                             "For using the blacklisted word " + w + "!")
                        return True
                    if self.filter[server.id][w]["action"] == "ban":
                        await self.auto_ban(message.author, 0, "For using the blacklisted word " + w + "!")
                        return True

                    if self.filter[server.id][w]["action"] == "kick":
                        await self.auto_kick(message.author, "using the blacklisted word " + w + "!")
                        return True
                        # except:
                        # pass
                    try:
                        data = discord.Embed(colour=discord.Colour.green())
                        if message.author.avatar_url:
                            data.set_thumbnail(url=message.author.avatar_url)
                        data.set_author(name="Automatic Action")
                        data.add_field(
                            name="Action: Deleted Message \"" + message.content + "\" of user " + message.author.name + "!",
                            value="Reason: Contains blacklisted word \"" + w + "\"")
                        await self.appendmodlog(data, message.server)
                        return True
                    except:
                        print("Message deleted. Filtered: " + w)

    async def check_spammychars(self, message):
        if (self.settings["spamdelete"]):
            match2 = re.split("[\n]{4,}", message.content)
            match = re.split(r"(.)\1{9,}", message.content)
            if len(match) > 1 or len(match2) > 1:
                await self.bot.delete_message(message)
                data = discord.Embed(description="Spammychar")
                if message.author.avatar_url:
                    data.set_thumbnail(url=message.author.avatar_url)
                data.set_author(name=message.author.name)
                data.add_field(name="Deleted Message for spammylooking characters", value=message.content)
                await self.appendmodlog(data, message.server)
                return True

    async def check_duplicates(self, message):
        server = message.server
        author = message.author
        if server.id not in self.settings:
            return False
        if self.settings[server.id]["delete_repeats"]:
            self.cache[author].append(message)
            msgs = self.cache[author]
            if len(msgs) == 3 and \
                                    msgs[0].content == msgs[1].content == msgs[2].content:
                if any([m.attachments for m in msgs]):
                    return False
                try:
                    await self.bot.delete_message(message)
                    return True
                except:
                    pass
        return False

    async def check_mention_spam(self, message):
        server = message.server
        author = message.author
        if server.id not in self.settings:
            return False
        if self.settings[server.id]["ban_mention_spam"]:
            max_mentions = self.settings[server.id]["ban_mention_spam"]
            mentions = set(message.mentions)
            if len(mentions) >= max_mentions:
                try:
                    self._tmp_banned_cache.append(author)
                    await self.bot.ban(author, 1)
                except:
                    logger.info("Failed to ban member for mention spam in "
                                "server {}".format(server.id))
                else:
                    await self.new_case(server,
                                        action="Ban \N{HAMMER}",
                                        mod=server.me,
                                        user=author,
                                        reason="Mention spam (Autoban)")
                    return True
                finally:
                    await asyncio.sleep(1)
                    self._tmp_banned_cache.remove(author)
        return False

    async def on_member_join(self, member):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        await self.appendserverlog("`" + ts + "` :white_check_mark: __**" + member.name + "#" + str(
            member.discriminator) + "**__ *(" + member.id + ")* **joined the server**", member.server)

    async def on_member_remove(self, member):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        await self.appendserverlog("`" + ts + "` :no_entry: __**" + member.name + "#" + str(
            member.discriminator) + "**__ *(" + member.id + ")* **left the server**", member.server)

    async def on_member_ban(self, member):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        await self.appendserverlog("`" + ts + "` :hammer: __**" + member.name + "#" + str(
            member.discriminator) + "**__ *(" + member.id + ")* **has been banned from the server**", member.server)


            # async def rate_limit(self, message):
        #   rate = 5.0; // unit: messages
        #  per  = 8.0; // unit: seconds
        # allowance = rate; // unit: messages
        # last_check = now(); // floating-point, e.g. usec accuracy. Unit: seconds

    #
    #       when (message_received):
    #          current = now();
    #         time_passed = current - last_check;
    #        last_check = current;
    #       allowance += time_passed * (rate / per);
    #      if (allowance > rate):
    #         allowance = rate; // throttle
    #    if (allowance < 1.0):
    #       discard_message();
    #  else:
    #     forward_message();
    #    allowance -= 1.0;

    async def on_message_delete(self, message):
        if message.channel.is_private or self.bot.user == message.author:
            return
        current_ch = message.channel
        if current_ch.id in self.ignore_list["CHANNELS"]:
            return
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        if len(message.content) > 40:
            await self.appendserverlog(
                "`" + ts + "` " + message.channel.mention + ":paintbrush: **" + message.author.name + "#" + str(
                    message.author.discriminator) + "** *deleted his/her message* \n " + message.content + "",
                message.server)
        else:
            await self.appendserverlog(
                "`" + ts + "` " + message.channel.mention + ":paintbrush: **" + message.author.name + "#" + str(
                    message.author.discriminator) + "** *deleted his/her message* \n " + message.content + "",
                message.server)

    async def on_message_edit(self, before, after):
        if before.channel.is_private or self.bot.user == before.author:
            return
        current_ch = before.channel
        if before.content == after.content:
            return
        if current_ch.id in self.ignore_list["CHANNELS"]:
            return
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        await self.appendserverlog(
            "`" + ts + "` " + before.channel.mention + " :pencil2: **" + before.author.name + "#" + str(
                before.author.discriminator) + "** *edited his/her message:* " +
            "\n**Original:** \n " + before.clean_content + " \n" +
            "**Update:** \n " + after.clean_content, before.server)

    async def on_member_update(self, before, after):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        if before.nick != after.nick:
            if after.nick is None:
                await self.appendserverlog("`" + ts + "` :pencil: **" + before.name + "#" + str(
                    before.discriminator) + "** removed his/her nickname!", before.server)
                return
            if before.nick is None:
                await self.appendserverlog("`" + ts + "` :pencil: **" + before.name + "#" + str(
                    before.discriminator) + "** *changed his/her nickname from* " +
                                           "`" + before.name + "`" + " to `" + after.nick + "`", before.server)
                return
            else:
                await self.appendserverlog("`" + ts + "` :pencil: **" + before.name + "#" + str(
                    before.discriminator) + "** *changed his/her name from* " +
                                           "`" + before.nick + "` to `" + after.nick + "`", before.server)
                return

        if before.roles != after.roles:
            rolesb = [x.name for x in before.roles if x.name != "@everyone"]
            if rolesb:
                rolesb = sorted(rolesb, key=[x.name for x in before.server.role_hierarchy
                                             if x.name != "@everyone"].index)
                rolesb = ", ".join(rolesb)
            else:
                rolesb = "None"

            rolesa = [x.name for x in after.roles if x.name != "@everyone"]
            if rolesa:
                rolesa = sorted(rolesa, key=[x.name for x in after.server.role_hierarchy
                                             if x.name != "@everyone"].index)
                rolesa = ", ".join(rolesa)
            else:
                rolesa = "None"
            await self.appendserverlog("`" + ts + "` :label: **" + before.name + "#" + str(
                before.discriminator) + "** *roles have changed* \n" +
                                       "**Original: **" + rolesb + "\n" +
                                       "**Update: **" + rolesa, before.server)

    async def on_message(self, message):
        if message.channel.is_private or self.bot.user == message.author:
            return
        elif self.is_mod_or_superior(message):
            return
        current_ch = message.channel
        if current_ch.id in self.ignore_list["CHANNELS"]:
            return
        deleted = await self.check_filter(message)
        if not deleted:
            deleted = await self.check_duplicates(message)
        if not deleted:
            deleted = await self.check_mention_spam(message)
        if not deleted:
            deleted = await self.check_spammychars(message)

    async def mute_check(self):
        CHECK_DELAY = 60
        while self == self.bot.get_cog("modenhanced"):
            currenttime = datetime.datetime.now()
            self.mutes = dataIO.load_json("data/modenhanced/mutes.json")
            for mute in self.mutes:
                if currenttime > datetime.datetime.strptime(self.mutes[mute]['time'], '%Y-%m-%d %H:%M'):
                    mydict = {k: v for k, v in self.mutes.items() if k != mute}
                    server = self.bot.get_server(self.settings["serverid"])
                    member = server.get_member(mute)
                    role = discord.utils.get(member.server.roles, name='Muted')
                    await self.bot.remove_roles(member, role)
                    dataIO.save_json("data/modenhanced/mutes.json", mydict)
                    data = discord.Embed(colour=discord.Colour.blue())
                    data.set_author(name="Automatic Action")
                    data.add_field(name="Action: Unmuted " + member.name + "!", value="Reason: No Reason needed.")
                    await self.appendmodlog(data, member.server)
            await asyncio.sleep(CHECK_DELAY)

    async def check_names(self, before, after):
        if before.name != after.name:
            if before.id not in self.past_names.keys():
                self.past_names[before.id] = [after.name]
            else:
                if after.name not in self.past_names[before.id]:
                    names = deque(self.past_names[before.id], maxlen=20)
                    names.append(after.name)
                    self.past_names[before.id] = list(names)
            dataIO.save_json("data/modenhanced/past_names.json", self.past_names)

        if before.nick != after.nick and after.nick is not None:
            server = before.server
            if server.id not in self.past_nicknames:
                self.past_nicknames[server.id] = {}
            if before.id in self.past_nicknames[server.id]:
                nicks = deque(self.past_nicknames[server.id][before.id],
                              maxlen=20)
            else:
                nicks = []
            if after.nick not in nicks:
                nicks.append(after.nick)
                self.past_nicknames[server.id][before.id] = list(nicks)
                dataIO.save_json("data/modenhanced/past_nicknames.json",
                                 self.past_nicknames)

    async def appendmodlog(self, data: discord.Embed, server):
        if (self.settings[server.id]["mod-log"] == None):
            return
        channel = self.settings[server.id]["mod-log"]
        channel_obj = self.bot.get_channel(channel)
        can_speak = channel_obj.permissions_for(channel_obj.server.me).send_messages
        if channel_obj and can_speak:
            await self.bot.send_message(
                self.bot.get_channel(channel),
                embed=data)

    async def appendmodlog_ne(self, msg: str, server):
        if (self.settings[server.id]["mod-log"] == None):
            return
        channel = self.settings[server.id]["mod-log"]
        channel_obj = self.bot.get_channel(channel)
        can_speak = channel_obj.permissions_for(channel_obj.server.me).send_messages
        if channel_obj and can_speak:
            await self.bot.send_message(
                self.bot.get_channel(channel),
                msg)

    async def appendserverlog(self, msg:str, server):
        if (self.settings[server.id]["server-log"] == None):
            return
        channel = self.settings[server.id]["server-log"]
        channel_obj = self.bot.get_channel(channel)
        can_speak = channel_obj.permissions_for(channel_obj.server.me).send_messages
        if channel_obj and can_speak:
            await self.bot.send_message(
                self.bot.get_channel(channel),
                msg)

    async def appendinternal(self, data: discord.Embed, server):
        if (self.settings[server.id]["int-mod-log"] == None):
            return
        channel = self.settings[server.id]["int-mod-log"]
        channel_obj = self.bot.get_channel(channel)
        can_speak = channel_obj.permissions_for(channel_obj.server.me).send_messages
        if channel_obj and can_speak:
            await self.bot.send_message(
                self.bot.get_channel(channel),
                embed=data)


def check_folders():
    folders = ("data", "data/modenhanced/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    ignore_list = {"SERVERS": [], "CHANNELS": []}

    if not os.path.isfile("data/modenhanced/mutes.json"):
        print("Creating empty mutes.json...")
        dataIO.save_json("data/modenhanced/mutes.json", {})

    if not os.path.isfile("data/modenhanced/blacklist.json"):
        print("Creating empty blacklist.json...")
        dataIO.save_json("data/modenhanced/blacklist.json", [])

    if not os.path.isfile("data/modenhanced/whitelist.json"):
        print("Creating empty whitelist.json...")
        dataIO.save_json("data/modenhanced/whitelist.json", [])

    if not os.path.isfile("data/modenhanced/ignorelist.json"):
        print("Creating empty ignorelist.json...")
        dataIO.save_json("data/modenhanced/ignorelist.json", ignore_list)

    if not os.path.isfile("data/modenhanced/filter.json"):
        print("Creating empty filter.json...")
        dataIO.save_json("data/modenhanced/filter.json", {})

    if not os.path.isfile("data/modenhanced/past_names.json"):
        print("Creating empty past_names.json...")
        dataIO.save_json("data/modenhanced/past_names.json", {})

    if not os.path.isfile("data/modenhanced/past_nicknames.json"):
        print("Creating empty past_nicknames.json...")
        dataIO.save_json("data/modenhanced/past_nicknames.json", {})

    if not os.path.isfile("data/modenhanced/settings.json"):
        print("Creating empty settings.json...")
        dataIO.save_json("data/modenhanced/settings.json", {})

    if not os.path.isfile("data/modenhanced/modlog.json"):
        print("Creating empty modlog.json...")
        dataIO.save_json("data/modenhanced/modlog.json", {})

    if not os.path.isfile("data/modenhanced/warnings.json"):
        print("Creating empty warnings.json...")
        dataIO.save_json("data/modenhanced/warnings.json", {})

    if not os.path.isfile("data/modenhanced/rules.json"):
        print("Creating empty rules.json...")
        dataIO.save_json("data/modenhanced/rules.json", {})

    if not os.path.isfile("data/modenhanced/slowmode.json"):
        print("Creating empty rules.json...")
        dataIO.save_json("data/modenhanced/slowmode.json", {})


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("mod")
    # Prevents the logger from being loaded again in case of module reload
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename='data/modenhanced/mod.log', encoding='utf-8', mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = modenhanced(bot)
    bot.add_listener(n.check_names, "on_member_update")
    loop = asyncio.get_event_loop()
    loop.create_task(n.mute_check())
    bot.add_cog(n)


default_settings = {
    "ban_mention_spam": False,
    "delete_repeats": False,
    "mod-log": None
}


class ModError(Exception):
    pass


class UnauthorizedCaseEdit(ModError):
    pass


class CaseMessageNotFound(ModError):
    pass


class NoModLogChannel(ModError):
    pass
