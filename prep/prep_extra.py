# -*- coding: utf-8 -*-
"""프로세스 브레이크다운 재료 만들기 (2/3) — 고침 요청 그림 · 다국어 가사
 inputs/old_sketch.png  먼저 「잘못 나온」 그림(주인공 자리에 한 붓으로 그려졌다가 빨간 동그라미 → 지워짐) → build/sheep_map.png
 inputs/reference.png   「이렇게」 기준 그림(고침 요청 옆에 붙는 카드 · 고정 댓글 프로필) → build/sticker_line.png(흰 선 · 투명 바탕)
 inputs/i18n.json       (선택) {"names": {"ko": "한국어", "en": "English", ...}, "lines": {"ko": [...32줄], "en": [...]}} → build/extra.js
사용: python prep/prep_extra.py   (prep_scene.py 다음)
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
IN, OUT = os.path.join(KIT, "inputs"), os.path.join(KIT, "build")
sys.path.insert(0, HERE)
from strokelib import stroke_order

D2 = json.loads(open(os.path.join(OUT, "data.js"), encoding="utf-8").read().split("\n")[0].replace("window.D2 = ", "").rstrip(";"))


def flat(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    return im.convert("RGB")


def strength(rgb, s1, s2):
    lum = np.asarray(rgb, np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    loc = ndimage.gaussian_filter(lum, s1)
    sm = ndimage.gaussian_filter(lum, s2)
    return np.maximum(np.clip(loc - lum, 0, None) * 1.6, np.hypot(ndimage.sobel(sm, 1), ndimage.sobel(sm, 0)) / 5)


# 기준 카드: 흰 선 · 투명 바탕 300×300
ref = flat(os.path.join(IN, "reference.png"))
ref.thumbnail((300, 300), Image.LANCZOS)
a = np.clip((strength(ref, 2.0, 0.8) - 10) / 18, 0, 1)
card = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
o = np.zeros(a.shape + (4,), np.uint8)
o[..., :3] = 255
o[..., 3] = (a * 255).round()
card.alpha_composite(Image.fromarray(o, "RGBA"), ((300 - a.shape[1]) // 2, (300 - a.shape[0]) // 2))
card.save(os.path.join(OUT, "sticker_line.png"))

# 옛 그림: 주인공 자리 크기로 · 한 붓 순서(R = 선 · G/B = 16비트 순서)
bx0, by0, bx1, by1 = D2["duru_bbox"]
side = int(min(bx1 - bx0, by1 - by0))
sk = flat(os.path.join(IN, "old_sketch.png"))
sc = side / max(sk.size)
sk = sk.resize((round(sk.size[0] * sc), round(sk.size[1] * sc)), Image.LANCZOS)
ln = strength(sk, 3.0, 1.4) > 16
ln = ndimage.binary_opening(ln, structure=np.ones((2, 2)))
lab, n = ndimage.label(ln, structure=np.ones((3, 3)))
sz = ndimage.sum(np.ones_like(lab), lab, index=np.arange(n + 1))
ln &= sz[lab] >= 30
order, pen, _ = stroke_order(ln)
hh, ww = ln.shape
m = np.zeros((hh, ww, 4), np.uint8)
o16 = np.clip(order * 65535, 0, 65535).round().astype(np.uint32)
m[..., 0] = np.where(ln, 255, 0)
m[..., 1] = o16 >> 8
m[..., 2] = o16 & 255
m[..., 3] = 255
Image.fromarray(m, "RGBA").save(os.path.join(OUT, "sheep_map.png"))
ox = (bx0 + bx1) // 2 - ww // 2
oy = (by0 + by1) // 2 - hh // 2

# 다국어 가사(없으면 가사 한 언어)
p = os.path.join(IN, "i18n.json")
if os.path.exists(p):
    I = json.load(open(p, encoding="utf-8"))
    names, lines = I["names"], I["lines"]
else:
    names, lines = {"ko": "한국어"}, {"ko": [l["text"] for l in D2["lyr"]]}
X2 = {"sheep": {"x": int(ox), "y": int(oy), "w": int(ww), "h": int(hh), "pen": pen, "n": int(ln.sum())}, "langs": names, "i18n": lines}
open(os.path.join(OUT, "extra.js"), "w", encoding="utf-8").write("window.X2 = " + json.dumps(X2, ensure_ascii=False) + ";")
print("old sketch", ww, hh, "px", int(ln.sum()), "· langs", len(names))
