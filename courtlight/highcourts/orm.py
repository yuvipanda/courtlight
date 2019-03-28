import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Table
from sqlalchemy.orm import relationship

Base = declarative_base()

class Case(Base):
    __tablename__ = 'case'
    id = Column(Integer, primary_key=True)
    case_number = Column(String)
    party = Column(String) 
    judgement_id = Column(Integer, ForeignKey('judgement.id'))

    judgement = relationship("Judgement", backref="cases")

judgement_authorship = Table('judgement_authorship', Base.metadata,
    Column('judgement_id', Integer, ForeignKey('judgement.id')),
    Column('judge_id', Integer, ForeignKey('judge.id'))
)

class Judgement(Base):
    __tablename__ = 'judgement'
    id = Column(Integer, primary_key=True)
    pdf_link = Column(String, unique=True, index=True)
    date = Column(Date)

    judges = relationship(
        "Judge",
        secondary=judgement_authorship,
        backref="judgements"
    )

class Judge(Base):
    __tablename__ = 'judge'
    id = Column(Integer, primary_key=True)
    name = Column(String)


class JudgementContent(Base):
    __tablename__ = 'judgement_content'
    id = Column(Integer, primary_key=True)
    judgement_id = Column(Integer, ForeignKey('judgement.id'))
    content_type = Column(String, index=True)
    content_hash = Column(String, index=True)
    content = Column(String)

    judgement = relationship('Judgement', backref='contents')