# notify.py
import os
import requests

LINE_API = 'https://notify-api.line.me/api/notify'
_MAX_TENDERS_PER_MSG = 10   # LINE Notify has a 1000-char limit per message


def _send(token: str, message: str) -> None:
    try:
        resp = requests.post(
            LINE_API,
            headers={'Authorization': f'Bearer {token}'},
            data={'message': message},
            timeout=10,
        )
        if resp.status_code == 200:
            print(f'[notify] LINE sent OK')
        else:
            print(f'[notify] LINE error {resp.status_code}: {resp.text[:100]}')
    except Exception as e:
        print(f'[notify] LINE failed: {e}')


def match_keywords(records: list[dict], keywords: list[str]) -> list[dict]:
    """Return records whose name or unit contains any active keyword."""
    results = []
    seen: set[str] = set()
    for r in records:
        for kw in keywords:
            if kw in r.get('name', '') or kw in r.get('unit', ''):
                if r['id'] not in seen:
                    seen.add(r['id'])
                    results.append({**r, 'matched_keyword': kw})
                break
    return results


def notify_new_tenders(token: str, matches: list[dict]) -> None:
    if not token:
        print('[notify] LINE_NOTIFY_TOKEN not set, skipping')
        return
    if not matches:
        return

    header = f'\n【標案監控】今日 {len(matches)} 筆相符標案\n'
    lines = []
    for m in matches[:_MAX_TENDERS_PER_MSG]:
        lines.append(
            f'\n🔍 {m["matched_keyword"]}\n'
            f'📋 {m["name"]}\n'
            f'🏢 {m["unit"]}\n'
            f'📅 {m["date"]}'
        )
    body = ''.join(lines)
    if len(matches) > _MAX_TENDERS_PER_MSG:
        body += f'\n\n⋯ 共 {len(matches)} 筆，其餘請至前端查看'

    _send(token, header + body)


def notify_awards(token: str, awarded: list[dict]) -> None:
    """Send LINE notification for newly awarded tenders."""
    if not token or not awarded:
        return

    header = f'\n【決標通知】{len(awarded)} 筆標案已決標\n'
    lines = []
    for a in awarded[:_MAX_TENDERS_PER_MSG]:
        price = f'{a.get("award_price", "")}元' if a.get('award_price') else '—'
        lines.append(
            f'\n📋 {a["name"]}\n'
            f'🏢 {a["unit"]}\n'
            f'🏆 {a.get("award_vendor", "—")}\n'
            f'💰 {price}\n'
            f'📅 {a.get("award_date", "—")}'
        )
    _send(token, header + ''.join(lines))
