import logging
import random
import requests
import io
from aiogram.types import InputFile
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import os
import asyncio
from bs4 import BeautifulSoup

load_dotenv(dotenv_path='/root/paybots/api.env')
API_TOKEN = os.getenv('API_TOKEN_KASSIFY')
MERCHANT_ID = os.getenv('MERCHANT_ID_KASSIFY')
KEY_SHOP = os.getenv('KEY_SHOP_KASSIFY')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

PAYMENT_URL = "https://kassify.com/sci/"

def generate_id():
    return str(random.randint(1000000, 9999999))

user_data = {}

payment_methods = ["epaycoreRUB", "yoomoney", "yoomoney_HIYP", "P2P_pay"]

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Введите сумму платежа (без копеек):")
    user_data[message.chat.id] = {}

@dp.message(lambda msg: msg.text.isdigit())
async def get_sum(message: Message):
    amount = message.text + ".00"
    user_data[message.chat.id]['amount'] = amount
    keyboard = InlineKeyboardBuilder()
    for method in payment_methods:
        keyboard.add(InlineKeyboardButton(text=method, callback_data=method))
    keyboard.adjust(2)
    await message.answer("Выберите систему оплаты:", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda call: call.data in payment_methods)
async def process_payment(callback_query: CallbackQuery):
    user_id = generate_id()
    order_id = generate_id()
    payment_system = callback_query.data
    amount = user_data[callback_query.message.chat.id]['amount']
    hash_string = f"{MERCHANT_ID}:{amount}:{KEY_SHOP}:{order_id}"
    signature = requests.utils.quote(hash_string)
    data = {
        "ids": MERCHANT_ID,
        "summ": amount,
        "us_id": order_id,
        "user_code": user_id,
        "paysys": payment_system,
        "s": signature
    }
    response = requests.post(PAYMENT_URL, data=data)
    response_text = response.text
    if response.status_code == 200:
        if response_text.startswith("<!DOCTYPE html>"):
            soup = BeautifulSoup(response_text, "html.parser")
            error_message = soup.find("p", class_="errorText")
            if error_message:
                await callback_query.message.answer(f"Ошибка: {error_message.text.strip()}")
            else:
                log_file = io.BytesIO(response_text.encode('utf-8'))
                log_file.seek(0)
                await callback_query.message.answer_document(InputFile(log_file, filename="response.html"))
        else:
            if len(response_text) > 4000:
                log_file = io.BytesIO(response_text.encode('utf-8'))
                log_file.seek(0)
                await callback_query.message.answer_document(InputFile(log_file, filename="response.txt"))
            else:
                await callback_query.message.answer(f"Ответ сервера: {response_text}")
    else:
        await callback_query.message.answer(f"Ошибка: {response.status_code}. Ответ сервера: {response.reason}")
    await callback_query.message.answer("Введите сумму следующего платежа:")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
