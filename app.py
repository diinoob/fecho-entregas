import sqlite3
import pandas as pd
import logging

# Configure logging at the DEBUG level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to connect to SQLite database
def connect_to_database(db_name):
    logging.debug(f"Attempting to connect to the database: {db_name}")
    try:
        conn = sqlite3.connect(db_name)
        logging.debug("Connection to database successful.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"SQLite error occurred: {e}")
        raise

# Function to execute a query and return data as a pandas DataFrame
def execute_query(conn, query):
    logging.debug(f"Preparing to execute query: {query}")
    try:
        df = pd.read_sql_query(query, conn)
        logging.debug("Query executed successfully and data loaded into DataFrame.")
        return df
    except pd.io.sql.DatabaseError as e:
        logging.error(f"Pandas Database error occurred: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while executing query: {e}")
        raise

# Example usage
def main():
    database_name = "example.db"
    query = "SELECT * FROM some_table;"

    try:
        conn = connect_to_database(database_name)
        data = execute_query(conn, query)
        logging.debug("Data retrieved from the database:")
        logging.debug(data)
    except Exception as e:
        logging.critical(f"Critical error in main execution: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logging.debug("Database connection closed.")

if __name__ == "__main__":
    main()