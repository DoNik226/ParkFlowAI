from typing import Optional

from sqlalchemy.orm import Session

from back.app.models.company import Company
from back.app.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: Session):
        super().__init__(db, Company)

    def get_by_slug(self, slug: str) -> Optional[Company]:
        return self.db.query(Company).filter(Company.slug == slug).first()

    def list_active(self):
        return (
            self.db.query(Company)
            .filter(Company.is_active == True)
            .order_by(Company.id.asc())
            .all()
        )