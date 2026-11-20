# -*- coding: utf-8 -*-
"""v8 3D 빛 분석 재료(◆작업자 11-20 「3D 광원 분석 연출 아쉬움」): 그림 선이 그대로 입체로 떠오르는 점 구름.
선화 픽셀(map_a) → 깊이: 벽(뒤) · 창(더 뒤) · 왼쪽 집(멀리) · 바닥(앞으로 기울어짐) · 두루(실루엣 거리로 부풀림) · 새싹 · 제목(조금 앞)
출력 build/cloud.js: window.C3 = {n, b64 Int16 x,y,z,nx,ny,nz(×1000) · kind(0 배경 · 1 두루 · 2 제목)}
좌표: X = (x-960)/540 · Y = -(y-540)/540(화면 높이 = 2) · Z 앞이 +
사용: python prep/prep_cloud.py
"""
import base64, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8")
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(KIT, "inputs")
OUT = os.path.join(KIT, "build")
D2 = json.loads(open(os.path.join(OUT, "data.js"), encoding="utf-8").read().split("\n")[0].replace("window.D2 = ", "").rstrip(";"))
A = np.asarray(Image.open(os.path.join(OUT, "map_a.png")).convert("RGBA"))
MW, MH = D2["MW"], D2["MH"]
reg = A[..., 0] >> 2
line = A[..., 0] > 0
mask = np.asarray(Image.open(os.path.join(IN, "subject_mask.png")).convert("L").resize((MW, MH), Image.LANCZOS), np.float32) / 255
duru = mask > 0.35
# 두루 부풀림 높이(실루엣 안쪽 거리) · 법선
dt = ndimage.distance_transform_edt(ndimage.binary_dilation(duru, iterations=6))
hgt = np.sqrt(dt / dt.max())
hgt = ndimage.gaussian_filter(hgt, 4)
gy, gx = np.gradient(hgt * 0.55 * 540)                  # 픽셀당 높이 변화(같은 단위로)
yy, xx = np.mgrid[0:MH, 0:MW]
rng = np.random.default_rng(3)
ys, xs = np.nonzero(line)
keep = rng.random(len(xs)) < min(1.0, 52000 / len(xs))
ys, xs = ys[keep], xs[keep]
X = (xs - 960) / 540.0
Y = -(ys - 540) / 540.0
r = reg[ys, xs]
kind = np.zeros(len(xs), np.int8)
Z = np.full(len(xs), -0.55)
NX, NY, NZ = np.zeros(len(xs)), np.zeros(len(xs)), np.ones(len(xs))
fl = ys > 0.72 * MH                                        # 바닥: 앞으로 기울어짐
Z[fl] = -0.55 + (ys[fl] - 0.72 * MH) / (0.28 * MH) * 1.25
NY[fl], NZ[fl] = 0.8, 0.6
win = (xs > 0.78 * MW) & (ys < 0.32 * MH)                  # 창(벽 안쪽으로)
Z[win] = -0.75
far = (xs < 0.27 * MW) & (ys > 0.28 * MH) & (ys < 0.76 * MH)   # 왼쪽 집들(멀리)
Z[far] = -1.5
sp = np.hypot(xs - 1001.7, ys - 885.7) < 70                # 새싹
Z[sp] = 0.25
du = duru[ys, xs] | (r == 1) | (r == 2)
kind[du] = 1
Z[du] = 0.12 + hgt[ys[du], xs[du]] * 0.55
n = np.stack([-gx[ys[du], xs[du]], gy[ys[du], xs[du]], np.ones(du.sum())], 1)
n /= np.linalg.norm(n, axis=1, keepdims=True)
NX[du], NY[du], NZ[du] = n[:, 0], n[:, 1], n[:, 2]
ti = r == D2["TITLE_REG"]
kind[ti] = 2
Z[ti] = 0.08
q = lambda v: base64.b64encode(np.clip(np.round(v * 1000), -32767, 32767).astype(np.int16).tobytes()).decode()
C3 = {"n": int(len(xs)), "x": q(X), "y": q(Y), "z": q(Z), "nx": q(NX), "ny": q(NY), "nz": q(NZ), "k": base64.b64encode(kind.tobytes()).decode()}
open(os.path.join(OUT, "cloud.js"), "w", encoding="utf-8").write("window.C3 = " + json.dumps(C3) + ";")
print("points", len(xs), "duru", int(du.sum()), "floor", int(fl.sum()), "far", int(far.sum()))
