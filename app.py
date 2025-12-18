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
st.set_page_config(page_title="Intercourier Corvo", layout="wide")

# ===============================
# DATABASE
# ===============================
def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_db() as con:
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
        cur.execute("INSERT OR IGNORE INTO empresas (nome) VALUES (?)", ("Intercourier Corvo",))
        cur.execute("SELECT id FROM empresas WHERE nome=?", ("Intercourier Corvo",))
        empresa_id = cur.fetchone()[0]
        # Admin padrão
        pwd = bcrypt.hashpw("Interadmin".encode(), bcrypt.gensalt())
        cur.execute("""INSERT OR IGNORE INTO utilizadores
            (username, password, empresa_id, role, telefone)
            VALUES (?, ?, ?, ?, ?)""", ("interadmin00", pwd, empresa_id, "admin", ""))

def initialize_session_state():
    if "login" not in st.session_state:
        st.session_state.login = False
    if "utilizador" not in st.session_state:
        st.session_state.utilizador = None
    if "empresa_id" not in st.session_state:
        st.session_state.empresa_id = None
    if "role" not in st.session_state:
        st.session_state.role = None

def validate_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode(), hashed)
    except:
        return False

init_db()
initialize_session_state()

# ===============================
# LOGIN / REGISTO
# ===============================
if not st.session_state.login:
    tab1, tab2 = st.tabs(["Login", "Registo"])

    with tab1:
        u = st.text_input("Utilizador", key="login_username")
        p = st.text_input("Password", type="password", key="login_password")
        if st.button("Entrar", key="login_button"):
            with get_db() as con:
                cur = con.cursor()
                cur.execute("SELECT password, empresa_id, role FROM utilizadores WHERE username=?", (u.lower(),))
                user = cur.fetchone()
                if user and validate_password(p, user[0]):
                    cur.execute(
                        "INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 1)",
                        (u, datetime.now().isoformat())
                    )
                    st.session_state.login = True
                    st.session_state.utilizador = u.lower()
                    st.session_state.empresa_id = user[1]
                    st.session_state.role = user[2]
                    st.experimental_rerun()
                else:
                    cur.execute(
                        "INSERT INTO login_logs (username, timestamp, success) VALUES (?, ?, 0)",
                        (u, datetime.now().isoformat())
                    )
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
                with get_db() as con:
                    cur = con.cursor()
                    cur.execute("SELECT id FROM utilizadores WHERE username=?", (nu,))
                    if cur.fetchone():
                        st.error("Username já existe")
                    else:
                        cur.execute("SELECT id FROM empresas WHERE nome=?", ("Intercourier Corvo",))
                        empresa_id = cur.fetchone()[0]
                        pwd = bcrypt.hashpw(np.encode(), bcrypt.gensalt())
                        cur.execute(
                            "INSERT INTO utilizadores (username,password,empresa_id,role,telefone) VALUES (?,?,?,?,?)",
                            (nu, pwd, empresa_id, "entregador", telefone)
                        )
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
# FUNCIONALIDADES
# ===============================
with get_db() as con:
    cur = con.cursor()

    # Nova Entrega
    if menu == "Nova Entrega":
        st.subheader("Nova Entrega")
        cliente = st.text_input("Cliente")
        morada = st.text_input("Morada")
        email_cliente = st.text_input("Email do Cliente")
        estado = st.selectbox("Estado", ["Entregue", "Não Entregue"])
        nota = st.text_area("Nota")
        entregador = st.selectbox("Entregador", [r[0] for r in cur.execute("SELECT username FROM utilizadores WHERE role='entregador' AND empresa_id=", (st.session_state.empresa_id,)).fetchall()])
        codigo_rastreio = st.text_input("Código Rastreio")
        foto = st.file_uploader("Foto da entrega", type=["jpg","png"])
        assinatura = st_canvas(height=150, width=300, drawing_mode="freedraw")

        if st.button("Guardar Entrega"):
            foto_bytes = foto.read() if foto else None
            assinatura_bytes = assinatura.image_data.tobytes() if assinatura and assinatura.image_data is not None else None
            cur.execute("""INSERT INTO entregas
                (cliente,morada,email,estado,nota,data,entregador,codigo_rastreamento,empresa_id,foto,assinatura)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (cliente, morada, email_cliente, estado, nota, datetime.now().isoformat(),
                 entregador, codigo_rastreio, st.session_state.empresa_id, foto_bytes, assinatura_bytes)
            )
            st.success("Entrega guardada com sucesso.")

    # Minhas Entregas
    if menu == "Minhas Entregas":
        st.subheader("Minhas Entregas")
        df = pd.read_sql_query("SELECT id, cliente, morada, estado, nota, data FROM entregas WHERE entregador=? AND empresa_id=",
                               con, params=(st.session_state.utilizador, st.session_state.empresa_id))
        st.dataframe(df)
        if st.button("Marcar todas como entregues"):
            cur.execute("UPDATE entregas SET estado='Entregue' WHERE entregador=? AND estado!='Entregue' AND empresa_id=",
                        (st.session_state.utilizador, st.session_state.empresa_id))
            st.success("Todas as entregas foram marcadas como entregues.")

    # Dashboard / Administração
    if menu == "Dashboard" or (menu=="Administração" and is_admin):
        st.subheader("Dashboard / Administração")
        df_entregadores = pd.read_sql_query("SELECT id, username, telefone FROM utilizadores WHERE role='entregador' AND empresa_id=",
                                            con, params=(st.session_state.empresa_id,))
        for index, row in df_entregadores.iterrows():
            st.write(f"Entregador: {row['username']} - Telefone: {row['telefone']}")
            pendentes = cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado!='Entregue' AND empresa_id=",
                                    (row['username'], st.session_state.empresa_id)).fetchone()[0]
            entregues = cur.execute("SELECT COUNT(*) FROM entregas WHERE entregador=? AND estado='Entregue' AND empresa_id=",
                                   (row['username'], st.session_state.empresa_id)).fetchone()[0]
            st.write(f"Entregas pendentes: {pendentes}, Entregas efetuadas: {entregues}")
            if st.button(f"Eliminar {row['username']}", key=f"del_{row['username']}"):
                cur.execute("DELETE FROM utilizadores WHERE id=", (row['id'],))
                cur.execute("DELETE FROM entregas WHERE entregador=", (row['username'],))

    # Fechar Dia
    if menu == "Fechar Dia":
        st.subheader("Fechar Dia")
        hoje = date.today().isoformat()
        df = pd.read_sql_query("SELECT cliente,morada,estado,nota,entregador FROM entregas WHERE date(data)=? AND empresa_id=",
                               con, params=(hoje, st.session_state.empresa_id))
        st.dataframe(df)
        if st.button("Exportar Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name="Relatório")
                writer.save()
                processed_data = output.getvalue()
            st.download_button(label="Baixar Relatório Excel",
                               data=processed_data,
                               file_name=f"relatorio_{hoje}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")