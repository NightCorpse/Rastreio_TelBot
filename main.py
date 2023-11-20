from dotenv import load_dotenv
from telebot import types
import configparser
import threading
import schedule
import requests
import platform
import datetime
import telebot
import random
import time
import json
import re
import os

load_dotenv()

def load_user(user_id):

    sections = ["Correios", "Settings", "Feedback_IDs"]

    if f"{user_id}.ini" not in os.listdir('users'):
        with open(f"users/{user_id}.ini", 'w') as file:
            for section in sections:
                file.write(f"[{section}]\n\n")

    user = configparser.ConfigParser()
    user.read(f'users/{user_id}.ini')

    for section in sections:
        if section not in user.sections():
            user.add_section(section)

    with open(f"users/{user_id}.ini", 'w') as file:
        user.write(file)

    return user

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

telBot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

header = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

if not os.path.exists('correios'):
    os.makedirs('correios')

if not os.path.exists('users'):
    os.makedirs('users')

if not os.path.exists('feedback'):
    os.makedirs('feedback')

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
    telBot.reply_to(message, f"<b>Olá, este bot serve para fazer rastreamento de encomendas e está atualmente em desenvolvimento.</b>\nV2.5\n\n - Use o comando /correios para rastrear uma encomenda.\n * Exemplo: /correios QA000000000BR *nome da encomenda*")

def statusEmoji(status, qnt, type, user_id, show):

    if type == "text":
        space = ""
    elif type == "subtext":
        space = "\n\n"

    text = ""
    user = load_user(user_id)
    
    def emojiLoop(field, user):
        if "postado" in field['status']:
            text = f"Status: 📥 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
        elif "trânsito" in field['status']:

            if user.has_option("Settings", "cidade") and user.get("Settings", "cidade") != "":
                if user.get("Settings", "cidade") in field['place'] and show == "show":
                    text = f"<b>‼️ Encomenda próxima do destino!</b>\nStatus: 🚚 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
                else:
                    text = f"Status: 🚚 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
            else:
                text = f"Status: 🚚 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
                
        elif "saiu para entrega" in field['status']:
            text = f"Status: 📤 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
        elif "entregue" in field['status']:
            text = f"Status: ✅ {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}" 
        elif "aguardando pagamento" in field['status']:
            text = f"Status: 🟠💰 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"         
        elif "Pagamento confirmado" in field['status']:
            text = f"Status: 🟢💸 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
        elif "Encaminhado para fiscalização" in field['status']:
            text = f"Status: 🟡👮🏻‍♂️ {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
        elif "Correios do Brasil" in field['status']:
            text = f"Status: 🇧🇷 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
        elif "no país de origem" in field['status']:
            text = f"Status: 🌎 {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
        else:
            text = f"Status: {field['status']}\n{field['date'].replace('Data  :','Data:')}\n{field['place']}{space}"
            if type == "text":
                with open("logs.txt", "a") as logs:
                    logs.write(f"{field['status']}\n")
        
        return text
    
    if qnt == "1":
        text += emojiLoop(status, user)
    elif qnt == "+":
        i = 1
        for field in status:
            text += emojiLoop(field, user)
            if i == 5:
                break
            i += 1
    elif qnt == "++":
        for field in status:
            text += emojiLoop(field, user)        

    return text    

