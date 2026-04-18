# upgrade_db.py
import sqlite3
import os

DB_PATH = "bot_database.db"

def alter_table():
    if not os.path.exists(DB_PATH):
        print("Banco nao existe, SQLAlchemy criara um novo na proxima execucao.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Message table
        cursor.execute("ALTER TABLE messages ADD COLUMN is_embed BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE messages ADD COLUMN embed_color VARCHAR(50) DEFAULT ''")
        cursor.execute("ALTER TABLE messages ADD COLUMN media_url VARCHAR(500) DEFAULT ''")
        print("Tabela messages alterada com sucesso!")
    except sqlite3.OperationalError as e:
        print(f"Ignorando ou erro na tabela messages: {e}")

    try:
        # TaskConfig table
        cursor.execute("ALTER TABLE task_configs ADD COLUMN roles_to_mention TEXT DEFAULT ''")
        print("Tabela task_configs (roles_to_mention) alterada!")
    except sqlite3.OperationalError as e:
        print(f"Ignorando ou erro na tabela task_configs roles: {e}")

    try:
        # TaskConfig table - Nova atualização DM
        cursor.execute("ALTER TABLE task_configs ADD COLUMN send_dm BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE task_configs ADD COLUMN target_users TEXT DEFAULT ''")
        print("Tabela task_configs (DMs) alterada com sucesso!")
    except sqlite3.OperationalError as e:
        print(f"Ignorando ou erro na tabela task_configs DMs: {e}")

    # Tabelas task_execution_logs e message_read_logs serão criadas automaticamente pelo Base.metadata.create_all

    conn.commit()
    conn.close()

if __name__ == "__main__":
    alter_table()
