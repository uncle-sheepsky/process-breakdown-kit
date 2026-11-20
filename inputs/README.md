# inputs/

이 폴더에 재료를 넣습니다. 저장소에는 이 설명 파일만 올라가요.

| 파일 | 필수 | 내용 |
|---|---|---|
| `art.png` | ✓ | 완성 그림(1920×1080 권장). 선화 · 색 덩어리 · 명암을 여기서 뽑아요 |
| `subject_mask.png` | ✓ | 주인공 실루엣(흰색 = 주인공). 주인공 선은 흰색, 배경 선은 파란색으로 그려지고 점 구름에서 주인공만 부풀어요 |
| `title_mask.png` | ✓ | 그림에 박힌 제목 글씨 자리(흰색). 처음엔 밋밋한 글자로 쳤다가 점으로 흩어져 이 손글씨 자리로 날아갑니다 |
| `song.wav` | ✓ | 곡 전체. 영상 길이 = 곡 길이 |
| `lyrics.json` | ✓ | 가사 줄과 시각. `{"lines": [{"text": "...", "t0": 2.76, "t1": 4.46, "words": [{"text": "...", "t": 2.76, "t_end": 3.5}]}]}` |
| `final.mp4` | ✓ | 완성 영상(1920×1080, 곡과 같은 시각). 스포이트로 색이 번질 때 이 영상이 드러나요 |
| `old_sketch.png` | ✓ | 고침 요청 받을 「잘못 나온」 옛 그림 |
| `reference.png` | ✓ | 「이렇게」 기준 그림(고침 요청 카드 · 댓글 프로필) |
| `stems/*.wav` 또는 `*.mp3` |  | 악기별 트랙. 이름에 vocals · keyboard · guitar · bass · drums 같은 낱말이 있으면 한국어 이름으로 바뀌어 줄로 나와요. 없으면 곡 한 줄 |
| `i18n.json` |  | 다국어 가사 `{"names": {"ko": "한국어", "en": "English"}, "lines": {"ko": [...], "en": [...]}}` (줄 수 = 가사 줄 수) |
| `icons/drums.png` … `woodwinds.png` |  | 악기 아이콘 7개(drums · percussion · bass · guitar · keyboard · brass · woodwinds) |
| `breath/f0001.png` … `f0080.png` |  | 입김 연속 그림(13.75fps) |
| `shadow_overlay.png` |  | 그림자 층(알파). 3D 빛 분석 뒤 파란 빗금으로 내려앉아요 |
| `thumbs/1.png` … `6.png` |  | 끝에서 고르는 썸네일 후보 |
