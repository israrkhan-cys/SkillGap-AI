# 🧠 SkillGap AI

**From resume to roadmap in seconds.**

A hackathon project that analyzes CVs/resumes using AI to identify skill gaps, create personalized learning roadmaps, and provide job readiness scores.

![Tech Stack](https://img.shields.io/badge/Python-Flask-blue)
![AI](https://img.shields.io/badge/AI-Groq%20%2F%20LLaMA%203-purple)
![Frontend](https://img.shields.io/badge/Frontend-Tailwind%20CSS-cyan)

---

## 🎯 The Problem

Students and early professionals struggle with:
- ❌ Not knowing what skills they're missing
- ❌ Not knowing what to learn next
- ❌ Not knowing how close they are to being job-ready
- ❌ Blindly following random courses without a clear path

## 💡 The Solution

**SkillGap AI** solves this by:
- ✅ Analyzing CVs using advanced AI (Groq LLaMA 3)
- ✅ Identifying missing skills for tech roles
- ✅ Creating personalized learning roadmaps
- ✅ Providing a job readiness score (0-100)
- ✅ Delivering results in under 10 seconds

---

## 🚀 Features

- 📤 **Upload or Paste**: Support for PDF, DOCX, TXT files or direct text input
- 🤖 **AI-Powered Analysis**: Uses Groq's LLaMA 3 (70B) model for intelligent analysis
- 📊 **Comprehensive Report**: 
  - Missing skills identification
  - Step-by-step learning roadmap
  - Job readiness score with explanation
- 🎨 **Beautiful UI**: Clean, modern interface with Tailwind CSS
- ⚡ **Fast Results**: Analysis completes in 5-10 seconds
- 💯 **Free to Use**: No registration required

---

## ⚙️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python + Flask |
| **AI API** | Groq (LLaMA 3.1 70B) |
| **Frontend** | HTML + Tailwind CSS |
| **File Processing** | PyPDF2, python-docx |
| **Hosting** | Local / Render / Any cloud platform |

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Groq API key ([Get one free here](https://console.groq.com/keys))

### Step 1: Clone the Repository
```bash
cd ~/Desktop/Skillgap_AI
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables
```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=your_actual_api_key_here
```

### Step 5: Run the Application
```bash
python app.py
```

The app will start at: **http://localhost:5000**

---

## 🎮 How to Use

1. **Open the app** in your browser (http://localhost:5000)
2. **Upload your CV** (PDF, DOCX, or TXT) OR **paste your CV text** directly
3. **Click "Analyze My Skills"**
4. **Get your results** in seconds:
   - Missing skills
   - Personalized learning roadmap
   - Job readiness score
5. **Print or save** your report

---

## 📁 Project Structure

```
Skillgap_AI/
├── app.py                  # Flask backend
├── templates/
│   └── index.html         # Frontend UI
├── uploads/               # Temporary file storage (auto-created)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

---

## 🔑 Getting a Groq API Key

1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up for a free account
3. Navigate to "API Keys"
4. Create a new API key
5. Copy and paste it into your `.env` file

**Note**: Groq offers generous free tier limits, perfect for hackathons and demos!

---

## 🎨 Screenshots

### Home Page
- Clean, professional landing page
- Problem/Solution overview
- Upload interface with drag-and-drop

### Results Page
- Formatted skill gap analysis
- Color-coded learning roadmap
- Visual job readiness score
- Print and re-analyze options

---

## 🚢 Deployment Options

### Deploy to Render (Free)
1. Push code to GitHub
2. Create new Web Service on Render
3. Connect your repository
4. Add environment variable: `GROQ_API_KEY`
5. Deploy!

### Deploy Locally for Demo
```bash
python app.py
# Share your local URL or use ngrok for public access
```

---

## 🧪 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/analyze` | POST | Analyze CV and return results |
| `/health` | GET | Health check endpoint |

---

## 🛠️ Customization

### Change AI Model
Edit `app.py`, line ~80:
```python
model="llama-3.1-70b-versatile",  # Try other Groq models
```

### Adjust Analysis Prompt
Edit the prompt in `analyze_cv_with_groq()` function in `app.py`

### Modify UI Colors
Edit Tailwind classes in `templates/index.html`

---

## 📝 Sample CV Input

You can test with this sample CV:

```
John Doe
Software Developer

EDUCATION
Bachelor of Computer Science, XYZ University (2020-2024)

SKILLS
- Python
- HTML/CSS
- Git
- Basic JavaScript

EXPERIENCE
Intern at ABC Corp (Summer 2023)
- Built simple web applications
- Worked with team on small projects

PROJECTS
Personal portfolio website
To-do list app in Python
```

---

## ⚡ Quick Demo Mode

For judges/demo purposes, you can use the included test CV or paste any job description to see instant results!

---

## 🤝 Contributing

This is a hackathon project, but suggestions are welcome!

---

## 📄 License

MIT License - Free to use for learning and hackathons

---

## 👨‍💻 Author

Built for **Hackathon 2026**

**Goal**: Help students and professionals bridge their skill gaps and advance their careers.

---

## 🎯 Hackathon Pitch Points

✨ **Solves a real problem**: Millions of students don't know what skills to learn  
⚡ **Fast & Simple**: Results in under 10 seconds, no signup required  
🆓 **Free & Accessible**: No cost to users, powered by free AI API  
🎨 **Clean UI**: Professional design that looks good on any device  
🚀 **Scalable**: Can easily add more features (job matching, course recommendations)  
💡 **Innovative Use of AI**: Leverages latest LLaMA 3.1 model for intelligent analysis  

---

## 🔮 Future Enhancements

- 📧 Email reports to users
- 💼 Job matching based on current skills
- 📚 Course recommendations from Coursera/Udemy
- 📈 Progress tracking over time
- 🤝 LinkedIn integration
- 🌍 Multi-language support

---

## 📞 Support

For issues or questions:
- Check the [Groq Documentation](https://console.groq.com/docs)
- Review the code comments in `app.py`
- Ensure your API key is valid

---

**Made with ❤️ for making career growth accessible to everyone**
