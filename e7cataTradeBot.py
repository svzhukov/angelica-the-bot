from __future__ import annotations

import json
import uuid
import os
import random
import boto3
import discord
import jsonpickle
import configparser
import traceback
import inspect
import sys

from enum import IntEnum
from typing import List
from typing import Optional
from typing import Union
from discord.ext import commands
from pyaztro import Aztro
from time import time
from botocore.exceptions import ClientError


# region Context Event
class EventLogger():
    def __init__(self):
        self.pfx = ''
        self.target = ''
        self.invoker = ''
        self.guild = ''
        self.action = ''
        self.function = ''

    def __repr__(self):
        return "{}{}{}{}{}".format(self.action, self.target, self.function, self.invoker, self.guild)


    @staticmethod
    def logger(target: str, action: str = None, ctx=None):
        logger = EventLogger()
        try:
            logger.invoker = "{} <{}>".format(ctx.message.author, ctx.message.author.id)
            logger.guild = "{} <{}>".format(ctx.guild, ctx.guild.id)
            logger.action = action if action else "{}{}".format(ctx.prefix, ctx.command)
        except AttributeError:
            logger.action = action
        finally:
            logger.target = target
            logger.function = inspect.getframeinfo(inspect.currentframe().f_back.f_back).function
        return logger

    @staticmethod
    def log(target: str, action: str = None, ctx=None):
        logger = EventLogger.logger(target, action, ctx)
        print(logger)

    # region Properties
    @property
    def function(self):
        return " -> [{}]".format(self._function) if self._function else ''

    @function.setter
    def function(self, value):
        self._function = value

    @property
    def target(self):
        return " {}".format(self._target) if self._target else ''

    @target.setter
    def target(self, value):
        self._target = value

    @property
    def invoker(self):
        return " by {}".format(self._invoker) if self._invoker else ''

    @invoker.setter
    def invoker(self, value):
        self._invoker = value

    @property
    def guild(self):
        return " in {}".format(self._guild) if self._guild else ''

    @guild.setter
    def guild(self, value):
        self._guild = value

    @property
    def action(self):
        return "{} -".format(self._action) if self._action else ''

    @action.setter
    def action(self, value):
        self._action = value
    # endregion
# endregion


# region Classes
class Config:
    config = None

    @staticmethod
    def load():
        Config.setup_config()
        Config.set_env_vars()

    @staticmethod
    def setup_config():
        Config.config = configparser.ConfigParser()
        Config.config.read('config.ini')

    @staticmethod
    def set_env_vars():
        try:
            os.environ['CLOUDCUBE_ACCESS_KEY_ID'] = Config.config['DEFAULT']['CLOUDCUBE_ACCESS_KEY_ID']
            os.environ['CLOUDCUBE_SECRET_ACCESS_KEY'] = Config.config['DEFAULT']['CLOUDCUBE_SECRET_ACCESS_KEY']
            os.environ['DISCORD_BOT_TOKEN'] = Config.config['DEFAULT']['DISCORD_BOT_TOKEN']
            os.environ['DISCORD_BOT_PREFIX'] = Config.config['DEFAULT']['DISCORD_BOT_PREFIX']
            os.environ['DISCORD_BOT_PREFIX_SECOND'] = Config.config['DEFAULT']['DISCORD_BOT_PREFIX_SECOND']
            EventLogger.log("From config.ini", action="load")
        except KeyError:
            EventLogger.log("From os", action="load")


