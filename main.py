from dotenv import load_dotenv
from telebot import types
import configparser
import threading
import schedule
import requests
import platform
import datetime
import telebot
import time
import json
import re
import os

load_dotenv()

def load_user(user_id):
    users = configparser.ConfigParser()
    users.read(f'users/{user_id}.ini')
    return users

BOT_TOKEN = os.getenv('BOT_TOKEN')

telBot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

header = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

if not os.path.exists('correios'):
    os.makedirs('correios')

if not os.path.exists('users'):
    os.makedirs('users')

def get_creation_date(file_path):
    if platform.system() == 'Windows':
        # Windows
        return datetime.datetime.fromtimestamp(os.path.getctime(file_path))
    else:
        # Linux e macOS
        stat = os.stat(file_path)
        try:
            return datetime.datetime.fromtimestamp(stat.st_birthtime)
        except AttributeError:
            # For Systems that don't support st_birthtime.
            return datetime.datetime.fromtimestamp(stat.st_mtime)

@telBot.message_handler(commands=['start'])
def send_commands(message):

    if message.chat.type != "private":
        return
    telBot.reply_to(message, f"<b>Olá, este bot serve para fazer rastreamento de encomendas e está atualmente em desenvolvimento.</b>\nV1.8\n\n - Use o comando /correios para rastrear uma encomenda.\n * Exemplo: /correios QA000000000BR *nome da encomenda*")

def statusEmoji(status, type):

    if type == "text":
        space = ""
    elif type == "subtext":
        space = "\n\n"

    text = ""

    if "postado" in status['status']:
        text += f"Status: 📥 {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
    elif "trânsito" in status['status']:
        text += f"Status: 🚚 {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
    elif "saiu para entrega" in status['status']:
        text += f"Status: 📤 {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
    elif "entregue" in status['status']:
        text += f"Status: ✅ {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}" 
    elif "aguardando pagamento" in status['status']:
        text += f"Status: 🟠💰 {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"         
    elif "Pagamento confirmado" in status['status']:
        text += f"Status: 🟢💸 {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
    elif "Encaminhado para fiscalização" in status['status']:
        text += f"Status: 🟡👮🏻‍♂️ {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
    elif "Correios do Brasil" in status['status']:
        text += f"Status: 🇧🇷 {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
    elif "no país de origem" in status['status']:
        text += f"Status: 🌎 {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
    else:
        text += f"Status: {status['status']}\n{status['date'].replace('Data  :','Data:')}\n{status['place']}{space}"
        if type == "text":
            with open("logs.txt", "a") as logs:
                logs.write(f"{status['status']}\n")

    return text    

@telBot.message_handler(commands=['encomendas'])
def encomendas(message):

    if message.chat.type != "private":
        return
    
    user_id = str(message.chat.id)
    markup = telebot.types.InlineKeyboardMarkup()


    if f"{user_id}.ini" in os.listdir('users'):

        users = load_user(user_id)

        encomendas = "📦📦Encomendas:"

        for key, value in users["Correios"].items():
            if value == "":
                value = key.upper()
            markup.row(telebot.types.InlineKeyboardButton(value, callback_data=f"view{key.upper()}"), telebot.types.InlineKeyboardButton("❌", callback_data=f"del{key.upper()}"))
        
    else:
        with open(f"users/{user_id}.ini", 'w') as file:
            file.write("[Correios]")

        users = load_user(user_id)

    if len(users["Correios"].items()) == 0:
        telBot.send_message(user_id, f"<b>❌ Nenhuma encomenda cadastrada!</b>\n\nCadastre com: /correios QA000000000BR *nome da encomenda*")
    else:
        telBot.send_message(user_id, encomendas,reply_markup=markup)
        
    @telBot.callback_query_handler(func=lambda query: query.data.startswith('view') or query.data.startswith('del'))
    def callback_handler1(query):
        chat_id = query.message.chat.id
        original_message = query.message

        if query.message.chat.type != "private":
            return
        
        if query.data.startswith("del"):
            
            packet = query.data.replace("del","")

            users = load_user(chat_id)
            users.remove_option("Correios", packet)
            users.write(open(f"users/{chat_id}.ini", "w"))
            
            telBot.answer_callback_query(query.id, text="✅ Encomenda removida com sucesso!")
            
            found = False

            for user in os.listdir("users"):
                users = load_user(user.replace('.ini', ''))
                if users.has_option("Correios", packet):
                    found = True

            if found == False and os.path.exists(f"correios/{packet}.json"):
                os.remove(f"correios/{packet}.json")

            users = load_user(chat_id)

            markup = telebot.types.InlineKeyboardMarkup()

            for key, value in users["Correios"].items():
                if value == "":
                    value = key.upper()
                markup.row(telebot.types.InlineKeyboardButton(value, callback_data=key.upper()), telebot.types.InlineKeyboardButton("❌", callback_data=f"del{key.upper()}"))

            if len(users["Correios"].items()) == 0:
                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"<b>❌ Nenhuma encomenda cadastrada!</b>\n\nCadastre com: /correios QA000000000BR *nome da encomenda*", reply_markup=markup)
            else:
                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=encomendas, reply_markup=markup)
            
        else:
            correios(f"{query.data.replace('view','')}:{chat_id}")
         

