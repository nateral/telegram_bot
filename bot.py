import os
import json
import requests
from flask import Flask, request
import time
from functools import wraps

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
TOKEN = "7532259267:AAGdCxqHXA_JcAbfHHCl09wZEoIpxmheQsA"
SITE_URL = "https://breadix-tier.ru"  # Ваш сайт
ADMINS = ['6380018406', '8198380412', '8208522743', '7886275415']
URL = f"https://api.telegram.org/bot{TOKEN}"

# ========== РАБОТА С ФАЙЛАМИ ==========
DATA_FILE = 'data.json'
DESC_FILE = 'descriptions.json'
HISTORY_FILE = 'history.json'
APPS_FILE = 'applications.json'
STATES_DIR = 'states'

# Создаём папку для состояний, если нет
if not os.path.exists(STATES_DIR):
    os.makedirs(STATES_DIR)

def load_json(filename, default=None):
    """Загружает JSON из файла"""
    if default is None:
        default = {} if filename.endswith('.json') else []
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return default

def save_json(filename, data):
    """Сохраняет JSON в файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# ========== РАБОТА С СОСТОЯНИЯМИ ==========
def get_state_file(user_id):
    return os.path.join(STATES_DIR, f'state_{user_id}.json')

def set_state(user_id, key, value):
    state_file = get_state_file(user_id)
    state = load_json(state_file, {})
    state[key] = value
    save_json(state_file, state)

def get_state(user_id, key, default=None):
    state_file = get_state_file(user_id)
    state = load_json(state_file, {})
    return state.get(key, default)

def clear_state(user_id):
    state_file = get_state_file(user_id)
    if os.path.exists(state_file):
        os.remove(state_file)

# ========== ОТПРАВКА СООБЩЕНИЙ ==========
def send_message(chat_id, text, reply_markup=None):
    url = f"{URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"{URL}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def answer_callback(callback_id, text=''):
    url = f"{URL}/answerCallbackQuery"
    payload = {'callback_query_id': callback_id}
    if text:
        payload['text'] = text
    
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def is_admin(user_id):
    return str(user_id) in ADMINS

def get_data():
    return load_json(DATA_FILE, {'tiers': {}, 'modes': []})

def get_descriptions():
    return load_json(DESC_FILE, {})

def get_history():
    return load_json(HISTORY_FILE, [])

def get_applications():
    return load_json(APPS_FILE, [])

def add_history(action, data):
    history = get_history()
    history.append({
        'action': action,
        'time': int(time.time()),
        **data
    })
    # Оставляем последние 1000 записей
    if len(history) > 1000:
        history = history[-1000:]
    save_json(HISTORY_FILE, history)

# ========== ОБРАБОТКА КОМАНД ==========
def cmd_start(chat_id, user_id):
    msg = """Привет! Команды:
/tier — просмотр тиров
/find [ник] — поиск игрока
/info [ник] — информация об игроке
/compare [ник1] [ник2] — сравнить
/last — последние добавленные
/count — статистика
!пинг — проверка пинга"""
    
    if is_admin(user_id):
        msg += """

