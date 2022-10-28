import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s %(name)s',
    filename='program.log',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler(sys.stdout)
handler = RotatingFileHandler(
    'program.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)
logger.addHandler(stream_handler)

PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('T_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        return False


def send_message(bot, message):
    """Отправка сообщения в телеграм, в случае обновления статуса ДЗ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Успешная отправка сообщения в Telegram.')
    except Exception as error:
        message = f'{error} - сбой при отправке сообщения в Telegram.'
        send_error(error, message)


def send_error(error, message):
    """Отправка сообщения об ошибке в Telegram."""
    message_telegram = f'В работе бота произошла ошибка: {error} {message}'
    logger.error(message_telegram)
    logger.info('Информация об ошибке отправлена в Telegram.')
    send_message(bot, message_telegram)


def get_api_answer(current_timestamp):
    """Отправка запроса на API сервера."""
    timestamp = current_timestamp or int(time.time())
    PAYLOAD = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=PAYLOAD)
    if response.status_code != 200:
        raise AssertionError('Недоступность эндпоинта.')
    response_json = response.json()
    return response_json


def check_response(response_json):
    """Проверка ответа API сервера."""
    if type(response_json) is not dict:
        raise TypeError('Ответ API отличен от словаря')
    try:
        homeworks2 = response_json.get('homeworks')
    except KeyError:
        logger.error('Ошибка словаря по ключу homeworks')
        raise KeyError('Ошибка словаря по ключу homeworks')
    try:
        homework = homeworks2[0]
    except IndexError:
        logger.debug('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Проверка статуса ДЗ."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logger.error('Непонятный статус домашней работы.')


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    global bot
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    check_tokens()
    while True:
        try:
            message = get_api_answer(current_timestamp)
            answer = check_response(message)
            status = parse_status(answer)
            print(status)
            if isinstance(status, str):
                send_message(bot, status)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
