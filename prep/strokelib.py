# -*- coding: utf-8 -*-
"""한 붓 선 순서(◆작업자 11-20: 선이 갈라지며 퍼지지 않고 펜 끝 하나가 선 하나를 쭉 이어 그리듯).
선 뼈대(1px)를 한 붓으로 걷는다: 이웃 중 꺾임이 가장 작은 쪽 · 막히면 가장 가까운 남은 점(끝점 우선)으로 펜을 들어 옮김.
stroke_order(mask) → (픽셀마다 0~1 순서 · 촘촘한 펜 경로 [[순서, x, y], …] · 끝점)"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def stroke_order(maskk, start_xy=None):
    sk = skeletonize(maskk)
    pts = np.argwhere(sk)
    if len(pts) == 0:
        return np.full(maskk.shape, -1.0), [], None
    idx = {tuple(p): i for i, p in enumerate(pts)}
    deg = np.array([sum((p[0] + dy, p[1] + dx) in idx for dy, dx in NB8) for p in pts])
    tree = cKDTree(pts)
    seen = np.zeros(len(pts), bool)
    ends = np.where(deg <= 1)[0]
    if start_xy is None:
        cand = ends if len(ends) else np.arange(len(pts))
        cur = cand[np.argmin(pts[cand, 0] * 4 + pts[cand, 1])]
    else:
        cur = tree.query([start_xy[1], start_xy[0]])[1]
    seq, cost, c = [], [], 0.0
    d0 = (0, 0)
    while True:
        seen[cur] = True
        seq.append(cur)
        cost.append(c)
        y, x = pts[cur]
        best, bd = None, None
        for dy, dx in NB8:
            j = idx.get((y + dy, x + dx))
            if j is None or seen[j]:
                continue
            turn = (dy - d0[0]) ** 2 + (dx - d0[1]) ** 2
            if best is None or turn < bd:
                best, bd = (j, (dy, dx)), turn
        if best is not None:
            cur, d0 = best[0], best[1]
            c += 1.0
            continue
        if seen.all():
            break
        k = 16
        while True:
            dd, ii = tree.query(pts[cur], k=min(k, len(pts)))
            ii = np.atleast_1d(ii)
            dd = np.atleast_1d(dd)
            ok = [(d - (3 if deg[i] <= 1 else 0), i) for d, i in zip(dd, ii) if not seen[i]]
            if ok:
                dist_, nxt = min(ok)
                break
            if k >= len(pts):
                rest = np.where(~seen)[0]
                nxt = rest[np.argmin(((pts[rest] - pts[cur]) ** 2).sum(1))]
                dist_ = float(np.hypot(*(pts[nxt] - pts[cur])))
                break
            k *= 4
        c += min(max(dist_, 1), 40) * 0.35
        cur, d0 = nxt, (0, 0)
    total = max(c, 1.0)
    sko = np.full(maskk.shape, -1.0)
    for i, cc in zip(seq, cost):
        sko[tuple(pts[i])] = cc / total
    _, (iy, ix) = ndimage.distance_transform_edt(~sk, return_indices=True)
    order = np.where(maskk, sko[iy, ix], -1.0)
    path, last = [], None
    for n, (i, cc) in enumerate(zip(seq, cost)):
        y, x = pts[i]
        jump = last is not None and abs(cc - last[2]) > 1.01
        if n % 4 == 0 or jump or n == len(seq) - 1:
            if jump and last is not None:
                path.append([round(last[2] / total, 5), int(last[1]), int(last[0])])
            path.append([round(cc / total, 5), int(x), int(y)])
        last = (y, x, cc)
    ey, ex = pts[seq[-1]]
    return order, path, (int(ex), int(ey))
