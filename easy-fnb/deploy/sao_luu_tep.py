"""Sao lưu các tệp không phải SQLite trong DATA_DIR lên Cloud Storage (bucket BACKUP_BUCKET, tiền tố tep/).

    python sao_luu_tep.py restore   tải mọi tệp đã sao lưu về DATA_DIR (chạy trước khi máy chủ khởi động)
    python sao_luu_tep.py sync      cứ SYNC_S giây đẩy tệp mới hoặc đã đổi, xoá bản sao của tệp đã xoá

Chỉ dùng trên Cloud Run: token lấy từ metadata server của service account. Hai file SQLite do Litestream lo.
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

DATA = Path(os.environ.get('DATA_DIR') or '/tmp/easyfnb')
BUCKET = os.environ['BACKUP_BUCKET']
PREFIX = 'tep/'
KEEP = ('config.json', 'staff', 'chat')   # cấu hình, ảnh nhận dạng nhân viên, ảnh trong nhóm chat
SYNC_S = 10
API = f'https://storage.googleapis.com/storage/v1/b/{BUCKET}/o'
UPLOAD = f'https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o'
TOKEN_URL = 'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token'

_token, _exp = None, 0.0


def headers(c):
    global _token, _exp
    if not _token or time.monotonic() > _exp:
        d = c.get(TOKEN_URL, headers={'Metadata-Flavor': 'Google'}, timeout=5).raise_for_status().json()
        _token, _exp = d['access_token'], time.monotonic() + d.get('expires_in', 300) - 60
    return {'Authorization': f'Bearer {_token}'}


def local_files():
    out = {}
    for name in KEEP:
        p = DATA / name
        files = [p] if p.is_file() else (f for f in p.rglob('*') if f.is_file()) if p.is_dir() else []
        for f in files:
            if f.name.endswith('.tmp') or '.tmp.' in f.name:
                continue
            st = f.stat()
            out[f.relative_to(DATA).as_posix()] = (st.st_mtime_ns, st.st_size)
    return out


def restore(c):
    n, token = 0, None
    while True:
        params = {'prefix': PREFIX, 'fields': 'items(name),nextPageToken'}
        if token:
            params['pageToken'] = token
        d = c.get(API, params=params, headers=headers(c), timeout=30).raise_for_status().json()
        for it in d.get('items', []):
            rel = it['name'][len(PREFIX):]
            dest = DATA / rel
            if not rel or dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            r = c.get(f'{API}/{quote(it["name"], safe="")}', params={'alt': 'media'}, headers=headers(c), timeout=60)
            dest.write_bytes(r.raise_for_status().content)
            n += 1
        token = d.get('nextPageToken')
        if not token:
            break
    print(f'sao_luu_tep: khôi phục {n} tệp', flush=True)


def push(c, rel):
    data = (DATA / rel).read_bytes()
    if rel.endswith('.json'):
        json.loads(data)   # đang ghi dở thì bỏ qua, lượt sau đẩy lại
    c.post(UPLOAD, params={'uploadType': 'media', 'name': PREFIX + rel}, content=data,
           headers=headers(c), timeout=60).raise_for_status()


def sync(c):
    known = local_files()   # vừa khôi phục xong: bản trên bucket đã giống bản ở máy
    while True:
        time.sleep(SYNC_S)
        try:
            now = local_files()
            for rel, sig in now.items():
                if known.get(rel) != sig:
                    try:
                        push(c, rel)
                        known[rel] = sig
                    except (ValueError, OSError):
                        pass
            for rel in [r for r in known if r not in now]:
                c.delete(f'{API}/{quote(PREFIX + rel, safe="")}', headers=headers(c), timeout=30)
                known.pop(rel)
        except Exception as e:   # mất mạng hay token lỗi: thử lại lượt sau, không bao giờ làm sập container
            print(f'sao_luu_tep: lỗi {e}', flush=True)


if __name__ == '__main__':
    DATA.mkdir(parents=True, exist_ok=True)
    with httpx.Client() as client:
        try:
            {'restore': restore, 'sync': sync}[sys.argv[1]](client)
        except Exception as e:
            print(f'sao_luu_tep: {sys.argv[1]} lỗi {e}', flush=True)
