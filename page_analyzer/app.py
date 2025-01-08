from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import os
from dotenv import load_dotenv
import validators
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Загрузка переменных окружения
load_dotenv()

# Инициализация Flask-приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')


# Подключение к базе данных
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# Нормализация URL
def normalize_url(url):
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


# Главная страница
@app.route('/')
def index():
    return render_template('index.html')


# Список всех URL
@app.route('/urls', methods=['GET', 'POST'])
def urls():
    if request.method == 'POST':
        url = request.form.get('url')

        # Проверка и нормализация URL
        if not validators.url(url):
            flash('Некорректный URL. Введите корректный адрес.', 'error')
            return redirect(url_for('index'))

        normalized_url = normalize_url(url)

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Проверка на уникальность
                    cursor.execute('SELECT id FROM urls WHERE name = %s;', (normalized_url,))
                    existing_url = cursor.fetchone()

                    if existing_url:
                        flash('URL уже существует!', 'info')
                        return redirect(url_for('show_url', id=existing_url[0]))

                    # Добавление нового URL
                    cursor.execute(
                        'INSERT INTO urls (name) VALUES (%s) RETURNING id;',
                        (normalized_url,)
                    )
                    conn.commit()
                    url_id = cursor.fetchone()[0]
            flash('URL успешно добавлен!', 'success')
            return redirect(url_for('show_url', id=url_id))
        except Exception as e:
            flash(f'Ошибка базы данных: {e}', 'error')
            return redirect(url_for('index'))

    # Получение всех URL
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT u.id, u.name, MAX(c.created_at) AS last_check,
                       MAX(c.status_code) AS last_status
                FROM urls u
                LEFT JOIN url_checks c ON u.id = c.url_id
                GROUP BY u.id
                ORDER BY u.created_at DESC;
            ''')
            urls = cursor.fetchall()

    return render_template('urls.html', urls=urls)


# Страница деталей URL
@app.route('/urls/<int:id>')
def show_url(id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Получение информации о URL
            cursor.execute('SELECT * FROM urls WHERE id = %s;', (id,))
            url = cursor.fetchone()

            if not url:
                flash('URL не найден.', 'error')
                return redirect(url_for('urls'))

            # Получение всех проверок
            cursor.execute('''
                SELECT id, created_at, status_code, h1, title, description
                FROM url_checks
                WHERE url_id = %s
                ORDER BY created_at DESC;
            ''', (id,))
            checks = cursor.fetchall()

    return render_template('url_details.html', url=url, checks=checks)


# Добавление проверки
@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT name FROM urls WHERE id = %s;', (id,))
            url = cursor.fetchone()

            if not url:
                flash('URL не найден.', 'error')
                return redirect(url_for('urls'))

            try:
                # Выполнение запроса к URL
                response = requests.get(url[0], timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Извлечение данных SEO
                h1 = soup.find('h1').get_text() if soup.find('h1') else None
                title = soup.title.string if soup.title else None
                description = None
                meta_description = soup.find('meta', attrs={'name': 'description'})
                if meta_description:
                    description = meta_description.get('content')

                # Добавление проверки в базу данных
                cursor.execute('''
                    INSERT INTO url_checks (url_id, status_code, created_at, h1, title, description)
                    VALUES (%s, %s, NOW(), %s, %s, %s);
                ''', (id, response.status_code, h1, title, description))
                conn.commit()

                flash('Проверка выполнена успешно!', 'success')
            except requests.RequestException as e:
                flash(f'Произошла ошибка при проверке: {e}', 'error')

    return redirect(url_for('show_url', id=id))


# Обработка ошибок
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)
