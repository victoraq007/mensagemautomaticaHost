# models.py
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()


class Settings(Base):
    __tablename__ = "settings"
    id    = Column(Integer, primary_key=True)
    key   = Column(String(100), unique=True, nullable=False)
    value = Column(String(500), nullable=False)


class MessageGroup(Base):
    __tablename__ = "message_groups"
    id          = Column(Integer, primary_key=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text, default="")
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship("Message", back_populates="group", cascade="all, delete-orphan")
    tasks    = relationship("TaskConfig", back_populates="message_group")


class Message(Base):
    __tablename__ = "messages"
    id         = Column(Integer, primary_key=True)
    group_id   = Column(Integer, ForeignKey("message_groups.id"), nullable=False)
    content    = Column(Text, nullable=False)
    is_embed   = Column(Boolean, default=False)
    embed_color= Column(String(50), default="")
    media_url  = Column(String(500), default="")
    active     = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    group = relationship("MessageGroup", back_populates="messages")


class TaskConfig(Base):
    """
    TIPOS DE SCHEDULE:

    fixed_times — horários fixos em dias específicos
      {"times":["09:00","18:00"], "days_of_month":[16,17], "days_of_week":[0,1,2,3,4], "months":[1..12]}
      days_of_month e days_of_week vazios = todo dia. months vazio = todo mês.

    interval_days — a cada N dias (com suporte a "a partir de X")
      {"every_days":15, "start_from":"2024-06-01", "hour_start":9, "hour_end":18, "random_time":true}

    weekly — uma vez por semana
      {"days_of_week":[0,1,2,3,4], "hour_start":9, "hour_end":18}

    monthly — uma vez por mês (em meses específicos ou todos)
      {"hour_start":9, "hour_end":18, "months":[1,2,3,4,5,6,7,8,9,10,11,12]}

    test — modo teste, envia a cada N minutos
      {"every_minutes":2}
    """
    __tablename__ = "task_configs"
    id               = Column(Integer, primary_key=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text, default="")
    type             = Column(String(50), nullable=False)
    channel_ids      = Column(Text, nullable=False)
    roles_to_mention = Column(Text, default="")
    message_group_id = Column(Integer, ForeignKey("message_groups.id"), nullable=True)
    schedule_config  = Column(Text, default="{}")
    active           = Column(Boolean, default=True)
    test_mode        = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    message_group = relationship("MessageGroup", back_populates="tasks")

    def get_channel_ids(self):
        return [int(x.strip()) for x in self.channel_ids.split(",") if x.strip()]

    def get_role_ids(self):
        if not self.roles_to_mention:
            return []
        return [x.strip() for x in self.roles_to_mention.split(",") if x.strip()]


class TaskExecutionLog(Base):
    """
    Log de execução de tarefas, mantido por 30 dias para não inflar o DB.
    """
    __tablename__ = "task_execution_logs"
    id          = Column(Integer, primary_key=True)
    task_id     = Column(Integer, ForeignKey("task_configs.id", ondelete="CASCADE"), nullable=False)
    task_name   = Column(String(200), nullable=False)
    channel_id  = Column(String(100), nullable=False)
    status      = Column(String(50), nullable=False)  # "SUCCESS", "ERROR"
    error_msg   = Column(Text, default="")
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)