@telBot.message_handler(commands=['correios'])
def correios(message):

    if str(type(message)) == "<class 'telebot.types.Message'>":
        if message.chat.type != "private":
            return
        
        chat_id = message.chat.id

        try:
            cod = message.text.split()[1].strip().upper()
        except:
            telBot.send_message(chat_id, "Digite um codigo de rastreio após o comando!\n<b>Exemplo: /correios QA000000000BR *nome da encomenda*</b>")
            return
        
        if len(message.text.split()) >= 3:
            name = " ".join(message.text.split()[2:]).strip()
            if len(name) > 24:
                telBot.send_message(chat_id, "❌ O nome da encomenda não pode ultrapassar de 24 caracteres!")
                return
        else:
            name = ""
    else:
        cod = message.split(":")[0].strip().upper()
        chat_id = message.split(":")[1].strip()
        name = ""

    if f"{chat_id}.ini" not in os.listdir('users'):
        with open(f"users/{chat_id}.ini", 'w') as file:
            file.write("[Correios]")

    if len(cod) == 13 and cod[:2].isalpha() and cod[-2:].isalpha():
        found = False

        msg = telBot.send_message(chat_id, "🔍 Consultando...")

        for encomenda in os.listdir('correios'):
            if cod in encomenda:

                with open(f'correios/{cod}.json', 'r') as file:
                    status = json.load(file)

                subtext = ""
                save = True

                if status == []:
                    subtext += "🛑 Aguardando Postagem!"
                else:
                    for field in status:
                        subtext += statusEmoji(field, "subtext")

                        if "entregue" in subtext:
                            save = False

                if save == True:
                    users = load_user(chat_id)
                    if users.has_option("Correios", cod):
                        if name != "":
                            users.set("Correios", cod, name)
                    else:
                        users.set("Correios", cod, name)
                    users.write(open(f"users/{chat_id}.ini", "w")) 

                    name = users.get("Correios", cod)

                if name != "":
                    text = f"📦Encomenda: <b>{name}</b>\nCódigo: <b>{cod}</b>\n\n"
                else:
                    text = f"📦Código: <b>{cod}</b>\n\n"
        
                telBot.delete_message(chat_id, msg.message_id)
                telBot.send_message(chat_id, text + subtext)

                found = True
                break

        if found == False:

            payload= f"tracking_code_pt={cod}"

            tries = 0
            while True:
                response = requests.post('https://www.nuvemshop.com.br/ferramentas/tracking', data=payload, headers=header)
                if response.status_code != 200:
                    tries += 1
                    time.sleep(2)
                elif response.status_code == 200:

                    status = response.json()[0]

                    subtext = ""
                    save = True

                    if status == []:
                        subtext += "🛑 Aguardando Postagem!"
                    else:
                        for field in status:
                            subtext += statusEmoji(field, "subtext")

                            if "entregue" in subtext:
                                save = False

                    if save == True:  
                        with open(f'correios/{cod}.json', 'w') as file:
                            json.dump(status, file, ensure_ascii=True, indent=4)

                        users = load_user(chat_id)
                        if users.has_option("Correios", cod):
                            if name != "":
                                users.set("Correios", cod, name)
                        else:
                            users.set("Correios", cod, name)
                        users.write(open(f"users/{chat_id}.ini", "w")) 

                        name = users.get("Correios", cod)                    

                    if name != "":
                        text = f"📦Encomenda: <b>{name}</b>\nCódigo: <b>{cod}</b>\n\n"
                    else:
                        text = f"📦Código: <b>{cod}</b>\n\n"


                    telBot.delete_message(chat_id, msg.message_id)
                    telBot.send_message(chat_id, text + subtext)
                    break

                if tries >= 3:
                    telBot.delete_message(chat_id, msg.message_id)
                    telBot.send_message(chat_id, "❌ Falha ao consultar o código de rastreio!")
                    break

    else:
        telBot.send_message(chat_id, "❌ Código de rastreio inválido!\n<b>Exemplo: /correios QA000000000BR *nome da encomenda*</b>")
        
