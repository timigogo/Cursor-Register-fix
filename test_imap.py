import imaplib
import time

def test_imap_connection():
    print("开始测试IMAP连接")
    imap_server = "imap.gmail.com"
    imap_port = 993
    username = "liuw48674@gmail.com"
    password = "ikgu cpqj bfld kigy"
    email_to = "liuw48674@gmail.com"
    
    try:
        print(f"尝试连接IMAP服务器: {imap_server}:{imap_port}")
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        print("IMAP服务器连接成功")
        
        print(f"尝试登录邮箱: {username}")
        mail.login(username, password)
        print("登录成功")
        
        print("尝试选择收件箱")
        mail.select('inbox')
        print("收件箱选择成功")
        
        print("尝试搜索邮件")
        _, data = mail.uid("SEARCH", None, 'ALL')
        email_ids = data[0].split()
        print(f"找到 {len(email_ids)} 封邮件")
        
        if len(email_ids) > 0:
            latest_id = email_ids[-1]
            print(f"最新邮件ID: {latest_id}")
            
            print("获取最新邮件内容")
            _, data = mail.uid('FETCH', latest_id, '(RFC822)')
            print("邮件内容获取成功")
        
        print("IMAP功能测试成功")
        return True
    except Exception as e:
        print(f"IMAP测试失败: {e}")
        return False

if __name__ == "__main__":
    test_imap_connection() 