# Railway Deployment Rehberi - parseldeger.com

## Adım 1: GitHub'a Kod Yükleme

1. GitHub hesabınızda yeni repository oluşturun: `parseldeger-app`
2. Emergent'den "Save to GitHub" özelliğini kullanın (eğer varsa)
3. Ya da manuel olarak kodu yükleyin

## Adım 2: MongoDB Atlas Kurulumu (Ücretsiz)

1. https://www.mongodb.com/cloud/atlas/register adresine gidin
2. Ücretsiz hesap oluşturun
3. "Build a Database" → "Free" (M0) seçin
4. Cloud provider: AWS, Region: yakın bir bölge seçin
5. Cluster adı: `parseldeger-db`
6. "Create" butonuna basın
7. **Database Access**:
   - "Add New Database User" butonuna tıklayın
   - Username: `parseldeger_admin`
   - Password: Güçlü bir şifre oluşturun (kaydedin!)
   - Built-in Role: "Atlas Admin"
8. **Network Access**:
   - "Add IP Address" → "Allow Access from Anywhere" (0.0.0.0/0)
9. **Connection String**:
   - "Connect" → "Connect your application"
   - Connection string'i kopyalayın:
   ```
   mongodb+srv://parseldeger_admin:<password>@parseldeger-db.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   - `<password>` yerine şifrenizi yazın

## Adım 3: Railway Hesabı ve Proje Oluşturma

1. https://railway.app/ adresine gidin
2. "Start a New Project" butonuna tıklayın
3. GitHub ile giriş yapın
4. "Deploy from GitHub repo" seçin
5. Repository'nizi seçin: `parseldeger-app`

## Adım 4: Environment Variables Ayarlama

Railway dashboard'da projenize tıklayın:

### Backend Environment Variables:
```
MONGO_URL=mongodb+srv://parseldeger_admin:ŞIFRENIZ@parseldeger-db.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=parseldeger_production
CORS_ORIGINS=*
GEMINI_API_KEYS=AIzaSyAmJKn66SJnn1N3wCs56ixGUOm1iFwr0jQ,AIzaSyCAFYqK500uCe0ji52j-kX8OAZwr4x0cYE,AIzaSyAYArbQB4ryShWXgYIR_kp4tm2U2sSyP3I,AIzaSyDVvuUXDvztiVY3gSQY4Wm08wT9gVByonY,AIzaSyA3Ahpka8NdMS_y6mhtzM06M6sJhw2N-yk,AIzaSyAbPgcVYwcjVJmGI9QOwUE-WTGkmJbnoFc
BRAVE_API_KEY=BSAkvmd9byYJ4hfCRlEdFSK5Ld_xhqL
SHOPIER_API_KEY=abc8145ed90f69218c7402a70cf490d0
SHOPIER_CLIENT_SECRET=7311fcb8508b668d72df3f1fd22c0451
PORT=8001
```

### Frontend Environment Variables:
```
REACT_APP_BACKEND_URL=https://BACKEND_URL_BURAYA_GELECEK
```

## Adım 5: Custom Domain Bağlama

1. Railway dashboard'da projenizi seçin
2. "Settings" → "Domains" bölümüne gidin
3. "Add Domain" butonuna tıklayın
4. `parseldeger.com` yazın
5. Railway size DNS ayarlarını gösterecek:
   ```
   Type: CNAME
   Name: @
   Value: xxx.railway.app
   ```
6. Domain sağlayıcınızın (GoDaddy, Namecheap vb.) paneline gidin
7. DNS ayarlarından CNAME record ekleyin
8. 5-30 dakika bekleyin

## Adım 6: HTTPS ve SSL

Railway otomatik olarak Let's Encrypt SSL sertifikası verir. Hiçbir şey yapmanıza gerek yok!

## Adım 7: Deployment

- Railway otomatik olarak deploy eder
- Her GitHub push'da otomatik yeniden deploy olur
- Logs'tan durumu takip edebilirsiniz

## Troubleshooting

### MongoDB Connection Hatası
- Connection string'deki şifreyi kontrol edin
- Network Access'te 0.0.0.0/0 olduğundan emin olun

### Backend Başlamıyor
- Logs'u kontrol edin: Railway dashboard → "View Logs"
- Environment variables'ların doğru olduğundan emin olun

### Frontend Backend'e Bağlanamıyor
- REACT_APP_BACKEND_URL doğru mu kontrol edin
- CORS_ORIGINS=* olduğundan emin olun

## Maliyet

- **MongoDB Atlas**: Ücretsiz (M0 Cluster)
- **Railway**: 
  - $5/ay başlangıç kredisi (kredi kartı gerekli)
  - Kullanıma göre ücretlendirme
  - Küçük projeler için ~$10-15/ay

## Alternatif: Render.com

Railway yerine Render kullanmak isterseniz:
- Daha uzun free tier
- Benzer kullanım
- https://render.com
