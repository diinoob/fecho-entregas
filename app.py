import streamlit as st
import sqlite3
from datetime import date, datetime
from reportlab.pdfgen import canvas
import bcrypt
import pandas as pd
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import yagmail

DB = "entregas.db"

def db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS utilizadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password BLOB,
        empresa_id INTEGER,
        role TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS entregas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        morada TEXT,
        estado TEXT,
        nota TEXT,
        data TEXT,
        motorista TEXT,
        empresa_id INTEGER,
        foto TEXT,
        assinatura TEXT,
        email TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        timestamp TEXT,
        success INTEGER)""")

    cur.execute("INSERT OR IGNORE INTO empresas (nome) VALUES ('Empresa Demo')")
    cur.execute("SELECT id FROM empresas WHERE nome='Empresa Demo'")
    empresa_id = cur.fetchone()[0]

    pwd = bcrypt.hashpw("admin".encode(), bcrypt.gensalt())

    cur.execute("""INSERT OR IGNORE INTO utilizadores
        (username, password, empresa_id, role)
        VALUES (?, ?, ?, ?)""", ("admin", pwd, empresa_id, "admin"))

    con.commit()

init_db()

st.title("📦 Intercourier entregas")


if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    tab1, tab2 = st.tabs(["Login", "Registar"])

    with tab1:
        u = st.text_input("Utilizador")
        p = st.text_input("Password", type="password")

        if st.button("Entrar"):
            con = db()
            cur = con.cursor()
            cur.execute("SELECT password, empresa_id, role FROM utilizadores WHERE username=?", (u,))
            user = cur.fetchone()

            if user and bcrypt.checkpw(p.encode(), user[0]):
                cur.execute("INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 1)", (u, str(datetime.now())))
                st.session_state.login = True
                st.session_state.utilizador = u
                st.session_state.empresa_id = user[1]
                st.session_state.role = user[2]
                st.rerun()
            else:
                cur.execute("INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 0)", (u, str(datetime.now())))
                st.error("Login inválido")
            con.commit()

    with tab2:
        st.subheader("Registar novo utilizador")
        nu = st.text_input("Novo utilizador", key="reg_user")
        np = st.text_input("Password", type="password", key="reg_pass")
        ncp = st.text_input("Confirmar Password", type="password", key="reg_confirm")

        if st.button("Registar"):
            if np != ncp:
                st.error("Passwords não coincidem")
            elif not nu:
                st.error("Username obrigatório")
            else:
                con = db()
                cur = con.cursor()
                cur.execute("SELECT id FROM utilizadores WHERE username=?", (nu,))
                if cur.fetchone():
                    st.error("Username já existe")
                else:
                    cur.execute("SELECT id FROM empresas WHERE nome='Empresa Demo'")
                    empresa_id = cur.fetchone()[0]
                    pwd = bcrypt.hashpw(np.encode(), bcrypt.gensalt())
                    cur.execute("INSERT INTO utilizadores (username,password,empresa_id,role) VALUES (?,?,?,?)",
                                (nu, pwd, empresa_id, "motorista"))
                    con.commit()
                    st.success("Utilizador registado com sucesso. Faça login.")
    st.stop()

is_admin = st.session_state.role == "admin"

menu = st.sidebar.selectbox(
    "Menu",
    ["Nova Entrega", "Fechar Dia", "Administração"] if is_admin else ["Nova Entrega", "Fechar Dia"]
)

if menu == "Administração" and is_admin:
    st.subheader("Criar Motorista")
    nu = st.text_input("Novo utilizador")
    np = st.text_input("Password", type="password")

    if st.button("Criar Motorista"):
        pwd = bcrypt.hashpw(np.encode(), bcrypt.gensalt())
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO utilizadores (username,password,empresa_id,role) VALUES (?,?,?,?)",
                    (nu, pwd, st.session_state.empresa_id, "motorista"))
        con.commit()
        st.success("Motorista criado")


if menu == "Nova Entrega":
    cliente = st.text_input("Cliente")
    morada = st.text_input("Morada")
    email_cliente = st.text_input("Email do Cliente")
    estado = st.selectbox("Estado", ["Entregue", "Não Entregue"])
    nota = st.text_area("Nota")

    foto = st.camera_input("Foto da entrega")
    assinatura = st_canvas(height=150, width=300, drawing_mode="freedraw")

    if st.button("Guardar Entrega"):
        con = db()
        cur = con.cursor()
        cur.execute("""INSERT INTO entregas
            (cliente,morada,email,estado,nota,data,motorista,empresa_id,foto,assinatura)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (
            cliente, morada, email_cliente, estado, nota,
            str(datetime.now()), st.session_state.utilizador, st.session_state.empresa_id,
            str(foto) if foto else None, str(assinatura)
        ))
        con.commit()
        st.success("Entrega guardada")

        if estado == "Entregue":
            try:
                # Configure with your email credentials
                yag = yagmail.SMTP('your_email@gmail.com', 'your_app_password')  # Replace with actual Gmail credentials
                subject = "Nova Entrega Realizada"
                body = f"""Entrega realizada com sucesso:

Cliente: {cliente}
Morada: {morada}
Email do Cliente: {email_cliente}
Estado: {estado}
Nota: {nota}
Data/Hora: {str(datetime.now())}
Motorista: {st.session_state.utilizador}
"""
                attachments = []
                if assinatura and isinstance(assinatura, dict) and 'data' in assinatura:
                    img_data = assinatura['data']
                    attachments.append({'data': img_data, 'name': 'assinatura.png'})
                yag.send('diogoribeiro109@msn.com', subject, body, attachments=attachments)
                st.info("Email enviado com sucesso.")
            except Exception as e:
                st.error(f"Erro ao enviar email: {e}")


if menu == "Fechar Dia":
    hoje = str(date.today())
    con = db()
    cur = con.cursor()
    cur.execute("SELECT cliente,morada,estado,nota,motorista FROM entregas WHERE date(data)=? AND empresa_id=?",
                (hoje, st.session_state.empresa_id))
    dados = cur.fetchall()

    if st.button("Exportar Excel"):
        df = pd.DataFrame(dados, columns=["Cliente","Morada","Estado","Nota","Motorista"])
        df.to_excel("relatorio.xlsx", index=False)
        st.download_button("Download Excel", open("relatorio.xlsx","rb"), file_name="relatorio.xlsx")
