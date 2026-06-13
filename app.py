import os
import time
import json
import random
import uuid
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Error as PWError
from playwright_stealth import stealth_page

app = Flask(__name__)

class ProxyHandler:
    @staticmethod
    def parse(proxy_str):
        if not proxy_str: return None
        p = proxy_str.split(':')
        if len(p) == 4:
            return {"server": f"http://{p[0]}:{p[1]}", "username": p[2], "password": p[3]}
        return {"server": f"http://{p[0]}:{p[1]}"} if len(p) == 2 else {"server": proxy_str}

class RazorpayAutomator:
    def __init__(self, url, card, amount, proxy):
        self.url = url
        self.card = card
        self.amount = amount
        self.proxy_str = proxy
        self.tx_id = str(uuid.uuid4())[:8].upper()

    def run(self):
        with sync_playwright() as p:
            proxy_cfg = ProxyHandler.parse(self.proxy_str)
            # Railway runs in a headless environment, so headless=True is mandatory
            browser = p.chromium.launch(headless=True, proxy=proxy_cfg)
            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            stealth_page(page)

            try:
                res = page.goto(self.url, wait_until="domcontentloaded", timeout=45000)
                if not res: raise Exception("PROXY_DEAD: Proxy failed to connect.")
                
                content = page.content().lower()
                if any(x in content for x in ["successful", "already paid", "completed"]):
                    raise Exception("ALREADY_PAID: Link already settled.")
                
                amt_input = page.locator("input#amount, [name='amount']").first
                if amt_input.is_visible(timeout=2000):
                    amt_input.fill(str(self.amount))

                page.click("button:has-text('Pay'), button:has-text('Proceed'), button:has-text('Donate')", timeout=5000)
                
                time.sleep(2)
                email_f = page.locator("input[type='email']").first
                if email_f.is_visible(timeout=3000):
                    email_f.fill(f"user_{random.randint(100,999)}@gmail.com")
                    page.locator("input[name='phone'], input[type='tel']").first.fill(f"9{random.randint(700000000, 999999999)}")
                    page.locator("button:has-text('Proceed'), button:has-text('Next')").first.click()

                page.wait_for_selector("iframe.razorpay-checkout-frame", timeout=15000)
                frame = page.frame_locator("iframe.razorpay-checkout-frame")

                frame.get_by_text("Card").first.click()
                
                n, m, y, c = [x.strip() for x in self.card.split('|')]
                frame.locator("input[name='card[number]']").fill(n.replace(" ", ""))
                frame.locator("input[name='card[expiry]']").fill(f"{m}/{y}")
                frame.locator("input[name='card[cvv]']").fill(c)
                
                frame.locator("button#footer-cta").click()
                time.sleep(8)

                err_toast = frame.locator(".toast-message, #error-desc").first
                if err_toast.is_visible(timeout=1000):
                    raise Exception(f"CARD_DECLINED: {err_toast.inner_text()}")

                return {
                    "status": "SUCCESS",
                    "id": self.tx_id,
                    "message": "Payment submitted. Reached Bank Page.",
                    "bank_url": page.url
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
        return jsonify({"status": "ERROR", "message": "Missing parameters"}), 400

    automator = RazorpayAutomator(url, cc, amount, proxy)
    result = automator.run()
    return jsonify(result)

@app.route('/')
def health():
    return "Razorpay API is running"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
