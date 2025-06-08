import os
from flask import Flask
from threading import Thread

# Ініціалізація Flask-додатку
app = Flask('')

# Маршрут для перевірки стану (health check)
@app.route('/')
def home():
    return "I'm alive"

# Функція для запуску Flask-додатку
def run_flask_app():
    # Отримуємо порт із змінних середовища. Scalingo надасть його.
    # Використовуємо 5000 як значення за замовчуванням, якщо змінна PORT не встановлена (наприклад, при локальному запуску)
    port = int(os.getenv('PORT', 5000)) 
    app.run(host='0.0.0.0', port=port)

# Функція для запуску Flask-додатку в окремому потоці
def keep_alive():
    t = Thread(target=run_flask_app)
    t.start()
