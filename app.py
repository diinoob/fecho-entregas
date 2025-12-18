import streamlit as st
import sqlite3
import os
from datetime import datetime, date
import bcrypt
import pandas as pd
from streamlit_drawable_canvas import st_canvas
import io

# ===============================
# CONFIGURAÇÃO GERAL
# ===============================
st.set_page_config(page_title="Intercourier Corvo", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "entregas.db")
EMPRESA_NOME = "Intercourier Corvo"

# ===============================
# BASE DE DADOS
# ===============================
def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return column in [c[1] for c in cur.fetchall()]

def init_db():
    con = get_db()
    cur = con.cursor()

    # EMPRESAS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE
    )
    """)

    # UTILIZADORES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS utilizadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password BLOB,
        empresa_id INTEGER,
        role TEXT
    )
    """)

    if not column_exists(cur, "utilizadores", "telefone"):
        cur.execute("ALTER TABLE utilizadores ADD COLUMN telefone TEXT")

    # ENTREGAS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entregas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        morada TEXT,
        email TEXT,
        estado TEXT,
        nota TEXT,
        data TEXT,
        entregador TEXT,
        codigo_rastreamento TEXT,
        empresa_id INTEGER,
        foto BLOB,
        assinatura BLOB
    )
    """)

    # EMPRESA FIXA
    cur.execute("INSERT OR IGNORE INTO empresas (nome) VALUES (?)", (EMPRESA_NOME,))
    cur.execute("SELECT id FROM empresas WHERE nome=?", (EMPRESA_NOME,))
    empresa_id = cur.fetchone()[0]

    # ADMIN DEFAULT
    pwd = bcrypt.hashpw("Interadmin".encode(), bcrypt.gensalt())
    cur.execute("""
    INSERT OR IGNORE INTO utilizadores (username,password,empresa_id,role,telefone)
    VALUES (?,?,?,?,?)
    """, ("interadmin00", pwd, empresa_id, "admin", ""))

    con.commit()
    con.close()

init_db()

# ===============================
# SESSION
# ===============================
if "login" not in st.session_state:
    st.session_state.login = False

# ===============================
# LOGIN / REGISTO
# ===============================
if not st.session_state.login:
    tab1, tab2 = st.tabs(["Login", "Registo Entregador"])

    with tab1:
        u = st.text_input("Utilizador")
        p = st.text_input("Password", type="password")
        if st.button("Entrar"):
            con = get_db()
            cur = con.cursor()
            cur.execute("SELECT password, empresa_id, role FROM utilizadores WHERE username=?", (u,))
            user = cur.fetchone()
            con.close()

            if user and bcrypt.checkpw(p.encode(), user[0]):
                st.session_state.login = True
                st.session_state.utilizador = u
                st.session_state.empresa_id = user[1]
                st.session_state.role = user[2]
                st.rerun()
            else:
                st.error("Credenciais inválidas")

    with tab2:
        nu = st.text_input("Novo entregador")
        np = st.text_input("Password", type="password")
        telefone = st.text_input("Telefone")
        if st.button("Registar"):
            con = get_db()
            cur = con.cursor()
            pwd = bcrypt.hashpw(np.encode(), bcrypt.gensalt())
            try:
                cur.execute("""
                INSERT INTO utilizadores (username,password,empresa_id,role,telefone)
                VALUES (?,?,?,?,?)
                """, (nu, pwd, 1, "entregador", telefone))
                con.commit()
                st.success("Entregador criado")
            except:
                st.error("Utilizador já existe")
            con.close()

    st.stop()

# ===============================
# MENU
# ===============================
is_admin = st.session_state.role == "admin"

menu = st.sidebar.selectbox(
    "Menu",
    ["Nova Entrega", "Minhas Entregas", "Fechar Dia", "Administração"] if is_admin
    else ["Nova Entrega", "Minhas Entregas", "Fechar Dia"]
)

# ===============================
# NOVA ENTREGA
# ===============================
if menu == "Nova Entrega":
    st.header("📦 Nova Entrega")

    con = get_db()
    df_entregadores = pd.read_sql_query(
        "SELECT username FROM utilizadores WHERE role='entregador' AND empresa_id=?",
        con, params=(st.session_state.empresa_id,))
    con.close()

    cliente = st.text_input("Cliente")
    morada = st.text_input("Morada")
    email = st.text_input("Email do Cliente")
    entregador = st.selectbox("Entregador", df_entregadores["username"].tolist())
    codigo = st.text_input("Código de Rastreamento (UPS)")
    estado = st.selectbox("Estado", ["Entregue", "Pendente"])
    nota = st.text_area("Nota")

    foto = st.camera_input("Foto (opcional)")
    assinatura = st_canvas(height=150, width=300)

    if st.button("Guardar Entrega"):
        con = get_db()
        cur = con.cursor()
        cur.execute("""
        INSERT INTO entregas
        (cliente,morada,email,estado,nota,data,entregador,codigo_rastreamento,empresa_id,foto,assinatura)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            cliente, morada, email, estado, nota,
            datetime.now().isoformat(),
            entregador, codigo, st.session_state.empresa_id,
            foto.getvalue() if foto else None,
            assinatura.image_data.tobytes() if assinatura.image_data is not None else None
        ))
        con.commit()
        con.close()
        st.success("Entrega registada")

