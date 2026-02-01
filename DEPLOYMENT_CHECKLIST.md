# SkillGap AI - Railway Deployment Checklist

## ✅ Pre-Deployment Checklist

### Code Updates
- [x] UTF-8 encoding fixes applied to app.py
  - [x] sys module import added
  - [x] stdout/stderr encoding configured
  - [x] Flask JSON_AS_ASCII = False set
  - [x] PDF extraction UTF-8 handling
  - [x] DOCX extraction UTF-8 handling
  - [x] Groq API response UTF-8 handling
  - [x] PORT environment variable support

- [x] HTML template has UTF-8 charset
  - [x] `<meta charset="UTF-8">` present in index.html

### Deployment Files Created
- [x] **Procfile** - App startup command
- [x] **runtime.txt** - Python 3.11.9
- [x] **railway.json** - Railway configuration
- [x] **RAILWAY_DEPLOYMENT.md** - Complete deployment guide

### Dependencies
- [x] requirements.txt has all packages
- [x] Local venv can install all packages
- [x] No conflicting dependencies

---

## 🚀 Quick Deployment Steps

### 1. Push to GitHub
```bash
cd /home/PaininAss/Desktop/Skillgap_AI
git add .
git commit -m "Add Railway deployment & UTF-8 fixes"
git push origin main
```

### 2. Railway Setup
- [ ] Go to https://railway.app
- [ ] New Project → Deploy from GitHub
- [ ] Select repository
- [ ] Add environment variables:
  ```
  GROQ_API_KEY=<your_key_from_console.groq.com/keys>
  FLASK_ENV=production
  ```
- [ ] Deploy

### 3. Verify
- [ ] Check health endpoint: `/health`
- [ ] Test with special characters CV
- [ ] Verify no encoding errors in logs

---

## 🔍 Testing UTF-8 Handling

### Test with special characters:
```
Characters to test: × ÷ é ñ ü ö ® © § € £ ¥ ¢
Languages: Spanish (ñ), French (é), German (ö), Russian (Кириллица)
Math: ∑ ∫ ∏ √ ≤ ≥ ≠ ±
```

### Expected Result:
No "ascii codec can't encode character" errors

---

## 📋 Environment Variables

### Required
- `GROQ_API_KEY` - Your API key from https://console.groq.com/keys

### Optional (Auto-configured)
- `FLASK_ENV` - Set to `production` automatically
- `PORT` - Auto-set by Railway (default 5000)

---

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| ASCII encoding errors | Already fixed in app.py |
| API key not working | Check key validity at console.groq.com |
| 503 service unavailable | Check Groq API status |
| Timeout errors | Increase healthcheckTimeout in railway.json |
| File upload failures | Verify < 16MB size limit |

---

## 📊 Deployment Info

- **Python Version**: 3.11.9
- **Framework**: Flask 3.0.0
- **API**: Groq LLaMA 3.3-70B
- **Encoding**: UTF-8 (enforced at all levels)
- **Platform**: Railway.app
- **Health Check**: `/health` endpoint available

---

## 🔐 Security Notes

- Never commit `.env` file (use `.env.example`)
- Keep `GROQ_API_KEY` confidential
- Rotate API keys periodically
- Monitor Railway logs for suspicious activity

---

## 📞 Support

- Railway Issues: https://docs.railway.app
- Groq API Docs: https://console.groq.com/docs/api
- Flask Docs: https://flask.palletsprojects.com
- Python Unicode: https://docs.python.org/3/howto/unicode.html
