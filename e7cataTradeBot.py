import discord
import json
import pprint
import uuid
from typing import Optional
from enum import IntEnum


class Var:
    defaultChannel = 635806850704474143
    commandNames = ['!respond', '!board', '!test', '!request', '!thanks', '!signs', '!setscore', '!catalysts', 'a!help']
    comRespond, comScore, comTest, comRequest, comThank, comSigns, comModify, comCatas, comHelp = commandNames
    discordTriviaAdmins = [118435077477761029, 165305568075055104, 191344684092620800]

    users = []
    catalysts = []
    signs = []
    requests = []

    score_min_threshold = -4
    reserve_max_count = 2
    sign_reservation_limit = 3
    amount_for_completion = 2


class User:
    id = ""
    name = ""
    score = 0
    current_request_id = ""
    reserved_signs_ids = []


class Rarity(IntEnum):
    rare = 1
    epic = 4


class Catalyst:
    id = ""
    name = ""
    rarity = Rarity.rare
    sign_id = ""


class Sign:
    id = ""
    name = ""
    catalysts_ids = []


class Request:
    id = ""
    user_id = ""
    cata_id = ""
    completion = 0
    active = True

    def next_completion_stage(self):
        self.completion += 1
        if self.completion == Var.amount_for_completion:
            self.active = False
            return True
        return False

    def completion_str(self):
        return "[" + str(self.completion) + "/" + str(Var.amount_for_completion) + "]"


# Commands
async def score_com():
    msg = "Guild's catalyst exchange board:\n"
    for user in Var.users:
        sign_names = []
        for sign_id in user.reserved_signs_ids:
            sign_names.append(sign_name_by_id(sign_id))
        sign_names = sign_names if len(sign_names) else ["None"]
        request = next((x for x in Var.requests if x.id == user.current_request_id), None)
        active_request_str = cata_name_by_id(request.cata_id) if request else "None"

        if request:
            req_str = active_request_str + " " + request.completion_str()
        else:
            req_str = active_request_str

        msg += user.name + " - Score: [" + str(user.score) + "], Signs: [" + ", ".join(sign_names) + "], Request: [" + req_str + "]\n"
    await send_msg(msg)


async def request_com(message):
    user = next((x for x in Var.users if x.id == str(message.author.id)), None)
    request = None
    if user:
        request = next((x for x in Var.requests if x.id == user.current_request_id), None)

    query = message.content.replace(Var.comRequest + " ", "")
    catas = search_cata(query)
    cata = None
    if len(catas) == 1:
        cata = catas[0]

    if len(query) < 3:
        await send_msg("Provide at least 3 characters for catalyst name")
    elif len(catas) == 0:
        await send_msg("No catalyst found")
    elif len(catas) > 1:
        await send_msg("Found more than one catalyst, please specify")
    elif cata.rarity == Rarity.epic:
        await send_msg("Can't request epic catalysts")
    elif request:
        await send_msg("You already have active aid request for " + cata_name_by_id(request.cata_id) + " " + request.completion_str())
    elif not user or cata.sign_id not in user.reserved_signs_ids:
        await send_msg("Catalysts should be in your reserved zodiac signs to be requested. Use !signs <sign1, sign2> (max " + str(Var.reserve_max_count) + ")")
    elif user.score <= Var.score_min_threshold:
        await send_msg("Your exchange score is too low: " + str(user.score) + ". Please aid other guild members to improve your score")
    else:
        request = add_new_request(cata.id, user.id)
        user.current_request_id = request.id
        user.score = user.score - cata.rarity * Var.amount_for_completion
        save_users()

        await send_msg(user.name + " has requested " + cata_name_by_id(request.cata_id) + " " + request.completion_str() + ". User's new score: [" + str(user.score) + "]")


async def signs_com(message):
    user = find_user(message.author.id)
    if not user:
        user = add_new_user(message.author.id, message.author.name)
    elif user.current_request_id:
        request = next(x for x in Var.requests if x.id == user.current_request_id)
        await send_msg("Finish your current request, before changing signs - " + cata_name_by_id(request.cata_id) + " " + request.completion_str())
        return

    sign_names = message.content.replace(Var.comSigns, "").replace(" ", "").split(",")
    limit_reached_sign = None
    recognized_signs = []
    user.reserved_signs_ids = []
    for name in sign_names:
        sign = next((x for x in Var.signs if x.name.lower() == name.lower()), None)
        if sign:
            user.reserved_signs_ids.append(sign.id)
            recognized_signs.append(sign.name)
            if is_sign_limit_reached(sign.id):
                limit_reached_sign = sign
                break

    if limit_reached_sign:
        user.reserved_signs_ids = []
        await send_msg("Reservation limit reached for " + limit_reached_sign.name + "(" + str(Var.sign_reservation_limit) + ") wait or ask other guild members to change their signs. Your signs have been reset [ ]")
    if not len(recognized_signs):
        user.reserved_signs_ids = []
        await send_msg("No zodiac sign found. Your signs have been reset [ ]")
    else:
        await send_msg("Your new signs: [" + ", ".join(recognized_signs) + "]")

    save_users()


