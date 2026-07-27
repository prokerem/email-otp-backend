import json
import base64
import random
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import socket

def gmail_gonder(to_email: str, subject: str, text_content: str):
    if not GMAIL_USER or not GMAIL_PWD:
        raise RuntimeError("GMAIL_USER veya GMAIL_PWD çevre değişkenleri tanımlanmamış!")

    # Render'ın IPv6 takılmasını engelleyen IPv4 zorlaması
    old_gai = socket.getaddrinfo
    def custom_gai(*args, **kwargs):
        res = old_gai(*args, **kwargs)
        return [item for item in res if item[0] == socket.AF_INET]
    
    socket.getaddrinfo = custom_gai

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

        # Port 587 ve TLS kullanımı time-out hatalarında daha kararlıdır
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.ehlo()
        server.starttls()  # Şifreli tünele geçiş yap
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_PWD)
        server.sendmail(GMAIL_USER, [to_email], msg.as_string())
        server.quit()

    except Exception as e:
        raise RuntimeError(f"Gmail gönderme hatası: {str(e)}")
    finally:
        # Soket ayarını eski haline getir
        socket.getaddrinfo = old_gai
app = FastAPI(title="E-Ticaret OTP Sunucusu")

# CORS AYARLARI: React projenizin sunucuya erişebilmesi için zorunludur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AKTIF_KODLAR = {}

# Çevre değişkenlerinden çekiyoruz (Varsayılan şifre kaldırıldı)
GMAIL_USER = os.environ.get("GMAIL_USER", "kerempro4654@gmail.com")
GMAIL_PWD = os.environ.get("GMAIL_PWD")

# Veri modelleri
class EncryptedPayload(BaseModel):
    payload: str  # React'ten gelecek base64 şifreli metin

def deşifre_et(payload_str: str):
    try:
        decoded_bytes = base64.b64decode(payload_str)
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz şifreli paket yapısı.")

# Şifreli yanıt paketi hazırlayan fonksiyon
def şifreli_yanıt(data_dict: dict):
    res_bytes = json.dumps(data_dict).encode('utf-8')
    return {"payload": base64.b64encode(res_bytes).decode('utf-8')}

# --- 1. KAYIT VE KOD GÖNDERME ENDPOINT ---
@app.post("/api/python-signup")
def python_signup(data: EncryptedPayload):
    raw_data = deşifre_et(data.payload)
    email = raw_data.get('email', '').strip().lower()
    full_name = raw_data.get('fullName', 'Değerli Kullanıcı')

    if not email:
        raise HTTPException(status_code=400, detail="E-posta adresi eksik.")

    try:
        rand_code = random.randint(100000, 999999)
        subject = "Güvenlik Doğrulama Kodu"
        text = f"Merhaba {full_name},\n\nSisteme kayıt işleminiz için doğrulama kodunuz: {rand_code}\n\nBu kodu kimseyle paylaşmayınız."

        gmail_gonder(email, subject, text)
        AKTIF_KODLAR[email] = rand_code

        return şifreli_yanıt({"status": "success", "message": "Güvenlik kodu gönderildi."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. KOD DOĞRULAMA ENDPOINT ---
@app.post("/api/python-verify")
def python_verify(data: EncryptedPayload):
    raw_data = deşifre_et(data.payload)
    email = raw_data.get('email', '').strip().lower()
    
    try:
        user_code = int(raw_data.get('code', 0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Kod formatı geçersiz.")

    if email in AKTIF_KODLAR and AKTIF_KODLAR[email] == user_code:
        del AKTIF_KODLAR[email]
        return şifreli_yanıt({"status": "success", "message": "Doğrulama başarılı!"})
    else:
        raise HTTPException(status_code=400, detail="Girdiğiniz doğrulama kodu hatalı!")