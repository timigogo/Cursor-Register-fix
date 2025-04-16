import os
import csv
import copy
import argparse
import concurrent.futures
import sys
# import hydra # 暂时注释掉 Hydra，可能不再需要
from faker import Faker
from datetime import datetime
# from omegaconf import OmegaConf, DictConfig # 暂时注释掉 OmegaConf
from DrissionPage import ChromiumOptions, Chromium

# 设置控制台输出编码为UTF-8，避免中文字符编码问题
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.6及更早版本没有reconfigure方法
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# from temp_mails import Tempmail_io, Guerillamail_com # 不再需要临时邮箱
from helper.cursor_register import CursorRegister
from helper.email import * # 仍然需要 IMAP

# Parameters for debugging purpose
hide_account_info = os.getenv('HIDE_ACCOUNT_INFO', 'false').lower() == 'true'
enable_headless = os.getenv('ENABLE_HEADLESS', 'false').lower() == 'true'
enable_browser_log = os.getenv('ENABLE_BROWSER_LOG', 'true').lower() == 'true' or not enable_headless

# 新增：从环境变量读取核心配置
registration_email = os.getenv('REGISTRATION_EMAIL')
receiving_gmail_address = os.getenv('RECEIVING_GMAIL_ADDRESS')
receiving_gmail_app_password = os.getenv('RECEIVING_GMAIL_APP_PASSWORD')
ingest_to_oneapi = os.getenv('INGEST_TO_ONEAPI', 'false').lower() == 'true'
oneapi_url = os.getenv('CURSOR_ONEAPI_URL')
oneapi_token = os.getenv('CURSOR_ONEAPI_TOKEN')
oneapi_channel_url = os.getenv('CURSOR_CHANNEL_URL')
max_workers = int(os.getenv('MAX_WORKERS', '1')) # 虽然现在可能只跑一个，但保留

# 新增：读取 Action 类型
action_type = os.getenv('ACTION_TYPE', 'signup').lower()

# 新增：读取接收邮箱的 IMAP 配置
receiving_imap_server = os.getenv('RECEIVING_IMAP_SERVER')
receiving_imap_port = os.getenv('RECEIVING_IMAP_PORT')
receiving_username = os.getenv('RECEIVING_USERNAME')
receiving_password = os.getenv('RECEIVING_PASSWORD')

def register_cursor_core(reg_email, options):

    try:
        browser = Chromium(options)
    except Exception as e:
        print(e)
        return None
    
    # 直接设置邮箱地址
    email_address = reg_email 
    
    # 使用从环境变量读取的配置实例化 IMAP 服务器
    print(f"[IMAP] Connecting to {receiving_username}@{receiving_imap_server} to find verification for {reg_email}")
    try:
      # 检查配置是否存在
      if not all([receiving_imap_server, receiving_imap_port, receiving_username, receiving_password]):
          raise ValueError("接收邮箱的 IMAP 配置环境变量不完整")
      
      # 注意端口需要是整数
      imap_port_int = int(receiving_imap_port)
      
      email_server = Imap(imap_server=receiving_imap_server, 
                          imap_port=imap_port_int, 
                          username=receiving_username, 
                          password=receiving_password,
                          email_to=reg_email) # 仍然传递注册邮箱用于可能的过滤
    except Exception as e:
        print(f"[IMAP Error] Failed to connect or initialize IMAP for {receiving_username}: {e}")
        if browser:
            browser.quit(force=True, del_data=True)
        return None # 初始化失败，无法继续

    register = CursorRegister(browser, email_server)
    
    # --- 根据 action_type 执行操作 --- 
    token = None
    final_tab = None 
    final_status = False

    if action_type == 'signin':
        print(f"[Register] Action Type: signin. Attempting sign in for {email_address}...")
        tab_signin, status_signin = register.sign_in(email_address)
        token = register.get_cursor_cookie(tab_signin)
        final_tab = tab_signin
        final_status = token is not None
        if not final_status:
            print(f"[Register] Sign in for {email_address} failed or did not yield token.")
            # 对于 signin 失败，通常不需要尝试 signup，因为意味着账号或验证流程有问题

    elif action_type == 'signup':
        print(f"[Register] Action Type: signup. Attempting sign up for {email_address}...")
        tab_signup, status_signup = register.sign_up(email_address)
        token = register.get_cursor_cookie(tab_signup)
        final_tab = tab_signup
        final_status = token is not None
        if not final_status:
             print(f"[Register] Sign up for {email_address} failed or did not yield token.")

    else: # 未知的 action_type
        print(f"[Error] Unknown ACTION_TYPE: {action_type}. Aborting.")
        # final_status 保持 False

    # 浏览器退出逻辑
    # final_status = token is not None # 这行已被上面的逻辑替代
    if not final_status or not enable_browser_log:
        # 确保 final_tab 存在才尝试关闭，尽管 quit 会关闭所有
        # if final_tab: 
        #    try: final_tab.close() except: pass 
        # 退出浏览器实例
        if browser:
            try:
                browser.quit(force=True, del_data=True)
            except Exception as quit_error:
                 print(f"[Warning] Error quitting browser: {quit_error}")

    if final_status and not hide_account_info:
        print(f"[Register] Cursor Email: {email_address}")
        print(f"[Register] Cursor Token: {token}")

    ret = {
        "username": email_address,
        "token": token
    }

    return ret

