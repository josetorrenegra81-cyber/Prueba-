# bot.py - Bot Telegram completo: knowledge base + evaluaciones cada 6 días + estado (versión WEBHOOK para PythonAnywhere)
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import sqlite3
import datetime
import json
import os
import traceback
from flask import Flask, request

TOKEN = "8202817343:AAHys04UEPVJEJ1f_Os04v8v3_hwG8iNqcU"
DB_FILE = "bot_db.sqlite"

# ---------------------------
# Inicializar DB
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # users
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        nombre TEXT,
        username TEXT,
        idioma TEXT DEFAULT 'es',
        fecha_registro TEXT DEFAULT (datetime('now'))
    )"""
    )
    # user_activity
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mensaje TEXT,
        respuesta_bot TEXT,
        fecha TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )"""
    )
    # evaluations (historial de tests)
    c.execute(
        """CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        fecha TEXT,
        correct INTEGER,
        total INTEGER,
        porcentaje INTEGER,
        detalle TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )"""
    )
    # analytics: respuestas provisionales de tests (test_answer)
    c.execute(
        """CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        evento TEXT,
        valor TEXT,
        fecha TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )"""
    )
    # system_logs
    c.execute(
        """CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        mensaje TEXT,
        fecha TEXT DEFAULT (datetime('now'))
    )"""
    )
    conn.commit()
    conn.close()


# ---------------------------
# Base de conocimiento
# ---------------------------
info_empresa = {
    "que_hace": "La empresa se dedica a proveer soluciones logísticas integrales, transporte y distribución.",
    "productos": "Servicios de transporte, almacenamiento, gestión aduanera y distribución.",
    "servicios": "Transporte nacional, almacenamiento, cross-docking, gestión aduanera.",
    "mision": "Brindar servicios logísticos eficientes y confiables que impulsen el éxito de nuestros clientes.",
    "vision": "Ser la empresa líder regional en soluciones logísticas para 2030.",
    "valores": "Responsabilidad, compromiso, integridad, calidad y trabajo en equipo.",
    "procesos": "Atención al cliente → Recepción → Almacenaje → Picking → Despacho → Entrega."
}

# ---------------------------
# Preguntas del test
# ---------------------------
preguntas_test = [
    {
        "p": "¿A qué se dedica la empresa?",
        "op": ["Soluciones logísticas integrales", "Fabricación de alimentos", "Servicios financieros"],
        "ans": 0,
    },
    {
        "p": "¿Cuál es uno de nuestros servicios principales?",
        "op": ["Transporte nacional", "Consultoría legal", "Diseño gráfico"],
        "ans": 0,
    },
    {
        "p": "¿Cuál es uno de nuestros valores?",
        "op": ["Impunidad", "Responsabilidad", "Anarquía"],
        "ans": 1,
    },
]

# ---------------------------
# Helpers DB
# ---------------------------
def db_conn():
    return sqlite3.connect(DB_FILE)

def log_system(tipo, mensaje):
    try:
        conn = db_conn()
        c = conn.cursor()
        c.execute("INSERT INTO system_logs (tipo, mensaje) VALUES (?, ?)", (tipo, mensaje))
        conn.commit()
        conn.close()
    except Exception:
        print("Error guardando log")
        print(traceback.format_exc())

def get_or_create_user_by_tg(tg_id, fullname="", username=""):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_id,))
    row = c.fetchone()
    if row:
        user_id = row[0]
    else:
        c.execute(
            "INSERT INTO users (telegram_id, nombre, username) VALUES (?, ?, ?)",
            (tg_id, fullname, username),
        )
        conn.commit()
        user_id = c.lastrowid
    conn.close()
    return user_id

def log_activity(user_id, mensaje, respuesta_bot=""):
    conn = db_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO user_activity (user_id, mensaje, respuesta_bot) VALUES (?, ?, ?)",
        (user_id, mensaje, respuesta_bot),
    )
    conn.commit()
    conn.close()

def save_evaluation(user_id, correct, total, porcentaje, detalle):
    conn = db_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO evaluations (user_id, fecha, correct, total, porcentaje, detalle) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, str(datetime.date.today()), correct, total, porcentaje, json.dumps(detalle)),
    )
    conn.commit()
    conn.close()


