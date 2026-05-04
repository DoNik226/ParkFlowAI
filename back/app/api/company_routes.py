from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from back.app.api.deps import get_audit_logger, require_super_admin
from back.app.logger import AuditLogger
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
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    repo = CompanyRepository(db)

    if repo.get_by_slug(data.slug):
        raise HTTPException(status_code=409, detail="Company slug already exists")

    company = repo.create(
        name=data.name,
        slug=data.slug,
        is_active=data.is_active,
    )
    audit_logger.log_admin_action(
        current_user.id,
        "Администратор создал компанию",
        details={
            "target_company_id": company.id,
            "target_company_name": company.name,
            "target_company_slug": company.slug,
            "is_active": company.is_active,
        },
    )
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
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

    updated = repo.update(company_id, **update_data)
    audit_logger.log_admin_action(
        current_user.id,
        "Администратор обновил компанию",
        details={
            "target_company_id": updated.id,
            "target_company_name": updated.name,
            "target_company_slug": updated.slug,
            "updated_fields": sorted(update_data.keys()),
        },
    )
    return updated


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: int,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    repo = CompanyRepository(db)
    company = repo.get_by_id(company_id)

    if not company or not repo.delete(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    audit_logger.log_admin_action(
        current_user.id,
        "Администратор удалил компанию",
        details={
            "target_company_id": company.id,
            "target_company_name": company.name,
            "target_company_slug": company.slug,
        },
    )