@telBot.message_handler(commands=['cidade'])
def cidade(message):
        
    chat_id = str(message.chat.id)

    if message.chat.type != "private":
        return
    
    user = load_user(chat_id)

    try:
        cod = message.text.split()[1].strip().upper()
    except:
        if not user.has_option("Settings", "cidade") or user.get("Settings", "cidade") == "":
            telBot.send_message(chat_id, "Digite um codigo de rastreio já entregue para cadastrar automaticamente sua cidade e ser alertado das encomendas mais próximas da entrega!\n\n<b>Exemplo: /cidade QA000000000BR</b>")
            return
        else:
            telBot.send_message(chat_id, f"🏙 Cidade cadastrada: <b>{user.get('Settings', 'cidade')}</b>\n\n<b>Para alterar digite: /cidade QA000000000BR</b>\n<b>Para ver encomendas proximas utilize: /proximas</b>")
            return
        
    if len(cod) == 13 and cod[:2].isalpha() and cod[-2:].isalpha():
            
        msg = telBot.send_message(chat_id, "🔍 Consultando...")
                          
        payload= f"tracking_code_pt={cod}"

        tries = 0
        while True:
            response = requests.post('https://www.nuvemshop.com.br/ferramentas/tracking', data=payload, headers=header)
            if response.status_code != 200:
                tries += 1
                time.sleep(2)
            elif response.status_code == 200:

                status = response.json()[0]
                if status == []:
                    telBot.delete_message(chat_id, msg.message_id)
                    telBot.send_message(chat_id, "❌ Código de rastreio não é valido!")
                    return
                elif "entregue" in status[0]['status']:
                    cidade = status[0]['place'].split("-")[1].split("/")[0].strip()

                    telBot.delete_message(chat_id, msg.message_id)

                    if user.has_option("Settings", "cidade"):
                        if user.get("Settings", "cidade") == cidade:
                            msg = telBot.send_message(chat_id, f"🏙 Cidade já cadastrada!\n\n<b>Para alterar digite: /cidade QA000000000BR</b>\n<b>Para ver encomendas proximas utilize: /proximas</b>")
                        elif user.get("Settings", "cidade") != "":
                            msg = telBot.send_message(chat_id, f"🏙 Cidade alterada: <b>{cidade}</b>\n\n<b>Para alterar novamente digite: /cidade QA000000000BR</b>\n<b>Para ver encomendas proximas utilize: /proximas</b>")
                    else:
                        msg = telBot.send_message(chat_id, f"🏙 Cidade cadastrada: <b>{cidade}</b>\n\n<b>Para alterar digite: /cidade QA000000000BR</b>\n<b>Para ver encomendas proximas utilize: /proximas</b>")
                    
                    try:
                        user.set("Settings", "cidade", cidade)
                        user.write(open(f"users/{chat_id}.ini", "w"))
                    except:
                        telBot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text="❌ Falha ao cadastrar cidade!")

                    return
                else:
                    telBot.delete_message(chat_id, msg.message_id)
                    telBot.send_message(chat_id, "❌ Encomenda ainda não foi entregue, envie um código de rastreio já entregue!")
                    return

            if tries >= 3:
                telBot.delete_message(chat_id, msg.message_id)
                telBot.send_message(chat_id, "❌ Falha ao consultar o código de rastreio!")
                return
    else:
        telBot.send_message(chat_id, "❌ Código de rastreio inválido!\n<b>Exemplo: /cidade QA000000000BR</b>")

