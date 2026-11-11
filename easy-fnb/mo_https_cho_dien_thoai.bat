@echo off
:: Mo duong ham HTTPS de iPhone dung duoc camera (Safari chan camera o http). Can internet.
:: Cua so se in dia chi dang https://xxxx.trycloudflare.com ; tren iPhone mo: <dia chi>/phat?cam=cam1
:: Mo nhan vien: <dia chi>/nv-tt/lan
type nul > "%TEMP%\fnb_empty.yml"
"C:\Program Files (x86)\cloudflared\cloudflared.exe" --config "%TEMP%\fnb_empty.yml" tunnel --url http://localhost:8080 --no-autoupdate