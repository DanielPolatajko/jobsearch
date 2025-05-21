from jobsearch.db.models import CompanyListPage, SearchCache, Company
from jobsearch.db.database import session_factory
from datetime import datetime


class CompanyListPageRepository:
    def get_company_list_page_by_name_and_url(
        self, name: str, url: str
    ) -> CompanyListPage | None:
        with session_factory() as session:
            return session.query(CompanyListPage).filter_by(name=name, url=url).first()

    def upsert_company_list_page(
        self,
        title: str,
        url: str,
        query: str,
        location_relevant: bool,
        last_scraped: datetime | None = None,
    ) -> CompanyListPage:
        with session_factory() as session:
            company_list_page = self.get_company_list_page_by_name_and_url(title, url)
            if company_list_page is None:
                company_list_page = CompanyListPage(
                    name=title,
                    url=url,
                    query=query,
                    location_relevant=location_relevant,
                    last_scraped=last_scraped,
                )
                session.add(company_list_page)
                session.commit()
            else:
                company_list_page.location_relevant = location_relevant
                company_list_page.last_scraped = last_scraped
                session.commit()
            return company_list_page

    def get_unscraped_company_list_pages(
        self,
        limit: int = 5,
    ) -> list[CompanyListPage]:
        with session_factory() as session:
            query = (
                session.query(CompanyListPage)
                .filter(CompanyListPage.last_scraped.is_(None))
                .order_by(CompanyListPage.location_relevant.desc())
            )
            return query.limit(limit).all()

    def update_company_list_page_last_scraped(
        self, id: int, last_scraped: datetime | None = None
    ) -> CompanyListPage:
        with session_factory() as session:
            company_list_page = session.query(CompanyListPage).filter_by(id=id).first()
            company_list_page.last_scraped = last_scraped
            session.commit()
            return company_list_page


class SearchCacheRepository:
    def get_search_cache_by_query(self, query: str) -> SearchCache | None:
        with session_factory() as session:
            return session.query(SearchCache).filter_by(query=query).first()

    def create_search_cache(
        self, query: str, last_searched: datetime | None = None
    ) -> SearchCache:
        with session_factory() as session:
            search_cache = SearchCache(query=query, last_searched=last_searched)
            session.add(search_cache)
            session.commit()
            return search_cache


class CompanyRepository:
    def get_company_by_name(self, name: str) -> Company | None:
        with session_factory() as session:
            return session.query(Company).filter_by(name=name).first()

    def upsert_company(
        self,
        name: str,
        homepage_url: str | None = None,
        careers_url: str | None = None,
        industry: str | None = None,
    ) -> Company:
        with session_factory() as session:
            company = self.get_company_by_name(name)
            if company is None:
                company = Company(
                    name=name,
                    homepage_url=homepage_url,
                    careers_url=careers_url,
                    industry=industry,
                )
                session.add(company)
                session.commit()
            else:
                company.homepage_url = homepage_url
                company.careers_url = careers_url
                company.industry = industry
                session.commit()
            return company
