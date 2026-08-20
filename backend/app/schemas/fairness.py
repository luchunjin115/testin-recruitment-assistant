"""Shared fairness rules used by human recruitment decisions."""

FAIRNESS_PROHIBITED_TERMS = (
    "年龄",
    "性别",
    "民族",
    "婚姻",
    "已婚",
    "未婚",
    "婚育",
    "生育",
    "照片",
    "籍贯",
    "985",
    "211",
    "双一流",
    "学校声誉",
    "名校",
    "age",
    "gender",
    "race",
    "ethnicity",
    "marital",
    "married",
    "pregnancy",
    "birthplace",
    "prestigious university",
)


__all__ = ["FAIRNESS_PROHIBITED_TERMS"]
