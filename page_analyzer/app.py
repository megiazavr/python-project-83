from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import os
from dotenv import load_dotenv
import validators
import requests
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()

# Инициализация Flask-приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')


def get_db_connection():
    """Создает соединение с базой данных."""
    return psycopg2.connect(DATABASE_URL)


@app.route('/')
def index():
    """Рендеринг главной страницы."""
    return render_template('index.html')


@app.route('/urls', methods=['GET', 'POST'])
def urls():
    """Добавление и отображение списка URL."""
    if request.method == 'POST':
        url = request.form.get('url')

        if not validators.url(url):
            flash('Некорректный URL. Введите корректный адрес.', 'error')
            return redirect(url_for('index'))

        normalized_url = url.lower()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        'INSERT INTO urls (name) VALUES (%s) RETURNING id;',
                        (normalized_url,)
                    )
                    conn.commit()
                    url_id = cursor.fetchone()[0]
            flash('URL успешно добавлен!', 'success')
            return redirect(url_for('show_url', id=url_id))
        except psycopg2.errors.UniqueViolation:
            flash('URL уже существует!', 'info')
            return redirect(url_for('index'))

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


@app.route('/urls/<int:id>')
def show_url(id):
    """Отображение деталей конкретного URL и его проверок."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM urls WHERE id = %s;', (id,))
            url = cursor.fetchone()

            if not url:
                flash('URL не найден.', 'error')
                return redirect(url_for('urls'))

            cursor.execute('''
                SELECT id, status_code, created_at
                FROM url_checks
                WHERE url_id = %s
                ORDER BY created_at DESC;
            ''', (id,))
            checks = cursor.fetchall()

    return render_template('url_details.html', url=url, checks=checks)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    """Добавление проверки для URL."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT name FROM urls WHERE id = %s;', (id,))
            url = cursor.fetchone()

            if not url:
                flash('URL не найден.', 'error')
                return redirect(url_for('urls'))

            try:
                response = requests.get(url[0], timeout=10)
                status_code = response.status_code
                created_at = datetime.now()

                cursor.execute('''
                    INSERT INTO url_checks (url_id, status_code, created_at)
                    VALUES (%s, %s, %s);
                ''', (id, status_code, created_at))
                conn.commit()

                flash('Проверка выполнена успешно!', 'success')
            except requests.RequestException as e:
                flash(f'Произошла ошибка при проверке: {e}', 'error')

    return redirect(url_for('show_url', id=id))


if __name__ == '__main__':
    app.run(debug=True)
