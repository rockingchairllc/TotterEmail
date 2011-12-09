import transaction
import sqlamp
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import ForeignKey

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relation
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from zope.sqlalchemy import ZopeTransactionExtension

from datetime import datetime

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base(metaclass=sqlamp.DeclarativeMeta)

class EventType(Base):
    __tablename__ = 'EventTypes'
    __mp_manager__ = 'mp'
    id = Column(Integer, primary_key=True)
    parent_id = Column(ForeignKey('EventTypes.id'))
    parent = relation("EventType", remote_side=[id])
    name = Column(Unicode(128), nullable=False, unique=True)

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
    
    def __repr__(self):
        return '<EventType %r>' % self.name
    
class Event(Base):
    __tablename__ = 'Events'
    id = Column(Integer, primary_key=True)
    type_id = Column(ForeignKey('EventTypes.id'), nullable=False)
    when = Column(DateTime, default=datetime.utcnow, nullable=False)
    subject = Column(String(256))
    message = Column(Text)
    
    type = relationship('EventType')
    

class Subscription(Base):
    __tablename__ = 'Subscriptions'
    id = Column(Integer, primary_key=True)
    email = Column(String(256), nullable=False)
    frequency = Column(Enum('instant', 'daily'), nullable=True)
    last_sent = Column(ForeignKey('Event.id'))
    
    # Subscriptions get notified of all events matching type_id and subtypes.
    type_id = Column(ForeignKey('EventTypes.id'), nullable=False)
    
    type = relationship('EventType')
    
def populate():
    #session = DBSession()
    #session.flush()
    #transaction.commit()
    pass
def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    try:
        populate()
    except IntegrityError:
        transaction.abort()
