from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from back.app.models.parking_occupancy_cache import ParkingOccupancyCache
from back.app.repositories.base_repository import BaseRepository


class ParkingOccupancyCacheRepository(BaseRepository[ParkingOccupancyCache]):
    def __init__(self, db: Session):
        super().__init__(db, ParkingOccupancyCache)

    def get_by_parking(self, parking_id: int) -> Optional[ParkingOccupancyCache]:
        return self.db.query(ParkingOccupancyCache).filter(
            ParkingOccupancyCache.parking_id == parking_id
        ).first()

    def update_or_create(self, parking_id: int, total_spots: int, free_spots: int) -> ParkingOccupancyCache:
        cache = self.get_by_parking(parking_id)
        occupancy_percentage = ((total_spots - free_spots) / total_spots * 100) if total_spots > 0 else 0

        if cache:
            cache.total_spots = total_spots
            cache.free_spots = free_spots
            cache.occupancy_percentage = occupancy_percentage
            cache.last_calculated = func.now()
        else:
            cache = self.create(
                parking_id=parking_id,
                total_spots=total_spots,
                free_spots=free_spots,
                occupancy_percentage=occupancy_percentage
            )

        self.db.commit()
        self.db.refresh(cache)
        return cache

    def get_all_cached_stats(self):
        return self.db.query(ParkingOccupancyCache).all()