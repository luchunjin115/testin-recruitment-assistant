import csv
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

from ..config import get_settings


class TencentDocsAdapter(ABC):
    """腾讯在线文档适配层接口。
    当需要替换为真实腾讯在线文档 API 时，实现此接口即可。
    真实 API 文档参考: https://docs.qq.com/open/wiki/
    """

    @abstractmethod
    def sync_candidate(self, candidate: dict) -> bool:
        ...

    @abstractmethod
    def sync_all(self, candidates: List[dict]) -> bool:
        ...

    @abstractmethod
    def read_sheet(self) -> List[dict]:
        ...


class LocalSheetAdapter(TencentDocsAdapter):
    """本地 CSV 适配器，模拟腾讯在线文档的行为。
    生产环境中替换为 TencentDocsCloudAdapter 即可实现真实同步。
    """

    COLUMNS = [
        "id", "name", "phone", "email", "school", "degree", "major",
        "target_role", "experience_years", "skills", "source_channel",
        "stage", "screening_status", "interview_time", "interview_method", "interviewer",
        "offer_position", "salary_range", "expected_onboard_date",
        "onboard_date", "reject_reason", "ai_summary", "ai_tags",
        "created_at", "updated_at",
    ]

    def __init__(self):
        settings = get_settings()
        self.data_dir = Path("./data")
        self.data_dir.mkdir(exist_ok=True)
        self.csv_path = self.data_dir / "candidates_sheet.csv"

    def sync_candidate(self, candidate: dict) -> bool:
        rows = self._read_csv()
        updated = False
        for i, row in enumerate(rows):
            if row.get("id") == str(candidate.get("id", "")):
                rows[i] = {k: str(candidate.get(k, "")) for k in self.COLUMNS}
                updated = True
                break
        if not updated:
            rows.append({k: str(candidate.get(k, "")) for k in self.COLUMNS})
        self._write_csv(rows)
        return True

    def sync_all(self, candidates: List[dict]) -> bool:
        rows = [{k: str(c.get(k, "")) for k in self.COLUMNS} for c in candidates]
        self._write_csv(rows)
        return True

    def read_sheet(self) -> List[dict]:
        return self._read_csv()

    def _read_csv(self) -> List[dict]:
        if not self.csv_path.exists():
            return []
        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def _write_csv(self, rows: List[dict]):
        with open(self.csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


class TencentDocsCloudAdapter(TencentDocsAdapter):
    """真实腾讯在线文档适配器（占位实现）。

    接入步骤:
    1. 注册腾讯文档开放平台应用
    2. 获取 client_id 和 client_secret
    3. 实现 OAuth 2.0 授权流程
    4. 使用文档 API 进行读写操作

    API 参考: https://docs.qq.com/open/wiki/
    """

    def __init__(self, client_id: str = "", client_secret: str = "", doc_id: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.doc_id = doc_id

    def sync_candidate(self, candidate: dict) -> bool:
        raise NotImplementedError("请配置腾讯在线文档 API 凭证后使用")

    def sync_all(self, candidates: List[dict]) -> bool:
        raise NotImplementedError("请配置腾讯在线文档 API 凭证后使用")

    def read_sheet(self) -> List[dict]:
        raise NotImplementedError("请配置腾讯在线文档 API 凭证后使用")


sync_adapter = LocalSheetAdapter()
