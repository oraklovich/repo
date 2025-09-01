# models.py
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, create_engine, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Result(Base):
    __tablename__ = 'results'
    id = Column(Integer, primary_key=True)
    home_team = Column(String(255), nullable=False)
    away_team = Column(String(255), nullable=False)
    match_time = Column(DateTime, nullable=False)
    home_score = Column(Integer)
    away_score = Column(Integer)
    status = Column(String(50), default='Scheduled')
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('home_team', 'away_team', 'match_time', name='results_home_team_away_team_match_time_key'),
    )

class Prediction(Base):
    __tablename__ = 'predictions'
    id = Column(Integer, primary_key=True)
    home_team = Column(String(255), nullable=False)
    away_team = Column(String(255), nullable=False)
    match_time = Column(DateTime, nullable=False)
    prediction_type = Column(String(50), nullable=False)
    prediction_value = Column(String(50), nullable=False)
    source = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Analysis(Base):
    __tablename__ = 'analysis'
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# Функция для создания сессии
def get_db_session():
    engine = create_engine('postgresql://football_user:<password>@localhost:5432/football_db')
    Session = sessionmaker(bind=engine)
    return Session()
