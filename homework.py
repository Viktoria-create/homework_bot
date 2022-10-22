from telegram import Bot
import os
import sys
import time
import requests
import logging
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Посылает сообщение от бота в чат с TELEGRAM_CHAT_ID."""
    try:
        logger.info(f'Отправлено сообщение: "{message}"')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(error)


def get_api_answer(current_timestamp):
    """Получает json со списком работ."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.info("К Яндекс.Практикум API отправлен запрос")
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(error)
    else:
        if response.status_code != 200:
            raise OSError("Response " + str(response.status_code)
                          + ": " + response.content)
    return response.json()


def check_response(response):
    """Проверяет наличие работы в ответе от сервера."""
    if type(response) is not dict:
        raise TypeError('Ответ API отличен от словаря')
    try:
        response['homeworks'][0]
    except KeyError:
        logger.error('Ошибка словаря по ключу homeworks')
        raise KeyError('Ошибка словаря по ключу homeworks')
    except Exception:
        logger.error('В ответе сервера нет данных о работе.')
        raise Exception('В ответе сервера нет данных о работе.')
    return response


def parse_status(homework):
    """Выносит вердикт о проверке работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_name is None:
        logger.error('В ответе сервера нет названия домашней работы.')
    if homework_status is None:
        logger.error('В ответе сервера нет статуса домашней работы.')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность токенов."""
    token = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(token)


def main():
    """Основная логика работы бота."""
    check_tokens_result = check_tokens()
    if not check_tokens_result:
        exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    homework_preload_id = 0
    homework_preload_status = 'initial'
    while True:
        try:
            current_timestamp = int(time.time())
            current_timestamp = [0]
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            status_received = homework['status']
            if (homework_preload_status != status_received
                    or homework_preload_id != homework['id']):
                verdict = parse_status(homework)
                send_message(bot, verdict)
                homework_preload_status = status_received
            else:
                logger.debug('Статус работы не обновлен.')
            if homework_preload_id != homework['id']:
                homework_preload_id = homework['id']
                homework_preload_status = status_received
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        else:
            current_timestamp = response['current_date']
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
