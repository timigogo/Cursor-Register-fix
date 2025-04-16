import time
import imaplib
import email
# import re # 不再需要 re
from email.policy import default
from datetime import datetime

from ._email_server import EmailServer

# 移除验证链接模式
# CURSOR_VERIFY_LINK_PATTERN = ...

class Imap(EmailServer):

    def __init__(self, imap_server, imap_port, username, password, email_to = None):
        self.mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        self.mail.login(username, password)

        self.email_to = email_to # 保留 email_to，可能用于日志或将来更精细的过滤
        
        self.mail.select('inbox')
        _, data = self.mail.uid("SEARCH", None, 'ALL')
        email_ids = data[0].split()
        self.latest_id = email_ids[-1] if len(email_ids) != 0 else None

    def fetch_emails_since(self, since_timestamp):

        # Get the latest email by id
        self.mail.select('inbox')
        search_criteria = f'UID {int(self.latest_id) + 1}:*' if self.latest_id else 'ALL'
        _, data = self.mail.uid("SEARCH", None, search_criteria)
        email_ids = data[0].split()
        if len(email_ids) == 0:
            return None
        self.latest_id = email_ids[-1]
        
        # Fetch the email message by ID
        _, data = self.mail.uid('FETCH', self.latest_id, '(RFC822)')
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email, policy=default)

        # Extract common headers
        from_header = msg.get('From')
        to_header = msg.get('To')
        subject_header = msg.get('Subject')
        date_header = msg.get('Date')

        # 移除严格的 To: 检查，允许处理转发邮件
        # if self.email_to not in (None, to_header):
        #    return None
        # print(f"[IMAP Debug] Fetched email - To: {to_header}, Subject: {subject_header}")

        email_datetime = datetime.strptime(date_header.replace(' (UTC)', ''), '%a, %d %b %Y %H:%M:%S %z').timestamp()
        if email_datetime < since_timestamp:
            return None

        # 获取邮件正文 (恢复简单逻辑，让调用者解析)
        text_part = msg.get_body(preferencelist=('plain',))
        html_part = msg.get_body(preferencelist=('html',))
        
        content = "" # 初始化为空字符串
        # 优先获取纯文本，如果获取不到再尝试HTML (或根据需要调整优先级)
        if text_part:
             content = text_part.get_content()
        elif html_part:
             content = html_part.get_content()
        # 如果需要原始 payload, 可以添加 else 分支
        # else:
        #    try:
        #        content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        #    except:
        #        content = "" # 获取失败则为空

        # 移除链接搜索逻辑
        # match = re.search(CURSOR_VERIFY_LINK_PATTERN, content_to_search)
        # if match: ...
        # else: return None
        
        # 直接返回包含内容的字典，供 cursor_register.py 解析
        return {
            "from": from_header,
            "to": to_header, # 仍然返回原始 To 头
            "date": date_header,
            "subject": subject_header,
            "content": content # 返回提取到的邮件内容
            # 不再返回 "verification_link"
        }
    
    def wait_for_new_message(self, delay=5, timeout=60):
        start_time = time.time()

        while time.time() - start_time <= timeout:
            try:
                email = self.fetch_emails_since(start_time)
                if email is not None:
                    return email
            except:
                pass
            time.sleep(delay)

        return None
