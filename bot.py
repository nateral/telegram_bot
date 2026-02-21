import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

# Токен бота (вы получили новый)
TOKEN = "7532259267:AAGdCxqHXA_JcAbfHHCl09wZEoIpxmheQsA"
URL = f"https://api.telegram.org/bot{TOKEN}"

# Данные (простые, для теста)
tiers = {
    "nodebuff": {
        "pc": {
            "S": ["Player1", "Player2"],
            "A": ["Player3", "Player4"],
            "B": ["Player5"],
            "C": [],
            "D": [],
            "E": []
        }
    }
}

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    
    # Логируем
    print(json.dumps(data, indent=2))
    
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        
        if text == '/start':
            send_message(chat_id, "Бот работает! Команды:\n/tier - показать тиры")
        
        elif text == '/tier':
            # Формируем ответ
            response = "Тиры (NodeBuff PC):\n\n"
            for tier, players in tiers["nodebuff"]["pc"].items():
                players_list = ", ".join(players) if players else "—"
                response += f"<b>{tier}:</b> {players_list}\n"
            
            send_message(chat_id, response)
    
    return "OK", 200

def send_message(chat_id, text):
    url = f"{URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
