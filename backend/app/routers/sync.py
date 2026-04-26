from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.candidate_service import candidate_service
from ..services.sync_adapter import sync_adapter

router = APIRouter(prefix="/sync", tags=["数据同步"])


@router.post("/export")
def export_all(db: Session = Depends(get_db)):
    candidates, total = candidate_service.list_candidates(db, page_size=10000)
    data_list = [candidate_service._candidate_to_dict(c) for c in candidates]
    sync_adapter.sync_all(data_list)
    return {"message": f"成功同步{len(data_list)}条候选人数据到本地CSV", "count": len(data_list)}


@router.get("/status")
def sync_status():
    rows = sync_adapter.read_sheet()
    return {
        "adapter": "LocalSheetAdapter",
        "row_count": len(rows),
        "csv_path": str(sync_adapter.csv_path),
    }


@router.get("/download-csv")
def download_csv():
    if not sync_adapter.csv_path.exists():
        return {"message": "CSV文件不存在，请先执行导出"}
    return FileResponse(
        path=str(sync_adapter.csv_path),
        filename="candidates_export.csv",
        media_type="text/csv",
    )
