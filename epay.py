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
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.dispatcher.fsm.state import State, StatesGroup

load_dotenv(dotenv_path='/root/paybots/api.env')

API_TOKEN = os.getenv('API_TOKEN_EPAY')
CHANNEL_ID = int(os.getenv('CHANNEL_ID_EPAY'))
GROUP_ID = int(os.getenv('GROUP_ID_EPAY'))
ADMINS = [831055006]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

visited_chats = set()

def load_bin_data():
    try:
        bin_module = importlib.import_module("BINs")
        logger.info("BINs.py успешно загружен.")
        return bin_module.bin_database
    except Exception as e:
        logger.error(f"Ошибка при загрузке BIN.py: {e}")
        return {}

def extract_bin(text):
    cleaned_text = re.sub(r"[^\d]", "", text)
    numbers = re.findall(r"\b\d{6,16}\b", cleaned_text)
    for number in numbers:
        bin_candidate = number[:6]
        logger.info(f"Найден BIN: {bin_candidate}")
        return bin_candidate
    return None

def git_pull():
    try:
        subprocess.run(["git", "-C", "/root/paybots/", "pull"], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при выполнении git pull:\n{e.stderr}")

@router.message()
async def handle_message(message: Message):
    if message.chat.id not in visited_chats:
        visited_chats.add(message.chat.id)
        await message.reply("Привет! Я готов помочь вам с определением BIN.")
    bin_data = load_bin_data()
    bin_code = extract_bin(message.text)
    if bin_code:
        bank_name = bin_data.get(bin_code, "Банк с данным BIN-кодом не найден в базе.")
        await message.reply(bank_name)
        if message.chat.id == CHANNEL_ID:
            await bot.send_message(GROUP_ID, bank_name)
        git_pull()

@router.message(lambda message: message.from_user.id in ADMINS, commands="send")
async def send_broadcast(message: Message):
    text = message.text.partition(" ")[2]
    if text:
        for chat_id in visited_chats:
            try:
                await bot.send_message(chat_id, text)
            except Exception as e:
                logger.error(f"Ошибка при рассылке в чат {chat_id}: {e}")
    else:
        await message.reply("Введите текст после команды /send")

if __name__ == '__main__':
    logger.info("Бот запущен и готов к работе.")
    dp.run_polling(bot)
