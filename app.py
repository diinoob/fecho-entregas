import streamlit as st
import sqlite3
import os
from datetime import datetime, date
import bcrypt
import pandas as pd
from streamlit_drawable_canvas import st_canvas
import io
from PIL import Image

# ===============================
# CONFIGURAÇÃO
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "entregas.db")
st.set_page_config(page_title="Intercourier Entregas", layout="wide")

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
    # Tabelas
    cur.execute("""CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS utilizadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password BLOB,
        empresa_id INTEGER,
        role TEXT,
        telefone TEXT DEFAULT ''
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS entregas (
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
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        timestamp TEXT,
        success INTEGER
    )""")
    # Empresa demo
    cur.execute("INSERT OR IGNORE INTO empresas (nome) VALUES (?)", ("Empresa Demo",))
    cur.execute("SELECT id FROM empresas WHERE nome=?", ("Empresa Demo",))
    empresa_id = cur.fetchone()[0]
    # Admin padrão
    cur.execute("SELECT id FROM utilizadores WHERE username='interadmin00'")
    if not cur.fetchone():
        pwd = bcrypt.hashpw("Interadmin".encode(), bcrypt.gensalt())
        cur.execute("""INSERT INTO utilizadores (username, password, empresa_id, role, telefone)
                       VALUES (?, ?, ?, ?, ?)""", ("interadmin00", pwd, empresa_id, "admin", ""))
    con.commit()
    con.close()

init_db()

# ===============================
# SESSION STATE
# ===============================
if "login" not in st.session_state:
    st.session_state.login = False

# ===============================
# LOGIN / REGISTO
# ===============================
if not st.session_state.login:
    tab1, tab2 = st.tabs(["Login", "Registo"])

    with tab1:
        u = st.text_input("Utilizador", key="login_username")
        p = st.text_input("Password", type="password", key="login_password")
        if st.button("Entrar", key="login_button"):
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
        nu = st.text_input("Novo utilizador", key="register_username")
        np = st.text_input("Password", type="password", key="register_password")
        ncp = st.text_input("Confirmar Password", type="password", key="register_confirm")
        telefone = st.text_input("Contacto telefónico", key="register_telefone")
        if st.button("Registar", key="register_button"):
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
                        "INSERT INTO utilizadores (username,password,empresa_id,role,telefone) VALUES (?,?,?,?,?)",
                        (nu, pwd, empresa_id, "entregador", telefone)
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
    ["Nova Entrega","Minhas Entregas","Dashboard","Fechar Dia","Administração"] if is_admin else ["Nova Entrega","Minhas Entregas","Dashboard","Fechar Dia"]
)

# ===============================
# FUNÇÕES AUXILIARES
# ===============================
def notificar_entregas_pendentes():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT username, telefone FROM utilizadores WHERE role='entregador' AND empresa_id=?", (st.session_state.empresa_id,))
    entregadores = cur.fetchall()
    for e in entregadores:
        cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado!='Entregue' AND empresa_id=?", (e[0], st.session_state.empresa_id))
        pendentes = cur.fetchone()[0]
        if pendentes > 0:
            print(f"Notificação: {e[0]} ({e[1]}) tem {pendentes} entregas pendentes")
    con.close()

