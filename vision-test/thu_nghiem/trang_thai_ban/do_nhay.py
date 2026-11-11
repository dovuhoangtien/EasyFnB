#!/usr/bin/env python
"""Độ nhạy theo từng tham số của bản đề xuất (K6), và chấm tách đôi bàn clip 01.

    python thu_nghiem/trang_thai_ban/do_nhay.py
"""
from bien_the import COMBOS, eval_labelled, eval_static, eval_stress, eval_latency

K6 = COMBOS['K6 a4 + vào 1 s, ra 5 s']


def line(tag, p, seeds=10):
    a30 = eval_labelled(p, 'out_v4', toc01=30)[0]
    a60 = eval_labelled(p, 'out_v4', toc01=60)[0]
    v3 = eval_labelled(p, 'out_v3', toc01=30)[0]
    st = eval_static(p)
    nz = eval_stress(p, seeds=seeds)
    la = eval_latency(p)
    print(f"{tag:<28} v4(toc30) {a30['dung']}/{a30['dung_tre']} sót {a30['bo_sot']} thừa {a30['doi_thua']} | "
          f"v4(toc60) {a60['dung']}/{a60['dung_tre']} sót {a60['bo_sot']} | v3 {v3['dung']}/{v3['dung_tre']} | "
          f"tĩnh {st['su_kien_nham']} | nhiễu {nz['su_kien_nham_moi_phut']}/ph KMảo {nz['khach_moi_ao_moi_phut']}/ph | "
          f"trễ vào {la['tre_khach_moi']} ra {la['tre_khach_roi']} dọn {la['tre_da_don']}", flush=True)


def main():
    line('cũ', None)
    line('K6', K6)
    for v in (0, 2, 3, 8, 10, 20):
        line(f'K6, ra {v} s', dict(K6, giu_ra=v))
    for v in (0, 2, 3):
        line(f'K6, vào {v} s', dict(K6, giu_vao=v))
    for v in (0.5, 0.45, 0.4, 0.3, 0.25):
        line(f'K6, bẩn tắt {v}', dict(K6, ban_sach=v))
    for v in (0.25, 1.0):
        line(f'K6, tau bẩn {v} win', dict(K6, tau_ban=v))
    print('\nTách đôi bàn clip 01 (cộng cả clip 02 vào mỗi nửa):')
    for half in (('B1', 'B3'), ('B2', 'B4')):
        tabs = {('01_phong_an_goc_cao', x) for x in half} | {('02_quan_ngoai_troi_nhieu_ban', x) for x in ('B1', 'B2', 'B3')}
        for tag, p in (('cũ', None), ('K6', K6), ('K1 (ra 10 s)', COMBOS['K1 a4+b3'])):
            for out in ('out_v4', 'out_v3'):
                a = eval_labelled(p, out, toc01=30, tables=tabs)[0]
                print(f"  {'+'.join(half)} {tag:<14} {out}: {a['dung']}/{a['tong']} chặt, {a['dung_tre']} cho trễ, "
                      f"đổi {a['doi_may']} (thật {a['doi_that']}, thừa {a['doi_thua']}, sót {a['bo_sot']})")


if __name__ == '__main__':
    main()
