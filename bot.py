from configparser import ConfigParser
import logging
from embeddings import OpenaiClient
import telebot
import re
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from queue_bot import start_thread, add_request_to_queue, get_queue_length

# Initialize the ConfigParser
parser = ConfigParser()
parser.read("configs.ini")

# Get values from the config file
testing = bool(parser["DEFAULTS"].get("testing"))

token = parser["DEFAULTS"].get("TOKEN")
test_token = parser["DEFAULTS"].get("TEST_TOKEN")

api_key = parser["DEFAULTS"].get("API_KEY")
max_size = int(parser["DEFAULTS"].get("max_size"))
delay = int(parser["DEFAULTS"].get("delay"))

test_bot_name = parser["DEFAULTS"].get("test_bot_name")
bot_name = parser["DEFAULTS"].get("bot_name") if not testing else test_bot_name

test_image_url = "https://t4.ftcdn.net/jpg/03/03/62/45/360_F_303624505_u0bFT1Rnoj8CMUSs8wMCwoKlnWlh5Jiq.jpg"

# Initialize the telebot and OpenaiClient
bot = telebot.TeleBot(test_token if testing else token)
client = OpenaiClient(api_key)

# Dictionary to store game data
games = {}

# Configure logging settings
logging.basicConfig(filename="logs.log", format="%(asctime)s %(message)s", filemode="w")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def contains_only_english_letters(word):
    return bool(re.match("^[a-zA-Z]+$", word))


def get_parameter(text):
    try:
        return text.split()[1] if 3 > len(text.split()) > 1 else False
    except:
        return False


@bot.message_handler(commands=["start", "help"])
def start(message: Message):
    try:
        # Get the parameter from the message text
        param = get_parameter(message.text)

        # Check if the parameter is empty
        if not param:
            # Send a welcome message with instructions
            bot.send_message(
                message.chat.id,
                "👋 Привет! Я - бот, с помощью которого можно загадывать слова, чтобы твои друзья их отгадывали. Я буду давать им подсказки и указывать, насколько они близки к правильному слову. Чтобы загадать слово, напиши в группе /play. (Играть надо на английском языке)",
            )
        else:
            # Check if the message is sent in a private chat
            if message.chat.type == "private":
                if param.startswith("pick"):
                    # Extract the group ID from the parameter
                    group_id = param[4:]

                    # Check if a game is already in progress for the group ID
                    if games.get(str(group_id)) is not None:
                        bot.send_message(
                            message.chat.id, "❌ Игра уже идет или вы уже в очереди!"
                        )
                    else:
                        # Prompt the user to send a word to be guessed
                        answer_message = bot.send_message(
                            message.chat.id,
                            "Отправь мне слово, которое хочешь загадать! 😨",
                        )
                        # Register a handler for the next message to start word picking
                        bot.register_next_step_handler(
                            answer_message, start_word_picking, int(group_id)
                        )
            else:
                # Send an error message if the command with parameter is used in a group chat
                bot.send_message(
                    message.chat.id,
                    "❌ Команду с параметром можно использовать только в личных сообщениях!",
                )
    except Exception as e:
        # Send an error message if an exception occurs
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["play"])
def play(message: Message):
    try:
        # Check if the message is in a private chat
        if not message.chat.type == "private":
            # Check if a game is already in progress for the chat
            if games.get(str(message.chat.id)) is None:
                # Send a message with a button to start the game
                bot.send_message(
                    message.chat.id,
                    "Чтобы загадать слово, нажми на кнопку ниже! 😁",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="Загадать!",
                                    url=f"https://t.me/{bot_name}?start=pick{message.chat.id}",
                                )
                            ],
                        ]
                    ),
                )
            else:
                # Send a message indicating that a game is already in progress
                bot.send_message(
                    message.chat.id,
                    f"❌ Игра уже идет или вы уже в очереди!",
                    parse_mode="Markdown",
                )
        else:
            # Send a message indicating that the command can only be used in a group chat
            bot.send_message(
                message.chat.id,
                "❌ Эту команду можно использовать только в групповом чате!",
            )
    except Exception as e:
        # Send a message indicating that an error occurred
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


