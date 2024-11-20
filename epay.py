import logging
import re
import importlib
import os
import subprocess
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.dispatcher.router import Router

# Загружаем переменные окружения
load_dotenv(dotenv_path='/root/paybots/api.env')

API_TOKEN = os.getenv('API_TOKEN_EPAY')
CHANNEL_ID = int(os.getenv('CHANNEL_ID_EPAY'))  # Преобразуем в число
GROUP_ID = int(os.getenv('GROUP_ID_EPAY'))  # Преобразуем в число

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# Импортируем BIN-данные из внешнего файла
def load_bin_data():
    """
    Загрузка или перезагрузка BIN данных из BINs.py.
    """
    try:
        if "BINs" in globals():
            importlib.reload(globals()["BINs"])  # Принудительная перезагрузка модуля
        else:
            globals()["BINs"] = importlib.import_module("BINs")  # Импортируем модуль
        logger.info("BINs.py успешно загружен.")
        return globals()["BINs"].bin_database
    except ModuleNotFoundError:
        logger.error("Файл BINs.py не найден. Проверьте, находится ли он в той же директории, что и бот.")
        return {}
    except Exception as e:
        logger.error(f"Ошибка при загрузке BINs.py: {e}")
        return {}

def extract_bin(text):
    """
    Ищет шестизначный BIN-код в тексте и фильтрует по диапазону 220000-220500.
    """
    cleaned_text = re.sub(r"[^\d\s]", "", text)  # Убираем все нечисловые символы, кроме пробелов
    logger.info(f"Очищенный текст для поиска BIN: {cleaned_text}")

    # Разделяем текст на числа
    numbers = re.findall(r"\b\d{6,16}\b", cleaned_text)  # Ищем числа длиной 6-16 символов (например, карты)
    for number in numbers:
        bin_candidate = number[:6]  # Берем первые 6 цифр каждого числа
        if 220000 <= int(bin_candidate) <= 220500:  # Проверяем диапазон BIN-кодов
            logger.info(f"Найден BIN: {bin_candidate}")
            return bin_candidate
    logger.info("BIN-код не найден после проверки диапазона.")
    return None

def git_pull():
    """
    Выполняет команду git pull в папке /root/paybots/
    """
    try:
        result = subprocess.run(
            ["git", "-C", "/root/paybots/", "pull"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Git pull выполнен успешно:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при выполнении git pull:\n{e.stderr}")

@router.channel_post()
async def handle_channel_post(message: Message):
    logger.info(f"Получено сообщение из канала {message.chat.id}")
    logger.info(f"Текст сообщения: {message.text}")

    # Проверка, что текст в сообщении присутствует
    if message.text is None:
        logger.info("Сообщение не содержит текст, пропуск обработки.")
        return

    # Проверка сообщений из канала
    if message.chat.id == CHANNEL_ID:
        logger.info("Сообщение поступило из целевого канала.")
        git_pull()  # Выполняем git pull перед загрузкой данных
        bin_data = load_bin_data()  # Загружаем BIN-данные после обновления
        bin_code = extract_bin(message.text)
        if bin_code:
            bank_name = bin_data.get(bin_code, "Банк с данным BIN-кодом не найден в базе. @azikmrazik")
            try:
                # Отправка сообщения только в группу
                await bot.send_message(GROUP_ID, bank_name)
                logger.info("Сообщение о банке отправлено в группу.")
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения в группу: {e}")
        else:
            logger.info("BIN-код не найден в тексте сообщения.")

if __name__ == '__main__':
    logger.info("Бот запущен и готов к работе.")
    dp.run_polling(bot)
