import streamlit as st

# Streamlit app
def main():
    st.title("Professional Delivery App")

    # Ensuring unique keys for inputs to avoid StreamlitDuplicateElementId issues
    user_name = st.text_input("Enter your username", key="text_input_username")
    user_password = st.text_input("Enter your password", type="password", key="text_input_password")

    if st.button("Login", key="login_button"):
        st.write(f"Welcome {user_name}!")

if __name__ == "__main__":
    main()