def from_queue_processing(request: tuple):
    answer, group_id, dms_id, user_nick, message_queue_id, user_id = request

    logging.info(f"{answer} | {group_id}")

    bot.delete_message(dms_id, message_queue_id)

    games[str(group_id)] = [answer, {}, "", {}, ""]

    image_generation = bot.send_message(
        dms_id,
        f'Картинка "*{answer}*" генерируется 😎',
        parse_mode="Markdown",
    )
    url = client.generate_image(answer) if not testing else (200, test_image_url)
    if url[0] == 200:
        bot.send_photo(
            group_id,
            url[1],
            f"Пользователь *{user_nick}* загадал слово!\nПишите свои ответы в формате `/guess ответ` в этом чате!\nЧтобы остановить игру, напишите `/stop`.",
            parse_mode="Markdown",
        )
        bot.delete_message(dms_id, image_generation.message_id)
        games[str(group_id)] = [
            answer,
            {},
            url[1],
            {},
            user_id,
        ]
        bot.send_message(
            dms_id,
            f'Ваше слово "*{answer}*" успешно загадано! ✅ Перейдите обратно в группу.',
            parse_mode="Markdown",
        )

        logging.info(f"game in {group_id} started")
    else:
        games.pop(str(group_id))
        bot.delete_message(dms_id, image_generation.message_id)
        bot.send_message(
            dms_id,
            f"❌ Ошибка генерации: `{url[1]}`",
            parse_mode="Markdown",
        )
        bot.send_message(
            group_id,
            f"❌ Ошибка генерации. Начните игру заново: `{url[1]}`",
            parse_mode="Markdown",
        )


def start_word_picking(message: Message, group_id: int):
    try:
        # Check if a game is already in progress
        if games.get(str(group_id)) is not None:
            bot.send_message(message.chat.id, "❌ Игра уже идет или вы уже в очереди!")
        else:
            answer = message.text.strip().lower()
            # Check if the answer is a single word
            if not len(answer.split()) > 1:
                # Check if the answer contains only English letters
                if contains_only_english_letters(answer):
                    answer_embedding = client.get_embedding(answer)
                    # Check if the answer exists in the embeddings
                    if client.exist(answer_embedding):
                        logging.info(f"{answer} | {group_id}")

                        games[str(group_id)] = [answer, {}, "", {}, ""]

                        lenght = get_queue_length() + 1
                        if lenght > max_size:
                            bot.send_message(
                                message.chat.id,
                                f"❌ К сожалению, очередь переполнена. Эта игра завершится.",
                            )
                            bot.send_message(
                                group_id,
                                f"❌ К сожалению, очередь переполнена. Эта игра завершится.",
                            )
                            games.pop(str(group_id))

                        else:
                            if lenght > 0:
                                queue_message = bot.send_message(
                                    message.chat.id,
                                    f"⌛ Вы добавлены в очередь.\nПримерное время ожидания: *{(lenght * delay) // 60}* мин.",
                                    parse_mode="Markdown",
                                )

                            add_request_to_queue(
                                answer,
                                group_id,
                                message.chat.id,
                                message.from_user.full_name,
                                queue_message.id,
                                message.from_user.id,
                            )

                    else:
                        bot.send_message(
                            message.chat.id,
                            "❌ Такого слова не существует!",
                            reply_markup=InlineKeyboardMarkup(
                                [
                                    [
                                        InlineKeyboardButton(
                                            text="Загадать заново!",
                                            url=f"https://t.me/{bot_name}?start=pick{group_id}",
                                        )
                                    ],
                                ]
                            ),
                        )
                else:
                    bot.send_message(
                        message.chat.id,
                        "❌ Слово должно быть английским и состоять только из букв!",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        text="Загадать заново!",
                                        url=f"https://t.me/{bot_name}?start=pick{group_id}",
                                    )
                                ],
                            ]
                        ),
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Пришли мне слово, а не предложение!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="Загадать заново!",
                                    url=f"https://t.me/{bot_name}?start=pick{group_id}",
                                )
                            ],
                        ]
                    ),
                )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["guess"])
