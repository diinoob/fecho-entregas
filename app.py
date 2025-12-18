import streamlit as st
import sqlite3
from datetime import date
from reportlab.pdfgen import canvas
import bcrypt
import pandas as pd
from PIL import Image
from streamlit_drawable_canvas import st_canvas

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
        assinatura TEXT)""")

    cur.execute("INSERT OR IGNORE INTO empresas (nome) VALUES ('Empresa Demo')")
    cur.execute("SELECT id FROM empresas WHERE nome='Empresa Demo'")
    empresa_id = cur.fetchone()[0]

    pwd = bcrypt.hashpw("admin".encode(), bcrypt.gensalt())

    cur.execute("""INSERT OR IGNORE INTO utilizadores
        (username, password, empresa_id, role)
        VALUES (?, ?, ?, ?)""", ("admin", pwd, empresa_id, "admin"))

    con.commit()

init_db()

st.title("📦 Fecho Diário de Entregas")


if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    u = st.text_input("Utilizador")
    p = st.text_input("Password", type="password")

    if st.button("Entrar"):
        con = db()
        cur = con.cursor()
        cur.execute("SELECT password, empresa_id, role FROM utilizadores WHERE username=?", (u,))
        user = cur.fetchone()

        if user and bcrypt.checkpw(p.encode(), user[0]):
            st.session_state.login = True
            st.session_state.utilizador = u
            st.session_state.empresa_id = user[1]
            st.session_state.role = user[2]
            st.experimental_rerun()
        else:
            st.error("Login inválido")
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
    estado = st.selectbox("Estado", ["Entregue", "Não Entregue"])
    nota = st.text_area("Nota")

    foto = st.camera_input("Foto da entrega")
    assinatura = st_canvas(height=150, width=300, drawing_mode="freedraw")

    if st.button("Guardar Entrega"):
        con = db()
        cur = con.cursor()
        cur.execute("""INSERT INTO entregas
            (cliente,morada,estado,nota,data,motorista,empresa_id)
            VALUES (?,?,?,?,?,?,?)""", (
            cliente, morada, estado, nota,
            str(date.today()), st.session_state.utilizador, st.session_state.empresa_id
        ))
        con.commit()
        st.success("Entrega guardada")


if menu == "Fechar Dia":
    hoje = str(date.today())
    con = db()
    cur = con.cursor()
    cur.execute("SELECT cliente,morada,estado,nota,motorista FROM entregas WHERE data=? AND empresa_id=?",
                (hoje, st.session_state.empresa_id))
    dados = cur.fetchall()

    if st.button("Exportar Excel"):
        df = pd.DataFrame(dados, columns=["Cliente","Morada","Estado","Nota","Motorista"])
        df.to_excel("relatorio.xlsx", index=False)
        st.download_button("Download Excel", open("relatorio.xlsx","rb"), file_name="relatorio.xlsx")
