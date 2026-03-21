from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector # <--- IMPORTANTE: Adicionamos o 'Vector'
import datetime

Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=False)
    messages = relationship("Mensagem", back_populates="autor")

class Mensagem(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    channel_id = Column(BigInteger, nullable=False)
    content = Column(String, nullable=False)
    
    # === A NOVA COLUNA DA IA ===
    embedding = Column(Vector(384)) 
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    autor = relationship("Usuario", back_populates="messages")