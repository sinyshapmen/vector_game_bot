from configparser import ConfigParser
import logging
from models.embeddings import Embeddings
from models.kandinsky import KandinskyClient
from models.dalle import OpenaiClient

import telebot
import re
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from queue_bot import start_thread, add_request_to_queue, get_queue_length
from tinydb import TinyDB, Query
from database.database import PostgreClient

gods = [1038099964, 1030055969]

# Configure logging settings
logging.basicConfig(filename="logs.log", format="%(asctime)s %(message)s", filemode="w")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the ConfigParser
parser = ConfigParser()
parser.read("configs.ini")

# Get values from the config file
testing = True

token = parser["DEFAULTS"].get("TOKEN")
test_token = parser["DEFAULTS"].get("TEST_TOKEN")

delay = int(parser["DEFAULTS"].get("delay")) if not testing else 10

test_bot_name = parser["DEFAULTS"].get("test_bot_name")
bot_name = parser["DEFAULTS"].get("bot_name") if not testing else test_bot_name

kandinsky_api_key = parser["IMAGEGEN"].get("kandisky_api_key")
kandinsky_secret_key = parser["IMAGEGEN"].get("kandinsky_secret_key")
dalle_api_key = parser["IMAGEGEN"].get("dalle_api_key")

host = parser["DATABASE"].get("host")
username = parser["DATABASE"].get("username")
password = parser["DATABASE"].get("password")

user_db_name = parser["DATABASE"].get("user_db_name")
games_db_name = parser["DATABASE"].get("games_db_name")

# Initialize the telebot and OpenaiClient
bot = telebot.TeleBot(test_token if testing else token)
dalle_client = OpenaiClient(dalle_api_key)
kandinsky_client = KandinskyClient(
    "https://api-key.fusionbrain.ai/", kandinsky_api_key, kandinsky_secret_key
)
embedding_client = Embeddings()

# Dictionary to store game data
games_db = TinyDB("database/games.json")
User = Query()
if not testing:
    database_client = PostgreClient(
        host=host,
        logger=logger,
        password=password,
        dbname=user_db_name,
        user=username,
    )
    database_client.init_user_table()

