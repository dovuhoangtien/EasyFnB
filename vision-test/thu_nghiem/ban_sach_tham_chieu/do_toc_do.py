"""Bước 5: đo thời gian và bộ nhớ GPU cho mỗi lần chấm bàn (FP16, như pipeline), 4 bàn một lượt như clip 01.

    python thu_nghiem/ban_sach_tham_chieu/do_toc_do.py
"""
import json
import time

import torch

from chung import HERE

N_BAN, K, LAP = 4, 5, 50


def bench(fn):
    for _ in range(5):
        fn()
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(LAP):
        fn()
    torch.cuda.synchronize()
    return (time.perf_counter() - t0) / LAP * 1000


def knn(q, bank):
    """q [B,P,C], bank [B,K*P,C] -> điểm top 1% cho từng bàn."""
    d = 1 - torch.einsum('bpc,bnc->bpn', q, bank).max(-1).values
    n = max(1, q.shape[1] // 100)
    return d.topk(n, dim=1).values.mean(1)


@torch.no_grad()
def main():
    import timm

    from clip_cls import backbone
    res = {}
    dev = 'cuda'
    base = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    visual, _, text = backbone(dev, 'pe_core_s16')
    x = torch.randn(N_BAN, 3, 384, 384, device=dev).half()
    ref_g = torch.nn.functional.normalize(torch.randn(N_BAN, K, 512, device=dev), dim=-1).half()
    trunk = visual.trunk

    def cls():
        f = torch.nn.functional.normalize(visual(x).float(), dim=-1)
        return (100 * f @ text.T).softmax(-1)

    def cls_global():
        f = torch.nn.functional.normalize(visual(x).float(), dim=-1)
        return (100 * f @ text.T).softmax(-1), 1 - torch.einsum('bc,bkc->bk', f.half(), ref_g).max(-1).values

    bank_pe = torch.nn.functional.normalize(torch.randn(N_BAN, K * 576, 384, device=dev), dim=-1).half()

    def cls_patch():
        last, inter = trunk.forward_intermediates(x, indices=[7], norm=False, output_fmt='NLC')
        g = visual.head(trunk.forward_head(last))
        f = torch.nn.functional.normalize(g.float(), dim=-1)
        p = (100 * f @ text.T).softmax(-1)
        t = inter[0]
        t = torch.nn.functional.normalize(t[:, -576:].float(), dim=-1).half()
        return p, knn(t, bank_pe)

    res['phan_loai_hien_tai_ms_4_ban'] = round(bench(cls), 2)
    res['phan_loai_+_toan_anh_ms_4_ban'] = round(bench(cls_global), 2)
    res['phan_loai_+_va_pe_ms_4_ban'] = round(bench(cls_patch), 2)
    res['vram_pe_mb'] = round((torch.cuda.max_memory_allocated() - base) / 2**20)
    res['bo_nho_tham_chieu_pe_moi_ban_kb'] = round(K * 576 * 384 * 2 / 1024)
    m0 = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    dino = timm.create_model('vit_small_patch14_dinov2.lvd142m', pretrained=True, num_classes=0,
                             img_size=448).to(dev).eval().half()
    xd = torch.randn(N_BAN, 3, 448, 448, device=dev).half()
    bank_d = torch.nn.functional.normalize(torch.randn(N_BAN, K * 1024, 384, device=dev), dim=-1).half()

    def dino_patch():
        f = dino.forward_features(xd)[:, dino.num_prefix_tokens:]
        return knn(torch.nn.functional.normalize(f.float(), dim=-1).half(), bank_d)

    res['them_dinov2_va_ms_4_ban'] = round(bench(dino_patch), 2)
    res['vram_them_dinov2_mb'] = round((torch.cuda.max_memory_allocated() - m0) / 2**20)
    res['gpu'] = torch.cuda.get_device_name()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (HERE / 'toc_do.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
