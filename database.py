# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
import contextlib

DATABASE_URL = "sqlite:///bot_database.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # necessário para SQLite com múltiplas threads
)

Base.metadata.create_all(engine)

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
