import requests
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import telegram
from http import HTTPStatus

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s',
    encoding='UTF-8',
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log',
                              encoding='UTF-8',
                              maxBytes=50000000,
                              backupCount=5
                              )
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 4
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат.
    Чат задан переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot и
    строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Ошибка отправки сообщения в телеграм')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params
                                         )
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        message = f'Ошибка при запросе к основному API: {error}'
        send_message(bot, message)
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        status_code = homework_statuses.status_code
        message = f'Ошибка {status_code}'
        logging.error(message)
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        send_message(bot, message)
        raise Exception(f'Ошибка {status_code}')
    response = homework_statuses.json()
    print(response)
    return response


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API.
    Ответ приведен к типам данных Python.
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ (он может бытьnи пустым), доступный в ответе
    API по ключу 'homeworks'
    """
    if type(response) is not dict:
        raise TypeError('Ответ API отличен от словаря')
    try:
        list_works = response.get('homeworks')
    except KeyError:
        message = 'Ошибка словаря по ключу homeworks'
        logger.error(message)
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        send_message(bot, message)
        return message
    try:
        homework = list_works[0]
    except IndexError:
        message = 'Нет домашних работ, отправленных на проверку'
        logger.error(message)
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        send_message(bot, message)
        return message
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает всего один элемент из списка домашних
    работ. В случае успеха, функция возвращает подготовленную для отправки в
    Telegram строку, содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы.
    Если отсутствует хотя бы одна переменная окружения — функция
    должна вернуть False, иначе — True.
    """
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1639945358 #int(time.time())
    STATUS = ''
    ERROR_CACHE_MESSAGE = ''
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise 'Отсутствуют одна или несколько переменных окружения'
    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            if message != STATUS:
                send_message(bot, message)
                STATUS = message
            current_timestamp = 1639945358 #response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            if message != ERROR_CACHE_MESSAGE:
                send_message(bot, message)
                ERROR_CACHE_MESSAGE = message
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
