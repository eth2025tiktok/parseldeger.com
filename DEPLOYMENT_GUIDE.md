# 🚀 DEPLOYMENT REHBERİ - parseldeger.com
# Render (Backend) + Vercel (Frontend) + MongoDB Atlas

## ✅ HAZIRLIK TAMAMLANDI
Tüm deployment dosyaları hazırlandı:
- ✅ render.yaml (Backend config)
- ✅ vercel.json (Frontend config)
- ✅ requirements.txt (Python dependencies)
- ✅ package.json (Node dependencies)

---

## 📋 ADIM 1: MONGODB ATLAS SETUP

### 1.1 Database User Oluştur
1. MongoDB Atlas → Database Access
2. "Add New Database User"
   - Username: `parseldeger_admin`
   - Password: **[GÜÇLÜ ŞİFRE OLUŞTURUN VE KAYDEDIN!]**
   - Role: "Atlas Admin"

### 1.2 Network Access
1. Network Access → "Add IP Address"
2. "Allow Access from Anywhere" → 0.0.0.0/0

### 1.3 Connection String Al
1. Database → Connect → "Connect your application"
2. Driver: Python, Version: 3.12 or later
3. Connection string'i kopyala:
```
mongodb+srv://parseldeger_admin:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```
4. `<password>` yerine ŞİFRENİZİ yazın
5. **BU STRING'İ KAYDET!** (MONGO_URL için gerekli)

---

## 📋 ADIM 2: GITHUB'A PUSH

### 2.1 GitHub Repository Oluştur
1. GitHub'da yeni repo: `parseldeger-app` (public veya private)

### 2.2 Kodu Yükle
Terminal'de veya Emergent'den "Save to GitHub" ile:

```bash
# Eğer manuel yapıyorsanız:
git init
git add .
git commit -m "Initial deployment"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADINIZ/parseldeger-app.git
git push -u origin main
```

---

## 📋 ADIM 3: RENDER - BACKEND DEPLOYMENT

### 3.1 Yeni Web Service Oluştur
1. https://dashboard.render.com → "New +" → "Web Service"
2. "Build and deploy from a Git repository"
3. GitHub repository'nizi seçin: `parseldeger-app`

### 3.2 Temel Ayarlar
```
Name: parseldeger-backend
Region: Frankfurt (veya yakın)
Branch: main
Root Directory: (boş bırak)
Runtime: Python 3
Build Command: pip install -r backend/requirements.txt
Start Command: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
Instance Type: Free
```

### 3.3 Environment Variables Ekle
**ÖNEMLİ:** Aşağıdaki tüm değişkenleri "Add Environment Variable" ile ekleyin:

```bash
# MongoDB (Adım 1.3'ten)
MONGO_URL=mongodb+srv://parseldeger_admin:ŞİFRENİZ@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=parseldeger_production

# CORS
CORS_ORIGINS=*

# Gemini API (6 anahtar - virgülle ayrılmış)
GEMINI_API_KEYS=AIzaSyAmJKn66SJnn1N3wCs56ixGUOm1iFwr0jQ,AIzaSyCAFYqK500uCe0ji52j-kX8OAZwr4x0cYE,AIzaSyAYArbQB4ryShWXgYIR_kp4tm2U2sSyP3I,AIzaSyDVvuUXDvztiVY3gSQY4Wm08wT9gVByonY,AIzaSyA3Ahpka8NdMS_y6mhtzM06M6sJhw2N-yk,AIzaSyAbPgcVYwcjVJmGI9QOwUE-WTGkmJbnoFc

# Brave Search
BRAVE_API_KEY=BSAkvmd9byYJ4hfCRlEdFSK5Ld_xhqL

# Shopier
SHOPIER_API_KEY=abc8145ed90f69218c7402a70cf490d0
SHOPIER_CLIENT_SECRET=7311fcb8508b668d72df3f1fd22c0451

# Port (Render otomatik atar ama ekleyin)
PORT=8001
```

### 3.4 Deploy Et
1. "Create Web Service" butonuna tıkla
2. Deploy başlayacak (5-10 dakika)
3. Başarılı olursa: `https://parseldeger-backend.onrender.com`

