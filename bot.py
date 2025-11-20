import telebot
import sqlite3
import datetime

TOKEN = "AQUI_TU_TOKEN"
bot = telebot.TeleBot(TOKEN)

# ---- Función para conectarse a DB ----
def get_db():
    return sqlite3.connect("bot.db")

# ---- Comando /start ----
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "¡Hola! Soy el bot de capacitación de Orange Freight. Usa /preguntar o /evaluar.")

# ---- Comando /preguntar ----
@bot.message_handler(commands=["preguntar"])
def preguntar(message):
    pregunta = message.text.replace("/preguntar", "").strip()

    if pregunta == "":
        bot.reply_to(message, "Escribe la pregunta así:\n/preguntar ¿Qué hace la empresa?")
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT respuesta FROM preguntas WHERE pregunta LIKE ?", ('%' + pregunta + '%',))
    data = cursor.fetchone()
    conn.close()

    if data:
        bot.reply_to(message, data[0])
    else:
        bot.reply_to(message, "No tengo esa respuesta registrada.")

# ---- Comando /evaluar ----
@bot.message_handler(commands=["evaluar"])
def evaluar(message):
    user_id = message.from_user.id

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT pregunta, respuesta FROM preguntas ORDER BY RANDOM() LIMIT 3")
    preguntas = cursor.fetchall()

    if not preguntas:
        bot.reply_to(message, "Error: No hay preguntas en la base de datos.")
        return

    puntaje = 0

    for p, r in preguntas:
        bot.send_message(message.chat.id, f"❓ {p}\n\nEscribe tu respuesta:")

        respuesta_usuario = bot.wait_for_reply(message.chat.id).text.lower()

        if r.lower() in respuesta_usuario:
            puntaje += 1

    cursor.execute(
        "INSERT INTO evaluaciones (user_id, puntaje, fecha) VALUES (?, ?, ?)",
        (user_id, puntaje, datetime.date.today().isoformat())
    )

    conn.commit()
    conn.close()

    porcentaje = int((puntaje / len(preguntas)) * 100)
    bot.reply_to(message, f"📊 Tu nivel actual es: {porcentaje}%")

# ---- Iniciar bot ----
print("Bot corriendo...")
bot.infinity_polling()