for game in games_db.all():
    game = game["id"]
    bot.send_message(
        int(game),
        "✨ *Спасибо за ожидание*. Вы можете продолжать играть",
        parse_mode="Markdown",
    )


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
            if message.chat.type == "private" and not testing:
                database_client.add_user_if_not_exists(message.from_user.id)

            bot.send_message(
                message.chat.id,
                "👋 Привет! Я - бот, с помощью которого можно загадывать слова, чтобы твои друзья их отгадывали. Я буду давать им подсказки и указывать, насколько они близки к правильному слову. Чтобы загадать слово, напиши в группе /play. (Играть надо на английском языке)",
            )
        else:
            # Check if the message is sent in a private chat
            if message.chat.type == "private":
                if not testing:
                    database_client.add_user_if_not_exists(message.from_user.id)

                if param.startswith("pick"):
                    # Extract the group ID from the parameter
                    group_id = param[4:]
                    if group_id.startswith("-"):
                        # Check if a game is already in progress for the group ID
                        if games_db.search(User.id == str(group_id)):
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
                        bot.send_message(
                            message.chat.id,
                            "❌ Не пытайся запустить игру в личных сообщениях!",
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
        logger.error(f"ERROR: {e}")


@bot.message_handler(commands=["play"])
def play(message: Message):
    try:
        # Check if the message is in a private chat
        if not message.chat.type == "private":
            # Check if a game is already in progress for the chat
            if not games_db.search(User.id == str(message.chat.id)):
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
        logger.error(f"ERROR: {e}")


def from_queue_processing(request: tuple):
    answer, group_id, dms_id, user_nick, message_queue_id, user_id = request

    bot.delete_message(dms_id, message_queue_id)

    games_db.upsert(
        {"id": str(group_id), "data": [answer, {}, "", {}, ""]},
        User.id == str(group_id),
    )

    image_generation = bot.send_message(
        dms_id,
        f'Картинка "*{answer}*" генерируется 😎',
        parse_mode="Markdown",
    )
    status, generated_photo_bytes = kandinsky_client.generate_image(answer)

    if status == 200:
        sent_image = bot.send_photo(
            group_id,
            generated_photo_bytes,
            f"Пользователь *{user_nick}* загадал слово!\nПишите свои ответы в формате `/guess ответ`,  `guess ответ` или просто отвечай на сообщения бота в этом чате!\nЧтобы остановить игру, напиши `/stop`.",
            parse_mode="Markdown",
        )
        bot.delete_message(dms_id, image_generation.message_id)

        games_db.upsert(
            {
                "id": str(group_id),
                "data": [answer, {}, sent_image.photo[0].file_id, {}, user_id],
            },
            User.id == str(group_id),
        )

        bot.send_message(
            dms_id,
            f'Ваше слово "*{answer}*" успешно загадано! ✅ Перейдите обратно в группу.',
            parse_mode="Markdown",
        )

    else:
        games_db.remove(doc_ids=[games_db.search(User.id == str(group_id))[0].doc_id])
        bot.delete_message(dms_id, image_generation.message_id)
        bot.send_message(
            dms_id,
            f"❌ Ошибка генерации. Возможно, ваш запрос содержит недопустимые слова.",
            parse_mode="Markdown",
        )
        bot.send_message(
            group_id,
            f"❌ Ошибка генерации. Начните игру заново.",
            parse_mode="Markdown",
        )


def start_word_picking(message: Message, group_id: int):
    try:
        # Check if a game is already in progress
        if games_db.search(User.id == str(group_id)):
            bot.send_message(message.chat.id, "❌ Игра уже идет или вы уже в очереди!")
        else:
            answer = message.text.strip().lower()
            # Check if the answer is a single word
            if not len(answer.split()) > 1:
                # Check if the answer contains only English letters
                if contains_only_english_letters(answer):
                    answer_embedding = embedding_client.get_embedding(answer)
                    # Check if the answer exists in the embeddings
                    if embedding_client.exist(answer_embedding):
                        logging.info(f"Game started | ans: {answer} | g_id: {group_id}")

                        lenght = get_queue_length() + 1

                        games_db.upsert(
                            {"id": str(group_id), "data": [answer, {}, "", {}, ""]},
                            User.id == str(group_id),
                        )

                        wait_time = lenght * delay

                        queue_message = bot.send_message(
                            message.chat.id,
                            "⌛ Вы добавлены в очередь.\nПримерное время ожидания: "
                            + (
                                f"*{wait_time // 60}* мин."
                                if (wait_time // 60) > 0
                                else f"*{wait_time}* сек."
                            ),
                            parse_mode="Markdown",
                        )

                        add_request_to_queue(
                            answer,
                            group_id,
                            message.chat.id,
                            message.from_user.full_name,
                            queue_message.id,
                            message.from_user.id,
                            logger,
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
        logger.error(f"ERROR: {e}")


@bot.message_handler(commands=["guess"])
def guess(message: Message):
    try:
        group_id = message.chat.id

        if not games_db.search(User.id == str(group_id)):
            bot.send_message(message.chat.id, "❌ Сейчас не идет никакая игра!")
        else:
            if not message.chat.type == "private":
                param = get_parameter(message.text)
                if param:
                    if games_db.search(User.id == str(group_id))[0]["data"][2] != "":
                        if contains_only_english_letters(param):
                            given_try = param.lower().strip()
                            correct_answer = (
                                games_db.search(User.id == str(group_id))[0]["data"][0]
                                .lower()
                                .strip()
                            )
                            if correct_answer == given_try:
                                if games_db.search(User.id == str(group_id)):
                                    new_dict = games_db.search(
                                        User.id == str(group_id)
                                    )[0]["data"][3]

                                    new_dict[str(message.from_user.id)] = new_dict.get(
                                        str(message.from_user.id), []
                                    ) + [100]

                                    games_db.upsert(
                                        {
                                            "id": str(group_id),
                                            "data": [
                                                correct_answer,
                                                games_db.search(
                                                    User.id == str(group_id)
                                                )[0]["data"][1],
                                                games_db.search(
                                                    User.id == str(group_id)
                                                )[0]["data"][2],
                                                new_dict,
                                                games_db.search(
                                                    User.id == str(group_id)
                                                )[0]["data"][4],
                                            ],
                                        },
                                        User.id == str(group_id),
                                    )
                                    top_final("10", message.chat.id)
                                    scoreboard_final(message.chat.id)
                                    if (
                                        len(
                                            games_db.search(User.id == str(group_id))[
                                                0
                                            ]["data"][3][str(message.from_user.id)]
                                        )
                                        == 1
                                    ):
                                        bot.send_message(
                                            group_id,
                                            f"🎉 *{message.from_user.full_name}*, молодец! Ты отгадал слово *{correct_answer}* с первой попытки! Вот это мастерство! 🤯",
                                            parse_mode="Markdown",
                                        )
                                    else:
                                        bot.send_message(
                                            group_id,
                                            f"🎉 *{message.from_user.full_name}* отгадал слово *{correct_answer}*! Игра заканчивается.",
                                            parse_mode="Markdown",
                                        )
                                    if games_db.search(User.id == str(group_id)):
                                        games_db.remove(
                                            doc_ids=[
                                                games_db.search(
                                                    User.id == str(group_id)
                                                )[0].doc_id
                                            ]
                                        )

                                    logger.info(f"Game ended | g_id: {group_id}")
                                else:
                                    bot.send_message(
                                        message.chat.id,
                                        "❌ Сейчас не идет никакая игра!",
                                    )
                            else:
                                correct_embedding = embedding_client.get_embedding(
                                    correct_answer
                                )
                                given_try_embedding = embedding_client.get_embedding(
                                    given_try
                                )

                                logger.info(
                                    f"Get {given_try} from {message.from_user.id} | {group_id}"
                                )

                                if embedding_client.exist(given_try_embedding):
                                    div = embedding_client.cosine_similarity(
                                        correct_embedding, given_try_embedding
                                    )
                                    bot.send_message(
                                        group_id,
                                        f"*{message.from_user.full_name}* близок к правильному ответу на *{round(div * 100, 2)}%*",
                                        parse_mode="Markdown",
                                    )
                                    if games_db.search(User.id == str(group_id)):
                                        new_dict1 = games_db.search(
                                            User.id == str(group_id)
                                        )[0]["data"][1]

                                        new_dict1[given_try] = f"{round(div * 100, 2)}%"

                                        new_dict2 = games_db.search(
                                            User.id == str(group_id)
                                        )[0]["data"][3]

                                        new_dict2[
                                            str(message.from_user.id)
                                        ] = new_dict2.get(
                                            str(message.from_user.id), []
                                        ) + [
                                            round(div * 100, 2)
                                        ]

                                        games_db.upsert(
                                            {
                                                "id": str(group_id),
                                                "data": [
                                                    games_db.search(
                                                        User.id == str(group_id)
                                                    )[0]["data"][0],
                                                    new_dict1,
                                                    games_db.search(
                                                        User.id == str(group_id)
                                                    )[0]["data"][2],
                                                    new_dict2,
                                                    games_db.search(
                                                        User.id == str(group_id)
                                                    )[0]["data"][4],
                                                ],
                                            },
                                            User.id == str(group_id),
                                        )

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
                            f"❌ *{message.from_user.full_name}*, не спеши! Картинка еще генерируется, или вы в очереди.",
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
        logger.error(f"ERROR: {e}")
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["top"])
def top(message: Message):
    try:
        if games_db.search(User.id == str(message.chat.id)):
            param = get_parameter(message.text)
            if not param:
                param = "5"
            if param.isdigit():
                count = int(param)
                if 1 <= count <= 100:
                    prep_val = games_db.search(User.id == str(message.chat.id))[0][
                        "data"
                    ][1]
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
                        bot.send_photo(
                            message.chat.id,
                            photo=games_db.search(User.id == str(message.chat.id))[0][
                                "data"
                            ][2],
                        )
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
        logger.error(f"ERROR: {e}")


def top_final(amount: str, id: int):
    prep_val = games_db.search(User.id == str(id))[0]["data"][1]

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
    players = games_db.search(User.id == str(group_id))[0]["data"][3]

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
        result += f"`{elem[0]}: {' ' * (max_len - len(elem[0]) - len(str(elem[1])))}{elem[1]} | {round(elem[2])}%`\n"

    bot.send_message(group_id, result, parse_mode="Markdown")


@bot.message_handler(commands=["stop"])
def stop(message: Message):
    try:
        if not message.chat.type == "private":
            if games_db.search(User.id == str(message.chat.id)):
                if games_db.search(User.id == str(message.chat.id))[0]["data"][4] != "":
                    if message.from_user.id == int(
                        games_db.search(User.id == str(message.chat.id))[0]["data"][4]
                    ):
                        games_db.remove(
                            doc_ids=[
                                games_db.search(User.id == str(message.chat.id))[
                                    0
                                ].doc_id
                            ]
                        )
                        bot.send_message(
                            message.chat.id,
                            f"🛑 Игра остановлена! Её остановил *{message.from_user.full_name}*.",
                            parse_mode="Markdown",
                        )
                    else:
                        bot.send_message(
                            message.chat.id,
                            f"❌ *{message.from_user.full_name}*, эту команду может использовать только создатель игры!",
                            parse_mode="Markdown",
                        )
                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ *{message.from_user.full_name}*, игра ещё не запустилась. Вы в очереди.",
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
        logger.error(f"ERROR: {e}")


@bot.message_handler(commands=["shutdown"])
def shutdown(message: Message):
    if message.from_user.id in gods:
        restart = bot.send_message(
            message.chat.id,
            f"⌛️ Произвожу рестарт...",
        )
        for game in games_db.all():
            game = game["id"]
            bot.send_message(
                int(game),
                "ℹ️ *Внимание!* ℹ️\n\nСейчас произойдёт запланированный рестарт бота. Ваша игра сохранится. Пожалуйста, подождите. Приносим свои извинения за неудобства.",
                parse_mode="Markdown",
            )
        bot.delete_message(message.chat.id, restart.message_id)
        logger.info("shutdowned bot")
        bot.send_message(
            message.chat.id,
            f"✅ Сообщения отправились успешно!",
        )
        bot.stop_bot()


@bot.message_handler(content_types=["text"])
def alternative_guess(message: Message):
    if message.text.lower().startswith('guess') and (len(message.text) == 5 or message.text[5] == ' '):
        message.text = '/' + message.text
        guess(message)
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        message.text = '/guess ' + message.text
        guess(message)



start_thread(f=from_queue_processing, logger=logger, delay=delay)
logger.info("started bot")
bot.infinity_polling()
