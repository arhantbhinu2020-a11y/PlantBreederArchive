from sqlalchemy import create_engine, Table, Column, Integer, String, ForeignKey, Float, Date, select, MetaData, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column, Mapped, relationship, declared_attr, Session
from sqlalchemy.orm.decl_api import DeclarativeMeta
from enum import Enum
from typing import List
from random import random
import os
from pathlib import Path
from datetime import date
Base: DeclarativeMeta = declarative_base()
servername = 'testserver'
dbname = 'testdb'
db_file = 'sqlite:///archiver.db'

engine = create_engine(
    db_file,
    echo=True
)
if __name__ == "__main__":
    Path("archiver.db").unlink(True)
Base.metadata.create_all(engine)
class Owner(Base):
    __tablename__ = 'owner'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owned_locations: Mapped[List["Location"]] = relationship()

class Location(Base):
    __tablename__ = 'location'
    id = Column(Integer, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    name = Column(String)
    ownerid = Column(ForeignKey("owner.id"))
    plots: Mapped[List["Plot"]] = relationship()

class OwnershipLog(Base):
    __tablename__ = "ownership log"
    id = Column(Integer, primary_key=True)
    locationid = Column(ForeignKey("location.id"))
    old_ownerid = Column(ForeignKey("owner.id"))
    date_of_agreement = Column(Date, default = date.today())
    date_of_confirmation = Column(Date, default = date(1, 1, 1))#01/01/0001 == not yet confirmed
    new_ownerid = Column(ForeignKey("owner.id"))#If the agreement fell through, simply set this to the same as old_ownerid

    def confirm_transfer(self, new_ownerid: int = None, date_of_confirmation: date = None):
        if not date_of_confirmation:
            date_of_confirmation = date.today()
        if not new_ownerid:
            #If no new owner was given or initially recorded, assume the agreement fell through.
            new_ownerid = self.new_ownerid if self.new_ownerid else self.old_ownerid
        
        self.date_of_confirmation = date_of_confirmation
        self.new_ownerid = new_ownerid
        return self
    

class Plot(Base):
    __tablename__ = 'plot'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    width = Column(Float, default = 10.0)
    height = Column(Float, default = 10.0)
    aisle = Column(Float, default = 10.0)
    locationid = Column(ForeignKey("location.id"))
    images: Mapped[List["Image"]] = relationship()
    history: Mapped[List["Management"]] = relationship()
    

class Image(Base):
    __tablename__ = 'image'
    id = Column(Integer, primary_key=True)
    url = Column(String)#Try to save the actual images to the cloud, with these being simple URLs
    plotid = Column(ForeignKey("plot.id"))
    

class Management(Base):#This is where all the known controllable information goes 
    __tablename__ = 'management'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    date = Column(Date)
    goal = Column(String, default = "Grow Gooder")
    imageid = Column(ForeignKey("image.id"))
    plotid = Column(ForeignKey("plot.id"))
    records: Mapped[List["Record"]] = relationship()

class PhysAttr(Base):#Known physical attributes not typically controllable
    __tablename__ = 'physical attributes'
    id = Column(Integer, primary_key=True)
    managementid = Column(ForeignKey('management.id'))
    soiltype = Column(String)
    elevation = Column(Float)

class VarEnum(Enum):
    YIELD = 1
    RESILIENCE_PESTS = 2
    RESILIENCE_DROUGHT = 3

class Variable(Base):
    __tablename__ = "variable"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    unit = Column(String, default = "ft.")
    pc_attribute = Column(Boolean, default = False)#False for physical, True for chemical
    records: Mapped[List["Record"]] = relationship()

class Record(Base):
    __tablename__ = "record"
    id = Column(Integer, primary_key=True)
    mean = Column(Float, default = 0.0)
    mode = Column(Float, default = 0.0)
    std = Column(Float, default = 0.0)
    ground_truth = Column(Float, default = 0.0)# The actual value recorded when testing the physical material.
    managementid = Column(ForeignKey("management.id"), default = 2)
    variableid = Column(ForeignKey("variable.id"))



if __name__ == "__main__":
    Owner.__table__.create(engine)
    Location.__table__.create(engine)
    OwnershipLog.__table__.create(engine)
    Plot.__table__.create(engine)
    Image.__table__.create(engine)
    Management.__table__.create(engine)
    Variable.__table__.create(engine)
    Record.__table__.create(engine)
    with Session(engine) as session:
        owner_1 = Owner(name = "Dr. Sean")
        session.add(owner_1)
        location_1 = Location(name = "UT Arlington", latitude = 32.7285, longitude = -97.1188, ownerid = select(Owner.id).where(Owner.name == "Dr. Sean"))
        session.add(location_1)
        
        for var in VarEnum:
            var_1 = Variable(name = var.name.lower())
            session.add(var_1)

        for i in range(5):
            for j in range(6):
                plot_1 = Plot(name = f"UTA_DS_{i}{j}", locationid = select(Location.id).where(Location.name == "UT Arlington"))
                session.add(plot_1)
                for dat in [date(2026, 7, 1), date(2026, 7, 16), date(2026, 7, 31), date(2026, 8, 15), date(2026, 8, 30)]:
                    image_1 = Image(url = f"plot_image_{i}{j}_{str(dat)}.jpg", plotid = select(Plot.id).where(Plot.name == f"UTA_DS_{i}{j}"))
                    session.add(image_1)
                    manage_1 = Management(name = f"UTA_DS_{i}{j}_{str(dat)}", date = dat, plotid = select(Plot.id).where(Plot.name == f"UTA_DS_{i}{j}"), imageid = select(Image.id).where(Image.url == f"plot_image_{i}{j}_{str(dat)}.jpg"))
                    session.add(manage_1)
                    session.commit()
                    for var in VarEnum:
                        var_1 = Record(ground_truth = abs(6*random() - random()), managementid = select(Management.id).where(Management.name == f"UTA_DS_{i}{j}_{str(dat)}"), variableid = select(Variable.id).where(Variable.id == var.value))
                        session.add(var_1)
                    session.commit()