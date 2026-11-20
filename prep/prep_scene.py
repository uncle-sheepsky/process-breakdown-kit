# -*- coding: utf-8 -*-
"""프로세스 브레이크다운 재료 만들기 (1/3) — inputs/ → build/
 선화 지도 map_a.png(R = 조각×4+단계 · G/B = 16비트 한 붓 순서) · 색 덩어리 map_b.png · 파란 명암 tone.png ·
 data.js(조각 · 펜 경로 · 색 씨앗 · 막대 표 · 악기 줄 · 가사) · final/(완성 영상 프레임 · 채색 하이라이트 조금 앞부터)
사용: python prep/prep_scene.py
"""
import base64, glob, json, os, subprocess, sys
from collections import deque
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.cluster.vq import kmeans2

sys.stdout.reconfigure(encoding="utf-8")
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(KIT, "inputs")
OUT = os.path.join(KIT, "build")
os.makedirs(OUT, exist_ok=True)
W, H = 1120, 630                      # 화면 속 영상 칸 크기(1920×1080 의 0.5833배)
SR = 44100
rng = np.random.default_rng(11)
LABEL = {"backing vocals": "백보컬", "vocals": "보컬", "keyboard": "건반", "guitar": "기타", "bass": "베이스",
         "drums": "드럼", "percussion": "퍼커션", "brass": "금관", "woodwinds": "목관", "fx": "FX"}


def pcm(path, sr=SR, ch=2):
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "pipe:1"], capture_output=True, check=True).stdout
    return np.frombuffer(b, np.float32).reshape(-1, ch)


# ── 1) 소리: 곡(inputs/song.wav) · 악기별 트랙(inputs/stems/*.wav|mp3 — 있으면 악기마다 한 줄 · 없으면 곡 한 줄)
mix = pcm(os.path.join(IN, "song.wav"))
END = round(len(mix) / SR, 3)
files = sorted(glob.glob(os.path.join(IN, "stems", "*.wav")) + glob.glob(os.path.join(IN, "stems", "*.mp3")))


def label(p):
    n = os.path.splitext(os.path.basename(p))[0]
    for k, v in LABEL.items():
        if k in n.lower():
            return v
    return n


srcs = [(label(p), pcm(p)) for p in files] or [("곡", mix)]
order = list(LABEL.values())
srcs.sort(key=lambda x: order.index(x[0]) if x[0] in order else 99)
COLS = 1400
lanes = []
for name, a in srcs:
    m = np.abs(a[:len(mix)]).max(1)
    e = np.linspace(0, len(m), COLS + 1).astype(int)
    lanes.append({"ko": name, "pk": [float(m[e[i]:e[i + 1]].max()) if e[i + 1] > e[i] else 0.0 for i in range(COLS)]})
gm = max(max(l["pk"]) for l in lanes) or 1.0
for l in lanes:
    l["pk"] = [round(x / gm, 3) for x in l["pk"]]
L = json.load(open(os.path.join(IN, "lyrics.json"), encoding="utf-8"))["lines"]
VON = [[0.0, END + 1.0]]                # 목소리는 처음부터 끝까지(내레이션 없는 판)

# 막대 48개 표(30fps · 로그 대역 · 원곡 마스터 기준)
mono = mix.mean(1)
FPS, NB = 30, 48
hop = SR // FPS
nf = int(END * FPS)
edges = np.geomspace(60, 12000, NB + 1)
fr = np.fft.rfftfreq(4096, 1 / SR)
win = np.hanning(4096)
tab = np.zeros((nf, NB), np.float32)
for f in range(nf):
    c = f * hop
    blk = mono[max(0, c - 2048):c + 2048]
    blk = np.pad(blk, (0, 4096 - len(blk)))
    P = np.abs(np.fft.rfft(blk * win)) ** 2
    for k in range(NB):
        s = (fr >= edges[k]) & (fr < edges[k + 1])
        tab[f, k] = P[s].mean() if s.any() else 0
