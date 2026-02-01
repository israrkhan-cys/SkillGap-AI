# SkillGap AI - Railway Deployment Guide

## Character Encoding Fix for Online Deployment

This guide covers the UTF-8 character encoding fixes implemented to handle non-ASCII characters (×, accented letters, special symbols) in CVs across different server environments.

### Problem Solved
Previously, when deploying online, the app would fail with:
```
Error analyzing CV: 'ascii' codec can't encode character '\xd7' in position 49: ordinal not in range(128)
```

This occurred because:
- **Local environment**: Used UTF-8 encoding by default
- **Online servers**: Often defaulted to ASCII encoding

### Solution Implemented

#### 1. **Application-Level UTF-8 Encoding** (app.py)
```python
# Force UTF-8 for stdout/stderr
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

#### 2. **Flask Configuration**
```python
app.config['JSON_AS_ASCII'] = False  # JSON responses use UTF-8
```

#### 3. **File Operations**
- PDF extraction: `extracted.encode('utf-8', errors='replace').decode('utf-8')`
- DOCX extraction: Proper UTF-8 encoding for all text
- TXT files: Opened with `encoding='utf-8'` explicitly

#### 4. **API Response Handling**
```python
response_text = chat_completion.choices[0].message.content
return response_text.encode('utf-8', errors='replace').decode('utf-8')
```

#### 5. **HTML Template**
- Meta charset tag: `<meta charset="UTF-8">` (already present)

---

## Railway Deployment Steps

### Prerequisites
1. GitHub account with repository containing SkillGap AI code
2. Railway account (https://railway.app)
3. Groq API key (get from https://console.groq.com/keys)

### Step-by-Step Deployment

#### 1. **Push Code to GitHub**
```bash
cd /home/PaininAss/Desktop/Skillgap_AI
git add .
git commit -m "Add Railway deployment files and UTF-8 encoding fixes"
git push origin main
```

#### 2. **Connect to Railway**
- Go to https://railway.app
- Click **"New Project"**
- Select **"Deploy from GitHub"**
- Authenticate and select your repository

#### 3. **Configure Environment Variables**
In Railway Dashboard:
- Click **Variables**
- Add the following:
  ```
  GROQ_API_KEY=your_api_key_here
  FLASK_ENV=production
  ```
- Get your API key from: https://console.groq.com/keys

#### 4. **Configure Settings**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app.py`
- **Port**: Railway will auto-set via `PORT` env variable (handled in app.py)

#### 5. **Deploy**
- Click **"Deploy"**
- Railway will automatically:
  - Install Python 3.11
  - Install dependencies from requirements.txt
  - Start the application
  - Assign a public URL

#### 6. **Verify Deployment**
- Check health endpoint: `https://your-railway-url/health`
- Should return: `{"status": "ok", "message": "SkillGap AI is running!"}`

### Files Added for Railway Deployment

1. **Procfile** - Specifies the command to run the app
2. **runtime.txt** - Specifies Python version (3.11.9)
3. **railway.json** - Railway-specific configuration with:
   - Health check endpoint `/health`
   - Restart policy
   - Timeout settings

### Testing Special Characters Online

Once deployed, test with CVs containing:
- Accented characters: é, ñ, ü, ö
- Math symbols: ×, ÷, ∑, ∫
- Other special chars: ®, ©, §

The UTF-8 encoding fixes ensure these are properly handled.

### Troubleshooting

#### Issue: "ascii" codec errors still appear
- **Solution**: Verify `FLASK_ENV=production` is set
- Check Railway logs for encoding warnings
- Ensure all files are UTF-8 encoded

#### Issue: API key not working
- Get fresh key from https://console.groq.com/keys
- Update in Railway Variables
- Restart deployment

#### Issue: Request timeout
- Increase timeout in railway.json's `healthcheckTimeout`
- Check Groq API status

#### Issue: PDF/DOCX extraction fails
- Ensure file size < 16MB (configured in app.config)
- Verify file format is valid
- Check Railway logs for details

### Production Best Practices

1. **Environment Separation**
   ```
   FLASK_ENV=production  (set in Railway)
   DEBUG=False (automatic when FLASK_ENV=production)
   ```

2. **Error Tracking** (optional)
   - Integrate Sentry for error monitoring
   - Set `SENTRY_DSN` in Railway Variables

3. **Rate Limiting** (optional)
   - Consider adding rate limiting for Groq API calls
   - Implement caching for frequently analyzed roles

4. **Security**
   - Never commit `.env` file
   - Use `.env.example` as template
   - Rotate API keys regularly

### Monitoring & Logs

View logs in Railway Dashboard:
- **Deploy Logs**: Build and startup messages
- **Runtime Logs**: Application output and errors
- **Metrics**: CPU, memory, network usage

### Rollback

If deployment fails:
1. Go to Railway Dashboard
2. Click **Deployments**
3. Select previous stable version
4. Click **Redeploy**

---

## UTF-8 Encoding Technical Details

### Why This Fix Works

1. **Explicit Encoding at Module Level**
   - Overrides system locale
   - Ensures consistent behavior across environments

2. **Error Replacement Strategy**
   - `errors='replace'`: Replaces invalid characters with `?`
   - Prevents crashes while preserving maximum data

3. **Flask Configuration**
   - `JSON_AS_ASCII=False`: Allows UTF-8 in JSON responses
   - Prevents double-encoding issues

### Compatibility

- ✅ Works with Python 3.8+
- ✅ Compatible with all modern browsers
- ✅ Supports Railway, Heroku, Render, and other PaaS
- ✅ No performance impact

---

## Support & Resources

- Railway Docs: https://docs.railway.app
- Groq API: https://console.groq.com
- Python Unicode: https://docs.python.org/3/howto/unicode.html
- Flask Configuration: https://flask.palletsprojects.com/config/
