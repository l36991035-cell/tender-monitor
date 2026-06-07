# notify.py
import os
import smtplib
import ssl
from email.message import EmailMessage

_SMTP_HOST = 'smtp.gmail.com'
_SMTP_PORT = 587
_MAX_PER_MSG = 20


def _send_email(subject: str, body: str) -> None:
    user = os.environ.get('GMAIL_USER', '')
    password = os.environ.get('GMAIL_APP_PASSWORD', '')
    if not user or not password:
        print('[notify] GMAIL_USER or GMAIL_APP_PASSWORD not set, skipping')
        return
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = user
        msg.set_content(body)
        ctx = ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(user, password)
            smtp.send_message(msg)
        print(f'[notify] Email sent: {subject}')
    except Exception as e:
        print(f'[notify] Email failed: {e}')


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


def notify_new_tenders(matches: list[dict]) -> None:
    if not matches:
        return
    subject = f'【標案監控】今日 {len(matches)} 筆相符標案'
    lines = [subject, '=' * 40]
    for m in matches[:_MAX_PER_MSG]:
        lines += [
            f'關鍵字：{m["matched_keyword"]}',
            f'標案名稱：{m["name"]}',
            f'機關：{m["unit"]}',
            f'公告日期：{m["date"]}',
            '',
        ]
    if len(matches) > _MAX_PER_MSG:
        lines.append(f'⋯ 共 {len(matches)} 筆，其餘請至前端查看')
    _send_email(subject, '\n'.join(lines))


def notify_awards(awarded: list[dict]) -> None:
    if not awarded:
        return
    subject = f'【決標通知】{len(awarded)} 筆標案已決標'
    lines = [subject, '=' * 40]
    for a in awarded[:_MAX_PER_MSG]:
        price = f'{a.get("award_price", "")} 元' if a.get('award_price') else '—'
        lines += [
            f'標案名稱：{a["name"]}',
            f'機關：{a["unit"]}',
            f'得標廠商：{a.get("award_vendor", "—")}',
            f'決標金額：{price}',
            f'決標日期：{a.get("award_date", "—")}',
            '',
        ]
    _send_email(subject, '\n'.join(lines))
