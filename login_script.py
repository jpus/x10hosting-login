from playwright.sync_api import sync_playwright
import os
import requests
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram_message(message: str) -> bool:
    """发送Telegram消息"""
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.error("未配置Telegram")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        logger.error(f"发送Telegram失败: {e}")
        return False

def check_captcha(page) -> bool:
    """检查是否有验证码"""
    try:
        # 常见的验证码特征
        captcha_selectors = [
            '.g-recaptcha',
            'iframe[src*="recaptcha"]',
            'text="reCAPTCHA"',
            'text="验证码"',
            'text="人机验证"'
        ]
        
        for selector in captcha_selectors:
            if page.locator(selector).first.is_visible(timeout=2000):
                return True
        return False
    except:
        return False

def login_x10hosting(email: str, password: str) -> str:
    """简单登录x10hosting"""
    
    logger.info(f"开始登录: {email}")
    
    with sync_playwright() as p:
        browser = None
        try:
            # 启动浏览器 - GitHub Actions用headless，本地可以改False
            browser = p.firefox.launch(
                headless=True,  # Actions必须True，本地调试可改False
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            
            # 访问登录页
            logger.info("访问登录页面...")
            page.goto("https://x10hosting.com/login", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 检查是否有验证码
            if check_captcha(page):
                logger.warning("检测到验证码，无法自动处理")
                return f"❌ {email} - 需要手动处理验证码"
            
            # 填写邮箱
            page.get_by_placeholder("Email Address").fill(email)
            time.sleep(0.5)
            
            # 填写密码
            page.get_by_placeholder("Password").fill(password)
            time.sleep(0.5)
            
            # 点击登录
            page.get_by_role("button", name="Login").click()
            
            # 等待响应
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)
            
            # 检查结果
            current_url = page.url
            
            if "panel" in current_url or "dashboard" in current_url:
                logger.info("✅ 登录成功")
                return f"✅ {email} - 登录成功"
            else:
                # 检查是否有错误提示
                try:
                    error = page.locator('.MuiAlert-message').first
                    if error.is_visible():
                        error_text = error.inner_text()
                        return f"❌ {email} - {error_text}"
                except:
                    pass
                
                return f"❌ {email} - 登录失败"
            
        except Exception as e:
            logger.error(f"登录出错: {e}")
            return f"❌ {email} - 错误: {str(e)[:50]}"
        finally:
            if browser:
                browser.close()

def main():
    """主函数"""
    logger.info("="*50)
    logger.info("x10hosting 自动登录脚本")
    logger.info("="*50)
    
    # 获取账户
    accounts_env = os.environ.get('WEBHOST', '')
    
    if not accounts_env:
        logger.warning("未配置账户")
        send_telegram_message("⚠️ 未配置任何账户")
        return
    
    # 解析账户
    accounts = []
    for account in accounts_env.split():
        try:
            email, password = account.split(':', 1)
            accounts.append((email, password))
            logger.info(f"解析账户: {email}")
        except:
            logger.error(f"账户格式错误: {account}")
    
    if not accounts:
        send_telegram_message("❌ 没有有效的账户")
        return
    
    # 逐个登录
    results = []
    for i, (email, password) in enumerate(accounts, 1):
        logger.info(f"\n处理第 {i}/{len(accounts)} 个账户")
        result = login_x10hosting(email, password)
        results.append(result)
        logger.info(f"结果: {result}")
        
        if i < len(accounts):
            time.sleep(5)  # 账户间等待
    
    # 发送结果
    message = "📊 *x10hosting 登录结果*\n\n" + "\n".join(results)
    send_telegram_message(message)
    logger.info("结果已发送")

if __name__ == "__main__":
    main()