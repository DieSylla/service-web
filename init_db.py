import sqlite3
import bcrypt

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT UNIQUE,
    password TEXT,
    role TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER,
    created_at DATETIME,
    expires_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    content TEXT,
    category_id INTEGER,
    created_at DATETIME,
    FOREIGN KEY (category_id) REFERENCES categories(id)
)''')

# Insert test data
hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
cursor.execute("INSERT OR IGNORE INTO users (login, password, role) VALUES (?, ?, ?)", 
               ('admin', hashed_password, 'admin'))

cursor.execute("INSERT OR IGNORE INTO tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)", 
               ('valid_token', 1, '2025-07-09 12:00:00', '2025-12-31 23:59:59'))
cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Sport'), ('Technologie')")
cursor.execute("INSERT OR IGNORE INTO articles (title, description, content, category_id, created_at) VALUES (?, ?, ?, ?, ?)", 
               ('Article 1', 'Description 1', 'Contenu 1', 1, '2025-07-09 12:00:00'))
cursor.execute("INSERT OR IGNORE INTO articles (title, description, content, category_id, created_at) VALUES (?, ?, ?, ?, ?)", 
               ('Article 2', 'Description 2', 'Contenu 2', 2, '2025-07-09 12:00:00'))
conn.commit()
conn.close()

print("Base de données initialisée avec succès et données de test insérées !")