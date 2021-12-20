import requests
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import telegram


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

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат, определяемый переменной окружения
    TELEGRAM_CHAT_ID. Принимает на вход два параметра: экземпляр класса Bot и
    строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Удачная отправка сообщения в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Ошибка отправки сообщения в телеграм')

def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса. В качестве параметра
    функция получает временную метку. В случае успешного запроса должна вернуть
    ответ API, преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        message = f'Ошибка при запросе к основному API: {error}'
        send_message(bot, message)
    response = homework_statuses.json()
    print(response)
    return response


def check_response(response):
    """Проверяет ответ API на корректность. В качестве параметра функция получает
    ответ API, приведенный к типам данных Python. Если ответ API соответствует
    ожиданиям, то функция должна вернуть список домашних работ (он может быть
    и пустым), доступный в ответе API по ключу 'homeworks'
    """
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
    """Извлекает из информации о конкретной домашней работе статус
    этой работы. В качестве параметра функция получает только один
    элемент из списка домашних работ. В случае успеха, функция возвращает
    подготовленную для отправки в Telegram строку, содержащую один из вердиктов
    словаря HOMEWORK_STATUSES.
    """
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        message = f'Невозможно проверить статус: отсутствуют работы: {error}'
        logger.error(message)
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        send_message(bot, message)
        return message


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы для работы
    программы. Если отсутствует хотя бы одна переменная окружения — функция
    должна вернуть False, иначе — True.
    """
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        return False


def main():
    """Основная логика работы бота.
    """
    current_timestamp = int(time.time())
    STATUS = ''
    ERROR_CACHE_MESSAGE = ''
    while check_tokens() == True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            if message != STATUS:
                send_message(bot, message)
                STATUS = message
            else:
                pass
            current_timestamp = 1638223261
            #response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            if message != ERROR_CACHE_MESSAGE:
                send_message(bot, message)
                ERROR_CACHE_MESSAGE = message
            else:
                pass
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
