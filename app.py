import streamlit as st
import pandas as pd
import datetime
import smtplib
from email.message import EmailMessage
import json
import os

USERS_FILE = "users.json"
DATA_FILE = "entregas.csv"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def register_user(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = password
    save_users(users)
    return True

def authenticate(username, password):
    users = load_users()
    return users.get(username) == password

def send_email(report):
    msg = EmailMessage()
    msg.set_content(report)
    msg['Subject'] = 'Fecho Diário de Entregas'
    msg['From'] = 'teuemail@gmail.com'
    msg['To'] = 'destino@gmail.com'

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('teuemail@gmail.com', 'TUA_PASSWORD')
        smtp.send_message(msg)

st.title("App de Entregas – Transitários")

menu = st.sidebar.selectbox("Menu", ["Login", "Registo"])

if menu == "Registo":
    st.subheader("Registo de Novo Entregador")
    new_user = st.text_input("Novo utilizador")
    new_pass = st.text_input("Password", type="password")
    if st.button("Registar"):
        if register_user(new_user, new_pass):
            st.success("Utilizador criado com sucesso")
        else:
            st.error("Utilizador já existe")

if menu == "Login":
    user = st.text_input("Utilizador")
    password = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if authenticate(user, password):
            st.session_state["user"] = user
            st.success("Login efetuado")
        else:
            st.error("Credenciais inválidas")

if "user" in st.session_state:
    st.subheader(f"Bem-vindo {st.session_state['user']}")
    cliente = st.text_input("Cliente")
    morada = st.text_input("Morada")
    estado = st.selectbox("Estado", ["Entregue", "Falhou"])

    if st.button("Guardar Entrega"):
        now = datetime.datetime.now()
        row = pd.DataFrame([[st.session_state['user'], cliente, morada, estado, now]],
                           columns=["Entregador","Cliente","Morada","Estado","Hora"])
        if os.path.exists(DATA_FILE):
            row.to_csv(DATA_FILE, mode='a', header=False, index=False)
        else:
            row.to_csv(DATA_FILE, index=False)
        st.success("Entrega registada")

    if st.button("Fechar Dia"):
        df = pd.read_csv(DATA_FILE)
        report = df.to_string()
        send_email(report)
        st.success("Relatório enviado por email")

        st.download_button("Download Excel", open("relatorio.xlsx","rb"), file_name="relatorio.xlsx")
