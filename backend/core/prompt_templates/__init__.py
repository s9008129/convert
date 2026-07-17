"""領域模板提示詞模組。

每個 domain 一個模組（如 procurement），內含該領域的系統提示詞、
萃取增補規則與術語表。新增領域＝新增一個模組＋在
backend/core/templates.py 註冊一筆 MeetingTemplate。
"""
