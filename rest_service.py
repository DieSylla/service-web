from flask import Flask, jsonify, request
from lxml import etree
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def articles_to_xml(articles, include_category_name=False):
    root = etree.Element("articles")
    for article in articles:
        article_elem = etree.SubElement(root, "article")
        etree.SubElement(article_elem, "id").text = str(article['id'])
        etree.SubElement(article_elem, "title").text = article['title']
        etree.SubElement(article_elem, "description").text = article['description']
        etree.SubElement(article_elem, "category_id").text = str(article['category_id'])
        if include_category_name and 'category_name' in article:
            etree.SubElement(article_elem, "category_name").text = article['category_name']
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')

@app.route('/articles', methods=['GET'])
def get_all_articles():
    format_type = request.args.get('format', 'json')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles")
    articles = cursor.fetchall()
    conn.close()

    if format_type == 'xml':
        return app.response_class(articles_to_xml(articles), mimetype='application/xml')
    return jsonify([dict(article) for article in articles])

@app.route('/articles/by-category', methods=['GET'])
def get_articles_by_category():
    format_type = request.args.get('format', 'json')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT a.*, c.name as category_name FROM articles a JOIN categories c ON a.category_id = c.id")
    articles = cursor.fetchall()
    conn.close()

    if format_type == 'xml':
        return app.response_class(articles_to_xml(articles, include_category_name=True), mimetype='application/xml')
    grouped = {}
    for article in articles:
        category = article['category_name']
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(dict(article))
    return jsonify(grouped)

@app.route('/articles/category/<int:category_id>', methods=['GET'])
def get_articles_in_category(category_id):
    format_type = request.args.get('format', 'json')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT a.*, c.name as category_name FROM articles a JOIN categories c ON a.category_id = c.id WHERE a.category_id = ?", (category_id,))
    articles = cursor.fetchall()
    conn.close()

    if format_type == 'xml':
        return app.response_class(articles_to_xml(articles, include_category_name=True), mimetype='application/xml')
    return jsonify([dict(article) for article in articles])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

    #Teste les endpoints avec Postman ou un navigateur :
    #http://localhost:5000/articles?format=json
    #http://localhost:5000/articles/by-category?format=xml
    #http://localhost:5000/articles/category/1?format=json