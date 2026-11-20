# process-breakdown-kit

노래 한 곡이 흐르는 동안 빈 작업 화면이 완성 영상 한 장면이 되어 가는 과정을 커서들이 만들어 보이는 모션그래픽, 그 영상을 만든 코드와 프롬프트입니다.
「아낌없이 주는 두루」 채널의 〈봄의 자리를 만들자〉 제작기(「빈 화면에서 완성까지 | 프로세스 브레이크다운」)를 이 코드로 렌더했어요. 원곡 영상은 https://youtu.be/AwQ-kufw6GQ 입니다.

실제 작업 기록을 그대로 옮긴 게 아니라 완성되어 가는 순서를 연출한 영상이에요. 처음에 옛 그림이 한 붓으로 그려졌다가 빨간 동그라미로 고침 요청을 받고 지워진 뒤 지금 캐릭터가 그려지고, 가사와 HUD가 타자 칸에서 생기고, 그림 선이 입체 점으로 떠올라 창 빛과 새싹 빛을 따져 본 다음, 파란 명암을 거쳐 마지막 가사에 맞춰 스포이트로 색이 번집니다.

## 어떻게 만들었나
- 그림 원본: GPT 이미지 모델 · 노래: SUNO · 이 화면을 그리는 코드: Claude
- 화면 한 장은 시각 T 하나로 정해지는 함수입니다(`window.__seekTo(T)`). 같은 입력이면 몇 번을 찍어도 프레임이 같아요. Playwright로 한 장씩 찍고 ffmpeg로 곡과 붙입니다.
- 움직임의 곡선은 GSAP `parseEase` 만 씁니다. CSS 트랜지션이나 시계 기반 애니메이션은 쓰지 않아요.
- 연출 방향은 [PROMPTS.md](PROMPTS.md) 에 순서대로 남겼어요. 판마다 어떤 말로 무엇이 바뀌었는지 보입니다.

## 준비물
- Python 3.10 이상 · `pip install -r requirements.txt`
- ffmpeg (PATH에 있어야 함)
- Node 18 이상 · `npm install` 다음 `npx playwright install chromium`
- 글꼴: 맑은 고딕 · Noto Serif KR (윈도우 기준. 없으면 비슷한 글꼴로 바뀌어 보여요)

## 넣을 것
`inputs/` 에 그림 · 곡 · 가사 시각 같은 재료를 넣습니다. 파일 이름과 형식은 [inputs/README.md](inputs/README.md) 에 있어요. 이 저장소에는 그림 · 음악 · 가사 전문이 들어 있지 않습니다. 화면 연출에 쓴 몇 낱말(메모장 낱말 · 고쳐 쓰는 마지막 줄 · 설명란 크레딧 · 고정 댓글)만 `page/index.html` 안에 글로 있어요.

## 돌리기
```
python prep/prep_scene.py     # 선화 지도(한 붓 순서) · 색 덩어리 · 명암 · 막대 표 · 악기 줄 · 완성 영상 프레임 → build/
python prep/prep_extra.py     # 옛 그림 한 붓 지도 · 기준 카드 선화 · 다국어 가사 → build/
python prep/prep_cloud.py     # 그림 선 점 구름(깊이 · 법선) → build/cloud.js
node render.js --stills 3,66,124,150          # 몇 장만 먼저 보기 → build/still_*.jpg
node render.js --tag my_video                 # 25fps 1920×1080 → out/my_video.mp4
```
`page/index.html` 을 브라우저로 열고 콘솔에서 `__seekTo(66)` 처럼 불러도 그 순간이 그려집니다(파일 열기 허용 옵션이 필요할 수 있어요).

## 이 영상에 맞춰진 값
코드는 이 한 곡 · 이 한 그림에 맞춰 짰습니다. 다른 곡과 그림으로 하려면 `page/index.html` 위쪽에서 아래를 고치면 돼요.
- 일정: 가사 줄 번호와 초로 정한 일감 시각(`job(...)`). 예: 스포이트 채색은 29~32번째 줄(`Lt(28)`~`Lt(31)`)에 맞춰 떨어집니다.
- 칸 자리: `ZN`(가사 · 아이콘 · 음파 · 바탕 칸 좌표, 1920×1080 기준)
- 광원 자리: `LW`(창 빛) · `LS`(새싹 빛)
- 카메라: `CAMK`(시각마다 다가가는 자리와 배율)
- 화면 글: `DESC`(설명란 크레딧) · `CM.text`(고정 댓글) · `MEMO`(메모장 낱말) · 댓글 칸의 채널 이름
- 선 추출 정도: `prep/prep_scene.py` 의 문턱값(그림마다 다르게 잡힘)

## 확인
같은 입력으로 `--stills` 를 두 번 돌려 `build/still_*.jpg` 의 해시가 같은지 보면 결정론이 깨졌는지 알 수 있어요. 이 영상은 4장 모두 같았습니다.

## 라이선스
코드는 MIT ([LICENSE](LICENSE)). 그림 · 음악 · 가사는 이 저장소에 없고 각자 권리를 가진 재료를 넣어 쓰면 됩니다. 쓰는 라이브러리는 [NOTICE.md](NOTICE.md) 에 적었어요.

---

**English (short).** Code and direction prompts for a motion-graphic "process breakdown": while one song plays, unnamed cursors build an empty canvas into a finished music-video frame (single-stroke line art, correction requests, typed HUD, a point-cloud light study, blue value pass, eyedropper color reveal, pinned comment). Every frame is a pure function of time (`window.__seekTo(T)`), rendered with Playwright + ffmpeg. Media (art, song, lyrics) is not included; put your own files in `inputs/`. Original art by an OpenAI image model, music by SUNO, rendering code written with Claude. Code: MIT.
