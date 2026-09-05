import os
import smtplib
import ssl
from email.message import EmailMessage

_SMTP_HOST = 'smtp.gmail.com'
_SMTP_PORT = 587
_MAX_PER_MSG = 20


def notify_new_tenders(matches: list[dict]) -> None:
    if not matches:
        print('[notify] 無符合標案，跳過寄信')
        return

    user = os.environ.get('GMAIL_USER', '')
    password = os.environ.get('GMAIL_APP_PASSWORD', '')
    if not user or not password:
        print('[notify] GMAIL_USER 或 GMAIL_APP_PASSWORD 未設定，跳過寄信')
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

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = user
        msg.set_content('\n'.join(lines))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(user, password)
            smtp.send_message(msg)
        print(f'[notify] Email 已寄出：{subject}')
    except Exception as e:
        print(f'[notify] Email 寄送失敗：{e}')