Админ команды:
/add — добавить игрока
/edit — редактировать
/id — сменить порядок
/history [ник] — история игрока
/apps — заявки на тир
/desc [ник] [текст] — добавить описание"""
    
    send_message(chat_id, msg)

def cmd_tier(chat_id):
    data = get_data()
    modes = data.get('modes', [])
    
    if not modes:
        send_message(chat_id, "Нет доступных режимов")
        return
    
    keyboard = {'inline_keyboard': []}
    row = []
    for mode in modes:
        name = mode.get('name', '')
        row.append({'text': name.upper(), 'callback_data': f'view_mode_{name}'})
        if len(row) == 2:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    
    send_message(chat_id, f"Выберите режим:\n\nСайт: {SITE_URL}", keyboard)

def cmd_find(chat_id, nick):
    if not nick:
        send_message(chat_id, "Введите: /find [ник]")
        return
    
    data = get_data()
    found = []
    
    tiers = data.get('tiers', {})
    for mode, platforms in tiers.items():
        for platform, tier_list in platforms.items():
            for tier, players in tier_list.items():
                for player in players:
                    if nick.lower() in player.lower():
                        found.append(f"{player} — {mode.upper()} | {platform.upper()} | {tier}")
                        if len(found) >= 20:
                            break
    
    if not found:
        send_message(chat_id, f"Не найдено: {nick}")
        return
    
    text = "Найдено:\n\n" + "\n".join(found[:20])
    if len(found) > 20:
        text += f"\n\n...и еще {len(found) - 20}"
    send_message(chat_id, text)

def cmd_info(chat_id, nick):
    if not nick:
        send_message(chat_id, "Введите: /info [ник]")
        return
    
    data = get_data()
    desc = get_descriptions()
    found = []
    
    tiers = data.get('tiers', {})
    for mode, platforms in tiers.items():
        for platform, tier_list in platforms.items():
            for tier, players in tier_list.items():
                if nick in players:
                    found.append(f"{mode.upper()} | {platform.upper()} | {tier}")
    
    if not found:
        send_message(chat_id, f"Не найдено: {nick}")
        return
    
    text = f"<b>{nick}</b>\n\n" + "\n".join(found)
    if nick in desc and desc[nick]:
        text += f"\n\n<b>Описание:</b>\n{desc[nick]}"
    else:
        text += "\n\n<i>Описание отсутствует</i>"
    
    send_message(chat_id, text)

def cmd_compare(chat_id, args):
    parts = args.split()
    if len(parts) < 2:
        send_message(chat_id, "Введите: /compare [ник1] [ник2]")
        return
    
    nick1, nick2 = parts[0], parts[1]
    data = get_data()
    info1, info2 = [], []
    tier_scores = {'S': 6, 'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
    
    tiers = data.get('tiers', {})
    for mode, platforms in tiers.items():
        for platform, tier_list in platforms.items():
            for tier, players in tier_list.items():
                if nick1 in players:
                    info1.append({'mode': mode, 'platform': platform, 'tier': tier})
                if nick2 in players:
                    info2.append({'mode': mode, 'platform': platform, 'tier': tier})
    
    if not info1 and not info2:
        send_message(chat_id, "Оба не найдены")
        return
    
    text = f"<b>{nick1}</b> vs <b>{nick2}</b>\n\n"
    
    text += f"{nick1}:\n"
    if not info1:
        text += "Не найден\n"
    else:
        for i in info1:
            text += f"{i['mode'].upper()} | {i['platform'].upper()} | {i['tier']}\n"
    
    text += f"\n{nick2}:\n"
    if not info2:
        text += "Не найден\n"
    else:
        for i in info2:
            text += f"{i['mode'].upper()} | {i['platform'].upper()} | {i['tier']}\n"
    
    best1 = max([tier_scores.get(i['tier'], 0) for i in info1], default=0)
    best2 = max([tier_scores.get(i['tier'], 0) for i in info2], default=0)
    
    text += "\n"
    if best1 > best2:
        text += f"Выше: {nick1}"
    elif best2 > best1:
        text += f"Выше: {nick2}"
    else:
        text += "Равны"
    
    send_message(chat_id, text)

def cmd_last(chat_id):
    history = get_history()
    last = history[-10:] if history else []
    
    if not last:
        send_message(chat_id, "История пуста")
        return
    
    text = "Последние добавленные:\n\n"
    for h in reversed(last):
        if h.get('action') == 'add':
            text += f"{h.get('player')} — {h.get('mode', '').upper()} | {h.get('platform', '').upper()} | {h.get('tier')}\n"
    
    send_message(chat_id, text)

def cmd_count(chat_id):
    data = get_data()
    counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
    total = 0
    
    tiers = data.get('tiers', {})
    for platforms in tiers.values():
        for tier_list in platforms.values():
            for tier, players in tier_list.items():
                cnt = len(players)
                counts[tier] = counts.get(tier, 0) + cnt
                total += cnt
    
    text = f"Всего игроков: {total}\n\n"
    for tier, cnt in counts.items():
        text += f"{tier}: {cnt}\n"
    
    send_message(chat_id, text)

def cmd_ping(chat_id):
    start = time.time()
    try:
        requests.get(SITE_URL, timeout=3)
        ms = int((time.time() - start) * 1000)
        send_message(chat_id, f"Пинг: {ms}мс")
    except:
        send_message(chat_id, "Пинг: ошибка")

def cmd_apps(chat_id):
    apps = get_applications()
    if not apps:
        send_message(chat_id, "Нет заявок")
        return
    
    text = "<b>Заявки на тир:</b>\n\n"
    for app in apps[-5:]:  # Последние 5
        text += f"<b>{app.get('nick')}</b> — {time.strftime('%d.%m %H:%M', time.localtime(app.get('time', 0)))}\n"
        text += f"Против: {app.get('opponent')}\n"
        text += f"Связь: {app.get('contact')}\n"
        if app.get('comment'):
            text += f"Комментарий: {app['comment']}\n"
        text += f"/appdelete_{app.get('id')} — удалить\n\n"
    
    send_message(chat_id, text)

def cmd_history(chat_id, nick):
    if not nick:
        send_message(chat_id, "Введите: /history [ник]")
        return
    
    history = get_history()
    player_history = []
    
    for h in history:
        if h.get('player', '').lower() == nick.lower():
            player_history.append(h)
    
    if not player_history:
        send_message(chat_id, f"История пуста для: {nick}")
        return
    
    text = f"История {nick}:\n\n"
    for h in player_history[-10:]:
        date = time.strftime('%d.%m %H:%M', time.localtime(h.get('time', 0)))
        action = h.get('action')
        if action == 'add':
            text += f"{date} → {h.get('mode', '').upper()} | {h.get('platform', '').upper()} | {h.get('tier')}\n"
        elif action == 'move':
            text += f"{date} ~> {h.get('to_mode', '').upper()} | {h.get('to_platform', '').upper()} | {h.get('to_tier')}\n"
        elif action == 'delete':
            text += f"{date} X удален\n"
    
    send_message(chat_id, text)

def cmd_desc(chat_id, user_id, args):
    if not is_admin(user_id):
        send_message(chat_id, "Нет доступа")
        return
    
    parts = args.split(' ', 1)
    if len(parts) < 2:
        send_message(chat_id, "Использование: /desc [ник] [описание]")
        return
    
    nick, description = parts[0], parts[1]
    desc = get_descriptions()
    desc[nick] = description
    save_json(DESC_FILE, desc)
    send_message(chat_id, f"Описание для <b>{nick}</b> сохранено!")

# ========== CALLBACK ОБРАБОТКА ==========
def handle_view_mode(chat_id, message_id, mode):
    data = get_data()
    platforms = []
    for m in data.get('modes', []):
        if m.get('name') == mode:
            platforms = m.get('platforms', [])
            break
    
    keyboard = {'inline_keyboard': []}
    row = []
    for pl in platforms:
        row.append({'text': pl.upper(), 'callback_data': f'view_platform_{mode}_{pl}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': 'view_back_modes'}])
    
    edit_message(chat_id, message_id, f"{mode.upper()}\n\nВыберите платформу:", keyboard)

def handle_view_platform(chat_id, message_id, mode, platform):
    data = get_data()
    desc = get_descriptions()
    tiers = data.get('tiers', {}).get(mode, {}).get(platform, {})
    
    text = f"{mode.upper()} | {platform.upper()}\n\n"
    for tier in ['S', 'A', 'B', 'C', 'D', 'E']:
        players = tiers.get(tier, [])
        if players:
            players_list = ', '.join(players[:30])  # Ограничиваем вывод
            desc_count = sum(1 for p in players if p in desc and desc[p])
            if desc_count:
                players_list += f" ({desc_count} с описанием)"
        else:
            players_list = '—'
        text += f"<b>{tier}:</b> {players_list}\n\n"
    
    text += f"Сайт: {SITE_URL}"
    keyboard = {'inline_keyboard': [[{'text': 'Назад', 'callback_data': f'view_back_platforms_{mode}'}]]}
    edit_message(chat_id, message_id, text, keyboard)

# ========== ВЕБХУК ==========
@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    
    # Логируем для отладки
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        user_id = data['message']['from']['id']
        text = data['message'].get('text', '').strip()
        
        # Убираем упоминание бота
        if '@' in text:
            text = text.split('@')[0]
        
        if text == '/start':
            cmd_start(chat_id, user_id)
        
        elif text == '/tier':
            cmd_tier(chat_id)
        
        elif text.startswith('/find '):
            cmd_find(chat_id, text[6:].strip())
        
        elif text.startswith('/info '):
            cmd_info(chat_id, text[6:].strip())
        
        elif text.startswith('/compare '):
            cmd_compare(chat_id, text[9:].strip())
        
        elif text == '/last':
            cmd_last(chat_id)
        
        elif text == '/count':
            cmd_count(chat_id)
        
        elif text == '/apps' and is_admin(user_id):
            cmd_apps(chat_id)
        
        elif text.startswith('/history ') and is_admin(user_id):
            cmd_history(chat_id, text[9:].strip())
        
        elif text.startswith('/desc ') and is_admin(user_id):
            cmd_desc(chat_id, user_id, text[6:].strip())
        
        elif text == '!пинг':
            cmd_ping(chat_id)
        
        elif text == '/add' and is_admin(user_id):
            cmd_tier(chat_id)  # Временно
    
    elif 'callback_query' in data:
        cb = data['callback_query']
        msg_id = cb['message']['message_id']
        chat_id = cb['message']['chat']['id']
        cb_user = cb['from']['id']
        cb_data = cb['data']
        
        if cb_data.startswith('view_mode_'):
            mode = cb_data[10:]
            handle_view_mode(chat_id, msg_id, mode)
        
        elif cb_data.startswith('view_platform_'):
            parts = cb_data.split('_')
            if len(parts) >= 4:
                mode, platform = parts[2], parts[3]
                handle_view_platform(chat_id, msg_id, mode, platform)
        
        elif cb_data == 'view_back_modes':
            cmd_tier(chat_id)
        
        elif cb_data.startswith('view_back_platforms_'):
            mode = cb_data[19:]
            handle_view_mode(chat_id, msg_id, mode)
        
        answer_callback(cb['id'])
    
    return "OK", 200

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
