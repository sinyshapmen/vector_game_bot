import threading
import time
from tinydb import TinyDB, Query

queue_db = TinyDB("database/queue.json")
User = Query()


# Функция для добавления запроса в очередь
def add_request_to_queue(
    answer: str,
    group_id: int,
    chat_id: int,
    full_name: str,
    message_queue_id: int,
    user_id: int,
    logger,
    selected_model: str,
):
    logger.info(
        f"Adding request: ans {answer} | g_id {group_id} | user {user_id} | q_len {len(queue_db.all()) + 1} | model: {selected_model}"
    )

    queue_db.insert(
        {"data": (answer, group_id, chat_id, full_name, message_queue_id, user_id, selected_model)}
    )


# Функция для обработки запросов из очереди
def process_requests(process_func, logger, delay):
    while True:
        time.sleep(delay)

        # Получаем запрос из очереди
        if queue_db.all():
            request = queue_db.all()[0]["data"]
            if request is None:
                break  # Завершаем цикл при получении None из очереди
            answer, group_id, _, _, _, user_id, selected_model = request

            process_func(request)

            if logger is not None:
                logger.info(
                    f"Processing request: ans {answer} | g_id {group_id} | user {user_id} | model: {selected_model}"
                )

            queue_db.remove(doc_ids=[queue_db.all()[0].doc_id])


def start_thread(f, logger=None, delay=60):
    request_thread = threading.Thread(target=process_requests, args=[f, logger, delay])
    request_thread.start()


def get_queue_length():
    return len(queue_db.all())
