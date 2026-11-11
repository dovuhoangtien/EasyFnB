"""Danh sách cử chỉ dùng chung cho chương trình nhắc lệnh, công cụ gán nhãn và bộ chấm.

Mỗi cử chỉ: mã, câu nhắc diễn viên, có phải gọi phục vụ không, tỉ trọng khi bốc lệnh.
"Gọi" là lớp dương; còn lại là cử chỉ dễ nhầm (lớp âm). `vay_ban` vốn mơ hồ (nhìn khung
xương khó phân biệt với vẫy gọi), nên bộ chấm báo riêng.
"""

CU_CHI = [
    # mã, câu nhắc, là gọi?, tỉ trọng
    ('goi_mot_tay', 'Giơ MỘT tay cao gọi phục vụ, giữ khoảng 2 giây', True, 10),
    ('goi_nhanh', 'Giơ tay gọi NHANH (khoảng 1 giây) rồi hạ', True, 6),
    ('goi_vay', 'Giơ tay VẪY gọi phục vụ', True, 6),
    ('goi_ngang_dau', 'Giơ tay ngang đầu (không duỗi thẳng) để gọi', True, 5),
    ('goi_hai_tay', 'Giơ HAI tay gọi phục vụ', True, 2),
    ('vuot_toc', 'Vuốt tóc', False, 8),
    ('gai_dau', 'Gãi đầu', False, 7),
    ('uong', 'Cầm ly lên uống', False, 8),
    ('chi_tay', 'Chỉ tay về phía xa (chỉ món, chỉ cửa)', False, 6),
    ('vuon_vai', 'Vươn vai', False, 5),
    ('nghe_dt', 'Đưa điện thoại lên tai nghe', False, 5),
    ('chinh_kinh_mu', 'Chỉnh kính hoặc chỉnh mũ, chỉnh tóc mái', False, 4),
    ('lau_mat', 'Lau miệng / lau mặt bằng khăn giấy', False, 4),
    ('chong_cam', 'Chống cằm, tay đỡ má', False, 4),
    ('vay_ban', 'Vẫy chào bạn ở bàn khác (KHÔNG gọi phục vụ)', False, 3),
]

MA = [c[0] for c in CU_CHI]
NHAC = {c[0]: c[1] for c in CU_CHI}
LA_GOI = {c[0]: c[2] for c in CU_CHI}
TI_TRONG = {c[0]: c[3] for c in CU_CHI}
MO_HO = {'vay_ban'}

# loại ghế: gần camera, xa camera, sát mép khung hình
LOAI_GHE = ('gan', 'xa', 'mep')


def phong_chu(size):
    """Font có dấu tiếng Việt cho chữ vẽ bằng PIL."""
    from PIL import ImageFont
    for f in ('C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()