db = 10 * np.log10(tab + 1e-10)
db = np.clip((db - np.percentile(db, 20)) / (np.percentile(db, 99.5) - np.percentile(db, 20)), 0, 1)
for f in range(1, nf):                                                 # 빠르게 오르고 천천히 내림
    db[f] = np.maximum(db[f], db[f - 1] * 0.86)
bars_b64 = base64.b64encode((db * 255).round().astype(np.uint8).tobytes()).decode()

# ── 2) 선화: 원본 배경 그림(bg_clear_v03) — 두루 = 흰 선 · 배경 = 파란 선 / 단계 1(큰 윤곽) 2(둘째 선) 3(잔결)
# v4: 선 · 채색 지도는 1920×1080(카메라가 다가가도 선이 또렷하게) · 덩어리 나누기만 1120×630 에서 하고 키움
HW, HH = 1920, 1080
SC = HW / W
src = Image.open(os.path.join(IN, "art.png")).convert("RGB")
art = src.resize((W, H), Image.LANCZOS)
col = np.asarray(art, np.float32)
mask = np.asarray(Image.open(os.path.join(IN, "subject_mask.png")).convert("L").resize((W, H), Image.LANCZOS), np.float32) / 255
duru = mask > 0.35
colH = np.asarray(src.resize((HW, HH), Image.LANCZOS), np.float32)
maskH = np.asarray(Image.open(os.path.join(IN, "subject_mask.png")).convert("L").resize((HW, HH), Image.LANCZOS), np.float32) / 255
duruH = maskH > 0.35
lum = colH @ np.array([0.299, 0.587, 0.114], np.float32)
loc = ndimage.gaussian_filter(lum, 2.5 * SC)
sm = ndimage.gaussian_filter(lum, 1.0 * SC)
sob = np.hypot(ndimage.sobel(sm, 1), ndimage.sobel(sm, 0)) * SC
ink = np.clip(loc - lum, 0, None)                                       # 둘레보다 어두운 가는 선
strength = np.maximum(ink * 1.6, sob / 5.0)
dedge = duruH & ~ndimage.binary_erosion(duruH, iterations=3)            # 두루 실루엣 테두리
cand = (strength > 9) | dedge
cand = ndimage.binary_opening(cand, structure=np.ones((2, 2))) | dedge
mx = ndimage.maximum_filter(np.where(cand, strength, 0), size=5)
line = cand & ((strength >= 0.7 * mx) | dedge)
lab0, n0 = ndimage.label(line, structure=np.ones((3, 3)))
sz = ndimage.sum(np.ones_like(lab0), lab0, index=np.arange(n0 + 1))
line &= sz[lab0] >= 20
s_on = strength[line]
q1, q2 = np.percentile(s_on, [62, 30])
tier = np.zeros((HH, HW), np.uint8)
tier[line] = np.where(strength[line] >= q1, 1, np.where(strength[line] >= q2, 2, 3))
tier[dedge & line] = 1
# v9(◆작업자 「첫 선화의 지붕 · 벽면 선 누락」): 부드러운 색 경계(지붕 끝 · 벽 모서리 · 벽돌)를 큰 눈금 경계로 한 번 더 — 한 줄로 가늘게(경사 방향 비최대 억제)
gxB = np.zeros_like(lum); gyB = np.zeros_like(lum); sobB = np.zeros_like(lum)
for ch in range(3):                                   # 밝기만이 아니라 색 경계도(어두운 하늘 ↔ 어두운 벽 · 처마)
    smc = ndimage.gaussian_filter(colH[..., ch], 1.6 * SC)
    gxc, gyc = ndimage.sobel(smc, 1), ndimage.sobel(smc, 0)
    mc = np.hypot(gxc, gyc)
    pick = mc > sobB
    gxB[pick], gyB[pick], sobB[pick] = gxc[pick], gyc[pick], mc[pick]