@telBot.message_handler(commands=['proximas'])
def proximas(message):
        
    chat_id = str(message.chat.id)

    if message.chat.type != "private":
        return
    
    markup = telebot.types.InlineKeyboardMarkup()

    user = load_user(chat_id)

    if not user.has_option("Settings", "cidade") or user.get("Settings", "cidade") == "":
        telBot.send_message(chat_id, "Para ver encomendas proximas da entrega, primeiro cadastre sua cidade com o comando /cidade!\n\n<b>Exemplo: /cidade QA000000000BR</b>")
        return
    else:
        if user.options("Correios") == []:
            telBot.send_message(chat_id, f"<b>❌ Nenhuma encomenda cadastrada!</b>\n\nCadastre com: /correios QA000000000BR *nome da encomenda*")
            return
        else:
            cidade = user.get("Settings", "cidade")
            text = ""
            found = False

            i = 1
            limit = 5
            pagData = []
            for packet in user.options("Correios"):
                with open(f"correios/{packet.upper()}.json", 'r') as file:
                    status = json.load(file)

                if status != []:
                    if "entregue" in status[0]['status']:
                        continue
                    else:
                        if cidade in status[0]['place'] or "saiu para entrega" in status[0]['status']:
                            found = True
                            if user.get("Correios", packet) != "":
                                text += f"📦Encomenda: <b>{user.get('Correios', packet)}</b>\n✉️Código: <b>{packet.upper()}</b>\n"
                            else:
                                text += f"✉️Código: <b>{packet.upper()}</b>\n"
                            
                            text += statusEmoji(status[0],"1", "subtext", chat_id, "notShow")

                            if i - limit == 0:
                                limit += 5

                                pagData.append(text)

                                text = ""
                            i += 1 
                else:
                    continue
            
            if found == False:
                telBot.send_message(chat_id, f"❌ Nenhuma encomenda próxima da entrega!")
                return
            
            if text != "":
                pagData.append(text)
            if len(pagData) > 1:
                pagsTotal = len(pagData)

                markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip3"),telebot.types.InlineKeyboardButton("➡", callback_data="next3"))
                title = f"‼️Encomendas próximas da entrega:\n📄 Pag: 1/{pagsTotal}\n\n"
            else:
                title = "‼️Encomendas próximas da entrega:\n\n"

            telBot.send_message(chat_id, title + pagData[0], reply_markup=markup)

    @telBot.callback_query_handler(func=lambda query: query.data.startswith('next3') or query.data.startswith('previous3') or query.data.startswith('return3') or query.data.startswith('skip3'))
    def callback_handler3(query):
            
            chat_id = query.message.chat.id
            original_message = query.message

            if query.message.chat.type != "private":
                return
            
            markup = telebot.types.InlineKeyboardMarkup()

            match = re.search(r'Pag: (\d+)/(\d+)', original_message.text)

            pagAtual = int(match.group(1)) - 1
            pagTotal = len(pagData) - 1

            nextPag = pagAtual + 1

            previousPag = pagAtual - 1

            if query.data == "next3":

                if nextPag == pagTotal:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous3"), telebot.types.InlineKeyboardButton("⏪", callback_data="return3"))
                else:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous3"), telebot.types.InlineKeyboardButton("⏪", callback_data="return3"),telebot.types.InlineKeyboardButton("⏩", callback_data="skip3"),telebot.types.InlineKeyboardButton("➡", callback_data="next3"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"‼️Encomendas próximas da entrega:\n📄 Pag: {nextPag + 1}/{pagTotal + 1}\n\n" + pagData[nextPag], reply_markup=markup)
            elif query.data == "previous3":

                if previousPag == 0 :
                    markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip3"),telebot.types.InlineKeyboardButton("➡", callback_data="next3"))
                else:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous3"), telebot.types.InlineKeyboardButton("⏪", callback_data="return3"),telebot.types.InlineKeyboardButton("⏩", callback_data="skip3"),telebot.types.InlineKeyboardButton("➡", callback_data="next3"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"‼️Encomendas próximas da entrega:\n📄 Pag: {previousPag + 1}/{pagTotal + 1}\n\n" + pagData[previousPag], reply_markup=markup)
                 
            elif query.data == "return3":

                markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip3"),telebot.types.InlineKeyboardButton("➡", callback_data="next3"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"‼️Encomendas próximas da entrega:\n📄 Pag: 1/{pagTotal + 1}\n\n" + pagData[0], reply_markup=markup)
            elif query.data == "skip3":

                markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous3"), telebot.types.InlineKeyboardButton("⏪", callback_data="return3"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"‼️Encomendas próximas da entrega:\n📄 Pag: {pagTotal + 1}/{pagTotal + 1}\n\n" + pagData[pagTotal], reply_markup=markup)
    

@telBot.message_handler(commands=['feedback'])
def feedback(message):

    if message.chat.type != "private":
        return
    
    user_id = str(message.chat.id)
    username = f"@{message.from_user.username}"


    if username == "@None":
        usernameText = ""
    else:
        usernameText = f"Username: {username}\n"

    message = message.text.replace("/feedback", "").strip()

    if message == "":
        telBot.send_message(user_id, "💌 Sua opnião é muito importante pois nós ajuda a manter o bot em funcionamento e com constantes melhorias, caso se depare com algum problema ou tenha alguma sugestão envie seu feedback com /feedback.\n\n<b>Exemplo: /feedback *mensagem*</b>\n\n<b>(❕Observação: A mensagem é limitada a 120 caracteres e só é possivel enviar feedback 1 vez por semana para evitar spam, por isso seja breve e conciso no que deseja dizer, retornaremos seu feedback caso necessitemos de mais informações.)</b>")
        return
    elif len(message) > 120:
        telBot.send_message(user_id, "😥 Mensagem além do limite de caracteres, tente resumir um pouco mais!")
        return
    
    user = load_user(user_id)

    for feedback_id in user.options("Feedback_IDs"):
        if f"{feedback_id}.txt" in os.listdir("feedback"):
            dias = (datetime.datetime.now() - get_creation_date(f"feedback/{feedback_id}.txt")).days
            restante = 7 - dias

            diasText = "dias"
            if restante <= 1:
                diasText = "dia"            

            if (datetime.datetime.now() - get_creation_date(f"feedback/{feedback_id}.txt")).days < 7:
                telBot.send_message(user_id, f"😥 Você já enviou um feedback recentemente, aguarde {restante} {diasText} para enviar outro!")
                return
            
    while True:
        id = ''.join(random.choices('0123456789', k=7))

        if os.path.exists(f"feedback/{id}.txt"):
            id = ''.join(random.choices('0123456789', k=7))
        else:
            break

    with open(f"feedback/{id}.txt", "w") as file:
        file.write(f"Feedback_ID: {id}\nID_Usuario: {user_id}\n{usernameText}Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\nMensagem: {message}")

    user.set("Feedback_IDs", id, f"Feedback {id}")
    user.write(open(f"users/{user_id}.ini", "w"))

    telBot.send_message(user_id, f"📨 Feedback enviado com sucesso! <b>(Feedback ID: {id})</b>\n\n<b>Retornaremos seu feedback caso necessitemos de mais informações ❣</b>")
    time.sleep(5)
    telBot.send_message(ADMIN_ID, f"📨 Novo feedback recebido!\n\nFeedback_ID: {id}\nID_Usuario: {user_id}\n{usernameText}Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n<b>Mensagem: {message}</b>")

