# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
import contextlib

DATABASE_URL = "sqlite:///bot_database.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},  # necessário para SQLite com múltiplas threads
)

from sqlalchemy import text, inspect

def auto_migrate(engine):
    """
    Verificador de integridade do Banco:
    O SQLite não faz ALTER TABLE automático com create_all(), portanto esta função injeta as alterações estruturais que 
    sofreram update, permitindo sistema livre de manutenção manual.
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    with engine.begin() as conn:
        if "messages" in tables:
            cols = [c["name"] for c in inspector.get_columns("messages")]
            if "is_embed" not in cols:    conn.execute(text("ALTER TABLE messages ADD COLUMN is_embed BOOLEAN DEFAULT 0"))
            if "embed_color" not in cols: conn.execute(text("ALTER TABLE messages ADD COLUMN embed_color VARCHAR(50) DEFAULT ''"))
            if "media_url" not in cols:   conn.execute(text("ALTER TABLE messages ADD COLUMN media_url VARCHAR(500) DEFAULT ''"))
        
        if "task_configs" in tables:
            cols = [c["name"] for c in inspector.get_columns("task_configs")]
            if "test_mode" not in cols:        conn.execute(text("ALTER TABLE task_configs ADD COLUMN test_mode BOOLEAN DEFAULT 0"))
            if "roles_to_mention" not in cols: conn.execute(text("ALTER TABLE task_configs ADD COLUMN roles_to_mention VARCHAR(500) DEFAULT ''"))
            # FIX BUG-7.2: Adicionar colunas de DM que faltavam no auto_migrate
            if "send_dm" not in cols:          conn.execute(text("ALTER TABLE task_configs ADD COLUMN send_dm BOOLEAN DEFAULT 0"))
            if "target_users" not in cols:     conn.execute(text("ALTER TABLE task_configs ADD COLUMN target_users TEXT DEFAULT ''"))

Base.metadata.create_all(engine)
auto_migrate(engine)

# scoped_session garante uma sessão por thread — seguro para uso com asyncio + Flask
SessionFactory = sessionmaker(bind=engine)
ScopedSession  = scoped_session(SessionFactory)


@contextlib.contextmanager
def get_session():
    """
    Context manager para uso seguro de sessão.
    Faz commit automático ou rollback em caso de erro.

    Uso:
        with get_session() as session:
            session.add(obj)
    """
    session = ScopedSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        ScopedSession.remove()