# todo: !help
# TODO: styles and foramttings, bot name
async def thank_com(message):
    requester = find_user(message.author.id)
    helper = find_user(message.mentions[0].id)

    if not requester or not len(requester.current_request_id):
        await send_msg("You don't have any active requests right now")

    elif not message.mentions[0]:
        await send_msg("Mention a discord user you want to thank")

    elif helper.id == requester.id:
        await send_msg("Don't do that!")

    else:
        if not helper:
            helper = add_new_user(message.mentions[0].id, message.mentions[0].name)
        helper.score += Rarity.rare
        request = next(x for x in Var.requests if x.id == requester.current_request_id)
        finished = request.next_completion_stage()
        if finished:
            requester.current_request_id = ""

        save_users()
        save_requests()
        await send_msg("Thanks for the assistance, " + helper.name + ", here's your +1! " + cata_name_by_id(request.cata_id) + " " + request.completion_str())


async def catas_com():
    with open('catas.png', 'rb') as fp:
        await client.get_channel(Var.defaultChannel).send(file=discord.File(fp, 'catas.png'))


async def modify_score_com(message):
    user = find_user(message.mentions[0].id)
    if not user:
        await send_msg("User not found")
    else:
        try:
            user.score = int(message.content.replace(Var.comModify, "").split(" ")[-1])
            save_users()
            await send_msg(user.name + "'s score successfully set to [" + str(user.score) + "]")
        except Exception as e:
            print(e)
            await send_msg("Failed to set user's score, perhaps invalid arguments provided")


async def help_com():
    line_start = "```\n"
    line_end = "\n```"
    msg = ""
    msg += line_start + "!request <catalyst> - requests catalyst from reserved signs, -2 to points from score" + line_end
    msg += line_start + "!signs <sign1, sign2> - sets zodiac signs you're allowed to request from, up to " + str(Var.reserve_max_count) + ". Type any argument to reset signs" + line_end
    msg += line_start + "!thanks <@user> - thanks the user who provided the assistance, +1 points" + line_end
    msg += line_start + "!catalysts - shows neat picture with all the catalysts" + line_end
    msg += line_start + "!board - board with all the user score, signs and currently active requests" + line_end
    msg += line_start + "!setscore <@user new_score> - manual score modifications in case of conflicted situations, bot admin permissions required" + line_end
    await send_msg(msg)


async def respond_com():
    await send_msg("Hello, I'm alive and responding!")


# Utility
def is_trivia_admin(message) -> bool:
    return message.author.id in Var.discordTriviaAdmins


def is_sign_limit_reached(sign_id: str) -> bool:
    reserved_count = 0
    for user in Var.users:
            reserved_count += 1 if sign_id in user.reserved_signs_ids else 0
    return True if reserved_count >= Var.sign_reservation_limit else False


def sign_name_by_id(sign_id: str) -> str:
    sign = next((x for x in Var.signs if x.id == sign_id), None)
    return sign.name if sign else "None"


def cata_name_by_id(cata_id: str) -> str:
    cata = next((x for x in Var.catalysts if x.id == cata_id), None)
    return cata.name if cata else "None"


def add_new_user(user_id, name: str) -> User:
    if not user_id:
        raise Exception
    user = User()
    user.id = str(user_id)
    user.name = name
    Var.users.append(user)
    print('New user created: ' + user.name)
    save_users()
    return user


def add_new_request(cata_id: str, user_id: str) -> Request:
    request = Request()
    request.id = str(uuid.uuid4())
    request.cata_id = str(cata_id)
    request.user_id = user_id
    Var.requests.append(request)
    save_requests()
    print("New request created by " + user_id + " for cata_id:" + cata_id)
    return request


def find_user(user_id) -> User:
    return next((x for x in Var.users if x.id == str(user_id)), None)


def search_cata(query: str) -> []:
    catas = []
    for cata in Var.catalysts:
        if query.lower() in cata.name.lower():
            catas.append(cata)
    return catas


