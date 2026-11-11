import json,sys
from pathlib import Path
for d in sys.argv[1:]:
    print(d)
    for f in sorted(Path(d).glob('*/su_kien.json')):
        s=json.loads(f.read_text(encoding='utf-8'))
        print(f"  {f.parent.name[:2]} người_tb={s['nguoi_tb']:<4} max={s['nguoi_max']:<3} ms_người={s['ms_nguoi']:<5} ms_nhỏ={s['ms_model_nho']} khung/giây(cũ)={s['khung_moi_giay']:<5} fps_thật={s['fps_thuc']} vram_torch={s.get('vram_torch_mb')}")
