import subprocess
import sys
import os

def install_requirements():
    if not os.path.isfile('requirements.txt'):
        print("Файл requirements.txt не найден.")
        return

    try:
        # Установка зависимостей
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    except subprocess.CalledProcessError as e:
        print(f"Ошибка установки зависимостей: {e}")

# Выполнение установки зависимостей
install_requirements()


import telebot
import requests
import json
from io import BytesIO
from PIL import Image
import openai
import base64
import time
import emoji

# ProxyAPI и Telegram токены
PROXY_API_KEY = "your_api"
TELEGRAM_BOT_TOKEN = "uour__bot_token"
OPENAI_API_KEY = "your-api

# Инициализируем бота и OpenAI
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

# Структура для хранения истории пользователей
user_history = {}

model = 'gpt-4o-mini' #gpt-4o-2024-08-06, gpt-4o-mini
assistant_message = (
    "Ты - дружелюбный ИИ-помощник"
    "Когда ты отвечаешь, размышляй шаг за шагом"
    "Ты должен генерировать длинные и детальные ответы. Если это смайлик, то отвечай коротко, как обычно"
)

# Функция для добавления сообщения в историю пользователя
def add_to_history(user_id, user_message, bot_response=None, image_url=None):
    if user_id not in user_history:
        user_history[user_id] = []  # Инициализируем историю для нового пользователя
    
    # Создаем запись о взаимодействии
    entry = {"user_message": user_message}
    if bot_response:
        entry["bot_response"] = bot_response
    if image_url:
        entry["image_url"] = image_url
    
    # Добавляем запись в историю пользователя
    user_history[user_id].append(entry)
    
    # Ограничиваем историю последних 50 сообщений
    if len(user_history[user_id]) > 50:
        user_history[user_id] = user_history[user_id][-50:]


# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я бот для работы с ProxyAPI. Напиши мне сообщение, и я отвечу на него через OpenAI. Ты можешь попросить меня нарисовать тебе любое изображение, просто напиши мне: 'Нарисуй...' ")

# Переменная для отслеживания отправки предупреждения
low_balance_warning_sent = False

