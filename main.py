import requests
from bs4 import BeautifulSoup
import sqlite3
import time
from urllib.parse import urljoin
from flask import Flask, render_template
from random import choice
from flask import Flask, render_template, request, redirect, url_for
DB_NAME = 'news.db'
BASE_URL = "https://www.eurointegration.com.ua"
def create_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            content TEXT,
            url TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()
def fix_spacing(text):
    if not text:
        return ""
    fixed_text = ""
    prev_char = ""
    for char in text:
        if char.isupper() and prev_char and prev_char.islower():
            fixed_text += " "
        elif char == "." and prev_char and prev_char != " ":
            fixed_text += ". "  
            prev_char = char
            continue
        fixed_text += char
        prev_char = char
    return fixed_text
def parse_articles():
    url = "https://www.eurointegration.com.ua/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('div', class_='article__title')
    article_data = []
    count = 0
    for article in articles:
        if count >= 30:
            break
        title_tag = article.find('a')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        title = fix_spacing(title) 
        link = title_tag.get('href')
        if not title or not link:
            continue
        full_link = urljoin(BASE_URL, link)
        print(f"Добавляється в базу: {title}")
        article_data.append((title, None, full_link))
        count += 1
    save_to_db(article_data)
def save_to_db(article_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for title, content, url in article_data:
        cursor.execute('''
            INSERT OR IGNORE INTO articles (title, content, url) VALUES (?, ?, ?)
        ''', (title, content, url))
    conn.commit()
    conn.close()
def update_articles_content():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, url FROM articles WHERE content IS NULL OR content = ''")
    articles = cursor.fetchall()
    conn.close()
    for article_id, url in articles:
        print(f"Загружаемо контент для: {url}")
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find('div', class_='post__text')
            content_text = content.get_text(strip=True) if content else 'Контенту не найдено'
            content_text = fix_spacing(content_text)
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE articles SET content = ? WHERE id = ?", (content_text, article_id))
            conn.commit()
            conn.close()
            time.sleep(1)
        except Exception as e:
            print(f"Помилка при загрузці {url}: {e}")
if __name__ == "__main__":
    create_db()
    parse_articles()
    update_articles_content()
app = Flask(__name__)
def get_articles():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title FROM articles ORDER BY id DESC LIMIT 20')  
    articles = cursor.fetchall()
    conn.close()
    return [(article[0], fix_spacing(article[1])) for article in articles]
@app.route('/')
def index():
    articles = get_articles()
    return render_template('index.html', articles=articles)
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/random-article')
def random_article():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM articles')
    articles = cursor.fetchall()
    if articles:
        random_article_id = choice(articles)[0]
        return redirect(url_for('article', id=random_article_id))
    return "Стаття не знайдена", 404
@app.route('/article/<int:id>')
def article(id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT title, content FROM articles WHERE id = ?', (id,))
    article = cursor.fetchone()
    conn.close()
    if article:
        title_fixed = fix_spacing(article[0])
        content_fixed = fix_spacing(article[1])  
        return render_template('article.html', title=title_fixed, content=content_fixed)
    return "Статья не знайдена", 404
@app.route('/search')
def search():
    query = request.args.get('query', '')
    if query:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title FROM articles 
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY id DESC
        ''', ('%' + query + '%', '%' + query + '%'))
        articles = cursor.fetchall()
        conn.close()
    else:
        articles = []
    return render_template('index.html', articles=articles, query=query)
if __name__ == "__main__":
    app.run(debug=True)