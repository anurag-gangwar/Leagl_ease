# ⚖️ Legal-Ease — AI Contract Analyzer for Regional Indian Languages

**Hackathon Project · Problem Statement 1.2 · ML & AI Track**

Legal-Ease is an LLM-powered contract analysis tool that helps small business owners and individuals in India understand complex legal contracts. Upload any PDF or text contract and receive a plain-language summary in Hindi, Tamil, Telugu, Marathi, Bengali, Kannada, or Gujarati — with highlighted risky clauses and severity scores.

---

## 🗂️ Project Structure

```
legal_ease/
├── app.py                    # Flask application + all routes
├── config.py                 # Configuration (API keys, languages, etc.)
├── database.py               # SQLAlchemy init
├── models.py                 # Database models (Contract, Clause, ChatMessage)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
│
├── utils/
│   ├── __init__.py
│   ├── pdf_parser.py         # PDF & text extraction (PyMuPDF, OCR fallback)
│   ├── llm_analyzer.py       # Sarvam AI integration (analysis + chatbot)
│   └── report_generator.py   # PDF & DOCX report generation
│
├── templates/
│   ├── base.html             # Base layout (navbar, footer, Bootstrap 5)
│   ├── index.html            # Home / landing page
│   ├── upload.html           # Upload + language/type selection
│   ├── analysis.html         # Analysis results + clause cards + donut chart
│   ├── report.html           # Full printable report
│   ├── chatbot.html          # Contract chatbot interface
│   ├── history.html          # Contract history + pagination
│   └── errors/
│       ├── 404.html
│       └── 500.html
│
└── static/
    ├── css/
    │   └── style.css         # Full custom design system
    ├── js/
    │   └── main.js           # Global JS (animations, tooltips, etc.)
    ├── uploads/              # Uploaded contract files (auto-created)
    └── reports/              # Generated PDF/DOCX reports (auto-created)
```

---

## ⚙️ Setup Instructions

### 1. Clone & Enter Directory

```bash
git clone <your-repo>
cd legal_ease
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For scanned/image-only PDFs on macOS, install the OCR engine once:

```bash
brew install tesseract
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and add your Sarvam API key:

```
SARVAM_API_KEY=your-sarvam-api-key
SARVAM_MODEL=sarvam-105b
SARVAM_REASONING_EFFORT=high
SARVAM_TIMEOUT_SECONDS=90
SECRET_KEY=use-a-long-random-string
```

Get a key from [Sarvam AI Console](https://console.sarvam.ai/). Keep `.env` local; it is intentionally ignored by Git.

### 5. Run the Application

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5001**

---


## ✨ Features

| Feature | Status |
|---|---|
| PDF upload & text extraction (PyMuPDF) | ✅ |
| Scanned PDF OCR fallback (pytesseract) | ✅ |
| Sarvam AI clause analysis | ✅ |
| Red flag detection (8+ types) | ✅ |
| Severity scoring (High / Medium / Low) | ✅ |
| Hindi, Tamil, Telugu translation | ✅ |
| Marathi, Bengali, Kannada, Gujarati | ✅ |
| Risk dashboard (donut chart) | ✅ |
| PDF report download | ✅ |
| DOCX report download | ✅ |
| Chatbot Q&A about contract | ✅ |
| Clause vs standard template comparison | ✅ (Bonus) |
| Contract history with pagination | ✅ |
| SQLite database | ✅ |
| Responsive UI (Bootstrap 5) | ✅ |

The chatbot uses a streamed response so answers appear progressively in the
browser. Provider and credential details are kept in server logs; the UI shows
short recovery messages instead of raw SDK errors.

---

## 🚩 Red Flags Detected

- Auto-Renewal Clauses
- Unlimited / Uncapped Liability
- One-sided Termination Rights
- Hidden Fees
- Broad Data Sharing
- Non-Compete Restrictions
- Steep Penalty Clauses
- Forced Arbitration
- IP Assignment
- Indemnification Clauses

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask + SQLAlchemy + SQLite |
| LLM | Sarvam AI (`sarvam-105b`) |
| PDF Parsing | PyMuPDF + pdfplumber |
| OCR | pytesseract (fallback) |
| Report Gen | ReportLab (PDF) + python-docx (DOCX) |
| Frontend | Bootstrap 5 + Chart.js |
| Fonts | Playfair Display + DM Sans |

---

## 📝 Evaluation Criteria Coverage

| Criterion | Weight | Implementation |
|---|---|---|
| Clause Detection & Relevance | 30% | Sarvam API with structured JSON output, 10+ clause types |
| Translation Quality | 25% | Sarvam translation, 7 languages |
| UI/UX & Report Usability | 20% | Bootstrap 5, custom design, PDF/DOCX download |
| Red Flag Coverage & Scoring | 15% | 8+ flag types, 3-tier severity, real-world explanations |
| Innovation & Bonus | 10% | Chatbot, clause comparison, multi-language chatbot |

---

## 🎯 Bonus Features Implemented

1. **Context-aware warnings**: Instead of "liability clause found", says "If something goes wrong, you may owe the other party an unlimited amount of money with no cap"
2. **Clause comparison**: Compare any clause against standard industry templates
3. **Chatbot interface**: Ask follow-up questions about any clause in English or regional language
4. **Additional languages**: Marathi, Bengali, Kannada, Gujarati (4 bonus languages)

---

## ⚠️ Disclaimer

This tool is for informational purposes only and does not constitute legal advice. Please consult a qualified lawyer before making any legal decisions.

---