def register_cursor(reg_email):

    options = ChromiumOptions()
    options.auto_port()
    options.new_env()
    # Use turnstilePatch from https://github.com/TheFalloutOf76/CDP-bug-MouseEvent-.screenX-.screenY-patcher
    turnstile_patch_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "turnstilePatch"))
    options.add_extension(turnstile_patch_path)

    # If fail to pass the cloudflare in headless mode, try to align the user agent with your real browser
    if enable_headless: 
        from platform import platform
        if platform == "linux" or platform == "linux2":
            platformIdentifier = "X11; Linux x86_64"
        elif platform == "darwin":
            platformIdentifier = "Macintosh; Intel Mac OS X 10_15_7"
        elif platform == "win32":
            platformIdentifier = "Windows NT 10.0; Win64; x64"
        # Please align version with your Chrome
        chrome_version = "130.0.0.0"        
        options.set_user_agent(f"Mozilla/5.0 ({platformIdentifier}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36")
        options.headless()

    # 直接打印要注册的邮箱
    print(f"[Register] Start to register account: {reg_email}")

    # 直接调用核心注册函数 (移除旧参数)
    result = register_cursor_core(reg_email, options)
    results = [result] if result and result.get("token") else [] 

    if len(results) > 0:
        formatted_date = datetime.now().strftime("%Y-%m-%d")

        fieldnames = results[0].keys()
        # Write username, token into a csv file
        with open(f"./output_{formatted_date}.csv", 'a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writerows(results)
        
        # 修改token.csv文件，加入邮箱和额度状态信息
        token_csv_data = []
        for row in results:
            token = row['token']
            username = row['username']
            
            # 增加余额状态检查
            is_low_balance = False
            balance = 0  # 默认值
            try:
                if token is not None:
                    user_id = token.split("%3A%3A")[0]
                    # 创建临时的 Register 对象来获取使用量，注意 options 需要复制
                    temp_options = copy.deepcopy(options)
                    temp_browser = Chromium(temp_options)
                    register_for_balance = CursorRegister(temp_browser, None) # 不需要 email server
                    usage = register_for_balance.get_usage(user_id)
                    balance = usage["gpt-4"]["maxRequestUsage"] - usage["gpt-4"]["numRequests"]
                    # 使用固定的阈值或从环境变量获取，但不再删除账号
                    # threshold = register_config.delete_low_balance_account_threshold # 旧逻辑
                    threshold = 50 # 或者从环境变量获取 os.getenv('LOW_BALANCE_THRESHOLD', 50)
                    is_low_balance = balance <= threshold
                    print(f"[Balance Check] Email: {username}, Balance: {balance}, Threshold: {threshold}, Low Balance: {is_low_balance}")
                    register_for_balance.browser.quit(force=True, del_data=True)
            except Exception as e:
                print(f"[Balance Check Error] {e}")
            
            token_csv_data.append({
                'token': token,
                'email': username,
                'balance': str(balance),
                'is_low_balance': str(is_low_balance)
            })
            
        # 写入包含额度状态的token文件
        token_file_path = f"./token_{formatted_date}.csv"
        # 检查文件是否已存在，不存在则先写入表头
        write_header = not os.path.exists(token_file_path)
        
        with open(token_file_path, 'a', newline='', encoding='utf-8') as file: # 添加 encoding='utf-8'
            fieldnames = ['token', 'email', 'balance', 'is_low_balance']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            if write_header:
                writer.writeheader() # 写入表头行
                
            writer.writerows(token_csv_data)

    return results

def main():
    # OmegaConf.set_struct(config, False) # 移除
    
    # 移除旧的从环境变量或 config 文件加载邮箱配置的逻辑
    # use_config_file = ...
    # email_configs_str = ...
    # if not use_config_file: ...
    # else: ...

    # 移除旧的 config 验证逻辑
    # email_server_name = ...
    # use_custom_address = ...
    # assert ...
    # if use_custom_address and ...

    # 检查必要的环境变量是否已设置
    if not registration_email:
        print("[Error] Missing required environment variable: REGISTRATION_EMAIL")
        sys.exit(1)
    # 现在 IMAP 配置检查移到 register_cursor_core 内部
    # if not all([receiving_imap_server, receiving_imap_port, receiving_username, receiving_password]):
    #     print("[Error] Missing required environment variables for receiving email config")
    #     sys.exit(1)

    # 调用修改后的 register_cursor 函数 (移除旧参数)
    account_infos = register_cursor(registration_email)
    
    tokens = list(set([row['token'] for row in account_infos if row and row.get('token')])) # 确保处理 None
    print(f"[Register] Register {len(tokens)} accounts successfully")
    
    # 保留 OneAPI 上传逻辑，检查环境变量 ingest_to_oneapi
    # if config.oneapi.enabled and len(account_infos) > 0: # 旧检查
    if ingest_to_oneapi and len(tokens) > 0:
        # 检查 OneAPI 配置
        if not oneapi_url or not oneapi_token:
            print("[Warning] Ingest to OneAPI is enabled, but CURSOR_ONEAPI_URL or CURSOR_ONEAPI_TOKEN is missing.")
        else:
            print("[OneAPI] Starting to upload tokens to OneAPI...")
            from tokenManager.oneapi_manager import OneAPIManager
            # from tokenManager.cursor import Cursor # Cursor 类似乎没有用到

            # oneapi_url = config.oneapi.url # 从环境变量读取
            # oneapi_token = config.oneapi.token # 从环境变量读取
            # oneapi_channel_url = config.oneapi.channel_url # 从环境变量读取

            oneapi = OneAPIManager(oneapi_url, oneapi_token)
            batch_size = min(10, len(tokens))
            for i in range(0, len(tokens), batch_size):
                batch_tokens = tokens[i:i+batch_size]
                # 确保 oneapi_channel_url 有值，或者提供默认值
                channel_url = oneapi_channel_url if oneapi_channel_url else "http://localhost:3000" # 提供一个默认值或报错
                oneapi.batch_add_channel(batch_tokens, channel_url)
            print("[OneAPI] Finished uploading tokens.")

if __name__ == "__main__":
    main()
