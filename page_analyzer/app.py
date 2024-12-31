from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import os
from dotenv import load_dotenv
import validators
from datetime omport datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')


def get_db_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    connection = psycopg2.connect(DATABASE_URL)
    return connection


@app.route('/urls/<int:id>/checks', methods=['POST'])
def create_check(id):
    connection = get_db_connection()
    cursor = connection.cursor()

    created_at = datetime.now()
    cursor.execute(
        'INSERT INTO url_checks (url_id, created_at) VALUES (%s, %s) RETURNING id;',
        (id, created_at)
    )
    connection.commit()
    cursor.close()
    connection.close()

    flash('Проверка добавлена!', 'success')
    return redirect(url_for('show_url, id=id)


@app.route('/urls')
def urls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls ORDER BY created_at DESC')
    urls = cur.fetchall()
    cur.close()
    conn.close()

    # Преобразование строк в объекты
    urls = [{'id': url[0], 'name': url[1], 'created_at': url[2]} for url in urls]

    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:id>')
def url_details(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls WHERE id = %s', (id,))
    url = cur.fetchone()
    cur.close()
    conn.close()

    if url is None:
        return 'URL not found', 404

    url = {'id': url[0], 'name': url[1], 'created_at': url[2]}
    return render_template('url_details.html', url=url)


@app.route('/urls')
def list_urls():
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Получаем список URL
    cursor.execute('SELECT * FROM urls ORDER BY created_at DESC;')
    urls = cursor.fetchall()
    
    # Получаем дату последней проверки для каждого URL
    cursor.execute('''
        SELECT url_id, MAX(created_at) AS last_check
        FROM url_checks
        GROUP BY url_id;
    ''')
    checks = {row[0]: row[1] for row in cursor.fetchall()}
    
    connection.close()
    return render_template('urls.html', urls=urls, checks=checks)


@app.route('/urls/<int:id>')
def show_url(id):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Получаем данные о конкретном URL
    cursor.execute('SELECT * FROM urls WHERE id = %s;', (id,))
    url = cursor.fetchone()
    
    # Получаем все проверки для этого URL
    cursor.execute('SELECT id, created_at FROM url_checks WHERE url_id = %s ORDER BY 
created_at DESC;', (id,))
    checks = cursor.fetchall()
    
    connection.close()
    return render_template('url_details.html', url=url, checks=checks)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Получаем URL из базы данных
    cursor.execute('SELECT name FROM urls WHERE id = %s', (id,))
    url = cursor.fetchone()

    if not url:
        flash('URL не найден', 'danger')
        return redirect(url_for('show_url', id=id))

    try:
        # Выполняем запрос к сайту
        response = requests.get(url[0], timeout=10)
        response.raise_for_status()

        # Извлекаем данные для проверки
        status_code = response.status_code

        # Добавляем данные проверки в базу данных
        cursor.execute('''
            INSERT INTO url_checks (url_id, status_code, created_at)
            VALUES (%s, %s, NOW())
        ''', (id, status_code))

        connection.commit()
        flash('Проверка выполнена успешно!', 'success')

    except requests.RequestException as e:
        # Обрабатываем ошибки запросов
        flash(f'Произошла ошибка при проверке: {str(e)}', 'danger')

    finally:
        connection.close()

    return redirect(url_for('show_url', id=id))


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']

        # Валидация URL
        if not validators.url(url):
            flash('Invalid URL. Please enter a valid URL.', 'error')
            return redirect(url_for('index'))

        # Сохранение в базу данных
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO urls (name) VALUES (%s)', (url,))
        conn.commit()
        cur.close()
        conn.close()

        flash('URL added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=True)
