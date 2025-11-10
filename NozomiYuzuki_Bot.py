import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====== CONFIGURACIÓN INICIAL ======
TOKEN = "8240561927:AAGeFMax-rsxC-qV-ODf1kpK2cs31UHOLwk"
DATA_FILE = "tasks_data.json"
DEFAULT_AUTOSAVE_MINUTES = 15

# ====== FUNCIONES DE GUARDADO ======
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"tasks": [], "notes": [], "autosave_interval": DEFAULT_AUTOSAVE_MINUTES}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ====== UTILIDADES ======
def parse_time(time_str):
    try:
        t = time_str.replace("hs", "").strip()
        h, m = map(int, t.split(":"))
        now = datetime.now()
        return now.replace(hour=h, minute=m, second=0, microsecond=0)
    except Exception:
        return None

def parse_duration(duration_str):
    duration_str = duration_str.lower().strip()
    if "hs" in duration_str:
        return timedelta(hours=int(duration_str.replace("hs", "")))
    elif "min" in duration_str:
        return timedelta(minutes=int(duration_str.replace("min", "")))
    elif "s" in duration_str:
        return timedelta(seconds=int(duration_str.replace("s", "")))
    return timedelta(minutes=30)

# ====== COMANDOS ======
async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = " ".join(context.args)
    try:
        *name_parts, time_str, duration_str = text.split()
        name = " ".join(name_parts)
        start_time = parse_time(time_str)
        duration = parse_duration(duration_str)

        if not start_time:
            await update.message.reply_text("⚠️ Formato incorrecto. Usa: /addtask Desayunar 09:30hs 30min")
            return

        task = {
            "name": name,
            "time": start_time.strftime("%H:%M"),
            "duration": duration_str,
            "status": "pending"
        }
        data["tasks"].append(task)
        save_data(data)

        await update.message.reply_text(f"✅ Tarea añadida: *{name}* a las *{start_time.strftime('%H:%M')}* ({duration_str})", parse_mode="Markdown")
        context.application.create_task(check_task(update, task))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error al añadir tarea. Usa:\n/addtask Nombre 09:30hs 30min\n\n{e}")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["tasks"]:
        await update.message.reply_text("🗒️ No hay tareas todavía.")
        return
    msg = "🧾 *Lista de tareas:*\n\n"
    for i, t in enumerate(data["tasks"], 1):
        icon = "⏳" if t["status"] == "pending" else "✔️" if t["status"] == "success" else "❌"
        msg += f"{i}. {t['name']} {icon} ({t['time']})\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    try:
        idx = int(context.args[0]) - 1
        data["tasks"][idx]["status"] = "success"
        save_data(data)
        await update.message.reply_text(f"✔️ Tarea completada: {data['tasks'][idx]['name']}")
    except:
        await update.message.reply_text("⚠️ Usa: /done <número>")

async def missed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    try:
        idx = int(context.args[0]) - 1
        data["tasks"][idx]["status"] = "failed"
        save_data(data)
        await update.message.reply_text(f"❌ Tarea marcada como fallida: {data['tasks'][idx]['name']}")
    except:
        await update.message.reply_text("⚠️ Usa: /missed <número>")

async def delettask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    try:
        idx = int(context.args[0]) - 1
        removed = data["tasks"].pop(idx)
        save_data(data)
        await update.message.reply_text(f"🗑️ Tarea eliminada: {removed['name']}")
    except:
        await update.message.reply_text("⚠️ Usa: /delettask <número>")

async def note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = " ".join(context.args)
    try:
        message, time_str = text.split(" - ")
        note_time = parse_time(time_str)

        note_item = {"message": message.strip(), "time": note_time.strftime("%H:%M")}
        data["notes"].append(note_item)
        save_data(data)

        await update.message.reply_text(f"📝 Nota añadida: '{message.strip()}' para las {note_time.strftime('%H:%M')}")
        context.application.create_task(check_note(update, note_item))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Formato incorrecto. Usa:\n/note mensaje - 03:00hs\n\n{e}")

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["notes"]:
        await update.message.reply_text("🗒️ No hay notas todavía.")
        return
    msg = "🧾 *Notas de recordatorio:*\n\n"
    for i, n in enumerate(data["notes"], 1):
        msg += f"{i}. {n['message']} ⏰ ({n['time']})\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def deletnote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    try:
        idx = int(context.args[0]) - 1
        removed = data["notes"].pop(idx)
        save_data(data)
        await update.message.reply_text(f"🗑️ Nota eliminada: {removed['message']}")
    except:
        await update.message.reply_text("⚠️ Usa: /deletnote <número>")

