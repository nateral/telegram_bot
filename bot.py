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
API_URL = f"{SITE_URL}/bot_api.php"   # Ваш API
API_TOKEN = "secret123"                # Тот же токен, что в PHP
ADMINS = ['6380018406', '8198380412', '8208522743', '7886275415']
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# Папка для состояний (админские сессии)
STATES_DIR = 'states'
if not os.path.exists(STATES_DIR):
    os.makedirs(STATES_DIR)

# ========== РАБОТА С API САЙТА ==========
def api_request(action, method='GET', data=None):
    """Универсальная функция для запросов к API сайта"""
    try:
        url = f"{API_URL}?action={action}"
        if method == 'POST':
            url += f"&token={API_TOKEN}"
            response = requests.post(url, json=data, timeout=5)
        else:
            response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"API Error: {e}")
    return None

def get_data():
    """Получает data.json с сайта"""
    return api_request('get_data') or {'tiers': {}, 'modes': []}

def get_descriptions():
    """Получает описания с сайта"""
    return api_request('get_descriptions') or {}

def get_history():
    """Получает историю с сайта"""
    return api_request('get_history') or []

def get_applications():
    """Получает заявки с сайта"""
    return api_request('get_applications') or []

def save_data(action, data):
    """Сохраняет данные на сайт"""
    return api_request(f'save_{action}', 'POST', data)

# ========== РАБОТА С СОСТОЯНИЯМИ (локально на Render) ==========
def get_state_file(user_id):
    return os.path.join(STATES_DIR, f'state_{user_id}.json')

def set_state(user_id, key, value):
    state_file = get_state_file(user_id)
    state = {}
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            try:
                state = json.load(f)
            except:
                state = {}
    state[key] = value
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_state(user_id, key, default=None):
    state_file = get_state_file(user_id)
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            try:
                state = json.load(f)
                return state.get(key, default)
            except:
                pass
    return default

def clear_state(user_id):
    state_file = get_state_file(user_id)
    if os.path.exists(state_file):
        os.remove(state_file)

# ========== ОТПРАВКА СООБЩЕНИЙ ==========
def send_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Send error: {e}")

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"{TELEGRAM_API}/editMessageText"
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
    except Exception as e:
        print(f"Edit error: {e}")

def answer_callback(callback_id, text=''):
    url = f"{TELEGRAM_API}/answerCallbackQuery"
    payload = {'callback_query_id': callback_id}
    if text:
        payload['text'] = text
    
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception as e:
        print(f"Answer error: {e}")

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def is_admin(user_id):
    return str(user_id) in ADMINS

