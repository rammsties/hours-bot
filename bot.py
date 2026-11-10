import telebot
import sqlite3

# ⚠️ ВСТАВЬ СЮДА СВОИ ДАННЫЕ:
ADMIN_ID = 515800903  # Твой числовой ID
BOT_TOKEN = '9293817596:AAH6TswkBCtXJh3QaLtduT3KbCuLHMSEgIc'  # Токен от BotFather

bot = telebot.TeleBot(BOT_TOKEN)
DB_NAME = 'college.db'

# Создаем базу данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            total_lectures INTEGER DEFAULT 0,
            total_prac1 INTEGER DEFAULT 0,
            total_prac2 INTEGER DEFAULT 0,
            spent_lectures INTEGER DEFAULT 0,
            spent_prac1 INTEGER DEFAULT 0,
            spent_prac2 INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    return user_id == ADMIN_ID

# /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = (
        "👋 Привет! Это бот для учёта часов по предметам.\n\n"
        "📊 Остаток часов: /status\n\n"
        "   Команды старосты:\n"
        "• /init Название лекций практ1 практ2\n"
        "• /add Название тип количество\n"
        "  (тип: л — лекция, п1 — практика 1 подгр., п2 — практика 2 подгр.)\n"
        "• /del Название — удалить предмет"
    )
    bot.reply_to(message, text)

# /status — красивая табличка
@bot.message_handler(commands=['status'])
def show_status(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, total_lectures, total_prac1, total_prac2, spent_lectures, spent_prac1, spent_prac2 FROM subjects')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.reply_to(message, "📭 Пока ни один предмет не добавлен.")
        return

    response = "📚 *Остаток часов:*\n\n"
    for row in rows:
        name, t_l, t_p1, t_p2, s_l, s_p1, s_p2 = row
        r_l = t_l - s_l
        r_p1 = t_p1 - s_p1
        r_p2 = t_p2 - s_p2
        
        # Общий прогресс
        total = t_l + t_p1 + t_p2
        done = s_l + s_p1 + s_p2
        percent = int((done / total) * 100) if total > 0 else 0
        filled = percent // 10
        bar = "🟩" * filled + "⬜" * (10 - filled)
        
        response += f"📌 *{name}* — {bar} {percent}%\n"
        response += f"   📖 Лекции: {s_l}/{t_l} (ост. {r_l})\n"
        response += f"   🔬 Практика (подгр. 1): {s_p1}/{t_p1} (ост. {r_p1})\n"
        response += f"   🔬 Практика (подгр. 2): {s_p2}/{t_p2} (ост. {r_p2})\n\n"

    bot.reply_to(message, response, parse_mode='Markdown')

# /init — добавить предмет
# Пример: /init Математика 14 10 10
@bot.message_handler(commands=['init'])
def init_subject(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Эта команда только для старосты!")
        return
    
    try:
        parts = message.text.split()
        name = parts[1]
        t_l = int(parts[2])
        t_p1 = int(parts[3])
        t_p2 = int(parts[4])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO subjects (name, total_lectures, total_prac1, total_prac2) 
            VALUES (?, ?, ?, ?)
        ''', (name, t_l, t_p1, t_p2))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, 
            f"✅ Предмет *{name}* добавлен!\n"
            f"Лекций: {t_l} | Практик (подгр. 1): {t_p1} | Практик (подгр. 2): {t_p2}", 
            parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, 
            "❌ Ошибка. Формат: /init Название лекций практ1 практ2\n"
            "Пример: /init Физика 10 8 8")

# /add — провести пару
# Примеры: /add Математика л 2  (или п1 1, или п2 1)
@bot.message_handler(commands=['add'])
def add_hours(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Эта команда только для старосты!")
        return
    
    try:
        parts = message.text.split()
        name = parts[1]
        type_pair = parts[2].lower()
        amount = int(parts[3])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT spent_lectures, spent_prac1, spent_prac2 FROM subjects WHERE name=?', (name,))
        row = cursor.fetchone()
        if not row:
            bot.reply_to(message, f"❌ Предмет *{name}* не найден. Сначала добавь через /init", parse_mode='Markdown')
            return
            
        s_l, s_p1, s_p2 = row
        
        if type_pair in ['л', 'лекция', 'лекции']:
            cursor.execute('UPDATE subjects SET spent_lectures = ? WHERE name=?', (s_l + amount, name))
            pair_type = "лекций"
        elif type_pair in ['п1', 'практика1', 'практики1', '1п']:
            cursor.execute('UPDATE subjects SET spent_prac1 = ? WHERE name=?', (s_p1 + amount, name))
            pair_type = "практик для подгруппы 1"
        elif type_pair in ['п2', 'практика2', 'практики2', '2п']:
            cursor.execute('UPDATE subjects SET spent_prac2 = ? WHERE name=?', (s_p2 + amount, name))
            pair_type = "практик для подгруппы 2"
        else:
            bot.reply_to(message, "❌ Тип пары: л (лекция), п1 (практика 1 подгр.), п2 (практика 2 подгр.)")
            return
            
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Добавлено {amount} {pair_type} по предмету *{name}*", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, "❌ Ошибка. Формат: /add Название тип количество\nПример: /add Математика п1 1")

# /del — удалить предмет
@bot.message_handler(commands=['del'])
def del_subject(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Эта команда только для старосты!")
        return
    
    try:
        name = message.text.split()[1]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subjects WHERE name=?', (name,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🗑 Предмет *{name}* удалён", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Формат: /del Название")

print("Бот запущен! Жду команд2...")
bot.polling(none_stop=True)
