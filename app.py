import uuid
import streamlit as st
import pandas as pd
from datetime import datetime, date
import bcrypt

# Configuração da página
st.set_page_config(
    page_title="Fecho de Entregas",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

def unique_key():
    return str(uuid.uuid4())

# Inicializar session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'deliveries' not in st.session_state:
    st.session_state.deliveries = pd.DataFrame(columns=[
        'ID', 'Data', 'Cliente', 'Endereço', 'Status', 'Entregador', 'Observações'
    ])

# Função de autenticação simples
def authenticate(username, password):
    # Credenciais demo (em produção, usar banco de dados)
    users = {
        'admin': bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
    }
    
    if username in users:
        if bcrypt.checkpw(password.encode('utf-8'), users[username]):
            return True
    return False

# Tela de Login
def login_page():
    st.title("🔐 Login - Sistema de Fecho de Entregas")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        username = st.text_input("Usuário", key=unique_key())
        password = st.text_input("Senha", type="password", key=unique_key())
        
        if st.button("Entrar", key=unique_key()):
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")
        
        st.info("💡 Credenciais demo: admin / admin123")

# Função para adicionar entrega
def add_delivery(data, cliente, endereco, entregador, observacoes):
    new_delivery = pd.DataFrame({
        'ID': [len(st.session_state.deliveries) + 1],
        'Data': [data],
        'Cliente': [cliente],
        'Endereço': [endereco],
        'Status': ['Pendente'],
        'Entregador': [entregador],
        'Observações': [observacoes]
    })
    st.session_state.deliveries = pd.concat([st.session_state.deliveries, new_delivery], ignore_index=True)

# Função para atualizar status
def update_status(delivery_id, new_status):
    st.session_state.deliveries.loc[st.session_state.deliveries['ID'] == delivery_id, 'Status'] = new_status

# Página principal do aplicativo
def main_app():
    # Sidebar
    with st.sidebar:
        st.title("📦 Menu")
        st.write(f"Usuário: **{st.session_state.username}**")
        st.markdown("---")
        
        menu = st.radio(
            "Navegação",
            ["Dashboard", "Nova Entrega", "Gerenciar Entregas", "Relatórios"],
            key=unique_key()
        )
        
        st.markdown("---")
        if st.button("Sair", key=unique_key()):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()
    
    # Conteúdo principal
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Nova Entrega":
        show_new_delivery()
    elif menu == "Gerenciar Entregas":
        show_manage_deliveries()
    elif menu == "Relatórios":
        show_reports()

# Dashboard
def show_dashboard():
    st.title("📊 Dashboard - Fecho de Entregas")
    
    # Métricas
    total_deliveries = len(st.session_state.deliveries)
    pending = len(st.session_state.deliveries[st.session_state.deliveries['Status'] == 'Pendente'])
    completed = len(st.session_state.deliveries[st.session_state.deliveries['Status'] == 'Concluída'])
    in_progress = len(st.session_state.deliveries[st.session_state.deliveries['Status'] == 'Em Andamento'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Entregas", total_deliveries)
    with col2:
        st.metric("Pendentes", pending, delta=None)
    with col3:
        st.metric("Em Andamento", in_progress, delta=None)
    with col4:
        st.metric("Concluídas", completed, delta=None)
    
    st.markdown("---")
    
    # Tabela de entregas recentes
    st.subheader("Entregas Recentes")
    if not st.session_state.deliveries.empty:
        st.dataframe(st.session_state.deliveries.tail(10), use_container_width=True)
    else:
        st.info("Nenhuma entrega cadastrada ainda.")

# Nova entrega
def show_new_delivery():
    st.title("➕ Nova Entrega")
    
    col1, col2 = st.columns(2)
    
    with col1:
        data = st.date_input("Data da Entrega", value=date.today(), key=unique_key())
        cliente = st.text_input("Nome do Cliente", key=unique_key())
        endereco = st.text_area("Endereço de Entrega", key=unique_key())
    
    with col2:
        entregador = st.text_input("Nome do Entregador", key=unique_key())
        observacoes = st.text_area("Observações", key=unique_key())
    
    if st.button("Cadastrar Entrega", key=unique_key()):
        if cliente and endereco and entregador:
            add_delivery(data, cliente, endereco, entregador, observacoes)
            st.success(f"✅ Entrega cadastrada com sucesso! ID: {len(st.session_state.deliveries)}")
            st.balloons()
        else:
            st.error("Por favor, preencha todos os campos obrigatórios.")

# Gerenciar entregas
def show_manage_deliveries():
    st.title("📋 Gerenciar Entregas")
    
    if st.session_state.deliveries.empty:
        st.info("Nenhuma entrega cadastrada ainda.")
        return
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect(
            "Filtrar por Status",
            ["Pendente", "Em Andamento", "Concluída", "Cancelada"],
            default=["Pendente", "Em Andamento"],
            key=unique_key()
        )
    
    # Aplicar filtros
    filtered_df = st.session_state.deliveries[st.session_state.deliveries['Status'].isin(status_filter)]
    
    st.dataframe(filtered_df, use_container_width=True)
    
    # Atualizar status
    st.markdown("---")
    st.subheader("Atualizar Status de Entrega")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        delivery_id = st.number_input("ID da Entrega", min_value=1, max_value=len(st.session_state.deliveries), step=1, key=unique_key())
    with col2:
        new_status = st.selectbox("Novo Status", ["Pendente", "Em Andamento", "Concluída", "Cancelada"], key=unique_key())
    with col3:
        st.write("")  # Espaçamento
        st.write("")  # Espaçamento
        if st.button("Atualizar", key=unique_key()):
            update_status(delivery_id, new_status)
            st.success(f"Status da entrega {delivery_id} atualizado para {new_status}!")
            st.rerun()

# Relatórios
def show_reports():
    st.title("📈 Relatórios")
    
    if st.session_state.deliveries.empty:
        st.info("Nenhuma entrega cadastrada ainda.")
        return
    
    st.subheader("Exportar Dados")
    
    # Exportar para Excel
    if st.button("Exportar para Excel", key=unique_key()):
        # Criar arquivo Excel
        output_file = f"/tmp/entregas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        st.session_state.deliveries.to_excel(output_file, index=False)
        
        with open(output_file, 'rb') as f:
            st.download_button(
                label="📥 Download Excel",
                data=f,
                file_name=f"entregas_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=unique_key()
            )
    
    st.markdown("---")
    st.subheader("Visualização dos Dados")
    st.dataframe(st.session_state.deliveries, use_container_width=True)

# Fluxo principal
if not st.session_state.authenticated:
    login_page()
else:
    main_app()
