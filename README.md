# Rotation Tracker

A local desktop app for tracking administrative tasks during clinical rotations.

## Features
- ✅ Task checklist grouped by category
- 📅 Calendar view showing tasks by due date
- 🔔 System tray reminders for upcoming/overdue tasks
- 💾 Auto git-commits every time you check off a task
- 📊 Dashboard with stats at a glance

## Setup

### 1. Prerequisites
- Python 3.10 or newer → https://python.org
- Git → https://git-scm.com (for auto-commit feature)

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python main.py
```

### 4. (Optional) Run on startup
**macOS**: Add a Login Item via System Settings → General → Login Items  
**Windows**: Create a shortcut to `pythonw main.py` in your Startup folder  
**Linux**: Add `python /path/to/main.py &` to `~/.profile`

## How it works

- Tasks are stored in `tasks.json` in the same folder as `main.py`
- Every time you check off or add a task, a `git commit` is made automatically — giving you a full history
- The app lives in your system tray when you close the window — reminders keep running
- Reminders fire when any task is due within **2 days** or is overdue

## Categories
- 📋 Paperwork
- 💉 Vaccinations & Health
- 🗓 Scheduling
- 📝 Evaluations
- 📁 Documentation
- 📌 Other

## Data file

`tasks.json` is human-readable. You can edit it directly if needed — just restart the app after.

```json
[
  {
    "id": 1,
    "title": "Submit health clearance forms",
    "category": "Vaccinations & Health",
    "due": "2025-09-01",
    "notes": "Include TB test, flu shot record",
    "completed": false,
    "completed_date": null
  }
]
```
