from DrissionPage import ChromiumOptions, Chromium

def test_browser():
    print("开始测试浏览器")
    options = ChromiumOptions()
    options.auto_port()
    options.new_env()
    
    try:
        print("尝试启动浏览器...")
        browser = Chromium(options)
        print("浏览器启动成功!")
        print("尝试打开网页...")
        tab = browser.new_tab("https://www.baidu.com")
        print("成功打开网页!")
        browser.quit()
        print("测试完成，浏览器关闭")
        return True
    except Exception as e:
        print(f"浏览器测试失败: {e}")
        return False

if __name__ == "__main__":
    test_browser() 