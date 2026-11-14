"""Test không dùng mạng và không dùng khoá thật: bỏ các biến mà tệp .env vừa nạp, để máy có .env hay
không thì test vẫn chạy như nhau."""
import os

for _ten in ('GEMINI_API_KEY', 'GEMINI_MODEL', 'GEMINI_VERIFY_MODEL', 'KIE_API_KEY'):
    os.environ.pop(_ten, None)
