from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import (
    CandidateCreate,
    CandidateFromResumeCreate,
    CandidateRead,
    CandidateUpdate,
)
from app.services.candidate_service import (
    CandidateJobNotFoundError,
    CandidateResumeAlreadyBoundError,
    CandidateResumeJobConflictError,
    CandidateResumeNotFoundError,
    candidate_service,
)


router = APIRouter(prefix="/candidates", tags=["candidates"])
CANDIDATE_NOT_FOUND = "候选人不存在"


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    return await candidate_service.create_candidate(db, data)


@router.post(
    "/from-resume",
    response_model=CandidateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_from_resume(
    data: CandidateFromResumeCreate,
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    try:
        return await candidate_service.create_candidate_from_resume(
            db,
            data.resume_id,
            data.candidate,
        )
    except CandidateResumeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CandidateJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (
        CandidateResumeAlreadyBoundError,
        CandidateResumeJobConflictError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[CandidateRead])
async def list_candidates(db: AsyncSession = Depends(get_db)) -> list[Candidate]:
    return await candidate_service.list_candidates(db)


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    candidate = await candidate_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CANDIDATE_NOT_FOUND,
        )
    return candidate


@router.put("/{candidate_id}", response_model=CandidateRead)
async def update_candidate(
    candidate_id: int,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    candidate = await candidate_service.update_candidate(db, candidate_id, data)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CANDIDATE_NOT_FOUND,
        )
    return candidate


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await candidate_service.delete_candidate(db, candidate_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CANDIDATE_NOT_FOUND,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