farD = ~ndimage.binary_dilation(duruH, iterations=4)
candB = (sobB > np.percentile(sobB[farD], 92)) & farD
angB = (np.rad2deg(np.arctan2(gyB, gxB)) + 180) % 180
nms = np.zeros_like(candB)
for a0, a1, dy, dx in [(0, 22.5, 0, 1), (157.5, 180.1, 0, 1), (22.5, 67.5, 1, 1), (67.5, 112.5, 1, 0), (112.5, 157.5, 1, -1)]:
    sel = (angB >= a0) & (angB < a1)
    n1 = np.roll(np.roll(sobB, dy, 0), dx, 1)
    n2 = np.roll(np.roll(sobB, -dy, 0), -dx, 1)
    nms |= sel & (sobB >= n1) & (sobB >= n2)
lineB = ndimage.binary_dilation(candB & nms, structure=np.ones((2, 2)))
labB, nB = ndimage.label(lineB, structure=np.ones((3, 3)))
szB = ndimage.sum(np.ones_like(labB), labB, index=np.arange(nB + 1))
lineB &= (szB[labB] >= 60) & ~line
tier[lineB] = 1
line |= lineB
# 색 덩어리 경계(어두운 하늘 ↔ 벽 · 처마 · 지붕 끝): 9색으로 나눈 판의 경계를 선으로(이미 선 옆이면 뺌) — 따로 씨앗(전체 난수 순서 안 건드림)
r2 = np.random.default_rng(91)
yyL, xxL = np.mgrid[0:H, 0:W]
fS = np.stack([col[..., 0], col[..., 1], col[..., 2], yyL / H * 40, xxL / W * 30], -1).reshape(-1, 5) / 255
cS, _ = kmeans2(fS[r2.choice(len(fS), 40000, replace=False)].astype(np.float64), 9, seed=11, minit="++")
flS = ndimage.median_filter(((fS[:, None, :] - cS[None]) ** 2).sum(-1).argmin(-1).reshape(H, W), 7)
flSH = np.asarray(Image.fromarray(flS.astype(np.uint8)).resize((HW, HH), Image.NEAREST)).astype(np.int16)
cd = np.linalg.norm(cS[:, None, :3] - cS[None, :, :3], axis=-1)        # 두 덩어리 색 차이(하늘 띠끼리처럼 비슷하면 선 아님)
up, lf = np.roll(flSH, 1, 0), np.roll(flSH, 1, 1)
bnd = ((flSH != up) & (cd[flSH, up] > 0.115)) | ((flSH != lf) & (cd[flSH, lf] > 0.115))
bnd = ndimage.binary_dilation(bnd, structure=np.ones((2, 2))) & farD & ~ndimage.binary_dilation(line, iterations=5)
labS, nS = ndimage.label(bnd, structure=np.ones((3, 3)))
szS = ndimage.sum(np.ones_like(labS), labS, index=np.arange(nS + 1))
bnd &= szS[labS] >= 90
# 하늘 덩어리의 바깥선 = 지붕 · 처마 · 벽 모서리 · 먼 집 실루엣(하늘 띠끼리는 같은 덩어리로 묶어 선 안 생김)
lumL = col.mean(2)
skyLow = (col[..., 2] > col[..., 0] + 8) & (lumL < 95)                  # 푸르고 어두운 = 밤하늘
skyLow = ndimage.binary_opening(ndimage.binary_closing(skyLow, iterations=3), iterations=3)
labK, nK = ndimage.label(skyLow)
szK = ndimage.sum(np.ones_like(labK), labK, index=np.arange(nK + 1))
skyLow = (labK > 0) & (szK[labK] >= 0.02 * H * W)                     # 큰 하늘 덩어리만(0 = 하늘 아님)
skyH = ndimage.gaussian_filter(np.asarray(Image.fromarray((skyLow * 255).astype(np.uint8)).resize((HW, HH), Image.BILINEAR)).astype(np.float32), 4) > 127   # 계단 없이 매끈하게
skyEdge = skyH & ~ndimage.binary_erosion(skyH, iterations=2)
YYm, XXm = np.mgrid[0:HH, 0:HW]
skyEdge &= (YYm > 14) & (YYm < HH - 14) & (XXm > 14) & (XXm < HW - 14)      # 화면 테두리는 선 아님
labE, nE = ndimage.label(skyEdge, structure=np.ones((3, 3)))
szE = ndimage.sum(np.ones_like(labE), labE, index=np.arange(nE + 1))
skyEdge &= szE[labE] >= 120
bnd |= skyEdge
tier[bnd] = 1
line |= bnd
print("structure lines added", int(lineB.sum()), "region edges", int(bnd.sum()))
# 조각: 두루(머리 · 몸) + 배경을 자리 · 색으로 12덩어리
yy, xx = np.mgrid[0:H, 0:W]
reg = np.zeros((H, W), np.int32)
dy0 = np.argwhere(duru)[:, 0]
dsplit = np.percentile(dy0, 45)
reg[duru & (yy < dsplit)] = 1
reg[duru & (yy >= dsplit)] = 2
feat = np.stack([xx / W * 1.4, yy / H * 1.4, col[..., 0] / 255, col[..., 1] / 255, col[..., 2] / 255], -1)
bgpx = ~duru
sample = feat[bgpx][rng.choice(bgpx.sum(), 30000, replace=False)]
cent, _ = kmeans2(sample.astype(np.float64), 12, seed=5, minit="++")
d2 = ((feat[..., None, :] - cent[None, None]) ** 2).sum(-1)
reg[bgpx] = 3 + d2[bgpx].argmin(-1)
NREG = 3 + len(cent)
# 제목 글씨(배경 그림에 박힌 손글씨)는 따로 한 조각 — 처음엔 밋밋한 글자로 치고, 나중에 손글씨 선으로 바꿈
tmask = np.asarray(Image.open(os.path.join(IN, "title_mask.png")).convert("L").resize((W, H), Image.LANCZOS), np.float32) / 255
tmask = ndimage.binary_dilation(tmask > 0.3, iterations=3)
reg[tmask & ~duru] = NREG
TITLE_REG = NREG
NREG += 1
regH = np.asarray(Image.fromarray(reg.astype(np.uint8)).resize((HW, HH), Image.NEAREST)).astype(np.int32)
regH[duruH & (np.mgrid[0:HH, 0:HW][0] < dsplit * SC)] = 1
regH[duruH & (np.mgrid[0:HH, 0:HW][0] >= dsplit * SC)] = 2


