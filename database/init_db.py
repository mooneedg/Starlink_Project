from sqlalchemy import create_engine, Column, Integer, ForeignKey, TIMESTAMP, TEXT
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Create Database
engine = create_engine('sqlite:///database/SpaceData.db', echo=True)

# Base class for table definitions
Base = declarative_base()

# Table: Space Objects (Main Table)
class Space_Object(Base):
    __tablename__ = 'space_objects'

    norad_id = Column(TEXT, primary_key=True)
    object_name = Column(TEXT)
    object_type = Column(TEXT)
    source = Column(TEXT)
    first_seen = Column(TIMESTAMP)
    last_seen = Column(TIMESTAMP)

# Table: TLES
class TLE(Base):
    __tablename__ = 'tles'

    tle_id = Column(Integer, primary_key=True, autoincrement=True)
    norad_id = Column(TEXT, ForeignKey('space_objects.norad_id'), nullable=False)
    line1 = Column(TEXT, nullable=False)
    line2 = Column(TEXT, nullable=False)
    epoch = Column(TIMESTAMP, nullable=False)
    ingest_time = Column(TIMESTAMP, nullable=False)
    source = Column(TEXT, nullable=False,)

# Table: Object Groups
class Object_Group(Base):
    __tablename__ = 'object_groups'

    norad_id = Column(TEXT, ForeignKey('space_objects.norad_id'), primary_key=True, nullable=False)
    group_name = Column(TEXT, primary_key=True, nullable=False)
    source = Column(TEXT, nullable=False)
    
if __name__ == "__main__":
    # Create all tables in the database
    Base.metadata.create_all(engine)