# Save & Load files
def load_catas():
    try:
        with open('catalysts.txt', 'r') as filehandler:
             parse_catas(json.load(filehandler))
    except (FileNotFoundError, IOError, json.decoder.JSONDecodeError):
        with open('catalysts.txt', 'w'): pass


def parse_catas(catas_dict):
    for key in catas_dict.keys():
        cata = Catalyst()
        cata.id = key
        cata.name = catas_dict[key]['name']
        cata.rarity = catas_dict[key]['rarity_id']
        cata.sign_id = catas_dict[key]['sign_id']
        Var.catalysts.append(cata)


def load_signs():
    try:
        with open('signs.txt', 'r') as filehandler:
            parse_signs(json.load(filehandler))
    except (FileNotFoundError, IOError, json.decoder.JSONDecodeError):
        with open('signs.txt', 'w'): pass
    except:
        raise


def parse_signs(signs_dict):
    for key in signs_dict.keys():
        sign = Sign()
        sign.id = key
        sign.name = signs_dict[key]['name']
        sign.catalysts_ids = signs_dict[key]['catalysts_ids']
        Var.signs.append(sign)


def load_users():
    try:
        with open('users.txt', 'r') as fileHandler:
            parse_users(json.load(fileHandler))
    except (FileNotFoundError, IOError, json.decoder.JSONDecodeError):
        with open('users.txt', "w"): pass
    except Exception as e:
        raise


def parse_users(users_dict):
    for key in users_dict.keys():
        user = User()
        user.id = key
        user.name = users_dict[key]['name']
        user.score = users_dict[key]['score']
        user.current_request_id = users_dict[key]['current_request_id']
        user.reserved_signs_ids = users_dict[key]['reserved_signs_ids']
        Var.users.append(user)


def save_users():
    users_dict = {}
    for user in Var.users:
        users_dict[user.id] = {'name': user.name, 'score': user.score, 'current_request_id': user.current_request_id, 'reserved_signs_ids': user.reserved_signs_ids}
    with open('users.txt', 'w') as filehandler:
        json.dump(users_dict, filehandler)


def load_requests():
    try:
        with open('requests.txt', 'r') as fileHandler:
            parse_requests(json.load(fileHandler))
    except (FileNotFoundError, IOError, json.decoder.JSONDecodeError):
        with open('requests.txt', "w"): pass
    except Exception as e:
        raise


def parse_requests(requests_dict):
    # TODO: refactor pasring (yymodel like style?)
    for key in requests_dict.keys():
        request = Request()
        request.id = key
        request.cata_id = requests_dict[key]["cata_id"]
        request.user_id = requests_dict[key]["user_id"]
        request.completion = requests_dict[key]["completion"]
        request.active = requests_dict[key]["active"]
        Var.requests.append(request)


def save_requests():
    requestsDict = {}
    for request in Var.requests:
        requestsDict[request.id] = {'cata_id': request.cata_id, 'user_id': request.user_id, 'completion': request.completion, 'active': request.active}
    with open('requests.txt', 'w') as filehandler:
        json.dump(requestsDict, filehandler)


# High level functions
async def send_msg(msg):
    print("msg: " + msg)
    if len(msg) > 0:
        await client.get_channel(Var.defaultChannel).send(msg)


def load_files():
    print("Loading files..")
    load_users()
    load_catas()
    load_signs()
    load_requests()


async def call_command(message):
    command = next((x for x in Var.commandNames if x in message.content), False).lower()
    print("Command recognized - " + command)
    if command == Var.comRespond:
        await respond_com()
    elif command == Var.comTest and is_trivia_admin(message):
        await test_com()
    elif command == Var.comScore:
        await score_com()
    elif command == Var.comRequest:
        await request_com(message)
    elif command == Var.comThank:
        await thank_com(message)
    elif command == Var.comSigns:
        await signs_com(message)
    elif command == Var.comModify and is_trivia_admin(message):
        await modify_score_com(message)
    elif command == Var.comCatas:
        await catas_com()
    elif command == Var.comHelp:
        await help_com()


async def test_com():
    pass


# Procedures
pp = pprint.PrettyPrinter()
load_files()


client = discord.Client()
@client.event
async def on_ready():
    print('ready')
    game = discord.Game("uwu")
    await client.change_presence(status=discord.Status.online, activity=game)


@client.event
async def on_message(message):
    # Ignore messages from self, wrong channel
    if message.author == client.user or message.channel.id != Var.defaultChannel:
        return

    # Command recognition
    if any(x in message.content for x in Var.commandNames):
        await call_command(message)


client.run('NjM1NTE3NjY3MjIyMjI0OTAy.XaySFQ.yM9trA9OkptpoAeQYMLAitLQLHk')