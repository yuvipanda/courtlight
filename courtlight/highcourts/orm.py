import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Table, create_engine
from sqlalchemy.orm import relationship, sessionmaker

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
    date = Column(Date, index=True)
    text_content = Column(String)
    text_content_hash = Column(String, index=True)

    judges = relationship(
        "Judge",
        secondary=judgement_authorship,
        backref="judgements"
    )

class Judge(Base):
    __tablename__ = 'judge'
    id = Column(Integer, primary_key=True)
    name = Column(String)


Session = sessionmaker()
session = None
def get_session(db_path):
    global session
    if session is None:
        engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(engine)
        Session.configure(bind=engine)
        session = Session()
    return session