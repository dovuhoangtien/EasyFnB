import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f, encoding='utf-8'))
    print('#', f)
    for key, res in d.items():
        for nguon in ('gallery', 'probe'):
            parts = []
            for c, trs in res['track'].items():
                tr = [r for r in trs.values() if r['n'] >= 5]
                nv = [r for r in tr if r['that'] == 'nv']; kh = [r for r in tr if r['that'] == 'khach']
                cuoi = f'{nguon}_cuoi'; tl = f'{nguon}_ti_le_nv'; doi = f'{nguon}_doi'
                nv_ok = sum(bool(r[cuoi]) for r in nv); kh_sai = sum(bool(r[cuoi]) for r in kh)
                t_nv = sum((r[tl] or 0) * r['n'] for r in nv) / max(1, sum(r['n'] for r in nv))
                t_kh = sum((r[tl] or 0) * r['n'] for r in kh) / max(1, sum(r['n'] for r in kh))
                flips = sum(r[doi] for r in tr)
                parts.append(f"{c[:2]}: NV đúng {nv_ok}/{len(nv)} (thời gian {t_nv:.0%}), khách bị gắn NV {kh_sai}/{len(kh)} (thời gian {t_kh:.0%}), đổi {flips}")
            print(f'  {key:<12} {nguon:<8}', ' | '.join(parts))
