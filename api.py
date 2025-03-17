from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

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

@app.route('/conversation-summary', methods=['GET'])
def conversation_summary():
    conn, cursor = connect_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor.execute("SELECT user_id, COUNT(*) FROM conversations GROUP BY user_id")
    data = cursor.fetchall()
    conn.close()
    return jsonify({"summary": data})

@app.route('/data-stats', methods=['GET'])
def data_stats():
    conn, cursor = connect_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor.execute("SELECT COUNT(*) FROM conversations")
    count = cursor.fetchone()
    conn.close()
    return jsonify({"total_conversations": count[0]})

if __name__ == '__main__':
    app.run(debug=True)
