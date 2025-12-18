import streamlit as st
import sqlite3
import os
import json
from datetime import datetime, date
import bcrypt
import pandas as pd
from streamlit_drawable_canvas import st_canvas
import yagmail

# ===============================
# CONFIGURAÇÃO BASE
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "entregas.db")
DB_FLAG = os.path.join(BASE_DIR, "db_initialized.flag")

st.set_page_config(page_title="Intercourier Entregas", layout="centered")

# ===============================
# DATABASE
# ===============================
def get_db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con

def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS utilizadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password BLOB,
        empresa_id INTEGER,
        role TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS entregas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        morada TEXT,
        email TEXT,
        estado TEXT,
        nota TEXT,
        data TEXT,
        motorista TEXT,
        empresa_id INTEGER,
        foto BLOB,
        assinatura TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        timestamp TEXT,
        success INTEGER
    )""")

    cur.execute("INSERT OR IGNORE INTO empresas (nome) VALUES (?)", ("Empresa Demo",))
    cur.execute("SELECT id FROM empresas WHERE nome=?", ("Empresa Demo",))
    empresa_id = cur.fetchone()[0]

    pwd = bcrypt.hashpw("admin".encode(), bcrypt.gensalt())

    cur.execute("""
    INSERT OR IGNORE INTO utilizadores
    (username, password, empresa_id, role)
    VALUES (?, ?, ?, ?)
    """, ("admin", pwd, empresa_id, "admin"))

    con.commit()
    con.close()

if not os.path.exists(DB_FLAG):
    init_db()
    open(DB_FLAG, "w").close()

# ===============================
# SESSION STATE
# ===============================
if "login" not in st.session_state:
    st.session_state.login = False

# ===============================
# LOGIN / REGISTO
# ===============================
st.title("📦 Intercourier Entregas")

if not st.session_state.login:
    tab1, tab2 = st.tabs(["Login", "Registo"])

    with tab1:
        u = st.text_input("Utilizador")
        p = st.text_input("Password", type="password")

        if st.button("Entrar"):
            con = get_db()
            cur = con.cursor()
            cur.execute("SELECT password, empresa_id, role FROM utilizadores WHERE username=?", (u.lower(),))
            user = cur.fetchone()

            if user and bcrypt.checkpw(p.encode(), user[0]):
                cur.execute(
                    "INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 1)",
                    (u, datetime.now().isoformat())
                )
                st.session_state.login = True
                st.session_state.utilizador = u.lower()
                st.session_state.empresa_id = user[1]
                st.session_state.role = user[2]
                con.commit()
                con.close()
                st.rerun()
            else:
                cur.execute(
                    "INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 0)",
                    (u, datetime.now().isoformat())
                )
                con.commit()
                con.close()
                st.error("Credenciais inválidas")

    with tab2:
        nu = st.text_input("Novo utilizador")
        np = st.text_input("Password", type="password")
        ncp = st.text_input("Confirmar Password", type="password")

        if st.button("Registar"):
            nu = nu.strip().lower()

            if not nu:
                st.error("Username obrigatório")
            elif np != ncp:
                st.error("Passwords não coincidem")
            elif len(np) < 6:
                st.error("Password demasiado curta")
            else:
                con = get_db()
                cur = con.cursor()
                cur.execute("SELECT id FROM utilizadores WHERE username=?", (nu,))
                if cur.fetchone():
                    st.error("Username já existe")
                else:
                    cur.execute("SELECT id FROM empresas WHERE nome=?", ("Empresa Demo",))
                    empresa_id = cur.fetchone()[0]
                    pwd = bcrypt.hashpw(np.encode(), bcrypt.gensalt())
                    cur.execute(
                        "INSERT INTO utilizadores (username,password,empresa_id,role) VALUES (?,?,?,?)",
                        (nu, pwd, empresa_id, "motorista")
                    )
                    con.commit()
                    con.close()
                    st.success("Utilizador criado. Faça login.")

    st.stop()

# ===============================
# MENU
# ===============================
is_admin = st.session_state.role == "admin"

menu = st.sidebar.selectbox(
    "Menu",
    ["Nova Entrega", "Fechar Dia", "Administração"] if is_admin else ["Nova Entrega", "Fechar Dia"]
)

# ===============================
# ADMIN
# ===============================
if menu == "Administração" and is_admin:
    st.subheader("Criar Motorista")
    nu = st.text_input("Utilizador")
    np = st.text_input("Password", type="password")

    if st.button("Criar"):
        nu = nu.strip().lower()
        pwd = bcrypt.hashpw(np.encode(), bcrypt.gensalt())
        con = get_db()
        cur = con.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO utilizadores (username,password,empresa_id,role) VALUES (?,?,?,?)",
            (nu, pwd, st.session_state.empresa_id, "motorista")
        )
        con.commit()
        con.close()
        st.success("Motorista criado")

# ===============================
# NOVA ENTREGA
# ===============================
if menu == "Nova Entrega":
    cliente = st.text_input("Cliente")
    morada = st.text_input("Morada")
    email_cliente = st.text_input("Email do Cliente")
    estado = st.selectbox("Estado", ["Entregue", "Não Entregue"])
    nota = st.text_area("Nota")

    foto = st.camera_input("Foto da entrega")
    assinatura = st_canvas(height=150, width=300, drawing_mode="freedraw")

    if st.button("Guardar Entrega"):
        foto_bytes = foto.getvalue() if foto else None
        assinatura_json = json.dumps(assinatura.json_data) if assinatura and assinatura.json_data else None

        con = get_db()
        cur = con.cursor()
        cur.execute("""
        INSERT INTO entregas
        (cliente,morada,email,estado,nota,data,motorista,empresa_id,foto,assinatura)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            cliente,
            morada,
            email_cliente,
            estado,
            nota,
            datetime.now().isoformat(),
            st.session_state.utilizador,
            st.session_state.empresa_id,
            foto_bytes,
            assinatura_json
        ))
        con.commit()
        con.close()
        st.success("Entrega registada")

# ===============================
# FECHAR DIA
# ===============================
if menu == "Fechar Dia":
    hoje = date.today().isoformat()
    con = get_db()
    cur = con.cursor()
    cur.execute("""
    SELECT cliente,morada,estado,nota,motorista
    FROM entregas
    WHERE data LIKE ? AND empresa_id=?
    """, (f"{hoje}%", st.session_state.empresa_id))
    dados = cur.fetchall()
    con.close()

    if dados:
        df = pd.DataFrame(dados, columns=["Cliente","Morada","Estado","Nota","Motorista"])
        st.dataframe(df)

        if st.button("Exportar Excel"):
            file_path = os.path.join(BASE_DIR, "relatorio.xlsx")
            df.to_excel(file_path, index=False)
            st.download_button("Download Excel", open(file_path, "rb"), file_name="relatorio.xlsx")
    else:
        st.info("Sem entregas hoje")
