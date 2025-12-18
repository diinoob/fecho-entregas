import sqlite3
import pandas as pd

def connect_to_db(db_name):
    try:
        return sqlite3.connect(db_name)
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        raise

def load_data_frame(conn, query):
    try:
        return pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"Failed to load data frame: {e}")
        raise

def save_data_frame_to_db(df, table_name, conn):
    try:
        df.to_sql(table_name, conn, if_exists='replace', index=False)
    except ValueError as ve:
        print(f"Value error: {ve}")
        raise
    except Exception as e:
        print(f"Error saving DataFrame to SQL: {e}")
        raise

def main():
    db_name = 'example.db'
    conn = connect_to_db(db_name)
    print("Connected to database.")

    print("Fetching sample table...")
    input_query = "SELECT * FROM sample_table"
    df = load_data_frame(conn, input_query)

    print(df.head())

if __name__ == '__main__':
    main()