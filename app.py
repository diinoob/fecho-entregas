import streamlit as st
import sqlite3
import os
from datetime import datetime, date
import bcrypt
import pandas as pd
from streamlit_drawable_canvas import st_canvas
import io

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
        telefone TEXT
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
    pwd = bcrypt.hashpw("Interadmin".encode(), bcrypt.gensalt())
    cur.execute("""INSERT OR IGNORE INTO utilizadores
        (username, password, empresa_id, role)
        VALUES (?, ?, ?, ?)""", ("interadmin00", pwd, empresa_id, "admin"))
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
                cur.execute("INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 1)", (u, datetime.now().isoformat()))
                st.session_state.login = True
                st.session_state.utilizador = u.lower()
                st.session_state.empresa_id = user[1]
                st.session_state.role = user[2]
                con.commit()
                con.close()
                st.rerun()
            else:
                cur.execute("INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 0)", (u, datetime.now().isoformat()))
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
                    cur.execute("INSERT INTO utilizadores (username,password,empresa_id,role,telefone) VALUES (?,?,?,?,?)", (nu, pwd, empresa_id, "entregador", telefone))
                    con.commit()
                    con.close()
                    st.success("Utilizador criado. Faça login.")
    st.stop()

# ===============================
# MENU
# ===============================
is_admin = st.session_state.role == "admin"
menu = st.sidebar.selectbox("Menu", ["Nova Entrega","Minhas Entregas","Dashboard","Fechar Dia","Administração"] if is_admin else ["Nova Entrega","Minhas Entregas","Dashboard","Fechar Dia"])

# ===============================
# FUNÇÕES
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

# ===============================
# NOVA ENTREGA
# ===============================
if menu == "Nova Entrega":
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT username FROM utilizadores WHERE role='entregador' AND empresa_id=?", (st.session_state.empresa_id,))
    entregadores = [x[0] for x in cur.fetchall()]
    entregador = st.selectbox("Entregador", entregadores)
    cliente = st.text_input("Cliente")
    morada = st.text_input("Morada")
    email_cliente = st.text_input("Email do Cliente")
    codigo_rastreio = st.text_input("Código de rastreio")
    estado = st.selectbox("Estado", ["Entregue", "Não Entregue"])
    nota = st.text_area("Nota")
    foto = st.file_uploader("Foto da entrega", type=["png","jpg","jpeg"])
    assinatura = st_canvas(height=150, width=300, drawing_mode="freedraw")
    if st.button("Guardar Entrega"):
        foto_bytes = foto.read() if foto else None
        assinatura_bytes = None
        cur.execute("""INSERT INTO entregas
            (cliente,morada,email,estado,nota,data,entregador,codigo_rastreamento,empresa_id,foto,assinatura)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (cliente, morada, email_cliente, estado, nota, datetime.now().isoformat(), entregador, codigo_rastreio, st.session_state.empresa_id, foto_bytes, assinatura_bytes)
        )
        con.commit()
        con.close()
        st.success("Entrega guardada")

# ===============================
# MINHAS ENTREGAS
# ===============================
if menu == "Minhas Entregas":
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, cliente, morada, estado, nota, data FROM entregas WHERE entregador=? AND empresa_id=?", (st.session_state.utilizador, st.session_state.empresa_id))
    entregas = cur.fetchall()
    for e in entregas:
        st.write(f"Cliente: {e[1]} | Morada: {e[2]} | Estado: {e[3]} | Nota: {e[4]} | Data: {e[5]}")
    con.close()

# ===============================
# DASHBOARD
# ===============================
if menu == "Dashboard":
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT username FROM utilizadores WHERE role='entregador' AND empresa_id=?", (st.session_state.empresa_id,))
    entregadores = [x[0] for x in cur.fetchall()]
    for e in entregadores:
        cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado='Entregue' AND empresa_id=?", (e, st.session_state.empresa_id))
        realizadas = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado!='Entregue' AND empresa_id=?", (e, st.session_state.empresa_id))
        pendentes = cur.fetchone()[0]
        st.write(f"{e} → Realizadas: {realizadas} | Pendentes: {pendentes}")
    con.close()

# ===============================
# FECHAR DIA
# ===============================
if menu == "Fechar Dia":
    hoje = date.today().isoformat()
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT cliente,morada,estado,nota,entregador,codigo_rastreamento FROM entregas WHERE data LIKE ? AND empresa_id=?", (f"{hoje}%", st.session_state.empresa_id))
    dados = cur.fetchall()
    if dados:
        df = pd.DataFrame(dados, columns=["Cliente","Morada","Estado","Nota","Entregador","Código Rastreio"])
        df.to_excel("relatorio_dia.xlsx", index=False)
        st.download_button("Download Excel do Dia", open("relatorio_dia.xlsx","rb"), file_name="relatorio_dia.xlsx")
    else:
        st.info("Nenhuma entrega hoje.")

# ===============================
# ADMINISTRAÇÃO
# ===============================
if menu == "Administração" and is_admin:
    st.subheader("Entregadores")
    con = get_db()
    cur = con.cursor()
    # Criar entregador
    st.write("Criar novo entregador")
    novo_user = st.text_input("Username")
    nova_pass = st.text_input("Password", type="password")
    telefone = st.text_input("Telefone")
    if st.button("Criar Entregador"):
        pwd = bcrypt.hashpw(nova_pass.encode(), bcrypt.gensalt())
        cur.execute("INSERT INTO utilizadores (username,password,empresa_id,role,telefone) VALUES (?,?,?,?,?)",
                    (novo_user, pwd, st.session_state.empresa_id, "entregador", telefone))
        con.commit()
        st.success("Entregador criado")
    # Listar entregadores e estatísticas
    cur.execute("SELECT username, telefone FROM utilizadores WHERE role='entregador' AND empresa_id=?", (st.session_state.empresa_id,))
    entregadores = cur.fetchall()
    for e in entregadores:
        cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado='Entregue' AND empresa_id=?", (e[0], st.session_state.empresa_id))
        realizadas = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado!='Entregue' AND empresa_id=?", (e[0], st.session_state.empresa_id))
        pendentes = cur.fetchone()[0]
        st.write(f"{e[0]} ({e[1]}) → Realizadas: {realizadas} | Pendentes: {pendentes}")
        if st.button(f"Eliminar {e[0]}"):
            cur.execute("DELETE FROM utilizadores WHERE username=? AND role='entregador'", (e[0],))
            con.commit()
            st.experimental_rerun()
    con.close()
