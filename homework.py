import json
import logging
import time
from dotenv import load_dotenv
import os
from http import HTTPStatus
import sys


import requests
import telegram

from exceptions import (
    TheAnswerIsNot200Error,
    UndocumentedStatusError,
    RequestExceptionError,
    JSONDecoderError
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        logger.debug(f'Отправка сообщения - "{message}" в Телеграм')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logger.error(f'Произошла ошибка при отправке сообщения {error}')


def get_api_answer(timestamp):
    """Получение API с практикума."""
    params = {'from_date': timestamp}
    try:
        homework = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as error_request: 
        message_error = f'Ошибка в запросе API: {error_request}'
        raise RequestExceptionError(message_error)
    status_code = homework.status_code
    if status_code != HTTPStatus.OK:
        message_error = (f'API {ENDPOINT} недоступен, '
                         f'код ошибки {status_code}')
        raise TheAnswerIsNot200Error(message_error)
    try:    
        return homework.json()
    except json.JSONDecodeError as error:
        raise JSONDecoderError(error)


def check_response(response):
    """Проверяем данные в response."""
    logging.info(f'Начало проверки ответа сервера {response}')
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарём')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError(
            f'Ключ "homeworks" или "current_date" не найден в {response}')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В ключе "homeworks" нет списка')
    ret = response['homeworks']
    if len(ret) == 0:
        return ""
    return ret[0]


def parse_status(homework):
    """Анализируем статус если изменился."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status not in HOMEWORK_VERDICTS:
        raise UndocumentedStatusError(
            'Ожидаемое значение и статус "verdict" отсутствует')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствует токен. Бот остановлен!'
        logging.critical(message)
        sys.exit(message)
    timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    start_message = 'Бот начал работу'
    send_message(bot, start_message)
    logging.info(start_message)
    prev_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
                prev_message = ''
            timestamp = response.get("current_date", timestamp)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            if message != prev_message:
                send_message(bot, message)
                prev_message = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
