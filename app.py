import os
import time
import random
import uuid
import logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Error as PWError
from playwright_stealth import stealth_sync

# --- Configuration ---
VERSION = "8.5.0-STABLE"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RazorpayRailway")

app = Flask(__name__)

class ProxyParser:
    @staticmethod
    def get_config(proxy_str):
        if not proxy_str: return None
        parts = proxy_str.split(':')
        if len(parts) == 4:
            return {"server": f"http://{parts[0]}:{parts[1]}", "username": parts[2], "password": parts[3]}
        elif len(parts) == 2:
            return {"server": f"http://{parts[0]}:{parts[1]}"}
        return {"server": proxy_str}

class RazorpayEngine:
    def __init__(self, url, card, amount, proxy):
        self.url = url
        self.card = card
        self.amount = amount
        self.proxy_str = proxy
        self.tx_id = str(uuid.uuid4())[:8].upper()

    def run(self):
        with sync_playwright() as p:
            proxy_cfg = ProxyParser.get_config(self.proxy_str)
            
            # STABILITY FIX: Added args for Docker/Cloud environments
            browser = p.chromium.launch(
                headless=True, 
                proxy=proxy_cfg,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            stealth_sync(page)

            try:
                logger.info(f"[{self.tx_id}] Processing: {self.url}")
                
                # Navigation
                try:
                    res = page.goto(self.url, wait_until="domcontentloaded", timeout=45000)
                    if not res: return {"status": "FAILED", "message": "Connection timeout."}
                except Exception as e:
                    return {"status": "FAILED", "message": str(e)}

                # Check Status
                content = page.content().lower()
                if "already paid" in content or "successful" in content:
                    return {"status": "ALREADY_PAID", "message": "Link already settled."}

                # Open Checkout
                amt_field = page.locator("input#amount, [name='amount']").first
                if amt_field.is_visible(timeout=2000):
                    amt_field.fill(str(self.amount))

                page.click("button:has-text('Pay'), button:has-text('Proceed'), button:has-text('Donate')", timeout=5000)
                
                # Contact Bypass
                time.sleep(2)
                email_f = page.locator("input[type='email']").first
                if email_f.is_visible(timeout=3000):
                    email_f.fill(f"user.{random.randint(100,999)}@gmail.com")
                    page.locator("input[name='phone'], input[type='tel']").first.fill(f"9{random.randint(700000000, 999999999)}")
                    page.locator("button:has-text('Proceed'), button:has-text('Next')").first.click()

                # iFrame & Card
                page.wait_for_selector("iframe.razorpay-checkout-frame", timeout=15000)
                frame = page.frame_locator("iframe.razorpay-checkout-frame")
                frame.get_by_text("Card").first.click()
                
                n, m, y, c = [x.strip() for x in self.card.split('|')]
                frame.locator("input[name='card[number]']").fill(n.replace(" ", ""))
                frame.locator("input[name='card[expiry]']").fill(f"{m}/{y}")
                frame.locator("input[name='card[cvv]']").fill(c)
                
                frame.locator("button#footer-cta").click()
                time.sleep(8)

                return {
                    "status": "SUCCESS",
                    "id": self.tx_id,
                    "message": "Initiation complete.",
                    "final_url": page.url
                }

            except Exception as e:
                return {"status": "FAILED", "id": self.tx_id, "message": str(e)}
            finally:
                browser.close()

@app.route('/rz', methods=['GET'])
def api_endpoint():
    cc = request.args.get('cc')
    url = request.args.get('url')
    amount = request.args.get('amount')
    proxy = request.args.get('proxy')

    if not all([cc, url, amount]):
        return jsonify({"status": "ERROR", "message": "Missing params"}), 400

    automator = RazorpayEngine(url, cc, amount, proxy)
    return jsonify(automator.run())

@app.route('/')
def health():
    return f"Razorpay API {VERSION} is active."

if __name__ == '__main__':
    # Flask is only used as a fallback; Gunicorn runs the app in production
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