@telBot.message_handler(commands=['feedback_comandos','feedback_lista','feedback_ler','feedback_responder','feedback_deletar'])
def feedback_comandos(message):

    user_id = str(message.chat.id)

    if user_id != ADMIN_ID:
        return
    
    mensagem = re.compile(r'Mensagem: (.+)')
    id_usuario = re.compile(r'ID_Usuario: (\d+)')

    if message.text.startswith("/feedback_comandos"):
        telBot.send_message(user_id, "✉ Comandos Disponiveis de Feedback:\n\n/feedback_lista - Lista todos os feedbacks recebidos.\n/feedback_ler *feedback_id* - Leia um feedback\n/feedback_responder *feedback_id* *mensagem* - Responda um feedback pelo ID.")
    elif message.text.startswith("/feedback_lista"):
        feedback_lista = "✉ Feedback Recebidos:\n\n"
        
        found = False
        
        for feedback in os.listdir("feedback"):
            with open(f"feedback/{feedback}", "r") as file:
                feedbackFile = file.read()

            found = True
            
            id = feedback.replace('.txt','')
            messageText = mensagem.search(feedbackFile).group(1)

            feedback_lista += f"📨 Feedback ID: {id}\n{feedbackFile.replace(f'Feedback_ID: {id}', '').replace(f'Mensagem: {messageText}', '').strip()}\n<b>Mensagem: {messageText[:32]}</b>\n\n"

        if found == True:
            telBot.send_message(user_id, feedback_lista)
        else:
            telBot.send_message(user_id, "❌ Nenhum feedback recebido!")
            
    elif message.text.startswith("/feedback_ler"):
        if message.text.replace("/feedback_ler", "").strip() == "":
            telBot.send_message(user_id, "❌ Digite o ID do feedback após o comando!\n<b>Exemplo: /feedback_ler *id*</b>")
            return

        id = message.text.replace("/feedback_ler", "").strip().upper()
        if len(id) != 7:
            telBot.send_message(user_id, "❌ ID de feedback inválido!")
            return

        if f"{id}.txt" not in os.listdir("feedback"):
            telBot.send_message(user_id, "❌ ID de feedback não encontrado!")
            return
        
        with open(f"feedback/{id}.txt", "r") as file:
            feedback = file.read()

        messageText = mensagem.search(feedback).group(1)

        telBot.send_message(user_id, f"📨 Feedback {id}\n\n{feedback.replace(f'Feedback_ID: {id}', '').replace(f'Mensagem: {messageText}', '').strip()}\n<b>Mensagem: {messageText}</b>")

    elif message.text.startswith("/feedback_responder"):
        if message.text.replace("/feedback_responder", "").strip() == "":
            telBot.send_message(user_id, "❌ Digite o ID do feedback após o comando!\n<b>Exemplo: /feedback_responder *id* *mensagem*</b>")
            return

        if len(message.text.split()) >= 3:
            id = message.text.split()[1].strip().upper()

            if len(id) != 7:
                telBot.send_message(user_id, "❌ ID de feedback inválido!")
                return
            
            if f"{id}.txt" not in os.listdir("feedback"):
                telBot.send_message(user_id, "❌ ID de feedback não encontrado!")
                return        
                
            resposta = " ".join(message.text.split()[2:]).strip()
        else:
            telBot.send_message(user_id, "❌ Digite a resposta do feedback após o ID e o comando!\n<b>Exemplo: /responder *id* *mensagem*</b>")
            return

        with open(f"feedback/{id}.txt", "r") as file:
            feedback = file.read()

        usuario_id = id_usuario.search(feedback).group(1)
        usuario_file = load_user(usuario_id)

        error = False
        placeholder = telBot.send_message(user_id, f"📨 Enviando resposta...")

        time.sleep(5)
        try:
            telBot.send_message(usuario_id, f"💌 Resposta do Desenvolvedor! <b>(Feedback ID: {id})</b>\n\n<b>{resposta}</b>")
        except Exception as e:
            error = e
        time.sleep(5)

        telBot.delete_message(user_id, placeholder.message_id)
        if error == False:
            usuario_file.remove_option("Feedback_IDs", id)
            usuario_file.write(open(f"users/{usuario_id}.ini", "w"))

            os.remove(f"feedback/{id}.txt")

            telBot.send_message(user_id, f"✅ Resposta enviada com sucesso!")
        else:
            telBot.send_message(user_id, f"❌ Não é possivel enviar a resposta!\n\nError: {error}")
    elif message.text.startswith("/feedback_deletar"):
        if message.text.replace("/feedback_deletar", "").strip() == "":
            telBot.send_message(user_id, "❌ Digite o ID do feedback após o comando!\n<b>Exemplo: /feedback_deletar *id*</b>")
            return

        id = message.text.replace("/feedback_deletar", "").strip().upper()
        if len(id) != 7:
            telBot.send_message(user_id, "❌ ID de feedback inválido!")
            return

        if f"{id}.txt" not in os.listdir("feedback"):
            telBot.send_message(user_id, "❌ ID de feedback não encontrado!")
            return

        with open(f"feedback/{id}.txt", "r") as file:
            feedback = file.read() 

        usuario_id = id_usuario.search(feedback).group(1)
        usuario = load_user(usuario_id)    

        usuario.remove_option("Feedback_IDs", id)
        usuario.write(open(f"users/{usuario_id}.ini", "w"))

        os.remove(f"feedback/{id}.txt")

        telBot.send_message(user_id, f"✅ Feedback {id} deletado com sucesso!")         