def add_history(action, data):
    """Добавляет запись в историю (через API)"""
    history = get_history()
    history.append({
        'action': action,
        'time': int(time.time()),
        **data
    })
    # Оставляем последние 1000
    if len(history) > 1000:
        history = history[-1000:]
    save_data('history', history)

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
/desc [ник] [текст] — добавить описание
/deldesc [ник] — удалить описание
/rename [старый] [новый] — переименовать игрока"""
    
    send_message(chat_id, msg)

def cmd_tier(chat_id, msg_id=None):
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
    
    text = f"Выберите режим:\n\nСайт: {SITE_URL}"
    
    if msg_id:
        edit_message(chat_id, msg_id, text, keyboard)
    else:
        send_message(chat_id, text, keyboard)

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
        text += f"\n\n<b>Описание:</b>\n<pre>{desc[nick]}</pre>"
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
        if h.get('player', '').lower() == nick.lower() or \
           h.get('old_name', '').lower() == nick.lower():
            player_history.append(h)
    
    if not player_history:
        send_message(chat_id, f"История пуста для: {nick}")
        return
    
    text = f"История {nick}:\n\n"
    for h in player_history[-15:]:
        date = time.strftime('%d.%m %H:%M', time.localtime(h.get('time', 0)))
        action = h.get('action')
        if action == 'add':
            text += f"{date} → {h.get('mode', '').upper()} | {h.get('platform', '').upper()} | {h.get('tier')}\n"
        elif action == 'move':
            text += f"{date} ~> {h.get('to_mode', '').upper()} | {h.get('to_platform', '').upper()} | {h.get('to_tier')}\n"
        elif action == 'delete':
            text += f"{date} X удален\n"
        elif action == 'rename':
            if h.get('player', '').lower() == nick.lower():
                text += f"{date} ⟲ переименован из {h.get('old_name')}\n"
            else:
                text += f"{date} ⟳ переименован в {h.get('player')}\n"
    
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
    save_data('descriptions', desc)
    send_message(chat_id, f"Описание для <b>{nick}</b> сохранено!")

def cmd_deldesc(chat_id, user_id, nick):
    if not is_admin(user_id):
        send_message(chat_id, "Нет доступа")
        return
    
    if not nick:
        send_message(chat_id, "Использование: /deldesc [ник]")
        return
    
    desc = get_descriptions()
    if nick in desc:
        del desc[nick]
        save_data('descriptions', desc)
        send_message(chat_id, f"Описание для <b>{nick}</b> удалено!")
    else:
        send_message(chat_id, f"У игрока <b>{nick}</b> нет описания")

def cmd_rename(chat_id, user_id, args):
    if not is_admin(user_id):
        send_message(chat_id, "Нет доступа")
        return
    
    parts = args.split()
    if len(parts) < 2:
        send_message(chat_id, "Использование: /rename [старый_ник] [новый_ник]")
        return
    
    old_name, new_name = parts[0], parts[1]
    
    if old_name.lower() == new_name.lower():
        send_message(chat_id, "Ники совпадают")
        return
    
    data = get_data()
    
    # Проверяем, не занят ли новый ник
    tiers = data.get('tiers', {})
    for mode, platforms in tiers.items():
        for platform, tier_list in platforms.items():
            for tier, players in tier_list.items():
                for player in players:
                    if player.lower() == new_name.lower():
                        send_message(chat_id, f"Ник <b>{new_name}</b> уже занят")
                        return
    
    found = False
    renamed_in = []
    
    # Переименовываем
    for mode, platforms in tiers.items():
        for platform, tier_list in platforms.items():
            for tier, players in tier_list.items():
                for i, player in enumerate(players):
                    if player.lower() == old_name.lower():
                        players[i] = new_name
                        found = True
                        renamed_in.append(f"{mode.upper()} | {platform.upper()} | {tier}")
                        add_history('rename', {
                            'player': new_name,
                            'old_name': old_name,
                            'mode': mode,
                            'platform': platform,
                            'tier': tier
                        })
    
    if not found:
        send_message(chat_id, f"Игрок не найден: {old_name}")
        return
    
    # Переносим описание
    desc = get_descriptions()
    desc_transferred = False
    if old_name in desc:
        desc[new_name] = desc[old_name]
        del desc[old_name]
        save_data('descriptions', desc)
        desc_transferred = True
    
    # Сохраняем данные
    save_data('data', data)
    
    text = f"Игрок переименован:\n<b>{old_name}</b> → <b>{new_name}</b>\n\n"
    text += "Обновлено в:\n" + "\n".join(renamed_in)
    if desc_transferred:
        text += "\n\nОписание перенесено"
    
    send_message(chat_id, text)

def cmd_add(chat_id, msg_id=None):
    data = get_data()
    modes = data.get('modes', [])
    
    keyboard = {'inline_keyboard': []}
    row = []
    for mode in modes:
        name = mode.get('name', '')
        row.append({'text': name.upper(), 'callback_data': f'add_mode_{name}'})
        if len(row) == 2:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    
    text = "Добавление игрока\n\nВыберите режим:"
    
    if msg_id:
        edit_message(chat_id, msg_id, text, keyboard)
    else:
        send_message(chat_id, text, keyboard)

def cmd_edit(chat_id, msg_id=None):
    data = get_data()
    modes = data.get('modes', [])
    
    keyboard = {'inline_keyboard': []}
    row = []
    for mode in modes:
        name = mode.get('name', '')
        row.append({'text': name.upper(), 'callback_data': f'edit_mode_{name}'})
        if len(row) == 2:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    
    text = "Редактирование игрока\n\nВыберите режим:"
    
    if msg_id:
        edit_message(chat_id, msg_id, text, keyboard)
    else:
        send_message(chat_id, text, keyboard)

def cmd_id(chat_id, msg_id=None):
    data = get_data()
    modes = data.get('modes', [])
    
    keyboard = {'inline_keyboard': []}
    row = []
    for mode in modes:
        name = mode.get('name', '')
        row.append({'text': name.upper(), 'callback_data': f'id_mode_{name}'})
        if len(row) == 2:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    
    text = "Смена порядка игроков\n\nВыберите режим:"
    
    if msg_id:
        edit_message(chat_id, msg_id, text, keyboard)
    else:
        send_message(chat_id, text, keyboard)

# ========== CALLBACK ОБРАБОТКА ==========
def handle_view_mode(chat_id, msg_id, mode):
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
    
    edit_message(chat_id, msg_id, f"{mode.upper()}\n\nВыберите платформу:", keyboard)

def handle_view_platform(chat_id, msg_id, mode, platform):
    data = get_data()
    desc = get_descriptions()
    tiers = data.get('tiers', {}).get(mode, {}).get(platform, {})
    
    text = f"{mode.upper()} | {platform.upper()}\n\n"
    for tier in ['S', 'A', 'B', 'C', 'D', 'E']:
        players = tiers.get(tier, [])
        if players:
            players_list = ', '.join(players[:30])
            desc_count = sum(1 for p in players if p in desc and desc[p])
            if desc_count:
                players_list += f" ({desc_count} с описанием)"
        else:
            players_list = '—'
        text += f"<b>{tier}:</b> {players_list}\n\n"
    
    text += f"Сайт: {SITE_URL}"
    keyboard = {'inline_keyboard': [[{'text': 'Назад', 'callback_data': f'view_back_platforms_{mode}'}]]}
    edit_message(chat_id, msg_id, text, keyboard)

def handle_add_mode(chat_id, msg_id, mode, user_id):
    data = get_data()
    platforms = []
    for m in data.get('modes', []):
        if m.get('name') == mode:
            platforms = m.get('platforms', [])
            break
    
    set_state(user_id, 'add_mode', mode)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for pl in platforms:
        row.append({'text': pl.upper(), 'callback_data': f'add_platform_{mode}_{pl}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': 'add_back_modes'}])
    
    edit_message(chat_id, msg_id, f"Добавление игрока\n\n{mode.upper()}\n\nВыберите платформу:", keyboard)

def handle_add_platform(chat_id, msg_id, mode, platform, user_id):
    set_state(user_id, 'add_platform', platform)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for tier in ['S', 'A', 'B', 'C', 'D', 'E']:
        row.append({'text': tier, 'callback_data': f'add_tier_{mode}_{platform}_{tier}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': f'add_back_platforms_{mode}'}])
    
    edit_message(chat_id, msg_id, f"Добавление игрока\n\n{mode.upper()} | {platform.upper()}\n\nВыберите тир:", keyboard)

def handle_add_tier(chat_id, msg_id, mode, platform, tier, user_id):
    set_state(user_id, 'add_tier', tier)
    set_state(user_id, 'waiting', 'nickname')
    
    # Убираем клавиатуру
    edit_message(chat_id, msg_id, f"Добавление игрока\n\n{mode.upper()} | {platform.upper()} | {tier}\n\nВведите ник в чат:", None)

def handle_edit_mode(chat_id, msg_id, mode, user_id):
    data = get_data()
    platforms = []
    for m in data.get('modes', []):
        if m.get('name') == mode:
            platforms = m.get('platforms', [])
            break
    
    set_state(user_id, 'edit_mode', mode)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for pl in platforms:
        row.append({'text': pl.upper(), 'callback_data': f'edit_platform_{mode}_{pl}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': 'edit_back_modes'}])
    
    edit_message(chat_id, msg_id, f"Редактирование игрока\n\n{mode.upper()}\n\nВыберите платформу:", keyboard)

def handle_edit_platform(chat_id, msg_id, mode, platform, user_id):
    set_state(user_id, 'edit_platform', platform)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for tier in ['S', 'A', 'B', 'C', 'D', 'E']:
        row.append({'text': tier, 'callback_data': f'edit_tier_{mode}_{platform}_{tier}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': f'edit_back_platforms_{mode}'}])
    
    edit_message(chat_id, msg_id, f"Редактирование игрока\n\n{mode.upper()} | {platform.upper()}\n\nВыберите тир:", keyboard)

def handle_edit_tier(chat_id, msg_id, mode, platform, tier, user_id):
    set_state(user_id, 'edit_tier', tier)
    
    data = get_data()
    players = data.get('tiers', {}).get(mode, {}).get(platform, {}).get(tier, [])
    
    if not players:
        text = f"Редактирование игрока\n\n{mode.upper()} | {platform.upper()} | {tier}\n\nПусто"
        keyboard = {'inline_keyboard': [[{'text': 'Назад', 'callback_data': f'edit_back_platforms_{mode}'}]]}
        edit_message(chat_id, msg_id, text, keyboard)
        return
    
    keyboard = {'inline_keyboard': []}
    for player in players:
        keyboard['inline_keyboard'].append([{'text': player, 'callback_data': f'edit_player_{mode}_{platform}_{tier}_{player}'}])
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': f'edit_back_tiers_{mode}_{platform}'}])
    
    edit_message(chat_id, msg_id, f"Редактирование игрока\n\n{mode.upper()} | {platform.upper()} | {tier}\n\nВыберите игрока:", keyboard)

def handle_edit_player(chat_id, msg_id, mode, platform, tier, player, user_id):
    set_state(user_id, 'edit_player', player)
    
    keyboard = {'inline_keyboard': [
        [{'text': 'Переместить', 'callback_data': 'edit_move'}],
        [{'text': 'Удалить', 'callback_data': 'edit_delete'}],
        [{'text': 'Назад', 'callback_data': f'edit_back_players_{mode}_{platform}_{tier}'}]
    ]}
    
    edit_message(chat_id, msg_id, f"Игрок: {player}\n\n{mode.upper()} | {platform.upper()} | {tier}", keyboard)

def handle_edit_move(chat_id, msg_id, user_id):
    data = get_data()
    modes = data.get('modes', [])
    
    keyboard = {'inline_keyboard': []}
    row = []
    for mode in modes:
        name = mode.get('name', '')
        row.append({'text': name.upper(), 'callback_data': f'edit_movemode_{name}'})
        if len(row) == 2:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': 'edit_back_actions'}])
    
    edit_message(chat_id, msg_id, "Переместить игрока\n\nВыберите новый режим:", keyboard)

def handle_edit_movemode(chat_id, msg_id, mode, user_id):
    set_state(user_id, 'move_mode', mode)
    
    data = get_data()
    platforms = []
    for m in data.get('modes', []):
        if m.get('name') == mode:
            platforms = m.get('platforms', [])
            break
    
    keyboard = {'inline_keyboard': []}
    row = []
    for pl in platforms:
        row.append({'text': pl.upper(), 'callback_data': f'edit_moveplatform_{mode}_{pl}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': 'edit_move'}])
    
    edit_message(chat_id, msg_id, f"Переместить игрока\n\n{mode.upper()}\n\nВыберите платформу:", keyboard)

def handle_edit_moveplatform(chat_id, msg_id, mode, platform, user_id):
    set_state(user_id, 'move_platform', platform)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for tier in ['S', 'A', 'B', 'C', 'D', 'E']:
        row.append({'text': tier, 'callback_data': f'edit_movetier_{mode}_{platform}_{tier}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': f'edit_movemode_{mode}'}])
    
    edit_message(chat_id, msg_id, f"Переместить игрока\n\n{mode.upper()} | {platform.upper()}\n\nВыберите тир:", keyboard)

def handle_edit_movetier(chat_id, msg_id, mode, platform, tier, user_id):
    old_mode = get_state(user_id, 'edit_mode')
    old_platform = get_state(user_id, 'edit_platform')
    old_tier = get_state(user_id, 'edit_tier')
    player = get_state(user_id, 'edit_player')
    
    data = get_data()
    
    # Удаляем из старого места
    if old_mode in data['tiers'] and old_platform in data['tiers'][old_mode] and old_tier in data['tiers'][old_mode][old_platform]:
        players = data['tiers'][old_mode][old_platform][old_tier]
        data['tiers'][old_mode][old_platform][old_tier] = [p for p in players if p != player]
    
    # Добавляем в новое место
    if mode not in data['tiers']:
        data['tiers'][mode] = {}
    if platform not in data['tiers'][mode]:
        data['tiers'][mode][platform] = {}
    if tier not in data['tiers'][mode][platform]:
        data['tiers'][mode][platform][tier] = []
    
    # Удаляем из нового места если был
    if player in data['tiers'][mode][platform][tier]:
        data['tiers'][mode][platform][tier] = [p for p in data['tiers'][mode][platform][tier] if p != player]
    
    data['tiers'][mode][platform][tier].append(player)
    
    # Сохраняем
    save_data('data', data)
    
    # История
    add_history('move', {
        'player': player,
        'from_mode': old_mode,
        'from_platform': old_platform,
        'from_tier': old_tier,
        'to_mode': mode,
        'to_platform': platform,
        'to_tier': tier
    })
    
    text = f"Перемещено:\n\n{player}\n\n{old_mode.upper()} | {old_platform.upper()} | {old_tier}\n↓\n{mode.upper()} | {platform.upper()} | {tier}"
    keyboard = {'inline_keyboard': [[{'text': 'Готово', 'callback_data': 'edit_back_modes'}]]}
    edit_message(chat_id, msg_id, text, keyboard)
    clear_state(user_id)

def handle_edit_delete(chat_id, msg_id, user_id):
    mode = get_state(user_id, 'edit_mode')
    platform = get_state(user_id, 'edit_platform')
    tier = get_state(user_id, 'edit_tier')
    player = get_state(user_id, 'edit_player')
    
    data = get_data()
    
    # Удаляем игрока
    if mode in data['tiers'] and platform in data['tiers'][mode] and tier in data['tiers'][mode][platform]:
        players = data['tiers'][mode][platform][tier]
        data['tiers'][mode][platform][tier] = [p for p in players if p != player]
    
    # Сохраняем
    save_data('data', data)
    
    # История
    add_history('delete', {
        'player': player,
        'mode': mode,
        'platform': platform,
        'tier': tier
    })
    
    text = f"Удалено:\n\n{player}"
    keyboard = {'inline_keyboard': [[{'text': 'Готово', 'callback_data': 'edit_back_modes'}]]}
    edit_message(chat_id, msg_id, text, keyboard)
    clear_state(user_id)

def handle_id_mode(chat_id, msg_id, mode, user_id):
    data = get_data()
    platforms = []
    for m in data.get('modes', []):
        if m.get('name') == mode:
            platforms = m.get('platforms', [])
            break
    
    set_state(user_id, 'id_mode', mode)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for pl in platforms:
        row.append({'text': pl.upper(), 'callback_data': f'id_platform_{mode}_{pl}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': 'id_back_modes'}])
    
    edit_message(chat_id, msg_id, f"Смена порядка\n\n{mode.upper()}\n\nВыберите платформу:", keyboard)

def handle_id_platform(chat_id, msg_id, mode, platform, user_id):
    set_state(user_id, 'id_platform', platform)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for tier in ['S', 'A', 'B', 'C', 'D', 'E']:
        row.append({'text': tier, 'callback_data': f'id_tier_{mode}_{platform}_{tier}'})
        if len(row) == 3:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': f'id_back_platforms_{mode}'}])
    
    edit_message(chat_id, msg_id, f"Смена порядка\n\n{mode.upper()} | {platform.upper()}\n\nВыберите тир:", keyboard)

def handle_id_tier(chat_id, msg_id, mode, platform, tier, user_id):
    set_state(user_id, 'id_tier', tier)
    
    data = get_data()
    players = data.get('tiers', {}).get(mode, {}).get(platform, {}).get(tier, [])
    
    if not players:
        text = f"Смена порядка\n\n{mode.upper()} | {platform.upper()} | {tier}\n\nПусто"
        keyboard = {'inline_keyboard': [[{'text': 'Назад', 'callback_data': f'id_back_platforms_{mode}'}]]}
        edit_message(chat_id, msg_id, text, keyboard)
        return
    
    keyboard = {'inline_keyboard': []}
    for idx, player in enumerate(players):
        keyboard['inline_keyboard'].append([{'text': f"{idx+1}. {player}", 'callback_data': f'id_player_{mode}_{platform}_{tier}_{player}_{idx}'}])
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': f'id_back_tiers_{mode}_{platform}'}])
    
    text = f"Смена порядка\n\n{mode.upper()} | {platform.upper()} | {tier}\n\nВсего игроков: {len(players)}\n\nВыберите игрока для перемещения:"
    edit_message(chat_id, msg_id, text, keyboard)

def handle_id_player(chat_id, msg_id, mode, platform, tier, player, idx, user_id):
    set_state(user_id, 'id_player', player)
    set_state(user_id, 'id_player_index', int(idx))
    
    data = get_data()
    players = data.get('tiers', {}).get(mode, {}).get(platform, {}).get(tier, [])
    total = len(players)
    
    keyboard = {'inline_keyboard': []}
    row = []
    for i in range(total):
        if i == int(idx):
            continue
        row.append({'text': str(i+1), 'callback_data': f'id_pos_{i}'})
        if len(row) == 5:
            keyboard['inline_keyboard'].append(row)
            row = []
    if row:
        keyboard['inline_keyboard'].append(row)
    keyboard['inline_keyboard'].append([{'text': 'Назад', 'callback_data': f'id_back_players_{mode}_{platform}_{tier}'}])
    
    text = f"Переместить: {player}\n\nТекущая позиция: {int(idx)+1} из {total}\n\nВыберите новую позицию:"
    edit_message(chat_id, msg_id, text, keyboard)

def handle_id_pos(chat_id, msg_id, new_idx, user_id):
    mode = get_state(user_id, 'id_mode')
    platform = get_state(user_id, 'id_platform')
    tier = get_state(user_id, 'id_tier')
    player = get_state(user_id, 'id_player')
    old_idx = int(get_state(user_id, 'id_player_index'))
    new_idx = int(new_idx)
    
    data = get_data()
    players = data['tiers'][mode][platform][tier]
    
    # Удаляем со старой позиции
    player_to_move = players.pop(old_idx)
    # Вставляем на новую
    players.insert(new_idx, player_to_move)
    
    # Сохраняем
    save_data('data', data)
    
    text = f"Перемещено:\n\n{player}\n\nПозиция {old_idx+1} → {new_idx+1}"
    keyboard = {'inline_keyboard': [[{'text': 'Готово', 'callback_data': 'id_back_modes'}]]}
    edit_message(chat_id, msg_id, text, keyboard)
    clear_state(user_id)

def handle_app_delete(chat_id, msg_id, app_id):
    apps = get_applications()
    apps = [a for a in apps if a.get('id') != int(app_id)]
    save_data('applications', apps)
    
    # Показываем обновлённый список
    cmd_apps(chat_id)

def handle_confirm_add(chat_id, user_id, text):
    mode = get_state(user_id, 'add_mode')
    platform = get_state(user_id, 'add_platform')
    tier = get_state(user_id, 'add_tier')
    
    data = get_data()
    
    # Удаляем из других тиров
    for t in ['S', 'A', 'B', 'C', 'D', 'E']:
        if t != tier and text in data['tiers'][mode][platform].get(t, []):
            data['tiers'][mode][platform][t] = [p for p in data['tiers'][mode][platform][t] if p != text]
    
    # Добавляем
    if text not in data['tiers'][mode][platform][tier]:
        data['tiers'][mode][platform][tier].append(text)
    
    # Сохраняем
    save_data('data', data)
    
    # История
    add_history('add', {
        'player': text,
        'mode': mode,
        'platform': platform,
        'tier': tier
    })
    
    send_message(chat_id, f"Добавлено:\n{mode.upper()} | {platform.upper()} | {tier}\n\n{text}")
    clear_state(user_id)

# ========== ОСНОВНОЙ ВЕБХУК ==========
@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        user_id = data['message']['from']['id']
        text = data['message'].get('text', '').strip()
        
        # Убираем упоминание бота
        if '@' in text:
            text = text.split('@')[0]
        
        # Проверяем, ожидаем ли мы ввод
        waiting = get_state(user_id, 'waiting')
        if waiting == 'nickname':
            handle_confirm_add(chat_id, user_id, text)
            return "OK", 200
        
        # Обработка команд
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
        
        elif text.startswith('/deldesc ') and is_admin(user_id):
            cmd_deldesc(chat_id, user_id, text[9:].strip())
        
        elif text.startswith('/rename ') and is_admin(user_id):
            cmd_rename(chat_id, user_id, text[8:].strip())
        
        elif text.startswith('/appdelete_') and is_admin(user_id):
            app_id = text[11:].strip()
            if app_id.isdigit():
                handle_app_delete(chat_id, None, app_id)
        
        elif text == '/add' and is_admin(user_id):
            cmd_add(chat_id)
        
        elif text == '/edit' and is_admin(user_id):
            cmd_edit(chat_id)
        
        elif text == '/id' and is_admin(user_id):
            cmd_id(chat_id)
        
        elif text == '!пинг':
            cmd_ping(chat_id)
    
    elif 'callback_query' in data:
        cb = data['callback_query']
        msg_id = cb['message']['message_id']
        chat_id = cb['message']['chat']['id']
        user_id = cb['from']['id']
        cb_data = cb['data']
        
        is_callback_admin = is_admin(user_id)
        
        # Разбираем callback
        parts = cb_data.split('_')
        
        # Просмотр (доступен всем)
        if parts[0] == 'view':
            if parts[1] == 'mode' and len(parts) >= 3:
                handle_view_mode(chat_id, msg_id, parts[2])
            elif parts[1] == 'platform' and len(parts) >= 4:
                handle_view_platform(chat_id, msg_id, parts[2], parts[3])
            elif parts[1] == 'back':
                if len(parts) >= 3 and parts[2] == 'modes':
                    cmd_tier(chat_id, msg_id)
                elif len(parts) >= 4:
                    handle_view_mode(chat_id, msg_id, parts[3])
        
        # Админские действия
        elif is_callback_admin:
            if parts[0] == 'add':
                if parts[1] == 'mode' and len(parts) >= 3:
                    handle_add_mode(chat_id, msg_id, parts[2], user_id)
                elif parts[1] == 'platform' and len(parts) >= 4:
                    handle_add_platform(chat_id, msg_id, parts[2], parts[3], user_id)
                elif parts[1] == 'tier' and len(parts) >= 5:
                    handle_add_tier(chat_id, msg_id, parts[2], parts[3], parts[4], user_id)
                elif parts[1] == 'back':
                    if len(parts) >= 3 and parts[2] == 'modes':
                        cmd_add(chat_id, msg_id)
                    elif len(parts) >= 4:
                        handle_add_mode(chat_id, msg_id, get_state(user_id, 'add_mode'), user_id)
            
            elif parts[0] == 'edit':
                if parts[1] == 'mode' and len(parts) >= 3:
                    handle_edit_mode(chat_id, msg_id, parts[2], user_id)
                elif parts[1] == 'platform' and len(parts) >= 4:
                    handle_edit_platform(chat_id, msg_id, parts[2], parts[3], user_id)
                elif parts[1] == 'tier' and len(parts) >= 5:
                    handle_edit_tier(chat_id, msg_id, parts[2], parts[3], parts[4], user_id)
                elif parts[1] == 'player' and len(parts) >= 6:
                    handle_edit_player(chat_id, msg_id, 
                                      get_state(user_id, 'edit_mode'), 
                                      get_state(user_id, 'edit_platform'), 
                                      get_state(user_id, 'edit_tier'), 
                                      parts[5], user_id)
                elif parts[1] == 'move':
                    handle_edit_move(chat_id, msg_id, user_id)
                elif parts[1] == 'movemode' and len(parts) >= 3:
                    handle_edit_movemode(chat_id, msg_id, parts[2], user_id)
                elif parts[1] == 'moveplatform' and len(parts) >= 4:
                    handle_edit_moveplatform(chat_id, msg_id, parts[2], parts[3], user_id)
                elif parts[1] == 'movetier' and len(parts) >= 5:
                    handle_edit_movetier(chat_id, msg_id, parts[2], parts[3], parts[4], user_id)
                elif parts[1] == 'delete':
                    handle_edit_delete(chat_id, msg_id, user_id)
                elif parts[1] == 'back':
                    if len(parts) >= 3 and parts[2] == 'modes':
                        cmd_edit(chat_id, msg_id)
                    elif len(parts) >= 3 and parts[2] == 'platforms':
                        handle_edit_mode(chat_id, msg_id, get_state(user_id, 'edit_mode'), user_id)
                    elif len(parts) >= 3 and parts[2] == 'tiers':
                        handle_edit_platform(chat_id, msg_id, get_state(user_id, 'edit_mode'), 
                                           get_state(user_id, 'edit_platform'), user_id)
                    elif len(parts) >= 3 and parts[2] == 'players':
                        handle_edit_tier(chat_id, msg_id, get_state(user_id, 'edit_mode'), 
                                       get_state(user_id, 'edit_platform'), 
                                       get_state(user_id, 'edit_tier'), user_id)
                    elif len(parts) >= 3 and parts[2] == 'actions':
                        handle_edit_player(chat_id, msg_id, get_state(user_id, 'edit_mode'), 
                                         get_state(user_id, 'edit_platform'), 
                                         get_state(user_id, 'edit_tier'), 
                                         get_state(user_id, 'edit_player'), user_id)
            
            elif parts[0] == 'id':
                if parts[1] == 'mode' and len(parts) >= 3:
                    handle_id_mode(chat_id, msg_id, parts[2], user_id)
                elif parts[1] == 'platform' and len(parts) >= 4:
                    handle_id_platform(chat_id, msg_id, parts[2], parts[3], user_id)
                elif parts[1] == 'tier' and len(parts) >= 5:
                    handle_id_tier(chat_id, msg_id, parts[2], parts[3], parts[4], user_id)
                elif parts[1] == 'player' and len(parts) >= 7:
                    handle_id_player(chat_id, msg_id, parts[2], parts[3], parts[4], parts[5], parts[6], user_id)
                elif parts[1] == 'pos' and len(parts) >= 3:
                    handle_id_pos(chat_id, msg_id, parts[2], user_id)
                elif parts[1] == 'back':
                    if len(parts) >= 3 and parts[2] == 'modes':
                        cmd_id(chat_id, msg_id)
                    elif len(parts) >= 3 and parts[2] == 'platforms':
                        handle_id_mode(chat_id, msg_id, get_state(user_id, 'id_mode'), user_id)
                    elif len(parts) >= 3 and parts[2] == 'tiers':
                        handle_id_platform(chat_id, msg_id, get_state(user_id, 'id_mode'), 
                                         get_state(user_id, 'id_platform'), user_id)
                    elif len(parts) >= 3 and parts[2] == 'players':
                        handle_id_tier(chat_id, msg_id, get_state(user_id, 'id_mode'), 
                                     get_state(user_id, 'id_platform'), 
                                     get_state(user_id, 'id_tier'), user_id)
            
            elif parts[0] == 'app' and len(parts) >= 3 and parts[1] == 'delete':
                handle_app_delete(chat_id, msg_id, parts[2])
        
        # Отвечаем на callback
        answer_callback(cb['id'])
    
    return "OK", 200

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