def bfs_order(maskk):
    """덩어리마다 위-왼쪽 시작점에서 선을 따라 퍼지는 거리 → 0~1 순서 · 붓 경로"""
    lab, n = ndimage.label(maskk, structure=np.ones((3, 3)))
    order = np.full(maskk.shape, -1.0)
    comps = sorted(range(1, n + 1), key=lambda k: tuple(np.argwhere(lab == k)[0]))
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(n + 1))
    total = sum(sizes[k] for k in comps) or 1
    base, path = 0.0, []
    for k in comps:
        pts = np.argwhere(lab == k)
        s = tuple(pts[0])
        dist = {s: 0}
        q = deque([s])
        while q:
            y, x = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    v = (y + dy, x + dx)
                    if 0 <= v[0] < H and 0 <= v[1] < W and lab[v] == k and v not in dist:
                        dist[v] = dist[(y, x)] + 1
                        q.append(v)
        dmax = max(dist.values()) or 1
        share = sizes[k] / total
        for (y, x), d in dist.items():
            order[y, x] = base + share * d / dmax
        far = sorted(dist.items(), key=lambda kv: kv[1])
        for j in range(0, len(far), max(1, len(far) // 6)):
            (y, x), d = far[j]
            path.append([round(base + share * d / dmax, 4), int(x), int(y)])
        base += share
    return order, sorted(path)


from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def stroke_order(maskk, start_xy=None):
    """◆작업자 11-20: 선이 갈라지며 퍼지지 않고, 펜 끝 하나가 선 하나를 쭉 이어 그리듯.
    선 뼈대(1px)를 한 붓으로 걷는다: 이웃 중 꺾임이 가장 작은 쪽으로 · 막히면 가장 가까운 남은 점으로 펜을 들어 옮김.
    돌려줌: 조각 픽셀마다 0~1 순서(가장 가까운 뼈대 점의 순서) · 촘촘한 펜 경로 · 끝점"""
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
        while True:                                                   # 펜 들기: 가장 가까운 남은 점(끝점이면 더 좋음)
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
    # 조각의 모든 선 픽셀 = 가장 가까운 뼈대 점의 순서
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


ordm = np.zeros((HH, HW), np.float32)
pieces = {}
for r in range(1, NREG):
    for tr in (1, 2, 3):
        mk = line & (regH == r) & (tier == tr)
        if mk.sum() < 24:
            continue
        o, p, _ = stroke_order(mk)
        ordm[mk] = o[mk]
        ys, xs = np.nonzero(mk)
        pieces[f"{r}_{tr}"] = {"r": r, "tier": tr, "n": int(mk.sum()), "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], "pen": p}
A = np.zeros((HH, HW, 4), np.uint8)
o16 = np.clip(ordm * 65535, 0, 65535).round().astype(np.uint32)       # 16비트 순서(한 붓 선이 덩어리로 튀지 않게)
line &= np.isin(regH * 4 + tier, [v["r"] * 4 + v["tier"] for v in pieces.values()])
A[..., 0] = np.where(line, regH * 4 + tier, 0)
A[..., 1] = o16 >> 8
A[..., 2] = o16 & 255
A[..., 3] = 255
Image.fromarray(A, "RGBA").save(os.path.join(OUT, "map_a.png"))

# ── 3) 채색(스포이트): 색 덩어리 7개 · 씨앗(덩어리 안 가장 깊은 곳)에서 번지는 순서
cf = np.stack([col[..., 0], col[..., 1], col[..., 2], yy / H * 90, xx / W * 60], -1).reshape(-1, 5) / 255
cc, _ = kmeans2(cf[rng.choice(len(cf), 40000, replace=False)].astype(np.float64), 7, seed=3, minit="++")
fl = ((cf[:, None, :] - cc[None]) ** 2).sum(-1).argmin(-1).reshape(H, W)
fl = ndimage.median_filter(fl, 5)
flH = np.asarray(Image.fromarray(fl.astype(np.uint8)).resize((HW, HH), Image.NEAREST))
YY, XX = np.mgrid[0:HH, 0:HW]
fills, ford = [], np.zeros((HH, HW), np.float32)
noiseH = ndimage.gaussian_filter(rng.random((HH, HW)), 10)
noiseH = (noiseH - noiseH.min()) / (noiseH.max() - noiseH.min())
for k in range(len(cc)):
    mk = flH == k
    if not mk.any():
        continue
    dt = ndimage.distance_transform_edt(np.pad(mk, 1))[1:-1, 1:-1]          # 화면 가장자리를 씨앗으로 고르지 않게
    sy, sx = np.unravel_index(np.argmax(dt), dt.shape)
    dist = np.hypot(YY - sy, XX - sx)
    o = dist / dist[mk].max() * 0.85 + 0.15 * noiseH
    ford[mk] = o[mk]
    swatch = np.median(col[fl == k], 0)
    fills.append({"id": k, "seed": [int(sx), int(sy)], "area": round(float(mk.mean()), 4), "rgb": [int(v) for v in swatch],
                  "duru": round(float(duruH[mk].mean()), 3), "cy": round(float(YY[mk].mean() / HH), 3)})
B = np.zeros((HH, HW, 4), np.uint8)
B[..., 0] = flH
B[..., 1] = np.clip(ford * 255, 0, 255).round()
B[..., 2] = (ndimage.gaussian_filter(maskH, 1.5) * 255).round()
B[..., 3] = 255
Image.fromarray(B, "RGBA").save(os.path.join(OUT, "map_b.png"))
# 파란 명암(채색 전 단계 · ◆검증단 1차: 간주 동안 가운데가 안 변함 → 색 대신 파란 명암을 칠해 나감)
lumN = np.clip((lum - np.percentile(lum, 2)) / (np.percentile(lum, 99) - np.percentile(lum, 2)), 0, 1) ** 0.85
lo, hi = np.array([10, 16, 36], np.float32), np.array([190, 226, 255], np.float32)
tone = lo[None, None] + (hi - lo)[None, None] * lumN[..., None]
Image.fromarray(np.dstack([tone.round().astype(np.uint8), np.full((HH, HW), 255, np.uint8)]), "RGBA").save(os.path.join(OUT, "tone.png"))

# ── 4) 가사(내레이션 자리는 이 판에서 뺌)
narr = []
need = 0.0
lyr = [{"text": l["text"], "t0": l["t0"], "t1": l["t1"], "words": [[w["text"], w["t"], w.get("t_end", l["t1"])] for w in l["words"]]} for l in L]
D = {"END": END, "W": W, "H": H, "MW": HW, "MH": HH, "NREG": NREG, "TITLE_REG": TITLE_REG,"pieces": pieces, "fills": fills, "lanes": lanes, "COLS": COLS,
     "bars": {"fps": FPS, "nb": NB, "nf": nf, "b64": bars_b64}, "lyr": lyr, "narr": narr, "von": VON,
     "duru_bbox": [int(np.argwhere(duruH)[:, 1].min()), int(np.argwhere(duruH)[:, 0].min()), int(np.argwhere(duruH)[:, 1].max()), int(np.argwhere(duruH)[:, 0].max())]}
open(os.path.join(OUT, "data.js"), "w", encoding="utf-8").write("window.D2 = " + json.dumps(D, ensure_ascii=False) + ";")
# 확인용 미리보기: 선화(단계별 색) · 채색 덩어리
pv = np.zeros((HH, HW, 3), np.uint8) + 12
pv[line & (tier == 1)] = (255, 255, 255)
pv[line & (tier == 2)] = (140, 205, 250)
pv[line & (tier == 3)] = (70, 110, 170)
Image.fromarray(pv).save(os.path.join(OUT, "_preview_lines.png"))
pal = np.array([f["rgb"] for f in fills], np.uint8)
Image.fromarray(pal[np.clip(fl, 0, len(pal) - 1)]).save(os.path.join(OUT, "_preview_fills.png"))
print("END", END, "line px", int(line.sum()), "tiers", [int((tier == k).sum()) for k in (1, 2, 3)], "pieces", len(pieces),
      "fills", len(fills), "narr need s", round(need, 1), "narr room s", round(sum(n["T1"] - n["T0"] for n in narr), 1))

# ── 5) 완성 영상 프레임(inputs/final.mp4 · 30fps) — 스포이트 채색이 시작하기 조금 앞부터만(채색이 번지는 자리에 깔림)
FROM = max(0.0, (L[28]["t0"] if len(L) > 28 else END * 0.72) - 2.0)
fd = os.path.join(OUT, "final")
os.makedirs(fd, exist_ok=True)
n0 = int(round(FROM * 30)) + 1
subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{FROM:.3f}", "-i", os.path.join(IN, "final.mp4"), "-vf", "fps=30,scale=1920:1080",
                "-q:v", "3", "-start_number", str(n0), os.path.join(fd, "f%05d.jpg")], check=True)
finalN = n0 + len(glob.glob(os.path.join(fd, "f*.jpg"))) - 1
open(os.path.join(OUT, "data.js"), "a", encoding="utf-8").write(f"\nwindow.D2.finalN = {finalN};\n")
print("final frames", n0, "..", finalN)