@telBot.message_handler(commands=['resumo'])
def resumo(message):

    user_id = str(message.chat.id)

    if message.chat.type != "private":
        return
    
    markup = telebot.types.InlineKeyboardMarkup()

    try:
        if f"{user_id}.ini" in os.listdir('users'):
            user = load_user(user_id)
            if len(user["Correios"].items()) == 0:
                raise
            else:

                resumoText = ""

                i = 1
                limit = 5
                pagData = []
                for packet in user["Correios"]:
                    try:
                        with open(f"correios/{packet.upper()}.json", 'r') as file:
                            status = json.load(file)
                    except:
                        continue

                    if user["Correios"][packet] != "":
                        resumoText += f"📦Encomenda: <b>{user['Correios'][packet]}</b>\nCódigo: <b>{packet.upper()}</b>\n"
                    else:
                        resumoText += f"📦Código: <b>{packet.upper()}</b>\n"
                        
                    if status == []:
                        resumoText += f"Status: 🛑 Aguardando Postagem!\n\n"
                    else:
                        lastStatus = status[0]

                        resumoText += statusEmoji(lastStatus, "subtext")
                        
                    if i - limit == 0:
                        limit += 5

                        pagData.append(resumoText)

                        resumoText = ""
                    i += 1 


                if resumoText != "":
                    pagData.append(resumoText)

                if len(pagData) > 1:
                    pagsTotal = len(pagData)

                    markup.row(telebot.types.InlineKeyboardButton("➡", callback_data="next"))
                    resumo = f"📦📦Resumo:\n📄 Pag: 1/{pagsTotal}\n\n"
                else:
                    resumo = "📦📦Resumo:\n\n"
                
                telBot.send_message(user_id, resumo + pagData[0], reply_markup=markup)
        else:
            with open(f"users/{user_id}.ini", 'w') as file:
                file.write("[Correios]")
            raise
    except:
        telBot.send_message(user_id, f"<b>❌ Nenhuma encomenda cadastrada!</b>\n\nCadastre com: /correios QA000000000BR *nome da encomenda*")

    @telBot.callback_query_handler(func=lambda query: query.data.startswith('next') or query.data.startswith('previous') or query.data.startswith('home'))
    def callback_handler2(query):
            
            chat_id = query.message.chat.id
            original_message = query.message

            if query.message.chat.type != "private" or query.data.startswith("view") or query.data.startswith("del"):
                return
            
            markup = telebot.types.InlineKeyboardMarkup()

            match = re.search(r'Pag: (\d+)/(\d+)', original_message.text)

            pagAtual = int(match.group(1)) - 1
            pagTotal = int(match.group(2)) - 1

            nextPag = pagAtual + 1

            previousPag = pagAtual - 1

            if query.data == "next":

                if nextPag == pagTotal:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous"), telebot.types.InlineKeyboardButton("🏠", callback_data="home"))
                else:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous"), telebot.types.InlineKeyboardButton("🏠", callback_data="home"),telebot.types.InlineKeyboardButton("➡", callback_data="next"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Resumo:\n📄 Pag: {nextPag + 1}/{pagsTotal}\n\n" + pagData[nextPag], reply_markup=markup)
            elif query.data == "previous":

                if previousPag == 0 :
                    markup.row(telebot.types.InlineKeyboardButton("➡", callback_data="next"))
                else:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous"), telebot.types.InlineKeyboardButton("🏠", callback_data="home"),telebot.types.InlineKeyboardButton("➡", callback_data="next"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Resumo:\n📄 Pag: {previousPag + 1}/{pagsTotal}\n\n" + pagData[previousPag], reply_markup=markup)
                 
            elif query.data == "home":

                markup.row(telebot.types.InlineKeyboardButton("➡", callback_data="next"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Resumo:\n📄 Pag: 1/{pagsTotal}\n\n" + pagData[0], reply_markup=markup)
            

def checkPackets(type):
    for packet in os.listdir('correios'):

        packetCod = packet.replace('.json', '')

        with open(f'correios/{packetCod}.json', 'r') as file:
            packetFile = json.load(file)

        if type == "normal" and packetFile == []:
                continue
        elif type == "pending" and packetFile != []:
                continue

        payload= f"tracking_code_pt={packetCod}"

        tries = 0
        while True:
            try:
                response = requests.post('https://www.nuvemshop.com.br/ferramentas/tracking', data=payload, headers=header)
                if response.status_code != 200:
                    raise Exception("Status Code != 200")
                elif response.status_code == 200:
                    packetResponse = response.json()[0]

                    if type == "pending" and packetResponse == []:
                        get_creation_date(f'correios/{packetCod}.json')
                        if (datetime.datetime.now() - get_creation_date(f'correios/{packetCod}.json')).days >= 15:
                            for user in os.listdir("users"):
                                users = load_user(user.replace('.ini', ''))
                                name = users.get("Correios", packetCod)

                                if name != "":
                                    text = f"📦Encomenda: <b>{name}</b>\nCódigo: <b>{packetCod}</b>"
                                else:
                                    text = f"📦Código: <b>{packetCod}</b>"

                                if users.has_option("Correios", packetCod):
                                    telBot.send_message(user.replace('.ini', ''), f"{text}\n\n<b>❌ Encomenda deletada por falta de atualização!</b>")

                                    users.remove_option("Correios", packetCod)
                                    users.write(open(f"users/{user}", "w"))
                            os.remove(f"correios/{packetCod}.json")
                            break

                    if len(packetResponse) != len(packetFile):
    
                        packetLastStatus = packetResponse[0]

                        if "entregue" in packetLastStatus['status']:
                            if os.path.exists(f"correios/{packetCod}.json"):
                                os.remove(f"correios/{packetCod}.json")
                        else:                    
                            with open(f'correios/{packetCod}.json', 'w') as file:
                                json.dump(packetResponse, file, ensure_ascii=True, indent=4)

                        for user in os.listdir("users"):
                            users = load_user(user.replace('.ini', ''))
                            if users.has_option("Correios", packetCod):

                                name = users.get("Correios", packetCod)
                                if name != "":
                                    text = f"📦Encomenda: <b>{name}</b>\nCódigo: <b>{packetCod}</b>\n\n<b>🔄 Encomenda Atualizada!</b>\n\n"
                                else:
                                    text = f"📦Código: <b>{packetCod}</b>\n\n<b>🔄 Encomenda Atualizada!</b>\n\n"

                                text += statusEmoji(packetLastStatus, "text")

                                if "entregue" in text:
                                    users.remove_option("Correios", packetCod)
                                    users.write(open(f"users/{user}", "w"))  

                                telBot.send_message(user, text)
                    break
            except Exception as e:
                if tries >= 3:
                    print(f"{e}")
                    break
                tries += 1
                time.sleep(10)
        time.sleep(10)
       

def schedule_polling():
    schedules = [9, 12, 15]

    schedule.every(15).minutes.do(lambda: checkPackets("normal"))  #Verify Normal Packets every 15 minutes
    for scheduleTime in schedules:
        schedule.every().day.at(f"{scheduleTime + 3}:00").do(lambda: checkPackets("pending")) #Verify Pending Packets every day at 9, 12 and 15 hours 

    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=checkPackets, args=("normal",)).start()
threading.Thread(target=schedule_polling).start()

print(f"@{telBot.get_me().username} is running...")
telBot.infinity_polling()