import streamlit as st

# Updated Streamlit app with unique keys for all widgets
def main():
    # Ensure each widget has a unique key to prevent duplication errors
    st.title("Professional Delivery App")

    name = st.text_input("Enter your name", key="name_input")
    age = st.number_input("Enter your age", min_value=0, max_value=100, key="age_input")
    address = st.text_area("Enter your address", key="address_input")

    submit_button = st.button("Submit", key="submit_button")

    if submit_button:
        st.write(f"Name: {name}")
        st.write(f"Age: {age}")
        st.write(f"Address: {address}")

if __name__ == "__main__":
    main()