def guess(message: Message):
    try:
        group_id = message.chat.id

        if games.get(str(group_id)) is None:
            bot.send_message(message.chat.id, "❌ Сейчас не идет никакая игра!")
        else:
            if not message.chat.type == "private":
                param = get_parameter(message.text)
                if param:
                    if games[str(group_id)][2] != "":
                        if contains_only_english_letters(param):
                            given_try = param.lower().strip()
                            correct_answer = games[str(group_id)][0].lower().strip()
                            if correct_answer == given_try:
                                if games.get(str(group_id)) is not None:
                                    games[str(group_id)][3][
                                        str(message.from_user.id)
                                    ] = games[str(group_id)][3].get(
                                        str(message.from_user.id), []
                                    ) + [
                                        100
                                    ]
                                    top_final("10", message.chat.id)
                                    scoreboard_final(message.chat.id)
                                    if (
                                        len(
                                            games[str(group_id)][3][
                                                str(message.from_user.id)
                                            ]
                                        )
                                        == 1
                                    ):
                                        bot.send_message(
                                            group_id,
                                            f"🎉 *{message.from_user.full_name}* молодец! Ты отгадал слово *{correct_answer}* с первой попытки! Вот это мастерство! 🤯",
                                            parse_mode="Markdown",
                                        )
                                    else:
                                        bot.send_message(
                                            group_id,
                                            f"🎉 *{message.from_user.full_name}* отгадал слово *{correct_answer}*! Игра заканчивается.",
                                            parse_mode="Markdown",
                                        )
                                    if str(group_id) in games.keys():
                                        games.pop(str(group_id))
                                else:
                                    bot.send_message(
                                        message.chat.id,
                                        "❌ Сейчас не идет никакая игра!",
                                    )
                            else:
                                correct_embedding = client.get_embedding(correct_answer)
                                given_try_embedding = client.get_embedding(given_try)

                                if client.exist(given_try_embedding):
                                    div = client.cosine_similarity(
                                        correct_embedding, given_try_embedding
                                    )
                                    bot.send_message(
                                        group_id,
                                        f"Ответ *{message.from_user.full_name}* близок к правильному на *{round(div * 100, 2)}%*",
                                        parse_mode="Markdown",
                                    )
                                    if games.get(str(group_id)) is not None:
                                        games[str(group_id)][1][
                                            given_try
                                        ] = f"{round(div * 100, 2)}%"

                                        games[str(group_id)][3][
                                            str(message.from_user.id)
                                        ] = games[str(group_id)][3].get(
                                            str(message.from_user.id), []
                                        ) + [
                                            round(div * 100, 2)
                                        ]

                                else:
                                    bot.send_message(
                                        message.chat.id,
                                        f"❌ *{message.from_user.full_name}*, такого слова не существует!",
                                        parse_mode="Markdown",
                                    )

                        else:
                            bot.send_message(
                                message.chat.id,
                                f"❌ *{message.from_user.full_name}*, отгадка должна быть на английском языке и состоять только из букв!",
                                parse_mode="Markdown",
                            )
                    else:
                        bot.send_message(
                            message.chat.id,
                            f"❌ Не спеши! Картинка еще генерируется, или вы в очереди.",
                            parse_mode="Markdown",
                        )
                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ *{message.from_user.full_name}*, отгадка должна быть одним словом!",
                        parse_mode="Markdown",
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Эту команду можно использовать только в групповом чате!",
                )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["top"])
