import json
import base64
import random
import smtplib
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

AKTIF_KODLAR = {}

# Şifre bilgisi sunucu ortam değişkeninden (Environment Variable) okunur.
# Yerel testte ortam değişkeni yoksa yedek şifre kullanılır.
GMAIL_USER = os.environ.get("GMAIL_USER", "kerempro4654@gmail.com")
GMAIL_PWD = os.environ.get("GMAIL_PWD", "ovsbbudvunoccpwj")

def gmail_gonder(TO, SUBJECT, TEXT):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PWD)
    
    BODY = '\r\n'.join([
        f'To: {TO}',
        f'From: {GMAIL_USER}',
        f'Subject: {SUBJECT}',
        'Content-Type: text/plain; charset=utf-8',
        '', 
        TEXT
    ]).encode('utf-8')

    server.sendmail(GMAIL_USER, [TO], BODY)
    server.quit()

class RequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Encrypted-Payload')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        # AĞ TRAFİĞİ GÜVENLİĞİ: React'ten gelen Base64 ile şifrelenmiş veriyi çözüyoruz
        try:
            decoded_data = base64.b64decode(post_data).decode('utf-8')
            data = json.loads(decoded_data)
        except Exception:
            # Şifrelenmemiş düz veri geldiyse fallback
            data = json.loads(post_data.decode('utf-8'))

        # --- KAYIT VE KOD GÖNDERME ---
        if self.path == '/api/python-signup':
            email = data.get('email', '').strip().lower()
            full_name = data.get('fullName', 'Değerli Kullanıcı')

            try:
                rand_code = random.randint(100000, 999999)
                SUBJECT = "Güvenlik Doğrulama Kodu"
                TEXT = f"Merhaba {full_name},\n\nSisteme kayıt işleminiz için doğrulama kodunuz: {rand_code}\n\nBu kodu kimseyle paylaşmayınız."

                gmail_gonder(email, SUBJECT, TEXT)
                AKTIF_KODLAR[email] = rand_code

                # Yanıtı da Base64 ile paketleyip yolluyoruz
                res_data = json.dumps({"status": "success", "message": "Güvenlik kodu gönderildi."})
                encoded_res = base64.b64encode(res_data.encode('utf-8'))

                self._set_headers(200)
                self.wfile.write(encoded_res)

            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        # --- KOD DOĞRULAMA ---
        elif self.path == '/api/python-verify':
            email = data.get('email', '').strip().lower()
            user_code = int(data.get('code', 0))

            if email in AKTIF_KODLAR and AKTIF_KODLAR[email] == user_code:
                del AKTIF_KODLAR[email]
                res_data = json.dumps({"status": "success", "message": "Doğrulama başarılı!"})
                encoded_res = base64.b64encode(res_data.encode('utf-8'))
                
                self._set_headers(200)
                self.wfile.write(encoded_res)
            else:
                self._set_headers(400)
                self.wfile.write(json.dumps({"status": "error", "message": "Girdiğiniz doğrulama kodu hatalı!"}).encode('utf-8'))

def run():
    # Bulut sunucular (Render vb.) kendi PORT değişkenlerini atarlar
    port = int(os.environ.get("PORT", 8000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"🔥 Python Sunucusu Port {port} Üzerinde Yayında...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()