def salvar_entrega(cliente, morada, email_cliente, estado, nota, entregador, codigo_rastreamento, foto, assinatura):
    assinatura_bytes = None
    if assinatura and assinatura.image_data is not None:
        im = Image.fromarray(assinatura.image_data.astype('uint8'))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        assinatura_bytes = buf.getvalue()
    foto_bytes = foto.read() if foto else None

    con = get_db()
    cur = con.cursor()
    cur.execute("""INSERT INTO entregas
        (cliente,morada,email,estado,nota,data,entregador,codigo_rastreamento,empresa_id,foto,assinatura)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        cliente, morada, email_cliente, estado, nota,
        datetime.now().isoformat(), entregador, codigo_rastreamento,
        st.session_state.empresa_id, foto_bytes, assinatura_bytes
    ))
    con.commit()
    con.close()
    st.success("Entrega guardada")
    notificar_entregas_pendentes()

# ===============================
# NOVA ENTREGA
# ===============================
if menu == "Nova Entrega":
    st.subheader("Nova Entrega")
    cliente = st.text_input("Cliente")
    morada = st.text_input("Morada")
    email_cliente = st.text_input("Email do Cliente")
    estado = st.selectbox("Estado", ["Entregue", "Não Entregue"])
    nota = st.text_area("Nota")
    entregador = st.selectbox("Entregador", [u[0] for u in get_db().cursor().execute("SELECT username FROM utilizadores WHERE role='entregador' AND empresa_id=?", (st.session_state.empresa_id,)).fetchall()])
    codigo_rastreamento = st.text_input("Código de Rastreamento (opcional)")
    foto = st.file_uploader("Foto da entrega (opcional)", type=["png","jpg","jpeg"])
    assinatura = st_canvas(height=150, width=300, drawing_mode="freedraw")
    if st.button("Guardar Entrega"):
        salvar_entrega(cliente, morada, email_cliente, estado, nota, entregador, codigo_rastreamento, foto, assinatura)

# ===============================
# MINHAS ENTREGAS
# ===============================
if menu == "Minhas Entregas":
    st.subheader("Minhas Entregas")
    con = get_db()
    df = pd.read_sql_query("SELECT * FROM entregas WHERE entregador=? AND empresa_id=?", con, params=(st.session_state.utilizador, st.session_state.empresa_id))
    con.close()
    st.dataframe(df)

# ===============================
# DASHBOARD
# ===============================
if menu == "Dashboard" and is_admin:
    st.subheader("Dashboard de Entregadores")
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT username FROM utilizadores WHERE role='entregador' AND empresa_id=?", (st.session_state.empresa_id,))
    entregadores = [e[0] for e in cur.fetchall()]
    for e in entregadores:
        cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado='Entregue' AND empresa_id=?", (e, st.session_state.empresa_id))
        realizadas = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado!='Entregue' AND empresa_id=?", (e, st.session_state.empresa_id))
        pendentes = cur.fetchone()[0]
        st.write(f"Entregador: {e} | Entregas Realizadas: {realizadas} | Pendentes: {pendentes}")
    con.close()

# ===============================
# FECHAR DIA
# ===============================
if menu == "Fechar Dia":
    st.subheader("Fechar Dia")
    hoje = date.today().isoformat()
    con = get_db()
    df = pd.read_sql_query("SELECT * FROM entregas WHERE date(data)=? AND empresa_id=?", con, params=(hoje, st.session_state.empresa_id))
    con.close()
    if st.button("Exportar Excel"):
        df.to_excel("relatorio.xlsx", index=False)
        with open("relatorio.xlsx", "rb") as f:
            st.download_button("Download Excel", f, file_name="relatorio.xlsx")

# ===============================
# ADMINISTRAÇÃO
# ===============================
if menu == "Administração" and is_admin:
    st.subheader("Administração")
    # Criar Entregador
    st.write("Criar Entregador")
    nu = st.text_input("Nome de utilizador (entregador)", key="admin_nu")
    np = st.text_input("Password", type="password", key="admin_np")
    telefone = st.text_input("Contacto telefónico", key="admin_telefone")
    if st.button("Criar Entregador", key="admin_button"):
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT id FROM utilizadores WHERE username=?", (nu,))
        if cur.fetchone():
            st.error("Username já existe")
        else:
            cur.execute("INSERT INTO utilizadores (username,password,empresa_id,role,telefone) VALUES (?,?,?,?,?)", (nu,bcrypt.hashpw(np.encode(),bcrypt.gensalt()),st.session_state.empresa_id,"entregador",telefone))
            con.commit()
            con.close()
            st.success("Entregador criado")
    # Listar Entregadores
    st.write("Entregadores Registrados")
    con = get_db()
    df_entregadores = pd.read_sql_query("SELECT username, telefone FROM utilizadores WHERE role='entregador' AND empresa_id=?", con, params=(st.session_state.empresa_id,))
    con.close()
    st.dataframe(df_entregadores)
