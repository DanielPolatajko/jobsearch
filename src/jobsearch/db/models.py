from sqlalchemy import Column, Integer, String, DateTime, Boolean
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
    query = Column(String, nullable=False, foreign_key="searchcache.query")
    location_relevant = Column(Boolean, nullable=False, default=False)
    last_scraped = Column(DateTime)

    def __repr__(self):
        return f"<CompanyListPage(url='{self.url}', name='{self.name}')>"


class SearchCache(Base):
    __tablename__ = "searchcache"

    id = Column(Integer, primary_key=True)
    query = Column(String, nullable=False)
    last_searched = Column(DateTime)

    def __repr__(self):
        return (
            f"<SearchCache(query='{self.query}', last_searched='{self.last_searched}')>"
        )
