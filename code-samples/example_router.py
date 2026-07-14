"""Sanitized example — Router Layer.
Shows the 'thin router' pattern: parse HTTP, validate, delegate to service.
No business logic lives here."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

# These imports are for type annotations only — no real business logic
from example_service import EntityService
from example_repository import EntityRepository

router = APIRouter(prefix="/entities", tags=["entities"])


def get_repo(db: Session) -> EntityRepository:
    """Dependency injection stub — in production this uses the real repo."""
    return EntityRepository()


@router.get("/{entity_id:int}", response_class=HTMLResponse)
async def entity_detail(
    entity_id: int,
    db: Session = Depends(lambda: None),  # stub
    repo: EntityRepository = Depends(get_repo),
):
    """
    Thin handler:
    - Validates the request (int constraint on path param)
    - Delegates to service
    - Returns HTTP response
    - NO BUSINESS LOGIC
    """
    service = EntityService(repo)
    data = service.get_detail(db, entity_id)

    if not data["entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")

    return HTMLResponse(f"<h1>{data['entity'].name}</h1>")


@router.get("/api/{entity_id:int}", response_class=JSONResponse)
async def entity_api_detail(
    entity_id: int,
    db: Session = Depends(lambda: None),
    repo: EntityRepository = Depends(get_repo),
):
    """API variant — returns JSON instead of HTML."""
    service = EntityService(repo)
    data = service.get_detail(db, entity_id)
    if not data["entity"]:
        raise HTTPException(status_code=404, detail="Not found")
    return JSONResponse({"id": entity_id, **data})