def top(message: Message):
    try:
        if games.get(str(message.chat.id)) != None:
            param = get_parameter(message.text)
            if not param:
                param = "5"
            if param.isdigit():
                count = int(param)
                if 1 <= count <= 100:
                    prep_val = games[str(message.chat.id)][1]
                    if len(prep_val.keys()) != 0:
                        sorted_words = list(
                            sorted(
                                list(prep_val.items()),
                                key=lambda x: float(x[1][:-1]),
                                reverse=True,
                            )
                        )

                        count = (
                            len(sorted_words) if len(sorted_words) < count else count
                        )

                        top = sorted_words[:count]

                        output = ""
                        for i, (word, percentage) in enumerate(top, start=1):
                            output += f"{i}) *{word}*: {percentage}\n"

                        bot.send_message(message.chat.id, output, parse_mode="Markdown")
                        bot.send_photo(message.chat.id, games[str(message.chat.id)][2])
                    else:
                        bot.send_message(
                            message.chat.id,
                            f"❌ *{message.from_user.full_name}*, никаких отгадок еще нет!",
                            parse_mode="Markdown",
                        )

                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ *{message.from_user.full_name}*, укажите количество слов для вывода от 1 до 100.",
                        parse_mode="Markdown",
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ *{message.from_user.full_name}*, параметр должен быть числом (от 1 до 100)!",
                    parse_mode="Markdown",
                )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ *{message.from_user.full_name}*, игра в данный момент не идет",
                parse_mode="Markdown",
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔️ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


def top_final(amount: str, id: int):
    prep_val = games[str(id)][1]

    if len(prep_val.keys()) != 0:
        count = int(amount)

        sorted_words = list(
            sorted(list(prep_val.items()), key=lambda x: float(x[1][:-1]), reverse=True)
        )

        count = len(sorted_words) if len(sorted_words) < count else count

        top = sorted_words[:count]

        output = "Статистика по словам:\n\n"
        for i, (word, percentage) in enumerate(top, start=1):
            output += f"{i}) *{word}*: {percentage}\n"

        bot.send_message(id, output, parse_mode="Markdown")


def scoreboard_final(group_id: int):
    players = games[str(group_id)][3]

    output_list = []
    for elem in players.items():
        output_list.append(
            [
                bot.get_chat_member(group_id, str(elem[0])).user.first_name,
                len(elem[1]),
                sum(elem[1]) / len(elem[1]),
            ]
        )

    output_list.sort(key=lambda x: x[2], reverse=True)

    result = "Статистика по пользователям (количество угадываний, средний показатель совпадения):\n\n"

    max_id = max(
        players.keys(),
        key=lambda x: (
            len(bot.get_chat_member(group_id, str(x)).user.first_name)
            + len(str(players[x][0]))
        ),
    )

    max_len = len(bot.get_chat_member(group_id, str(max_id)).user.first_name) + len(
        str(len(players[str(max_id)]))
    )

    for elem in output_list:
        print(elem)
        result += f"`{elem[0]}: {' ' * (max_len - len(elem[0]) - len(str(elem[1])))}{elem[1]} | {round(elem[2])}%`\n"

    bot.send_message(group_id, result, parse_mode="Markdown")


@bot.message_handler(commands=["stop"])
def stop(message: Message):
    try:
        if not message.chat.type == "private":
            if games.get(str(message.chat.id)) != None:
                if message.from_user.id == int(games[str(message.chat.id)][4]):
                    games.pop(str(message.chat.id))
                    bot.send_message(
                        message.chat.id,
                        f"🛑 Игра остановлена! Её остановил *{message.from_user.full_name}*.",
                        parse_mode="Markdown",
                    )
                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ Эту команду может использовать только создатель игры!",
                        parse_mode="Markdown",
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ *{message.from_user.full_name}*, игра в данный момент не идет",
                    parse_mode="Markdown",
                )
        else:
            # Send a message indicating that the command can only be used in a group chat
            bot.send_message(
                message.chat.id,
                "❌ Эту команду можно использовать только в групповом чате!",
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔️ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


start_thread(f=from_queue_processing, logger=logger, delay=delay)
bot.infinity_polling()
