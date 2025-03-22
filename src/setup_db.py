import sqlite3
import yaml
import os

def load_config(config_path="config/settings.yaml"):
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

def setup_database():
    config = load_config()
    db_file = config["database"]["file"]

    os.makedirs(os.path.dirname(db_file), exist_ok=True)

    try:
        conn = sqlite3.connect(db_file)
        print(f"Connected to SQLite database at '{db_file}'.")

        cursor = conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS communication_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            spacecraft TEXT,
            antenna_id TEXT,
            signal_strength REAL,
            communication_duration REAL
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'communication_logs' created or already exists.")

    except sqlite3.Error as e:
        print(f"Error setting up database: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_database()