# Функция для запроса баланса
def get_balance():
    global low_balance_warning_sent  # Позволяет менять глобальную переменную
    
    url = "https://api.proxyapi.ru/proxyapi/balance"
    headers = {
        "Authorization": f"Bearer {PROXY_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        balance_info = response.json()
        balance = balance_info['balance']
        
        # Формируем сообщение с балансом
        balance_message = f"Текущий баланс: {balance} ₽"
        
        # Если баланс меньше 50 рублей и предупреждение не отправлялось, добавляем предупреждение в сообщение
        if balance < 50 and not low_balance_warning_sent:
            balance_message += "\n⚠️ Внимание: На вашем счету осталось меньше 50 рублей!"
            low_balance_warning_sent = True  # Устанавливаем флаг, чтобы больше не отправлять предупреждения
        
        # Если баланс восстановился выше 50 рублей, сбрасываем флаг предупреждения
        elif balance >= 50 and low_balance_warning_sent:
            low_balance_warning_sent = False  # Сбрасываем флаг, чтобы отправлять предупреждение в будущем
        
        return balance_message
    
    elif response.status_code == 402:
        return "Ошибка 402: Недостаточно средств для выполнения запроса."
    
    else:
        return f"Ошибка: {response.status_code}, {response.text}"

# Обработка команды /balance
@bot.message_handler(commands=['balance'])
def balance(message):
    balance_info = get_balance()
    bot.reply_to(message, balance_info)


# Обработка команды /recognize для распознавания изображения
@bot.message_handler(commands=['recognize'])
def recognize_image(message):
    bot.send_message(message.chat.id, "Отправьте изображение, которое нужно распознать.")


# Обработка команды /history для вывода истории
@bot.message_handler(commands=['history'])
def show_history(message):
    user_id = message.chat.id

    # Проверяем, есть ли история у пользователя
    if user_id not in user_history or len(user_history[user_id]) == 0:
        bot.send_message(user_id, "У вас пока нет истории запросов.")
        return
    
    # Составляем сообщение с историей
    history_entries = user_history[user_id][-10:]  # Отправляем последние 10 записей
    history_text = "Ваша история запросов:\n\n"
    
    for idx, entry in enumerate(history_entries, start=1):
        history_text += f"{idx}. Вы: {entry['user_message']}\n"
        if "bot_response" in entry:
            history_text += f"   Бот: {entry['bot_response']}\n"
        if "image_url" in entry:
            # Формируем гиперссылку на изображение
            history_text += f"   [Ссылка на изображение]({entry['image_url']})\n"
        history_text += "\n"
    
    bot.send_message(user_id, history_text, parse_mode="Markdown", disable_web_page_preview=True)

data = ()

def create_data(model, assistant_message, prompt):
    data = {
        "model": model,
        "messages": [
            {"role": "assistant", "content": assistant_message},
            {"role": "user", "content": prompt}
        ]
    }
    return data

# Хранение истории сообщений для каждого чата
chat_histories = {}

def send_chat_completion(chat_id, prompt, emojis=None, stickers=None):
    url = "https://api.proxyapi.ru/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {PROXY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Получение истории сообщений для текущего чата
    history = chat_histories.get(chat_id, [])
    
    # Добавляем новое сообщение пользователя в историю
    history.append({"role": "user", "content": prompt})
    
    # Добавляем системные сообщения, если есть
    if emojis:
        history.append({"role": "system", "content": f"Эмодзи: {emojis}"})
    if stickers:
        history.append({"role": "system", "content": f"Стикеры: {stickers}"})
    
    # Формируем данные для запроса
    data = {
        "model": model,
        "messages": history
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        completion = response.json()
        answer = completion['choices'][0]['message']['content']
        
        # Добавляем ответ ассистента в историю
        history.append({"role": "assistant", "content": answer})
        
        # Обновляем историю сообщений
        chat_histories[chat_id] = history
        
        return answer
    else:
        return f"Ошибка: {response.status_code}, {response.text}"

@bot.message_handler(content_types=['text', 'sticker'])
def handle_message(message):
    text = message.text
    sticker = message.sticker.file_id if message.content_type == 'sticker' else None
    emojis = emoji.demojize(text) if text else None
    
    response = send_chat_completion(message.chat.id, text or "", emojis, sticker)
    
    # Отправка сообщения в Telegram
    bot.send_message(message.chat.id, response, parse_mode='HTML')

# Функция для генерации изображения по текстовому запросу
def generate_image(prompt):
    enhanced_prompt = f"{prompt}. Create a beautiful, clear, and high-quality image"
    url = "https://api.proxyapi.ru/openai/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "prompt": enhanced_prompt, #prompt most better if u write it on english 
        "n": 1,
        "size": "1024x1024"
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Проверка на ошибки HTTP
        if response.status_code == 200:
            image_url = response.json()['data'][0]['url']
            return image_url
        else:
            return f"Ошибка генерации изображения: {response.status_code}, {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Ошибка запроса: {e}"

# Функция для генерации вариации изображения с использованием данных в памяти
def generate_image_variation(image_path):
    try:
        # Открываем изображение и изменяем его размер
        with Image.open(image_path) as img:
            img = img.resize((1024, 1024))
            
            # Сохраняем изображение в объект BytesIO
            byte_stream = BytesIO()
            img.save(byte_stream, format='PNG')
            byte_array = byte_stream.getvalue()

            # Запрос к OpenAI API для создания вариаций изображения
            response = openai.Image.create_variation(
                image=byte_array,
                n=1,
                model="dall-e-2", #dall-e-3
                size="1024x1024"
            )
            return response['data'][0]['url']
    except openai.OpenAIError as e:
        return f"Ошибка генерации вариации изображения: {e.http_status}, {e.error}"

# Функция для загрузки и сохранения изображения
def download_and_save_image(url, file_path):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверка на ошибки HTTP
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path
    except requests.exceptions.RequestException as e:
        return f"Ошибка загрузки изображения: {e}"
    
    

def split_message(message, max_length=4096):
    """ Разделяет длинное сообщение на части, каждая из которых не превышает max_length символов. """
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

# Очистка ключевых слов из запроса
def clean_prompt(prompt):
    keywords = [
        "нарисуй", "draw", "рисунок"
    ]
    for keyword in keywords:
        prompt = prompt.lower().replace(keyword, "")
    return prompt.strip()

# Обработка текстовых сообщений для генерации текста или изображения
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_message = message.text
    user_id = message.chat.id
    
    # Проверяем, содержит ли сообщение команду на генерацию изображения
    if any(word in user_message.lower() for word in ["нарисуй", "draw", "рисунок"]):
        # Генерация изображения
        prompt = clean_prompt(user_message)  # Убираем ключевые слова из запроса
        image_url = generate_image(prompt)
        
        if image_url.startswith("Ошибка"):
            bot.send_message(user_id, image_url)
        else:
            bot.send_message(user_id, "Генерация изображения...")
            file_path = download_and_save_image(image_url, "generated_image.png")
            
            if file_path and os.path.isfile(file_path):
                with open(file_path, 'rb') as image:
                    bot.send_photo(user_id, image)
                    add_to_history(user_id, user_message, image_url=image_url)  # Сохраняем запрос и изображение в историю
                os.remove(file_path)  # Удаляем файл
            else:
                bot.send_message(user_id, file_path)
    else:
        # Отправляем запрос в OpenAI и сохраняем результат
        bot_response = send_chat_completion(user_message)

         # Разделяем длинный ответ на части и отправляем каждую часть отдельно
        messages = split_message(bot_response)
        for msg in messages:
            bot.send_message(user_id, msg)

        add_to_history(user_id, user_message, bot_response=bot_response)  # Сохраняем запрос и ответ в историю

# Функция кодирования изображения в base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Функция для распознавания содержимого изображения с низким разрешением
def recognize_image_low_res(image_path, prompt):
    base64_image = encode_image(image_path)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    payload = {
        "model": "gpt-4-turbo", #only this avialiable, idk
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt  # Используем промпт, переданный пользователем
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low"  # Указываем низкое разрешение 
                        }
                    }
                ]
            }
        ],
        "max_tokens": 2000
    }
    
    response = requests.post("https://api.proxyapi.ru/openai/v1/chat/completions", headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Ошибка распознавания изображения: {response.status_code}, {response.text}"

# Обработка изображения и сообщения, отправленного пользователем
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # Ожидаем следующего сообщения от пользователя в качестве промпта
        sent_message = bot.send_message(message.chat.id, "Напишите описание или подпись для изображения.")
        bot.register_next_step_handler(sent_message, get_prompt_and_recognize_image, message)
    
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при обработке изображения: {e}")

# Получение промпта и распознавание изображения
def get_prompt_and_recognize_image(prompt_message, original_message):
    try:
        # Сохраняем изображение
        file_info = bot.get_file(original_message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Указываем путь для сохранения изображения
        image_path = file_info.file_path.split('/')[-1]
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Распознаем содержимое изображения с переданным промптом
        prompt = prompt_message.text
        recognition_result = recognize_image_low_res(image_path, prompt)
        
        # Отправляем результат пользователю
        bot.send_message(original_message.chat.id, recognition_result)
        
        # Удаляем изображение после обработки (опционально)
        os.remove(image_path)
    
    except Exception as e:
        bot.send_message(original_message.chat.id, f"Произошла ошибка при обработке изображения: {e}")


# Запуск бота
def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except requests.exceptions.ReadTimeout:
            print("ReadTimeout error. Retrying in 5 seconds...")
            time.sleep(5)  # Задержка перед повторной попыткой
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

run_bot()
