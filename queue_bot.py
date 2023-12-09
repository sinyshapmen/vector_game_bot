import threading
from queue import Queue
import time

# Определите глобальную переменную для очереди запросов
request_queue = Queue()


# Функция для добавления запроса в очередь
def add_request_to_queue(answer: str, group_id: str, chat_id: str, full_name: str):
    request_queue.put((answer, group_id, chat_id, full_name))


# Функция для обработки запросов из очереди
def process_requests(f, logger, delay):
    while True:
        time.sleep(60)

        # Получаем запрос из очереди
        request = request_queue.get()
        if request is None:
            break  # Завершаем цикл при получении None из очереди
        answer, group_id, chat_id, full_name = request

        f(request)
        print(f"Processing request: {answer}, {group_id}, {chat_id}, {full_name}")

        if logger is not None:
            logger.info(
                f"Processing request: {answer}, {group_id}, {chat_id}, {full_name}"
            )

        request_queue.task_done()


def start_thread(f, logger=None, delay=60):
    request_thread = threading.Thread(target=process_requests, args=[f, logger, delay])
    request_thread.start()


def get_queue_length():
    return request_queue.qsize()
