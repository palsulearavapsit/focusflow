# 🌊 FocusFlow

FocusFlow is an intelligent study assistant that leverages computer vision and machine learning to help you maintain peak concentration and gamify your productivity.

## ✨ Key Features
- 👁️ **Precision Eye-Tracking**: Real-time monitoring of your gaze to detect when you're drifting away from your work.
- 🧘 **Emotion Intelligence**: Integrated facial emotion analysis to understand your stress and focus levels throughout a session.
- 🎮 **Gamified Success**: Earn unique titles, build daily streaks, and unlock achievements as you maintain healthy study habits.
- 🤖 **FocusBot AI**: A personal assistant powered by Google's Gemini to guide your study sessions and answer questions.
- 📊 **Insightful Analytics**: Dynamic charts to visualize your study patterns, distraction peaks, and productivity trends.
- 🎥 **Smooth Live Backgrounds**: Immersive particle-based backgrounds that respond to your session's status.

## 🚀 Getting Started
1. **Requirements**: Python 3.10+ and MySQL Server.
2. **Environment**: Configure your API keys in `backend/.env` (Gemini, YouTube, etc.).
3. **Run**: Launch the entire system with a single command:
   ```bash
   python run.py
   ```

## 🛠️ Tech Stack
- **Backend Architecture**: FastAPI, SQLAlchemy, PyJWT.
- **AI & Computer Vision**: TensorFlow Lite, Mediapipe (Face/Eye Mesh).
- **Frontend Layer**: Vanilla ES6+, Bootstrap 5, Chart.js, Particles.js.
- **Database**: MySQL.
- **LLM Integration**: Google Gemini API.

## 📂 Project Structure
- 📁 `backend/` – FastAPI application, ML services, and database migrations.
- 📁 `frontend/` – Static assets, modern UI components, and browser-side CV logic.
- 📁 `database/` – SQL schema definitions and local persistent storage.
- 📄 `run.py` – Unified CLI tool for system-wide orchestration.

---
<div align="center">
  <p>Designed for the next generation of students.</p>
  <b>Master your focus. Elevate your flow.</b>
</div>


