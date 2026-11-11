"""Chạy lại các phép thử Hub/Gemini của kiem_thu.py trên bản server ĐÃ VÁ (bản sao, không phải server thật).

    python kiem_ban_va.py <thư mục chứa gói server đã vá>

Thư mục đó phải có server/{__init__,gemini,hub}.py sau khi áp diff trong KET_QUA.md.
"""
import sys
import unittest
from pathlib import Path

patched = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(patched))
import server.gemini as pg  # noqa: E402
import server.hub as ph  # noqa: E402

assert Path(ph.__file__).resolve().parent.parent == patched, ph.__file__

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiem_thu as kt  # noqa: E402
import xac_minh_v2 as xm  # noqa: E402


def hub_factory(data_dir, gemini, clock=None, timeout_s=None):
    h = ph.Hub(data_dir, gemini)
    if clock is not None:
        h.breaker = ph.CircuitBreaker(3, 60.0, clock)
    ph.VERIFY_TIMEOUT_S = 2.5 if timeout_s is None else timeout_s
    return h


class PatchedGemini(pg.Gemini):
    pass


# Thay các lớp thử nghiệm bằng bản vá
xm.HubV2 = hub_factory
xm.decide = pg.decide
xm.CircuitBreaker = ph.CircuitBreaker
xm.GeminiV2 = PatchedGemini

if __name__ == '__main__':
    suite = unittest.TestSuite()
    load = unittest.defaultTestLoader.loadTestsFromTestCase
    for c in (kt.TestDecide, kt.TestBreaker, kt.TestHubVerdicts, kt.TestHubResilience, kt.TestClient):
        suite.addTests(load(c))
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if r.wasSuccessful() else 1)
