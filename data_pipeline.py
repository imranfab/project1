# Task 1: Data Pipeline Setup (data_pipeline.py)
import psycopg2
import pandas as pd
import requests

# Database connection
DB_CONFIG = {
    "dbname": "your_db",
    "user": "your_user",
    "password": "your_password",
    "host": "your_host",
    "port": "your_port"
}

def connect_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

# Create table
def setup_database():
    conn, cursor = connect_db()
    if conn is None:
        return
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(50),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        query TEXT,
        generated_response TEXT
    );
    ''')
    conn.commit()
    conn.close()
    print("Database setup completed.")

# ETL Pipeline
def etl_pipeline():
    url = "https://example.com/amazon_reviews.json"  # Replace with actual dataset link
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    conn, cursor = connect_db()
    if conn is None:
        return
    
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO conversations (user_id, query, generated_response)
            VALUES (%s, %s, %s)
        """, (row['user_id'], row['review_text'], row['response_text']))
    conn.commit()
    conn.close()
    print("ETL Process Completed")

if __name__ == "__main__":
    setup_database()
    etl_pipeline()
