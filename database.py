import sqlite3
def create_tables():
    conn=sqlite3.connect('medicine.db')
    cursor=conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       email TEXT NOT NULL UNIQUE,
                       password TEXT NOT NULL
                       
                   ) 
                   ''')
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS medicines(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       manufacture_date TEXT,
                       expiry_date TEXT NOT NULL,
                       quantity INTEGER NOT NULL,
                       purpose TEXT,
                       side_effects TEXT,
                       user_id INTEGER,
                       FOREIGN KEY(user_id) REFERENCES users(id)
                       
                   )''')
    conn.commit()
    conn.close()
    print('Tables created successfuly!')
create_tables()
    
    