### 3.5 Backend URL'ini Kaydet
Deploy tamamlanınca Render size URL verecek:
```
https://parseldeger-backend-XXXX.onrender.com
```
**BU URL'İ KAYDET!** (Frontend için gerekli)

---

## 📋 ADIM 4: VERCEL - FRONTEND DEPLOYMENT

### 4.1 Vercel'e Gir ve Import Et
1. https://vercel.com/new
2. "Import Git Repository"
3. GitHub repository'nizi seçin: `parseldeger-app`

### 4.2 Proje Ayarları
```
Framework Preset: Create React App
Root Directory: frontend
Build Command: yarn build (otomatik)
Output Directory: build (otomatik)
Install Command: yarn install (otomatik)
```

### 4.3 Environment Variables
**SADECE BU 1 DEĞİŞKENİ EKLE:**

```bash
# Render Backend URL (Adım 3.5'ten)
REACT_APP_BACKEND_URL=https://parseldeger-backend-XXXX.onrender.com
```

**ÖNEMLİ:** Backend URL'inizin sonunda `/` olmasın!

### 4.4 Deploy Et
1. "Deploy" butonuna tıkla
2. Deploy başlayacak (3-5 dakika)
3. Başarılı olursa: `https://parseldeger-app.vercel.app`

---

## 📋 ADIM 5: CUSTOM DOMAIN BAĞLAMA

### 5.1 Vercel'de Domain Ekle
1. Vercel Dashboard → Project → Settings → Domains
2. "Add Domain" → `parseldeger.com` yazın
3. Vercel size DNS ayarlarını gösterecek:
```
Type: A
Name: @
Value: 76.76.21.21

Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

### 5.2 Domain Sağlayıcınızda DNS Ayarla
(GoDaddy, Namecheap, vb. - nereden aldıysanız)

1. DNS Management'e git
2. Eski A ve CNAME kayıtlarını sil
3. Vercel'in verdiği kayıtları ekle:
   - A record: @ → 76.76.21.21
   - CNAME record: www → cname.vercel-dns.com
4. Kaydet

### 5.3 SSL Sertifikası (Otomatik)
- Vercel otomatik Let's Encrypt SSL verir
- 5-30 dakika içinde https://parseldeger.com çalışacak

---

## 📋 ADIM 6: SHOPIER WEBHOOK GÜNCELLE

Backend URL'iniz değişti, Shopier'de güncelleyin:

1. Shopier Panel → Entegrasyonlar → OSB
2. Bildirim URL:
```
https://parseldeger-backend-XXXX.onrender.com/api/payment/webhook
```
3. Protokol: `https://`
4. Kaydet → Bildirim Testi → Aktifleştir

---

## ✅ DEPLOYMENT TAMAMLANDI!

### Test Edin:
1. **Frontend**: https://parseldeger.com
2. **Backend API**: https://parseldeger-backend-XXXX.onrender.com/api/
3. **Analiz testi**: Bir arsa analizi yapın
4. **Ödeme testi**: Test ödemesi yapın

---

## 🐛 SORUN GİDERME

### Backend 404 Hatası
- Render logs kontrol edin
- Environment variables doğru mu?
- Start command doğru mu? `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT`

### Frontend Backend'e Bağlanamıyor
- `REACT_APP_BACKEND_URL` doğru mu?
- URL sonunda `/` var mı? (olmamalı)
- Backend CORS ayarları doğru mu?

### MongoDB Connection Hatası
- Connection string doğru mu?
- Şifre doğru mu?
- Network Access 0.0.0.0/0 mu?

### Domain Çalışmıyor
- DNS değişiklikleri 5-30 dakika sürer
- Vercel'de domain "Ready" durumunda mı?

---

## 💰 MALİYET

- **MongoDB Atlas**: ÜCRETSİZ (512 MB)
- **Render**: ÜCRETSİZ (750 saat/ay, 15 dakika inactivity sonrası sleep)
- **Vercel**: ÜCRETSİZ (100 GB bandwidth)

**Not:** Render free tier'da 15 dakika kullanılmazsa sleep'e geçer. İlk istek 30-60 saniye sürebilir.

---

## 📞 DESTEK

Sorun yaşarsanız:
1. Render Logs: Dashboard → Logs
2. Vercel Logs: Dashboard → Deployments → View Function Logs
3. MongoDB Logs: Database → Browse Collections

Başarılar! 🚀
