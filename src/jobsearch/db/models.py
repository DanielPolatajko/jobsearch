from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    homepage_url = Column(String)
    careers_url = Column(String)
    industry = Column(String)

    def __repr__(self):
        return f"<Company(name='{self.name}', industry='{self.industry}')>"


class CompanyListPage(Base):
    __tablename__ = "companylistpages"

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    last_scraped = Column(DateTime)

    def __repr__(self):
        return f"<CompanyListPage(url='{self.url}', name='{self.name}')>"