@telBot.message_handler(commands=['encomendas'])
def encomendas(message):

    if message.chat.type != "private":
        return
    
    user_id = str(message.chat.id)
    markup = telebot.types.InlineKeyboardMarkup()

    users = load_user(user_id)

    if len(users["Correios"].items()) == 0:
        telBot.send_message(user_id, f"<b>❌ Nenhuma encomenda cadastrada!</b>\n\nCadastre com: /correios QA000000000BR *nome da encomenda*")
    else:
        
        i = 1
        limit = 7

        markupData = []
        pagData = []
        for key, value in users["Correios"].items():
            if value == "":
                value = key.upper()
            markupData.append([telebot.types.InlineKeyboardButton(value, callback_data=f"view{key.upper()}"), telebot.types.InlineKeyboardButton("❌", callback_data=f"del{key.upper()}")])
            
            if i - limit == 0:
                limit += 7

                pagData.append(markupData)

                markupData = []
            i += 1     
            
        if markupData != []:
            pagData.append(markupData)

        for button in pagData[0]:
            markup.row(button[0], button[1])

        if len(pagData) > 1:
            pagsTotal = len(pagData)

            markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip1"),telebot.types.InlineKeyboardButton("➡", callback_data="next1"))

            title = f"📦📦Encomendas:\n📄 Pag: 1/{pagsTotal}\n\n"
        else:
            title = "📦📦Encomendas:\n\n"                    

        telBot.send_message(user_id, title,reply_markup=markup)
        
    @telBot.callback_query_handler(func=lambda query: query.data.startswith('view') or query.data.startswith('del') or query.data.startswith('next1') or query.data.startswith('previous1') or query.data.startswith('return1') or query.data.startswith('skip1'))
    def callback_handler1(query):
        chat_id = query.message.chat.id
        original_message = query.message

        if query.message.chat.type != "private":
            return
        
        markup = telebot.types.InlineKeyboardMarkup()        
    
        if query.data.startswith("del"):
            
            packet = query.data.replace("del","")

            user = load_user(chat_id)
            user.remove_option("Correios", packet)
            user.write(open(f"users/{chat_id}.ini", "w"))
            
            telBot.answer_callback_query(query.id, text="✅ Encomenda removida com sucesso!")
            
            found = False

            for users in os.listdir("users"):
                otherUser = load_user(users.replace('.ini', ''))
                if otherUser.has_option("Correios", packet):
                    found = True

            if found == False and os.path.exists(f"correios/{packet}.json"):
                os.remove(f"correios/{packet}.json")

            if len(user["Correios"].items()) == 0:
                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"<b>❌ Nenhuma encomenda cadastrada!</b>\n\nCadastre com: /correios QA000000000BR *nome da encomenda*")
            else:
                
                pageNumber = 0
                rowNumber = 0
                found = False

                for page in pagData:

                    if found == False:
                        for button in page:
                            if button[0].callback_data.replace("view", "") == packet and button[1].callback_data.replace("del", "") == packet:
                                found = True
                                break
                            rowNumber += 1

                    if found == True:
                        while True:
                            if rowNumber == len(pagData[pageNumber]) - 1:
                                try:
                                    pagData[pageNumber][rowNumber] = pagData[pageNumber + 1][0]
                                    rowNumber = 0
                                except:
                                    pagData[pageNumber][rowNumber] = None
                                    pagData[pageNumber].remove(None)

                                    if [] in pagData:
                                        pagData.pop()
                                break
                            else:
                                pagData[pageNumber][rowNumber] = pagData[pageNumber][rowNumber + 1]

                                rowNumber += 1                          
                    pageNumber += 1
                    rowNumber = 0


                if len(pagData) > 1:
                    match = re.search(r'Pag: (\d+)/(\d+)', original_message.text)

                    pagAtual = int(match.group(1)) - 1
                    pagsTotal = len(pagData) - 1

                    try:
                        for button in pagData[pagAtual]:
                            markup.row(button[0], button[1])
                    except:
                        for button in pagData[pagAtual-1]:
                            markup.row(button[0], button[1])

                        pagAtual = pagAtual - 1

                    if pagAtual == 0:
                        markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip1"),telebot.types.InlineKeyboardButton("➡", callback_data="next1"))
                    elif pagAtual == pagsTotal:
                        markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous1"), telebot.types.InlineKeyboardButton("⏪", callback_data="return1"))
                    else:
                        markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous1"), telebot.types.InlineKeyboardButton("⏪", callback_data="return1"),telebot.types.InlineKeyboardButton("⏩", callback_data="skip1"),telebot.types.InlineKeyboardButton("➡", callback_data="next1"))

                    title = f"📦📦Encomendas:\n📄 Pag: {pagAtual + 1}/{pagsTotal + 1}\n\n"
                else:
                    for button in pagData[0]:
                        markup.row(button[0], button[1])
                    title = "📦📦Encomendas:\n\n"                  
  
                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=title, reply_markup=markup)
            return
        elif query.data.startswith("view"):
            correios(f"{query.data.replace('view','')}:{chat_id}")
            return 

        match = re.search(r'Pag: (\d+)/(\d+)', original_message.text)

        pagAtual = int(match.group(1)) - 1
        pagTotal = len(pagData) - 1

        nextPag = pagAtual + 1

        previousPag = pagAtual - 1     

        if query.data == "next1":

            for button in pagData[nextPag]:
                markup.row(button[0], button[1])

            if nextPag == pagTotal:
                markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous1"), telebot.types.InlineKeyboardButton("⏪", callback_data="return1"))
            else:
                markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous1"), telebot.types.InlineKeyboardButton("⏪", callback_data="return1"),telebot.types.InlineKeyboardButton("⏩", callback_data="skip1"),telebot.types.InlineKeyboardButton("➡", callback_data="next1"))

            telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Encomendas:\n📄 Pag: {nextPag + 1}/{pagTotal + 1}", reply_markup=markup)
        elif query.data == "previous1":

            for button in pagData[previousPag]:
                markup.row(button[0], button[1])

            if previousPag == 0 :
                markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip1"),telebot.types.InlineKeyboardButton("➡", callback_data="next1"))
            else:
                markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous1"), telebot.types.InlineKeyboardButton("⏪", callback_data="return1"),telebot.types.InlineKeyboardButton("⏩", callback_data="skip1"),telebot.types.InlineKeyboardButton("➡", callback_data="next1"))

            telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Encomendas:\n📄 Pag: {previousPag + 1}/{pagTotal + 1}", reply_markup=markup)
                
        elif query.data == "return1":

            for button in pagData[0]:
                markup.row(button[0], button[1])            

            markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip1"),telebot.types.InlineKeyboardButton("➡", callback_data="next1"))

            telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Encomendas:\n📄 Pag: 1/{pagTotal + 1}", reply_markup=markup)
        elif query.data == "skip1":

            for button in pagData[pagTotal]:
                markup.row(button[0], button[1])            

            markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous1"), telebot.types.InlineKeyboardButton("⏪", callback_data="return1"))

            telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Encomendas:\n📄 Pag: {pagTotal + 1}/{pagTotal + 1}", reply_markup=markup)
         

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
            
            users = load_user(chat_id)
            for packet in users.options("Correios"):
                if users.get("Correios", packet) == name:
                    telBot.send_message(chat_id, "❌ Já existe uma encomenda com este nome!")
                    return
        else:
            name = ""
    else:
        cod = message.split(":")[0].strip().upper()
        chat_id = message.split(":")[1].strip()
        name = ""

    markup = telebot.types.InlineKeyboardMarkup()

    if f"{chat_id}.ini" not in os.listdir('users'):
        with open(f"users/{chat_id}.ini", 'w') as file:
            file.write("[Correios]")

    if len(cod) == 13 and cod[:2].isalpha() and cod[-2:].isalpha():
        found = False

        for encomenda in os.listdir('correios'):
            if cod in encomenda:

                with open(f'correios/{cod}.json', 'r') as file:
                    status = json.load(file)

                subtext = ""
                save = True

                if status == []:
                    subtext += "🛑 Aguardando Postagem!"
                else:
                    if len(status) > 5:
                        markup.add(telebot.types.InlineKeyboardButton("➕ Ver mais", callback_data=f"all{cod}"))       

                    if "entregue" in status[0]['status']:
                        show = "notShow"
                        save = False
                    else:
                        show = "show"

                    subtext += statusEmoji(status,"+", "subtext", chat_id, show)

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
                    text = f"📦Encomenda: <b>{name}</b>\n✉️Código: <b>{cod}</b>\n\n"
                else:
                    text = f"✉️Código: <b>{cod}</b>\n\n"
        
                telBot.send_message(chat_id, text + subtext, reply_markup=markup)

                found = True
                break

        if found == False:

            msg = telBot.send_message(chat_id, "🔍 Consultando...")

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
                        if len(status) > 5:
                            markup.add(telebot.types.InlineKeyboardButton("➕ Ver mais", callback_data=f"all{cod}"))

                        if "entregue" in status[0]['status']:
                            show = "notShow"
                            save = False
                        else:
                            show = "show"

                        subtext += statusEmoji(status,"+", "subtext", chat_id, show)

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
                        text = f"📦Encomenda: <b>{name}</b>\n✉️Código: <b>{cod}</b>\n\n"
                    else:
                        text = f"✉️Código: <b>{cod}</b>\n\n"


                    telBot.delete_message(chat_id, msg.message_id)
                    telBot.send_message(chat_id, text + subtext, reply_markup=markup)
                    break

                if tries >= 3:
                    telBot.delete_message(chat_id, msg.message_id)
                    telBot.send_message(chat_id, "❌ Falha ao consultar o código de rastreio!")
                    break

    else:
        telBot.send_message(chat_id, "❌ Código de rastreio inválido!\n<b>Exemplo: /correios QA000000000BR *nome da encomenda*</b>")

    @telBot.callback_query_handler(func=lambda query: query.data.startswith('all') or query.data.startswith('less'))
    def callback_handler4(query):
            
        chat_id = query.message.chat.id
        original_message = query.message

        if query.message.chat.type != "private":
            return
        
        markup = telebot.types.InlineKeyboardMarkup()

        cod = query.data.replace("all","").replace("less","")
        subtext = ""

        if query.data.startswith("all"):

            qnt = "++"

            markup.add(telebot.types.InlineKeyboardButton("➖ Ver Menos", callback_data=f"less{cod}"))
        elif query.data.startswith("less"):

            qnt = "+"

            markup.add(telebot.types.InlineKeyboardButton("➕ Ver mais", callback_data=f"all{cod}"))

        if name != "":
            text = f"📦Encomenda: <b>{name}</b>\n✉️Código: <b>{cod}</b>\n\n"
        else:
            text = f"✉️Código: <b>{cod}</b>\n\n"

        subtext += statusEmoji(status,qnt, "subtext", chat_id, show)

        telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=text + subtext, reply_markup=markup)

        
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
                        resumoText += f"📦Encomenda: <b>{user['Correios'][packet]}</b>\n✉️Código: <b>{packet.upper()}</b>\n"
                    else:
                        resumoText += f"✉️Código: <b>{packet.upper()}</b>\n"
                        
                    if status == []:
                        resumoText += f"Status: 🛑 Aguardando Postagem!\n\n"
                    else:
                        lastStatus = status[0]

                        resumoText += statusEmoji(lastStatus,"1", "subtext", user_id, "show")
                        
                    if i - limit == 0:
                        limit += 5

                        pagData.append(resumoText)

                        resumoText = ""
                    i += 1 


                if resumoText != "":
                    pagData.append(resumoText)

                if len(pagData) > 1:
                    pagsTotal = len(pagData)

                    markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip2"),telebot.types.InlineKeyboardButton("➡", callback_data="next2"))
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

    @telBot.callback_query_handler(func=lambda query: query.data.startswith('next2') or query.data.startswith('previous2') or query.data.startswith('return2') or query.data.startswith('skip2'))
    def callback_handler2(query):
            
            chat_id = query.message.chat.id
            original_message = query.message

            if query.message.chat.type != "private":
                return
            
            markup = telebot.types.InlineKeyboardMarkup()

            match = re.search(r'Pag: (\d+)/(\d+)', original_message.text)

            pagAtual = int(match.group(1)) - 1
            pagTotal = len(pagData) - 1

            nextPag = pagAtual + 1

            previousPag = pagAtual - 1

            if query.data == "next2":

                if nextPag == pagTotal:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous2"), telebot.types.InlineKeyboardButton("⏪", callback_data="return2"))
                else:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous2"), telebot.types.InlineKeyboardButton("⏪", callback_data="return2"),telebot.types.InlineKeyboardButton("⏩", callback_data="skip2"),telebot.types.InlineKeyboardButton("➡", callback_data="next2"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Resumo:\n📄 Pag: {nextPag + 1}/{pagTotal + 1}\n\n" + pagData[nextPag], reply_markup=markup)
            elif query.data == "previous2":

                if previousPag == 0 :
                    markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip2"),telebot.types.InlineKeyboardButton("➡", callback_data="next2"))
                else:
                    markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous2"), telebot.types.InlineKeyboardButton("⏪", callback_data="return2"),telebot.types.InlineKeyboardButton("⏩", callback_data="skip2"),telebot.types.InlineKeyboardButton("➡", callback_data="next2"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Resumo:\n📄 Pag: {previousPag + 1}/{pagTotal + 1}\n\n" + pagData[previousPag], reply_markup=markup)
                 
            elif query.data == "return2":

                markup.row(telebot.types.InlineKeyboardButton("⏩", callback_data="skip2"),telebot.types.InlineKeyboardButton("➡", callback_data="next2"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Resumo:\n📄 Pag: 1/{pagTotal + 1}\n\n" + pagData[0], reply_markup=markup)
            
            elif query.data == "skip2":

                markup.row(telebot.types.InlineKeyboardButton("⬅", callback_data="previous2"), telebot.types.InlineKeyboardButton("⏪", callback_data="return2"))

                telBot.edit_message_text(chat_id=chat_id, message_id=original_message.message_id, text=f"📦📦Resumo:\n📄 Pag: {pagTotal + 1}/{pagTotal + 1}\n\n" + pagData[pagTotal], reply_markup=markup)
        

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
                                    text = f"📦Encomenda: <b>{name}</b>\n✉️Código: <b>{packetCod}</b>"
                                else:
                                    text = f"✉️Código: <b>{packetCod}</b>"

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
                                    text = f"📦Encomenda: <b>{name}</b>\n✉️Código: <b>{packetCod}</b>\n\n<b>🔄 Encomenda Atualizada!</b>\n\n"
                                else:
                                    text = f"✉️Código: <b>{packetCod}</b>\n\n<b>🔄 Encomenda Atualizada!</b>\n\n"

                                text += statusEmoji(packetLastStatus,"1", "text", user.replace('.ini', ''), "show")

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