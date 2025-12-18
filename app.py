import uuid
import streamlit as st

def unique_key():
    return str(uuid.uuid4())

st.title("App com UUID Unico para Elementos")

for i in range(5):
    key = unique_key()
    st.button(f"Botão {i+1}", key=key)
