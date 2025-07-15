import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Afficher les catégories
print("Catégories :")
cursor.execute("SELECT * FROM categories")
for row in cursor.fetchall():
    print(row)

# Afficher les articles
print("\nArticles :")
cursor.execute("SELECT * FROM articles")
for row in cursor.fetchall():
    print(row)

# Afficher les utilisateurs
print("\nUtilisateurs :")
cursor.execute("SELECT * FROM users")
for row in cursor.fetchall():
    print(row)

# Afficher les jetons
print("\nJetons :")
cursor.execute("SELECT * FROM tokens")
for row in cursor.fetchall():
    print(row)

conn.close()