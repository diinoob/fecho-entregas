import sqlite3
import pandas as pd
import streamlit as st
import time
from hashlib import sha256

# Create and configure the database initially (if does not exist)
def initialize_database():
    conn = sqlite3.connect("deliveries.db")
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # Insert initial data if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       ("admin", sha256("admin".encode()).hexdigest()))

    cursor.execute("SELECT COUNT(*) FROM deliveries")
    if cursor.fetchone()[0] == 0:
        deliveries = [
            ("Item A",),
            ("Item B",),
            ("Item C",)
        ]
        cursor.executemany("INSERT INTO deliveries (item_name) VALUES (?)", deliveries)

    conn.commit()
    conn.close()

# Authenticate the user
def authenticate_user(username, password):
    conn = sqlite3.connect("deliveries.db")
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] == sha256(password.encode()).hexdigest():
        return True
    return False

# Fetch deliveries
def fetch_deliveries():
    conn = sqlite3.connect("deliveries.db")
    deliveries = pd.read_sql_query("SELECT * FROM deliveries", conn)
    conn.close()
    return deliveries

# Mark a delivery as completed
def mark_delivery_as_completed(delivery_id):
    conn = sqlite3.connect("deliveries.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE deliveries SET status = 'Delivered' WHERE id = ?", (delivery_id,))
    conn.commit()
    conn.close()

# Function to ensure unique keys and avoid duplication error
def generate_unique_key(base_key):
    return f"{base_key}_{int(time.time() * 1000000)}"

# Main Streamlit app
def main():
    st.title("Gestão de Entregas")

    # Authentication
    st.sidebar.title("Login")
    login_username_key = generate_unique_key("login_username")
    login_password_key = generate_unique_key("login_password")
    login_button_key = generate_unique_key("login_button")
    
    username = st.sidebar.text_input("Usuário", key=login_username_key)
    password = st.sidebar.text_input("Senha", type="password", key=login_password_key)
    login_button = st.sidebar.button("Entrar", key=login_button_key)

    if login_button and authenticate_user(username, password):
        st.sidebar.success(f"Logado como {username}")

        # Display deliveries
        st.header("Entregas")
        deliveries = fetch_deliveries()
        st.dataframe(deliveries)

        # Mark delivery as delivered
        delivery_id = st.number_input("ID da Entrega", min_value=1, key=generate_unique_key("delivery_id"))
        if st.button("Marcar como Entregue", key=generate_unique_key("mark_delivered")):
            mark_delivery_as_completed(delivery_id)
            st.success(f"Entrega {delivery_id} marcada como entregue.")

        # Refresh deliveries
        if st.button("Recarregar Dados", key=generate_unique_key("refresh_button")):
            deliveries = fetch_deliveries()
            st.dataframe(deliveries)

    elif login_button:
        st.sidebar.error("Usuário ou senha inválidos.")

if __name__ == "__main__":
    initialize_database()
    main()