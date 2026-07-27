import json
import base64
import random
import smtplib
import os
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

GMAIL_USER = os.environ.get("GMAIL_USER", "kerempro4654@gmail.com")
GMAIL_PWD = os.environ.get("GMAIL_PWD", "ovsbbudvunoccpwj")

# Veri modelleri
class EncryptedPayload(BaseModel):
    payload: str  # React'ten gelecek base64 şifreli metin

def gmail_gonder(TO, SUBJECT, TEXT):
    try:
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
    except Exception as e:
        raise RuntimeError(f"Gmail gönderme hatası: {str(e)}")

# Şifreli gelen base64 verisini çözen fonksiyon
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
        SUBJECT = "Güvenlik Doğrulama Kodu"
        TEXT = f"Merhaba {full_name},\n\nSisteme kayıt işleminiz için doğrulama kodunuz: {rand_code}\n\nBu kodu kimseyle paylaşmayınız."

        gmail_gonder(email, SUBJECT, TEXT)
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
    except ValueError:
        raise HTTPException(status_code=400, detail="Kod formatı geçersiz.")

    if email in AKTIF_KODLAR and AKTIF_KODLAR[email] == user_code:
        del AKTIF_KODLAR[email]
        return şifreli_yanıt({"status": "success", "message": "Doğrulama başarılı!"})
    else:
        raise HTTPException(status_code=400, detail="Girdiğiniz doğrulama kodu hatalı!")
