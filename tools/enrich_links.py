#!/usr/bin/env python3
"""各回のニュースカードに link（出典＋サムネイル）を付ける。
- 画像は旧マルラジの生成サムネイル（thumbs/<date>/NN.jpg）、ピックアップは当番キャスターの固定サムネ
- 記事タイトル/概要は ogp-cache.json（無ければ空で、カードはURL表示にフォールバック）
usage: enrich_links.py [ogp-cache.json のパス]
"""
import json, glob, os, sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = sys.argv[1] if len(sys.argv) > 1 else '/home/hatch/workspace/your_files/maru-radio/ogp-cache.json'
cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
DET = {}
_dp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'details.json')
if os.path.exists(_dp): DET = json.load(open(_dp, encoding='utf-8'))
MAIN = {'2026-11-06': 'amane', '2026-11-09': 'kaede', '2026-11-10': 'makoto',
        '2026-11-11': 'amane', '2026-11-12': 'kaede', '2026-11-13': 'makoto'}
for f in sorted(glob.glob(f'{ROOT}/episodes/*-ja.json')):
    ep = json.load(open(f, encoding='utf-8'))
    date = ep['date']
    pickup_idx = None
    for i, card in enumerate(ep['news']):
        det = DET.get(date, {}).get(str(i))
        if det: card['details'] = det
        if card.get('freetalk'):
            card['link'] = {'title': card['label'], 'image': 'assets/freetalk.jpg'}
        elif card['label'].startswith('ピックアップ'):
            card['link'] = {'title': card['label'], 'image': f"assets/pickup-{MAIN[date]}.jpg"}
            pickup_idx = i
        else:
            url = card.get('url', '')
            ogp = cache.get(url, {})
            host = urlparse(url).hostname or ''
            card['link'] = {'url': url, 'title': ogp.get('title', ''), 'site': host.removeprefix('www.'),
                            'description': ogp.get('description', ''), 'image': f'thumbs/{date}/{i + 1:02d}.jpg'}
    ep['highlight'] = pickup_idx if pickup_idx is not None else 0
    json.dump(ep, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(date, '| cards:', len(ep['news']), '| highlight:', ep['highlight'])
