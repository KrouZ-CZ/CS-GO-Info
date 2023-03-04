import threading
import time

import telebot
from telebot import types
import valve.source.a2s

from config import *

bot = telebot.TeleBot(TOKEN)

def logging(func):
    def wrapper(*args, **kwargs):
        print(f"{args[1].from_user.username}({args[1].from_user.id}): {args[1].text}")
        func(*args, **kwargs)
    return wrapper

class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.current_status = 'Off'
        self.min_online = 3
        self.msg = None
        self.ismon = False
        self.ipformon = None

    @logging
    def handler(self, message):
        self.msg = message

        if message.text == "/start":
            self.m_start()
        elif message.text == "Начать мониторинг":
            self.current_status = "StartMon"
            self.send("Введите IP:Port сервера")
        elif message.text == "Узнать информацию о сервере":
            self.current_status = "GetTempIp"
            self.send("Введите IP:Port сервера")
        elif message.text == "Настройки":
            self.current_status = "Settings1"
            self.send("Введите мин количество игроков на сервере")
        elif message.text == "Остановить":
            self.ismon = False
            self.send("Мониторинг успешно остановлен")
        elif self.current_status == "StartMon":
            self.m_startmon()
        elif self.current_status == "GetTempIp":
            self.m_info()
        elif self.current_status == "Settings1":
            self.m_settings1()

    def query_handler(self, call):
        for player in self.get_players(call.data):
            msg = "Name: {name}\nScore: {score}".format(**player)
            self.send(msg)

    def get_players(self, ip):
        server_adress = ip.split(":")
        server_adress[1] = int(ip.split(":")[1])

        try:
            with valve.source.a2s.ServerQuerier(server_adress) as server:
                players = dict(server.players())['players']
            return players
        except:
            return []

    def m_start(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_1 = types.KeyboardButton("Начать мониторинг")
        btn_2 = types.KeyboardButton("Узнать информацию о сервере")
        btn_3 = types.KeyboardButton("Настройки")
        btn_4 = types.KeyboardButton("Остановить")
        markup.row(btn_1)
        markup.row(btn_2)
        markup.row(btn_3, btn_4)

        self.send("Используйте этот бот для мониторинга серверов cs:go", markup)

    def m_startmon(self):
        self.ismon = True
        self.ipformon = self.msg.text
        self.send("Мониторинг успешно начат")

    def m_info(self):
        data = self.get_info(self.msg.text) # (Name, map, online, max_online)
        form = f"Имя сервера: {data[0]}\nКарта: {data[1]}\nОнлайн: {data[2]}/{data[3]}"
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Показать игроков", callback_data=self.msg.text)
        markup.add(btn1)
        self.send(form, markup)

    def mon(self):
        data = self.get_info(self.msg.text)
        if int(data[2]) > self.min_online:
            form = f"Имя сервера: {data[0]}\nКарта: {data[1]}\nОнлайн: {data[2]}/{data[3]}"
            markup = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton("Показать игроков", callback_data=self.msg.text)
            markup.add(btn1)
            self.send(form, markup)

    def m_settings1(self):
        self.min_online = int(self.msg.text)
        self.send(f"Мин онлайн - {self.min_online}")

    def get_info(self, ip):
        server_adress = ip.split(":")
        server_adress[1] = int(ip.split(":")[1])

        try:
            with valve.source.a2s.ServerQuerier(server_adress) as server:
                info = dict(server.info())

            Name = info["server_name"]
            Map = info["map"]
            Online = int(info["player_count"])
            Max_online = info["max_players"]
        except:
            return None, None, 0, 0

        return Name, Map, Online, Max_online

    def send(self, msg, markup=None):
        bot.send_message(self.user_id, msg, reply_markup=markup)

all_users = {}

@bot.callback_query_handler(func=lambda call:True)
def query_handler(call):
    global all_users

    if not all_users.get(call.from_user.id):
        all_users[call.from_user.id] = User(call.from_user.id)

    all_users.get(call.from_user.id).query_handler(call)


@bot.message_handler(content_types=['text'])
def main(msg):
    global all_users

    if not all_users.get(msg.from_user.id):
        all_users[msg.from_user.id] = User(msg.from_user.id)

    all_users.get(msg.from_user.id).handler(msg)

def loop():
    while True:
        for user in all_users.values():
            if user.ismon:
                user.mon()

        time.sleep(30)

threading.Thread(target=loop).start()

while True:
    try:
        bot.infinity_polling()
    except Exception as e:
        time.sleep(5)
        # print(e)