# ===============================
# MINHAS ENTREGAS
# ===============================
if menu == "Minhas Entregas":
    st.header("📋 Minhas Entregas")

    con = get_db()
    df = pd.read_sql_query("""
    SELECT id, cliente, morada, estado, nota, data
    FROM entregas
    WHERE entregador=? AND empresa_id=?
    """, con, params=(st.session_state.utilizador, st.session_state.empresa_id))
    con.close()

    st.dataframe(df)

    if st.button("Fechar TODAS como Entregues"):
        con = get_db()
        cur = con.cursor()
        cur.execute("""
        UPDATE entregas SET estado='Entregue'
        WHERE entregador=? AND empresa_id=?
        """, (st.session_state.utilizador, st.session_state.empresa_id))
        con.commit()
        con.close()
        st.success("Todas fechadas")
        st.rerun()

# ===============================
# FECHAR DIA
# ===============================
if menu == "Fechar Dia":
    st.header("📅 Fecho do Dia")

    hoje = date.today().isoformat()
    con = get_db()
    df = pd.read_sql_query("""
    SELECT cliente, morada, estado, nota, entregador
    FROM entregas
    WHERE data LIKE ? AND empresa_id=?
    """, con, params=(f"{hoje}%", st.session_state.empresa_id))
    con.close()

    st.dataframe(df)

    output = io.BytesIO()
    df.to_excel(output, index=False)
    st.download_button(
        "📥 Download Excel",
        output.getvalue(),
        "fecho_dia.xlsx"
    )

# ===============================
# ADMINISTRAÇÃO
# ===============================
if menu == "Administração" and is_admin:
    st.header("⚙️ Administração")

    con = get_db()
    df_entregadores = pd.read_sql_query("""
    SELECT u.username,
           u.telefone,
           SUM(CASE WHEN e.estado='Entregue' THEN 1 ELSE 0 END) as entregues,
           SUM(CASE WHEN e.estado!='Entregue' THEN 1 ELSE 0 END) as pendentes
    FROM utilizadores u
    LEFT JOIN entregas e ON u.username = e.entregador
    WHERE u.role='entregador' AND u.empresa_id=?
    GROUP BY u.username
    """, con, params=(st.session_state.empresa_id,))
    con.close()

    st.dataframe(df_entregadores)

    st.subheader("Eliminar Entregador")
    eliminar = st.selectbox("Selecionar", df_entregadores["username"].tolist())
    if st.button("Eliminar"):
        con = get_db()
        cur = con.cursor()
        cur.execute("DELETE FROM utilizadores WHERE username=?", (eliminar,))
        cur.execute("DELETE FROM entregas WHERE entregador=?", (eliminar,))
        con.commit()
        con.close()
        st.success("Entregador eliminado")
        st.rerun()
