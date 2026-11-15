#!/usr/bin/env python3
"""旧マルラジの回（ep-YYYY-MM-DD 等）を本家フォーマットへ変換する。
usage: convert_ep.py <ep_dir> <YYYY-MM-DD>
- sentences.json / timings.json / episode.json を読み、episodes/<date>-ja.json を書く
- 話者（who）は speaker に変換（tan -> makoto）
- 構成： opening=天気トピック範囲まで / news=各トピック(+ピックアップ) / closing=残り
"""
import json, sys, os

SRC = sys.argv[1]; DATE = sys.argv[2]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sens = json.load(open(f'{SRC}/sentences.json', encoding='utf-8'))
tims = json.load(open(f'{SRC}/timings.json', encoding='utf-8'))
meta = json.load(open(f'{SRC}/episode.json', encoding='utf-8'))
assert len(sens) == len(tims), (len(sens), len(tims))
MP = {'tan': 'makoto', 'amane': 'amane', 'kaede': 'kaede'}
def line(i):
    s = sens[i]
    return {'say': s.get('read') or s['show'], 'show': s['show']}
def timed(i):
    s = sens[i]
    d = {'show': s['show'], 'start': tims[i]['start'], 'end': tims[i]['end'], 'speaker': MP[s['who']]}
    if s.get('motion'): d['motion'] = s['motion']
    return d
topics = meta['topics']
segs = {g['key']: g['line'] for g in meta['segments']}
n = len(sens)
news_starts = topics[1]['from']
opening = [line(i) for i in range(0, news_starts)]
cards = []
for ti, t in enumerate(topics[1:]):
    end = t['to']
    nxt = topics[ti + 2]['from'] if ti + 2 < len(topics) else (segs.get('pickup', n))
    end = max(end, nxt - 1) if nxt - 1 > end else end  # fold gap lines into this card
    cards.append({'label': t['title'], 'points': t.get('bullets', []),
                  'url': t.get('url', ''), 'lines': [line(i) for i in range(t['from'], end + 1)]})
rest_start = topics[-1]['to'] + 1
main_caster = None
mid_closing = None  # 新形式（締めの挨拶の後におまけトラック）用: (締め開始行, おまけ開始行)
if 'pickup' in segs:
    p = segs['pickup']; f = segs.get('freetalk', n)
    main_caster = MP[sens[p]['who']]
    intro = sens[p]['show']
    label = 'ピックアップ'
    if '持参トピックです。' in intro:
        tail = intro.split('持参トピックです。', 1)[1].split('。')[0]
        if tail: label = 'ピックアップ：' + tail
    ppts = {}
    ppf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pickup-points.json')
    if os.path.exists(ppf): ppts = json.load(open(ppf, encoding='utf-8'))
    sign_pre = next((i for i in range(p, f) if '今日のマルラジオはここまで' in sens[i]['show']), None) if 'freetalk' in segs else None
    pend = sign_pre if sign_pre is not None else f
    cards.append({'label': label, 'points': ppts.get(DATE, []), 'url': '', 'lines': [line(i) for i in range(p, pend)]})
    rest_start = f
    if sign_pre is not None: mid_closing = (sign_pre, f)
if 'freetalk' in segs:
    f = segs['freetalk']
    pts = {}
    pf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freetalk-points.json')
    if os.path.exists(pf): pts = json.load(open(pf, encoding='utf-8'))
    fentry = pts.get(DATE, [])
    if isinstance(fentry, dict): fpts, fabout = fentry.get('points', []), fentry.get('about')
    else: fpts, fabout = fentry, None
    def ftcard(flines):
        c = {'label': '姉妹トーク', 'freetalk': True, 'points': fpts, 'url': '', 'lines': flines}
        if fabout is not None: c['about'] = fabout
        return c
    if mid_closing is not None:
        cards.append(ftcard([line(i) for i in range(f, n)]))
    else:
        sign = next((i for i in range(f, n) if '今日のマルラジオはここまで' in sens[i]['show']), None)
        if sign is not None:
            cards.append(ftcard([line(i) for i in range(f, sign)]))
            rest_start = sign
closing = [line(i) for i in range(mid_closing[0], mid_closing[1])] if mid_closing else [line(i) for i in range(rest_start, n)]
# segments (player parts) from timed boundaries
def tstart(i): return tims[i]['start']
parts = [{'kind': 'opening', 'start': 0.0, 'end': tstart(news_starts)}]
idx = news_starts
for ci, c in enumerate(cards):
    if mid_closing is not None and c.get('freetalk'):
        parts.append({'kind': 'closing', 'start': tstart(mid_closing[0]), 'end': tstart(mid_closing[1])})
        idx += mid_closing[1] - mid_closing[0]
    cnt = len(c['lines'])
    parts.append({'kind': 'news', 'index': ci, 'start': tstart(idx), 'end': tstart(idx + cnt) if idx + cnt < n else tims[-1]['end']})
    idx += cnt
if rest_start < n and mid_closing is None:
    parts.append({'kind': 'closing', 'start': tstart(rest_start), 'end': tims[-1]['end']})
ep = {'format': 'monoradio/news-1', 'title': f"{meta['date_label']}の放送", 'date': DATE, 'lang': 'ja', 'main': main_caster,
      'seconds': tims[-1]['end'], 'opening': opening, 'news': cards, 'closing': closing,
      'lines_timed': [timed(i) for i in range(n)], 'segments': parts,
      'made_at': __import__('datetime').datetime.now(__import__('datetime').timezone(__import__('datetime').timedelta(hours=9))).isoformat(timespec='seconds')}
out = f'{ROOT}/episodes/{DATE}-ja.json'
json.dump(ep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"{DATE}: opening {len(opening)} / cards {len(cards)} / closing {len(closing)} / total {n} / {ep['seconds']:.1f}s -> {out}")
