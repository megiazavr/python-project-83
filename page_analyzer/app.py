from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import os
from dotenv import load_dotenv
import validators

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')


def get_db_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    connection = psycopg2.connect(DATABASE_URL)
    return connection


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
def url_detail(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls WHERE id = %s', (id,))
    url = cur.fetchone()
    cur.close()
    conn.close()

    if url is None:
        return 'URL not found', 404

    url = {'id': url[0], 'name': url[1], 'created_at': url[2]}
    return render_template('url_detail.html', url=url)


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
