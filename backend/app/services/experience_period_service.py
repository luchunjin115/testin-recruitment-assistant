from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.schemas.experience_period import (
    ExperiencePeriodFact,
    ExperiencePeriodFactsSnapshot,
)


EXPERIENCE_PERIOD_FACTS_RULE_VERSION = "experience_period_facts_v1"
SCREENING_EVALUATION_TIMEZONE = "Asia/Shanghai"


class ExperiencePeriodFactsError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _ParsedEndpoint:
    raw: str
    year: int
    month: int | None
    precision: str


class ExperiencePeriodService:
    _ENDPOINT = (
        r"\d{4}(?:\s*(?:[./-]\s*\d{1,2}|年(?:\s*\d{1,2}\s*月?)?))?"
    )
    _RANGE = re.compile(
        rf"(?P<start>{_ENDPOINT})\s*"
        rf"(?P<separator>—|–|~|～|至|到|-(?=\s*(?:\d{{4}}|present\b|current\b|至今)))\s*"
        rf"(?P<end>{_ENDPOINT}|至今|现在|目前|present|current)",
        re.IGNORECASE,
    )
    _PRESENT = re.compile(r"^(?:至今|现在|目前|present|current)$", re.IGNORECASE)
    _MONTH = re.compile(
        r"^(?P<year>\d{4})\s*(?:[./-]\s*(?P<month>\d{1,2})|年\s*(?P<cn_month>\d{1,2})\s*月?)$"
    )
    _YEAR = re.compile(r"^(?P<year>\d{4})\s*年?$")

    def build(
        self,
        resume_text: str,
        *,
        evaluation_reference_at: datetime,
        evaluation_timezone: str = SCREENING_EVALUATION_TIMEZONE,
        rule_version: str = EXPERIENCE_PERIOD_FACTS_RULE_VERSION,
    ) -> ExperiencePeriodFactsSnapshot:
        if not isinstance(evaluation_reference_at, datetime) or (
            evaluation_reference_at.tzinfo is None
            or evaluation_reference_at.utcoffset() is None
        ):
            raise ExperiencePeriodFactsError("评价基准必须是带时区时间")
        if evaluation_timezone != SCREENING_EVALUATION_TIMEZONE:
            raise ExperiencePeriodFactsError("阶段 7 评价时区必须是 Asia/Shanghai")
        if rule_version != EXPERIENCE_PERIOD_FACTS_RULE_VERSION:
            raise ExperiencePeriodFactsError("经历时间事实规则版本与代码不一致")
        # Stage 7 is intentionally fixed to modern China Standard Time (UTC+8).
        # Using an explicit offset avoids depending on the host's local timezone
        # or an optional Windows IANA timezone database.
        business_zone = timezone(timedelta(hours=8), name=evaluation_timezone)
        reference = evaluation_reference_at.astimezone(business_zone)
        cutoff_index = self._month_index(reference.year, reference.month)
        facts: list[ExperiencePeriodFact] = []
        normalized = resume_text.replace("\r\n", "\n").replace("\r", "\n")
        for line_number, line in enumerate(normalized.split("\n"), start=1):
            for match_index, match in enumerate(self._RANGE.finditer(line), start=1):
                source_date_text = match.group(0).strip()
                raw_start = match.group("start").strip()
                raw_end = match.group("end").strip()
                facts.append(
                    self._build_fact(
                        source_line=line_number,
                        match_index=match_index,
                        source_date_text=source_date_text,
                        raw_start=raw_start,
                        raw_end=raw_end,
                        cutoff_index=cutoff_index,
                    )
                )

        reference_iso = evaluation_reference_at.isoformat()
        return ExperiencePeriodFactsSnapshot(
            rule_version=rule_version,
            evaluation_reference_at=reference_iso,
            evaluation_timezone=evaluation_timezone,
            reference_month=self._format_month(cutoff_index),
            facts=facts,
        )

    def fingerprint(self, snapshot: ExperiencePeriodFactsSnapshot) -> str:
        serialized = json.dumps(
            snapshot.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def duration_bounds_for_keys(
        self,
        facts: Iterable[ExperiencePeriodFact],
        keys: Iterable[str],
    ) -> tuple[int, int] | None:
        fact_by_key = {fact.key: fact for fact in facts}
        selected_keys = list(keys)
        if not selected_keys or any(key not in fact_by_key for key in selected_keys):
            return None
        selected = [fact_by_key[key] for key in selected_keys]
        if any(not fact.usable_for_reference for fact in selected):
            return None

        exact_intervals: list[tuple[int, int]] = []
        lower_intervals: list[tuple[int, int]] = []
        upper_intervals: list[tuple[int, int]] = []
        for fact in selected:
            start_lower, start_upper, end_lower, end_upper = self._fact_interval_bounds(fact)
            lower_intervals.append((start_upper, max(start_upper, end_lower)))
            upper_intervals.append((start_lower, max(start_lower, end_upper)))
            if fact.duration_months is not None:
                exact_intervals.append((start_lower, end_lower))

        if len(exact_intervals) == len(selected):
            exact = self._union_duration(exact_intervals)
            return exact, exact
        return (
            self._union_duration(lower_intervals),
            self._union_duration(upper_intervals),
        )

    def _build_fact(
        self,
        *,
        source_line: int,
        match_index: int,
        source_date_text: str,
        raw_start: str,
        raw_end: str,
        cutoff_index: int,
    ) -> ExperiencePeriodFact:
        key_payload = f"{source_line}:{match_index}:{source_date_text}"
        key = "experience_period:" + hashlib.sha256(
            key_payload.encode("utf-8")
        ).hexdigest()[:16]
        start = self._parse_endpoint(raw_start)
        present = bool(self._PRESENT.fullmatch(raw_end))
        end = None if present else self._parse_endpoint(raw_end)
        warnings: list[str] = []

        if start is None or (not present and end is None):
            return ExperiencePeriodFact(
                key=key,
                source_line=source_line,
                source_date_text=source_date_text,
                raw_start=raw_start,
                raw_end=raw_end,
                normalized_start_month=None,
                normalized_end_month=None,
                start_precision="year",
                end_precision="present" if present else "year",
                resolved_cutoff_month=self._format_month(cutoff_index),
                usable_for_reference=False,
                warnings=["unparseable_date"],
                unavailable_reason="日期范围无法可靠解析",
            )

        assert start is not None
        start_min = self._month_index(start.year, start.month or 1)
        start_max = self._month_index(start.year, start.month or 12)
        if present:
            end_min = end_max = cutoff_index
            end_precision = "present"
            normalized_end = self._format_month(cutoff_index)
        else:
            assert end is not None
            end_min = self._month_index(end.year, end.month or 1)
            end_max = self._month_index(end.year, end.month or 12)
            end_precision = end.precision
            normalized_end = (
                self._format_month(end_min) if end.month is not None else None
            )
            if end_min > cutoff_index or end_max > cutoff_index:
                warnings.append("end_after_evaluation_reference")
                end_min = min(end_min, cutoff_index)
                end_max = min(end_max, cutoff_index)

        normalized_start = (
            self._format_month(start_min) if start.month is not None else None
        )
        if start_min > cutoff_index:
            return ExperiencePeriodFact(
                key=key,
                source_line=source_line,
                source_date_text=source_date_text,
                raw_start=raw_start,
                raw_end=raw_end,
                normalized_start_month=normalized_start,
                normalized_end_month=normalized_end,
                start_precision=start.precision,
                end_precision=end_precision,
                resolved_cutoff_month=self._format_month(cutoff_index),
                usable_for_reference=False,
                warnings=[*warnings, "start_after_evaluation_reference"],
                unavailable_reason="经历开始时间晚于投递时间",
            )
        if end_max < start_min:
            return ExperiencePeriodFact(
                key=key,
                source_line=source_line,
                source_date_text=source_date_text,
                raw_start=raw_start,
                raw_end=raw_end,
                normalized_start_month=normalized_start,
                normalized_end_month=normalized_end,
                start_precision=start.precision,
                end_precision=end_precision,
                resolved_cutoff_month=self._format_month(cutoff_index),
                usable_for_reference=False,
                warnings=[*warnings, "end_before_start"],
                unavailable_reason="经历结束时间早于开始时间",
            )

        exact = start.month is not None and (present or (end and end.month is not None))
        lower = max(0, end_min - start_max)
        upper = max(0, end_max - start_min)
        if not exact:
            warnings.append("year_precision_only")
        return ExperiencePeriodFact(
            key=key,
            source_line=source_line,
            source_date_text=source_date_text,
            raw_start=raw_start,
            raw_end=raw_end,
            normalized_start_month=normalized_start,
            normalized_end_month=normalized_end,
            start_precision=start.precision,
            end_precision=end_precision,
            resolved_cutoff_month=self._format_month(cutoff_index),
            duration_months=lower if exact else None,
            duration_months_lower_bound=None if exact else lower,
            duration_months_upper_bound=None if exact else upper,
            usable_for_reference=True,
            warnings=warnings,
            unavailable_reason=None,
        )

    def _fact_interval_bounds(
        self, fact: ExperiencePeriodFact
    ) -> tuple[int, int, int, int]:
        cutoff = self._parse_year_month(fact.resolved_cutoff_month)
        if fact.normalized_start_month is not None:
            start_min = start_max = self._parse_year_month(fact.normalized_start_month)
        else:
            year = int(fact.raw_start.strip().rstrip("年"))
            start_min = self._month_index(year, 1)
            start_max = self._month_index(year, 12)
        if fact.end_precision == "present":
            end_min = end_max = cutoff
        elif fact.normalized_end_month is not None:
            parsed_end = self._parse_year_month(fact.normalized_end_month)
            end_min = end_max = min(parsed_end, cutoff)
        else:
            end = self._parse_endpoint(fact.raw_end)
            assert end is not None
            end_min = min(self._month_index(end.year, 1), cutoff)
            end_max = min(self._month_index(end.year, 12), cutoff)
        return start_min, start_max, end_min, end_max

    @classmethod
    def _parse_endpoint(cls, raw: str) -> _ParsedEndpoint | None:
        value = raw.strip()
        month_match = cls._MONTH.fullmatch(value)
        if month_match:
            month = int(month_match.group("month") or month_match.group("cn_month"))
            if not 1 <= month <= 12:
                return None
            return _ParsedEndpoint(value, int(month_match.group("year")), month, "month")
        year_match = cls._YEAR.fullmatch(value)
        if year_match:
            return _ParsedEndpoint(value, int(year_match.group("year")), None, "year")
        return None

    @staticmethod
    def _month_index(year: int, month: int) -> int:
        return year * 12 + month - 1

    @staticmethod
    def _format_month(index: int) -> str:
        return f"{index // 12:04d}-{index % 12 + 1:02d}"

    @classmethod
    def _parse_year_month(cls, value: str) -> int:
        year, month = value.split("-", 1)
        return cls._month_index(int(year), int(month))

    @staticmethod
    def _union_duration(intervals: Iterable[tuple[int, int]]) -> int:
        ordered = sorted((start, end) for start, end in intervals if end >= start)
        if not ordered:
            return 0
        total = 0
        current_start, current_end = ordered[0]
        for start, end in ordered[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                total += current_end - current_start
                current_start, current_end = start, end
        return total + current_end - current_start


experience_period_service = ExperiencePeriodService()