class S3FileManager:
    client = None

    bucket = 'cloud-cube-eu'
    key = 'ln75ki813ek6/public/'

    guild_ids_file_name = 'guild_ids.txt'
    guild_file_prefix = 'guild-'
    guild_file_suffix = '.json'

    guild_ids: List[int] = list()

    @staticmethod
    def load():
        EventLogger.log("S3FileManager", action="load")
        S3FileManager.setup_client()
        S3FileManager.download()

    @staticmethod
    def setup_client():
        S3FileManager.client = boto3.client(
            's3',
            aws_access_key_id=os.environ['CLOUDCUBE_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['CLOUDCUBE_SECRET_ACCESS_KEY'],
            region_name='eu-west-1')

    @staticmethod
    def download():
        S3FileManager.download_guild_ids()
        S3FileManager.download_guilds()

    @staticmethod
    def upload(ctx):
        # Save and upload guild_ids.txt if needed
        if ctx.guild.id not in S3FileManager.guild_ids:
            S3FileManager.guild_ids.append(ctx.guild.id)
            S3FileManager.upload_guild_ids()

        # Save and upload guild-<id>.json
        S3FileManager.upload_guild(ctx)

    @staticmethod
    def download_guild_ids():
        EventLogger.log(S3FileManager.guild_ids_file_name, action="download")
        try:
            S3FileManager.client.download_file(S3FileManager.bucket, S3FileManager.key + S3FileManager.guild_ids_file_name,
                                               S3FileManager.guild_ids_file_name)
            with open(S3FileManager.guild_ids_file_name, 'r') as f:
                S3FileManager.guild_ids = json.load(f)
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                S3FileManager.guild_ids = []
                S3FileManager.upload_guild_ids()

    @staticmethod
    def download_guilds():
        EventLogger.log("All guild-<id>.json", action="download")
        for guild in S3FileManager.guild_ids:
            S3FileManager.client.download_file(S3FileManager.bucket, S3FileManager.key + S3FileManager.file_name(guild),
                                               S3FileManager.file_name(guild))

    @staticmethod
    def upload_guild_ids():
        EventLogger.log(S3FileManager.guild_ids_file_name, action="upload")
        with open(S3FileManager.guild_ids_file_name, 'w') as f:
            json.dump(S3FileManager.guild_ids, f)
        S3FileManager.client.upload_file(S3FileManager.guild_ids_file_name, S3FileManager.bucket,
                                         S3FileManager.key + S3FileManager.guild_ids_file_name)

    @staticmethod
    def upload_guild(ctx):
        file = S3FileManager.file_name(ctx.guild.id)
        EventLogger.log(file, ctx=ctx, action="upload")
        with open(file, 'w') as f:
            json.dump(jsonpickle.encode(Guild.guild(ctx)), f)
        S3FileManager.client.upload_file(file, S3FileManager.bucket, S3FileManager.key + file)

    @staticmethod
    def file_name(guild_id) -> str:
        return S3FileManager.guild_file_prefix + str(guild_id) + S3FileManager.guild_file_suffix


class Guild:
    guilds: List[Guild] = list()

    def __init__(self, guild_id: int, name: str, users: List[User] = None, requests: List[Request] = None, bot_var: BotVar = None):
        self.id = guild_id
        self.name = name
        self.users = users if users else []
        self.requests = requests if requests else []
        self.bot_var = bot_var if bot_var else BotVar()

    def __repr__(self):
        return "{}-{}".format(self.name, self.id)

    def assign_admin_role(self, ctx, role: Union[int, str]):
        self.bot_var.admin_role = role
        S3FileManager.upload(ctx)

    def assign_min_score(self, ctx, score: int):
        self.bot_var.min_score = score
        S3FileManager.upload(ctx)

    @staticmethod
    # Finds and creates a new one if not found
    def guild(ctx) -> Guild:
        gld = Guild.find_guild(ctx)
        return gld if gld else Guild.add(ctx)

    @staticmethod
    def find_guild(ctx) -> Optional[Guild]:
        return next((guild for guild in Guild.guilds if guild.id == ctx.guild.id), None)

    @staticmethod
    def add(ctx) -> Guild:
        EventLogger.log("NEW trade hub {} is now open!".format(ctx.guild), ctx=ctx)
        gld = Guild(ctx.guild.id, ctx.guild.name)
        Guild.guilds.append(gld)
        return gld

    @staticmethod
    def load():
        EventLogger.log("Guilds[{}]".format(len(S3FileManager.guild_ids)), action="load")
        Guild.guilds = []
        for guild in S3FileManager.guild_ids:
            with open(S3FileManager.file_name(guild), 'r') as f:
                Guild.guilds.append(jsonpickle.decode(json.load(f)))


class Request:
    total_stages = 2
    points_per_stage = 1

    def __init__(self, guild_id: int, user_id: int, cata_id: uuid.UUID, date_created: float = None,
                 req_id: uuid.UUID = None, stage: int = None, active: bool = None):
        self.guild_id = guild_id
        self.id = req_id if req_id else uuid.uuid4()
        self.user_id = user_id
        self.cata_id = cata_id
        self.stage = stage if stage else 0
        self.active = active if active else True
        self.date_created = date_created if date_created else time()

    def __repr__(self):
        finished = " - finished" if self.is_complete() else ''
        return "{name} [{stage}/{total}{finished}]".format(name=self.name(), stage=self.stage, total=Request.total_stages, finished=finished)

    def stage_advance(self) -> bool:
        self.stage += 1
        self.active = False if self.is_complete() else True
        return self.active

    def name(self) -> str:
        return Catalyst.catalyst(self.cata_id).name

    def is_complete(self) -> bool:
        return self.stage == Request.total_stages

    def cancel(self):
        self.active = False

    @staticmethod
    def repr(ctx, req_id: uuid.UUID) -> str:
        return Request.find_request(ctx, req_id).__repr__() if Request.find_request(ctx, req_id) else "None"

    @staticmethod
    def requests(ctx) -> List[Request]:
        return Guild.guild(ctx).requests

    @staticmethod
    def find_request(ctx, req_id: uuid.UUID) -> Optional[Request]:
        return next((req for req in Request.requests(ctx) if req.id == req_id), None)

    @staticmethod
    def add(ctx, user_id: int, cata_id: uuid.UUID) -> Request:
        req = Request(ctx.guild.id, user_id, cata_id)
        EventLogger.log("Don't miss the fresh deal for {}<{}>!".format(req.name(), req.id), ctx=ctx)
        Guild.guild(ctx).requests.append(req)
        return req


class User:
    bot_dev_id = 118435077477761029

    class AdminRoleCheckError(commands.CommandError):
        def __init__(self, message: str = None):
            self.message = message if message else "Comand is restricted to bot admin role"

        def __repr__(self):
            return self.message

    class RoleManagementCheckError(commands.CommandError):
        def __init__(self, message: str = None):
            self.message = message if message else "Command requires discord role management permissions"

        def __repr__(self):
            return self.message

    def __init__(self, guild_id: int, user_id: int, name: str, score: int = None, request_id: uuid.UUID = None, assistance: int = None):
        self.guild_id = guild_id
        self.id = user_id
        self.name = name
        self.score = score if score else 0
        self.request_id = request_id if request_id else None
        self.assistance = assistance if assistance else 0

    def __repr__(self):
        return "{}-{}".format(self.name, self.id)

    def finished_request_count(self, ctx) -> int:
        return len([req for req in Request.requests(ctx) if req.user_id == self.id and not req.active and req.is_complete()])

    def assign_request(self, ctx, request: Request):
        self.request_id = request.id
        self.score -= Request.points_per_stage * Request.total_stages
        S3FileManager.upload(ctx)

    def request_cancel(self, ctx) -> int:
        score_refund = Request.points_per_stage * (Request.total_stages - Request.find_request(ctx, self.request_id).stage)
        self.score += score_refund
        Request.find_request(ctx, self.request_id).cancel()
        self.request_id = None
        S3FileManager.upload(ctx)
        return score_refund

    def thank(self, ctx, user: User):
        if user.id == self.id: return

        active = Request.find_request(ctx, self.request_id).stage_advance()
        self.request_id = self.request_id if active else None
        if user.id == bot.user.id:
            self.score += Request.points_per_stage
        elif user.id != self.id:
            user.score += Request.points_per_stage
            user.assistance += Request.points_per_stage
        S3FileManager.upload(ctx)

    def gift(self, ctx, user: User):
        if user.id != bot.user.id and user.id != self.id:
            self.score -= Request.points_per_stage
            self.assistance += Request.points_per_stage
            user.score += Request.points_per_stage
            S3FileManager.upload(ctx)

    def set_score(self, ctx, score: int):
        self.score = score
        S3FileManager.upload(ctx)

    @staticmethod
    def users(ctx) -> List[User]:
        return Guild.guild(ctx).users

    @staticmethod
    # Finds and creates a new one if not found
    def user(ctx, dc_user) -> User:
        usr = User.find_user(ctx, dc_user.id)
        return usr if usr else User.add(ctx, dc_user.id, dc_user.name)

    @staticmethod
    def find_user(ctx, user_id: int) -> Optional[User]:
        return next((usr for usr in User.users(ctx) if usr.id == user_id), None)

    @staticmethod
    def add(ctx, user_id: int, user_name: str) -> User:
        usr = User(ctx.guild.id, user_id, user_name)
        EventLogger.log("Welcome, new trader {} <{}>!".format(usr.name, usr.id), ctx=ctx)
        Guild.guild(ctx).users.append(usr)
        return usr

    @staticmethod
    def remove(ctx, user: User):
        EventLogger.log("Farewell, {} <{}>!".format(user.name, user.id), ctx=ctx)
        if user.request_id:
            Request.find_request(ctx, user.request_id).cancel()
        Guild.guild(ctx).users.remove(user)
        S3FileManager.upload(ctx)

    # Checks
    @staticmethod
    def has_bot_admin_role(ctx) -> bool:
        role = Guild.guild(ctx).bot_var.admin_role
        try:
            if int(role) in [role.id for role in ctx.message.author.roles]:
                return True
            else:
                raise User.AdminRoleCheckError

        except ValueError:
            if role in [role.name for role in ctx.message.author.roles]:
                return True
            else:
                raise User.AdminRoleCheckError

    @staticmethod
    def has_role_management_permissions(ctx) -> bool:
        if True in [role.permissions.manage_roles for role in ctx.message.author.roles] or ctx.message.author.id == ctx.guild.owner.id:
            return True
        else:
            raise User.RoleManagementCheckError


class Catalyst:
    catalysts: List[Catalyst] = list()

    class Rarity(IntEnum):
        rare = 1
        epic = 4

    def __init__(self, cata_id: uuid.UUID, sign_id: uuid.UUID, name: str, rarity_id: Catalyst.Rarity):
        self.id = cata_id
        self.sign_id = sign_id
        self.name = name
        self.rarity_id = rarity_id

    def __repr__(self):
        return "{} <{}>".format(self.name, self.id)

    @staticmethod
    def search(query: str) -> List[Catalyst]:
        return [cata for cata in Catalyst.catalysts if query.lower() in cata.name.lower()]

    @staticmethod
    def catalyst(cata_id: uuid.UUID) -> Catalyst:
        return next(cata for cata in Catalyst.catalysts if cata.id == cata_id)


class Sign:
    signs: List[Sign] = list()

    def __init__(self, sign_id: uuid.UUID, name: str, catas: List[Catalyst]):
        self.id = sign_id
        self.name = name
        self.catas = catas

    @staticmethod
    def all_names() -> List[str]:
        return [sign.name.lower() for sign in Sign.signs]

    @staticmethod
    def load():
        with open('catalysts.json', 'r') as f:
            Sign.signs = jsonpickle.decode(json.load(f))
            Catalyst.catalysts = [cata for cata_list in [sign.catas for sign in Sign.signs] for cata in cata_list]
            EventLogger.log("Signs[{}], Catalysts[{}]".format(len(Sign.signs), len(Catalyst.catalysts)), action="load")


class BotVar:
    default_role = 'Angelica\'s Crew'
    default_min_score = -6

    def __init__(self, admin_role: Union[str, int] = None, min_score: int = None):
        self.admin_role = admin_role if admin_role else BotVar.default_role
        self.min_score = min_score if min_score else BotVar.default_min_score


# endregion


# region Boot up
def load():
    Config.load()
    S3FileManager.load()
    Sign.load()
    Guild.load()


load()
# endregion


# region Commands
# Admin
bot = commands.Bot(command_prefix=(os.environ['DISCORD_BOT_PREFIX'], os.environ['DISCORD_BOT_PREFIX_SECOND']))
@bot.command(name='adminrole')
@commands.check(User.has_role_management_permissions)
async def com_admin_role(ctx, *args):
    if len(args):
        Guild.guild(ctx).assign_admin_role(ctx, ' '.join(args))
        await ctx.send("New bot admin role has been set to **" + ' '.join(args) + "**")
    else:
        await ctx.send("Current bot admin role is **{}**, to set a new one specify either role id or role name"
                       .format(Guild.guild(ctx).bot_var.admin_role))


@bot.command(name='minscore')
@commands.check(User.has_bot_admin_role)
async def com_min_score(ctx, score=None):
    try:
        Guild.guild(ctx).assign_min_score(ctx, int(score))
        await ctx.send("New minimum score has been set to **" + score + "**")
    except (ValueError, TypeError):
        await ctx.send("Current minimum score is **" + str(Guild.guild(ctx).bot_var.min_score) + "**, to set a new one specify a value")


@bot.command(name='cancel')
@commands.check(User.has_bot_admin_role)
async def com_cancel(ctx):
    try:
        user = User.find_user(ctx, ctx.message.mentions[0].id)

        score_refund = user.request_cancel(ctx)
        await ctx.send("**{}**'s active request is canceled, **{}** points are refunded back".format(user.name, score_refund))
    except (AttributeError, IndexError):
        await ctx.send("Nothing to cancel ¯\\_(ツ)_/¯")


@bot.command(name='remove')
@commands.check(User.has_bot_admin_role)
async def com_remove(ctx, user_id=None):
    try:
        remove_id = ctx.message.mentions[0].id if len(ctx.message.mentions) else int(user_id)
        User.remove(ctx, User.find_user(ctx, remove_id))
        await ctx.send("User **{}** has been removed".format(user_id))
    except (ValueError, AttributeError, TypeError):
        await ctx.send("User not found")


@bot.command(name='setscore')
@commands.check(User.has_bot_admin_role)
async def com_set_score(ctx, mention=None, value=None):
    try:
        user = User.user(ctx, ctx.message.mentions[0])
        user.set_score(ctx, int(value))
        await ctx.send("**{}**'s score successfully set to **{}**".format(user.name, user.score))
    except (ValueError, IndexError, TypeError, AttributeError):
        await ctx.send("Please provide correct arguments")


@bot.command(name='test')
@commands.check(User.has_bot_admin_role)
async def com_test(ctx, arg=None):
    pass


# All user
@bot.command(name='respond')
async def com_respond(ctx):
    print("Hello, I'm alive and responding!")
    await ctx.send("Hello, I'm alive and responding!")


@bot.command(name='board')
async def com_board(ctx):
    msg = "{} guild catalyst exchange board:\n".format(ctx.guild.name.capitalize())
    for user in User.users(ctx):
        msg += "**{}** - score: **{}**, request: **{}**, assistance: **[{}]**\n". \
            format(user.name, user.score, Request.repr(ctx, user.request_id), user.assistance)

    await ctx.send(msg)


@bot.command(name='request', aliases=['req'])
async def com_request(ctx, *args):
    query = ' '.join(args) if len(args) else ''
    user = User.user(ctx, ctx.message.author)
    catas = Catalyst.search(query)

    if user.request_id:
        await ctx.send("**{}**, you already have active request for **{}**".format(user.name, Request.repr(ctx, user.request_id)))
    elif len(query) < 3:
        await ctx.send("Provide at least **3** characters for catalyst name")
    elif len(catas) == 0:
        await ctx.send("No catalyst found")
    elif len(catas) > 1:
        await ctx.send("Found more than one catalyst, please specify")
    elif catas[0].rarity_id == Catalyst.Rarity.epic:
        await ctx.send("Can't request epic catalysts")
    elif user.score <= Guild.guild(ctx).bot_var.min_score:
        await ctx.send("**{}**, your exchange score **({})** has reached its minimum threshold **({})**."
                       " Aid other guild members to improve your score"
                       .format(user.name, user.score, Guild.guild(ctx).bot_var.min_score))
    else:
        request = Request.add(ctx, user.id, catas[0].id)
        user.assign_request(ctx, request)
        await ctx.send("**{}** has requested **{}**. User's new score: **{}**".format(user.name, request, user.score))


@bot.command(name='signs', aliases=['sign', 'horoscope'])
async def com_horoscope(ctx, query=None):
    if not query:
        await ctx.send("Here's the list of available zodiac signs: {}".format(Sign.all_names()))
    else:
        sign = query.lower() if query.lower() in Sign.all_names() else random.choice(Sign.all_names())
        print(sign)
        await ctx.send(Aztro(sign=sign).description)


@bot.command(name='thank', aliases=['thanks'])
async def com_thank(ctx):
    try:
        mention = User.user(ctx, ctx.message.mentions[0])
        author = User.find_user(ctx, ctx.message.author.id)
        request = Request.find_request(ctx, author.request_id)
        if mention.id == ctx.message.author.id:
            await ctx.send("Don't do that!")
        else:
            author.thank(ctx, mention)
            msg = "No problem :blush:, here's a blessing from the Goddess for you **+1** :pray:! **{}**'s request: **{}**" \
                .format(author.name, request) if mention.id == bot.user.id else \
                "Thanks for the assistance, **{}**, here's your **+1** :thumbsup:! **{}**'s request: **{}**" \
                    .format(mention.name, author.name, request)
            await ctx.send(msg)

    except (IndexError, AttributeError) as e:
        await ctx.send("Please mention a user you want to thank, you must have an active request")


@bot.command(name='catalysts', aliases=['catas'])
async def com_catalysts(ctx):
    await send_file(ctx, 'catas.jpg')


@bot.command(name='how')
async def com_how(ctx):
    await send_file(ctx, 'how.jpg')


@bot.command(name='aid')
async def com_aid(ctx):
    try:
        mention = User.find_user(ctx, ctx.message.mentions[0].id)
        author = User.find_user(ctx, ctx.message.author.id)
        request = Request.find_request(ctx, mention.request_id)
        await ctx.send("**{}**, check your guild box, there might be some :gift: **{}**'s for you from **{}**!"
                       .format(mention.name, request.name(), author.name))
    except (IndexError, AttributeError):
        await ctx.send("Please mention user with an active request you want to notify")


@bot.command(name='gift')
@commands.cooldown(3, 28800, type=commands.BucketType.member)
async def com_gift(ctx):
    try:
        author = User.find_user(ctx, ctx.message.author.id)
        mention = User.user(ctx, ctx.message.mentions[0])
        if author.score < 1:
            await ctx.send("Your score must be above zero to gift to other users")
        elif mention.id == author.id:
            await ctx.send("**{}** throws their own party, everyone is invited :partying_face:!".format(author.name))
        elif mention.id == bot.user.id:
            await ctx.send("Thank you, **{}** :blush:, I have a gift for you as well **+1** :heart:!".format(ctx.message.author.name))
        else:
            author.gift(ctx, mention)
            await ctx.send("**{}** feels generous today and gifts one of their points to **{} +1** :heart:!"
                           .format(ctx.message.author.name, ctx.message.mentions[0].name))
    except IndexError:
        await ctx.send("Please mention user you want to send gifts to")
    except AttributeError:
        await ctx.send("Get on the board first!")


@bot.command(name='ahelp')
async def com_help(ctx):
    embed = discord.Embed(title="Angelica The Bot",
                          description="See more info about the bot on [GitHub](https://github.com/svzhukov/angelica-the-bot)",
                          color=0xffc0cb)

    embed.add_field(name="`[User commands]`", value="All arguments should be provided without **<**, **>** brackets", inline=False)
    embed.add_field(name="!how    **<--**", value="Quick visual tutorial that shows how to use the bot", inline=False)
    embed.add_field(name="!request <catalyst_query>", value="Makes a request for named catalysts, **-2** to points", inline=False)
    embed.add_field(name="!thanks <@user>", value="Thanks the user who provided the assistance, "
                                                  "**+1** to exchange and assistance scores of the mentioned user", inline=False)
    embed.add_field(name="!aid <@user>", value="Notifies mentioned user about your aid, optional command", inline=False)
    embed.add_field(name="!board", value="Guild board with user scores and active requests", inline=False)
    embed.add_field(name="!gift <@user>", value="Gifts **1** of your points to the mentioned user, "
                                                "gifter receives **+1** assistance in return. Has a cooldown", inline=False)
    embed.add_field(name="!catalysts", value="Shows neat picture with all the catalysts", inline=False)
    embed.add_field(name="!signs <sign_name>", value="Your daily horoscope, provide no argument to see all available signs,"
                                                     " if provided sign is not on the list random one will be chosen", inline=False)

    embed.add_field(name="**\n`[Admin commands]`**", value="Requires bot admin role", inline=False)
    embed.add_field(name="!adminrole <role_id> or <role_name>",
                    value="Sets bot admin role, requires discord role management permissions to call, "
                          "pass no arguments to view current role",
                    inline=False)
    embed.add_field(name="!minscore <score>", value="Sets the minimum score threshold value, default is **-6**", inline=False)
    embed.add_field(name="!setscore <@user new_score>",
                    value="Sets the score manually, should only be used in cases of malfunction. "
                          "Note that all exchange scores from active bot users, taking into account current requests,"
                          " should add up close to **0**", inline=False)
    embed.add_field(name="!cancel <@user>", value="Cancels current request and refunds remaining points", inline=False)
    embed.add_field(name="!remove <@user> or <user_discord_id>", value="Removes user from the board", inline=False)

    me = bot.get_user(User.bot_dev_id)
    embed.set_footer(text="Developed by {0} (Discord ID: {0.id})".format(me), icon_url=me.avatar_url)

    await ctx.send(embed=embed)


# endregion


# region Events
@bot.event
async def on_guild_join(guild):
    print("A NEW guild {} welcomes Angelica!".format(guild))


@bot.event
async def on_guild_remove(guild):
    print("Angelica just got kicked out from {}, too bad for them!".format(guild))


@bot.event
async def on_command(ctx):
    EventLogger.log('-', ctx=ctx)


@bot.event
async def on_ready():
    print('Bot is ready')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("!ahelp"))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, User.AdminRoleCheckError) or isinstance(error, User.RoleManagementCheckError):
        EventLogger.log(error.message, ctx=ctx)
        await ctx.send(error.message)
    elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        EventLogger.log(str(error), ctx=ctx)
        await ctx.send("**{}**, {}".format(ctx.message.author.name, error))
    elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
        # Disable the spam from other bots with the same prefixes
        pass
    else:
        traceback.print_exception(type(error), error, error.__traceback__)
# endregion


# region Utils
async def send_file(ctx, file_name: str):
    with open(file_name, 'rb') as f:
        await ctx.send(file=discord.File(f, file_name))
# endregion

#######################################################
bot.run(os.environ['DISCORD_BOT_TOKEN'])
