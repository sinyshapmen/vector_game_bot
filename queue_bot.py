import threading
import time

# Определите глобальную переменную для очереди запросов
request_queue = []


# Функция для добавления запроса в очередь
def add_request_to_queue(
    answer: str,
    group_id: str,
    chat_id: str,
    full_name: str,
    message_queue_id: str,
    user_id: str,
    logger,
):
    logger.info(
        f"Adding request: ans {answer} | g_id {group_id} | user {user_id} | q_len {len(request_queue) + 1}"
    )

    request_queue.append(
        (answer, group_id, chat_id, full_name, message_queue_id, user_id)
    )


# Функция для обработки запросов из очереди
def process_requests(process_func, logger, delay):
    while True:
        time.sleep(delay)

        # Получаем запрос из очереди
        if len(request_queue):
            request = request_queue[0]
            if request is None:
                break  # Завершаем цикл при получении None из очереди
            answer, group_id, _, _, _, user_id = request

            process_func(request)

            if logger is not None:
                logger.info(
                    f"Processing request: ans {answer} | g_id {group_id} | user {user_id}"
                )

            request_queue.pop(0)


def start_thread(f, logger=None, delay=60):
    request_thread = threading.Thread(target=process_requests, args=[f, logger, delay])
    request_thread.start()


def get_queue_length():
    return len(request_queue)
