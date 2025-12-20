# 📦 Fecho de Entregas

Sistema de gerenciamento e controle de entregas desenvolvido com Streamlit.

## 📋 Descrição

O **Fecho de Entregas** é uma aplicação web para gerenciar e acompanhar entregas, permitindo:
- Cadastro de novas entregas
- Acompanhamento de status (Pendente, Em Andamento, Concluída, Cancelada)
- Dashboard com métricas em tempo real
- Relatórios e exportação de dados para Excel
- Sistema de autenticação

## 🚀 Funcionalidades

- **Dashboard**: Visão geral com métricas e entregas recentes
- **Nova Entrega**: Cadastro rápido de entregas com informações do cliente, endereço e entregador
- **Gerenciar Entregas**: Visualização e atualização de status das entregas
- **Relatórios**: Exportação de dados para Excel e visualização completa

## 🔧 Tecnologias

- Python 3.11
- Streamlit (Interface web)
- Pandas (Manipulação de dados)
- Bcrypt (Autenticação segura)
- OpenPyXL (Exportação Excel)
- Streamlit-drawable-canvas (Recursos de assinatura - futuro)

## 📦 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/diinoob/fecho-entregas.git
cd fecho-entregas
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute a aplicação:
```bash
streamlit run app.py
```

## 🔐 Credenciais de Acesso

Para acessar o sistema, use as credenciais demo:
- **Usuário**: admin
- **Senha**: admin123

> ⚠️ **Nota**: Em produção, as credenciais devem ser armazenadas em um banco de dados seguro.

## 🐳 Desenvolvimento com Devcontainer

Este projeto está configurado para uso com devcontainers:

1. Abra o projeto no VS Code
2. Quando solicitado, reabra no container
3. A aplicação será iniciada automaticamente na porta 8501

## 📝 Uso

1. Faça login com as credenciais fornecidas
2. Use o menu lateral para navegar entre as funcionalidades
3. Cadastre novas entregas através do menu "Nova Entrega"
4. Acompanhe o status no Dashboard
5. Gerencie e atualize entregas existentes
6. Exporte relatórios quando necessário

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## 📄 Licença

Este projeto é de código aberto e está disponível para uso educacional e comercial.