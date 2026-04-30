from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from back.app.api.deps import require_super_admin
from back.app.database import get_db
from back.app.models.user import User
from back.app.repositories.company_repository import CompanyRepository
from back.app.schemas.companies import CompanyCreate, CompanyUpdate, CompanyResponse

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyResponse])
def list_companies(
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    repo = CompanyRepository(db)
    return repo.get_all(limit=1000)


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    data: CompanyCreate,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    repo = CompanyRepository(db)

    if repo.get_by_slug(data.slug):
        raise HTTPException(status_code=409, detail="Company slug already exists")

    return repo.create(
        name=data.name,
        slug=data.slug,
        is_active=data.is_active,
    )


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    repo = CompanyRepository(db)
    company = repo.get_by_id(company_id)

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = data.model_dump(exclude_unset=True)

    if "slug" in update_data and repo.get_by_slug(update_data["slug"]):
        existing = repo.get_by_slug(update_data["slug"])
        if existing and existing.id != company_id:
            raise HTTPException(status_code=409, detail="Company slug already exists")

    return repo.update(company_id, **update_data)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: int,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    repo = CompanyRepository(db)

    if not repo.delete(company_id):
        raise HTTPException(status_code=404, detail="Company not found")