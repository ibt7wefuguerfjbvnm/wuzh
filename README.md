# Razorpay Automation API (Railway Edition)

A high-performance, resilient API for automating Razorpay.me payment links.

## 🚀 Endpoints

### 1. Execute Payment
`GET /rz?cc=number|mm|yy|cvv&url=https://razorpay.me/@user&amount=100&proxy=ip:port:user:pass`

### 2. Health Check
`GET /`

## 🛡️ Response Status Codes

| Status | Description |
|---|---|
| `SUCCESS` | Payment initiation reached the Bank OTP page. |
| `ALREADY_PAID` | The link is already completed. |
| `DEAD_SITE` | The payment link returns 404. |
| `PROXY_ERROR` | The provided proxy is offline or failed. |
| `CARD_DECLINED` | The card was rejected by Razorpay/Bank. |
| `LINK_EXPIRED` | The payment link has expired. |

## 🛠️ Local Setup
```bash
pip install -r requirements.txt
playwright install chromium
python app.py
```
