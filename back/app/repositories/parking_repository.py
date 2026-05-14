from typing import Optional, List

from sqlalchemy.orm import Session

from back.app.models.parking import Parking
from back.app.repositories.base_repository import BaseRepository


class ParkingRepository(BaseRepository[Parking]):
    def __init__(self, db: Session):
        super().__init__(db, Parking)

    def get_by_slug(self, slug: str, company_id: int | None = None) -> Optional[Parking]:
        query = self.db.query(Parking).filter(Parking.slug == slug)

        if company_id is not None:
            query = query.filter(Parking.company_id == company_id)

        return query.first()

    def get_by_id_or_slug(self, parking_id: str, company_id: int | None = None) -> Optional[Parking]:
        base_query = self.db.query(Parking)

        if company_id is not None:
            base_query = base_query.filter(Parking.company_id == company_id)

        if parking_id.isdigit():
            parking = base_query.filter(Parking.id == int(parking_id)).first()

            if parking:
                return parking

        return base_query.filter(Parking.slug == parking_id).first()

    def get_with_stats(self, parking_id: int) -> Optional[Parking]:
        return self.db.query(Parking).filter(Parking.id == parking_id).first()

    def list_for_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Parking]:
        return (
            self.db.query(Parking)
            .filter(Parking.company_id == company_id)
            .filter(Parking.is_active == True)
            .order_by(Parking.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all_active(self, skip: int = 0, limit: int = 100) -> List[Parking]:
        return (
            self.db.query(Parking)
            .filter(Parking.is_active == True)
            .order_by(Parking.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_by_ids(self, parking_ids: list[int]) -> List[Parking]:
        if not parking_ids:
            return []
        return self.db.query(Parking).filter(Parking.id.in_(parking_ids)).all()

    def slug_exists(self, company_id: int, slug: str, exclude_parking_id: int | None = None) -> bool:
        query = (
            self.db.query(Parking)
            .filter(Parking.company_id == company_id)
            .filter(Parking.slug == slug)
        )

        if exclude_parking_id is not None:
            query = query.filter(Parking.id != exclude_parking_id)

        return self.db.query(query.exists()).scalar()