async def save_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    save_data(data)
    await update.message.reply_text("💾 Datos guardados manualmente.")

async def confing_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not context.args:
        data["autosave_interval"] = DEFAULT_AUTOSAVE_MINUTES
        save_data(data)
        await update.message.reply_text(f"🔁 Intervalo de autoguardado restaurado a {DEFAULT_AUTOSAVE_MINUTES} minutos.")
        return

    try:
        arg = context.args[0].lower().strip()
        if "hs" in arg:
            minutes = int(arg.replace("hs", "")) * 60
        elif "min" in arg:
            minutes = int(arg.replace("min", ""))
        elif "s" in arg:
            minutes = max(1, int(arg.replace("s", "")) // 60)
        else:
            minutes = int(arg)

        data["autosave_interval"] = minutes
        save_data(data)
        await update.message.reply_text(f"⚙️ Intervalo de autoguardado actualizado a {minutes} minutos.")
    except Exception:
        await update.message.reply_text("⚠️ Formato incorrecto. Usa por ejemplo: /confingSave 27min")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
📋 *Menú de comandos:*

/addtask <nombre> <hora> <duración> → Añadir tarea  
/list → Ver todas las tareas  
/done <número> → Marcar tarea completada  
/missed <número> → Marcar tarea fallida  
/delettask <número> → Eliminar tarea  
/note <mensaje> - <hora> → Añadir nota recordatorio  
/listnote → Ver notas  
/deletnote <número> → Eliminar nota  
/save → Guardado manual  
/confingSave [tiempo] → Configurar autoguardado (ej: 27min)  
/menu → Mostrar este menú
"""
    await update.message.reply_text(msg, parse_mode="Markdown")

# ====== CONTROL DE TIEMPO ======
async def check_task(update, task):
    await asyncio.sleep(1)
    start_time = parse_time(task["time"] + "hs")
    duration = parse_duration(task["duration"])
    end_time = start_time + duration
    now = datetime.now()

    if now < end_time:
        await asyncio.sleep((end_time - now).total_seconds())

    data = load_data()
    for t in data["tasks"]:
        if t["name"] == task["name"] and t["status"] == "pending":
            t["status"] = "failed"
            save_data(data)
            for _ in range(3):
                await update.message.reply_text(f"⚠️ La tarea '{t['name']}' no fue completada ❌")
                await asyncio.sleep(30)

async def check_note(update, note_item):
    note_time = parse_time(note_item["time"] + "hs")
    delay = (note_time - datetime.now()).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    await update.message.reply_text(f"⏰ Recordatorio: {note_item['message']}")

# ====== AUTOGUARDADO ======
async def autosave_loop(app):
    while True:
        data = load_data()
        minutes = data.get("autosave_interval", DEFAULT_AUTOSAVE_MINUTES)
        await asyncio.sleep(minutes * 60)
        save_data(data)
        chat_ids = [c.chat_id for c in app.chat_data.values() if c.get("chat_id")]
        for cid in chat_ids:
            try:
                await app.bot.send_message(cid, f"💾 Datos guardados automáticamente ({datetime.now().strftime('%H:%M')})")
            except:
                pass
        print(f"💾 Autoguardado ({datetime.now().strftime('%H:%M:%S')})")

# ====== MAIN ======
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("addtask", addtask))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("missed", missed))
    app.add_handler(CommandHandler("delettask", delettask))
    app.add_handler(CommandHandler("note", note))
    app.add_handler(CommandHandler("listnote", list_notes))
    app.add_handler(CommandHandler("deletnote", deletnote))
    app.add_handler(CommandHandler("save", save_manual))
    app.add_handler(CommandHandler("confingSave", confing_save))
    app.add_handler(CommandHandler("menu", menu))

    asyncio.create_task(autosave_loop(app))
    print("✅ Bot iniciado. Esperando comandos...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