# ---------------------------
# Handlers (tu lógica original)
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg = update.message.from_user
        user_id = get_or_create_user_by_tg(tg.id, tg.full_name, tg.username or "")
        log_activity(user_id, "/start", "Bienvenida enviada")
        texto = (
            "¡Hola! Soy el bot de capacitación de la empresa.\n\n"
            "Comandos útiles:\n"
            "/evaluar - Recibir evaluación ahora (manual)\n"
            "/estado - Ver tu porcentaje actual\n"
            "/help - Mostrar ayuda\n\n"
            "También puedes preguntar cosas como: ¿Qué hace la empresa?, ¿Qué productos vendemos?, ¿Cuál es la misión?"
        )
        await update.message.reply_text(texto)
    except Exception as e:
        log_system("error", f"start: {e}")
        await update.message.reply_text("Error en /start. Revisa los logs.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.lower()
        tg = update.message.from_user
        user_id = get_or_create_user_by_tg(tg.id, tg.full_name, tg.username or "")
        respuesta = None

        if "qué hace" in text or "que hace" in text or "a qué se dedica" in text or "dedica" in text:
            respuesta = info_empresa["que_hace"]
        elif "vende" in text or "productos" in text or "comercializ" in text:
            respuesta = info_empresa["productos"]
        elif "servicios" in text or "servicio" in text:
            respuesta = info_empresa["servicios"]
        elif "mision" in text or "misión" in text:
            respuesta = info_empresa["mision"]
        elif "vision" in text or "visión" in text:
            respuesta = info_empresa["vision"]
        elif "valores" in text or "valor" in text:
            respuesta = info_empresa["valores"]
        elif "procesos" in text or "proceso" in text:
            respuesta = info_empresa["procesos"]
        else:
            if text.strip().isdigit():
                await respuestas_handler(update, context)
                return
            respuesta = (
                "No entendí bien. Puedes preguntar:\n"
                "- ¿Qué hace la empresa?\n- ¿Qué productos vendemos?\n- ¿Servicios?\n- ¿Misión?/¿Visión?/¿Valores?/¿Procesos?\n\n"
                "O usa /evaluar para recibir un test."
            )

        log_activity(user_id, update.message.text, respuesta)
        await update.message.reply_text(respuesta)
    except Exception as e:
        log_system("error", f"info_handler: {e}")
        await update.message.reply_text("Error al procesar tu mensaje.")

async def respuestas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg = update.message.from_user
        user_id = get_or_create_user_by_tg(tg.id, tg.full_name, tg.username or "")
        text = update.message.text.strip()
        log_activity(user_id, text, "")

        if text.isdigit():
            conn = db_conn()
            c = conn.cursor()
            c.execute("INSERT INTO analytics (user_id, evento, valor) VALUES (?, ?, ?)", 
                      (user_id, "test_answer", text))
            conn.commit()
            conn.close()
            await update.message.reply_text("Respuesta recibida. Cuando termines, usa /calcular.")
            return

        await info_handler(update, context)
    except Exception as e:
        log_system("error", f"respuestas_handler: {e}")
        await update.message.reply_text("Error al procesar tu respuesta.")

async def calcular_porcentaje_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg = update.message.from_user
        user_id = get_or_create_user_by_tg(tg.id, tg.full_name, tg.username or "")

        conn = db_conn()
        c = conn.cursor()
        total_preg = len(preguntas_test)
        c.execute(
            "SELECT valor FROM analytics WHERE user_id = ? AND evento = ? ORDER BY id ASC LIMIT ?",
            (user_id, "test_answer", total_preg),
        )
        rows = c.fetchall()
        conn.close()

        respuestas = [int(r[0]) for r in rows] if rows else []

        total = len(preguntas_test)
        correct = 0
        detalle = []

        for i, q in enumerate(preguntas_test):
            try:
                resp = respuestas[i] - 1
            except:
                resp = None
            ok = (resp is not None and resp == q["ans"])
            detalle.append({
                "pregunta": q["p"], 
                "resp": resp if resp is not None else "sin responder",
                "correcta": q["ans"], 
                "ok": ok
            })
            if ok:
                correct += 1

        porcentaje = int((correct / total) * 100)

        save_evaluation(user_id, correct, total, porcentaje, detalle)

        conn = db_conn()
        c = conn.cursor()
        c.execute("DELETE FROM analytics WHERE user_id = ? AND evento = ?", 
                  (user_id, "test_answer"))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"📊 Tu porcentaje de conocimiento es: {porcentaje}%\nCorrectas: {correct}/{total}"
        )
    except Exception as e:
        log_system("error", f"calcular_porcentaje_command: {e}")
        await update.message.reply_text("Error al calcular tu porcentaje.")

async def estado_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg = update.message.from_user
        user_id = get_or_create_user_by_tg(tg.id, tg.full_name, tg.username or "")
        conn = db_conn()
        c = conn.cursor()
        c.execute(
            "SELECT fecha, porcentaje, correct, total FROM evaluations WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,))
        row = c.fetchone()
        conn.close()

        if row:
            fecha, porcentaje, correct, total = row
            await update.message.reply_text(
                f"Última evaluación: {fecha}\n📊 Porcentaje: {porcentaje}%\nCorrectas: {correct}/{total}"
            )
        else:
            await update.message.reply_text("Aún no tienes evaluaciones registradas.")
    except Exception as e:
        log_system("error", f"estado_command: {e}")
        await update.message.reply_text("Error al obtener tu estado.")

async def evaluar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ En versión WEBHOOK no se permiten tareas programadas en background desde Telegram.")

async def programar_evaluaciones_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ No disponible en webhook + hosting gratuito.")

# ---------------------------
# Flask + Webhook
# ---------------------------
app_flask = Flask(__name__)

@app_flask.route("/", methods=["POST"])
def receive_update():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    application.process_update(update)
    return "OK", 200

@app_flask.route("/", methods=["GET"])
def index():
    return "Bot de Telegram corriendo con webhook 🚀"


# ---------------------------
# Main Webhook
# ---------------------------
init_db()
application = ApplicationBuilder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("evaluar", evaluar_command))
application.add_handler(CommandHandler("estado", estado_command))
application.add_handler(CommandHandler("calcular", calcular_porcentaje_command))
application.add_handler(CommandHandler("programar", programar_evaluaciones_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, info_handler))


if __name__ == "__main__":
    app_flask.run() 
