import imaplib
import yaml
import time
from omegaconf import OmegaConf
import sys

def test_imap_configs():
    print("开始测试多IMAP邮箱配置")
    
    # 读取配置文件
    try:
        with open('config/config.yaml', 'r', encoding='utf-8') as file:
            config_str = file.read()
            print("成功读取配置文件")
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return False
    
    # 解析配置文件
    try:
        config = OmegaConf.create(yaml.safe_load(config_str))
        print("成功解析配置文件")
    except Exception as e:
        print(f"解析配置文件失败: {e}")
        return False
    
    # 检查是否有custom_email_addresses字段
    if not hasattr(config.register.email_server, 'custom_email_addresses'):
        print("配置中缺少custom_email_addresses字段")
        return False
    
    # 测试每个IMAP配置
    email_configs = config.register.email_server.custom_email_addresses
    print(f"找到 {len(email_configs)} 个邮箱配置")
    
    for i, email_config in enumerate(email_configs):
        print(f"\n--- 测试邮箱配置 {i+1} ---")
        try:
            email = email_config.email
            imap_server = email_config.imap_server
            imap_port = email_config.imap_port
            username = email_config.username
            password = email_config.password
            
            print(f"邮箱: {email}")
            print(f"IMAP服务器: {imap_server}:{imap_port}")
            print(f"用户名: {username}")
            
            # 连接IMAP服务器
            print(f"尝试连接IMAP服务器...")
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            print("连接成功")
            
            # 登录邮箱
            print(f"尝试登录邮箱...")
            mail.login(username, password)
            print("登录成功")
            
            # 选择收件箱
            print("尝试选择收件箱...")
            mail.select('inbox')
            print("选择收件箱成功")
            
            # 搜索邮件
            print("尝试搜索邮件...")
            _, data = mail.uid("SEARCH", None, 'ALL')
            email_ids = data[0].split()
            print(f"找到 {len(email_ids)} 封邮件")
            
            mail.logout()
            print("已关闭连接")
            print(f"邮箱 {email} 测试成功")
        except Exception as e:
            print(f"邮箱 {email if 'email' in locals() else '未知'} 测试失败: {e}")
    
    print("\n所有配置测试完成")
    return True

if __name__ == "__main__":
    test_imap_configs() 