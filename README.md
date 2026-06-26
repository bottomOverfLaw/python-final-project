# 🚦 CrashLens — Victorian Road Accidents Dashboard

An interactive data dashboard for exploring Victorian road accident statistics. Built as a team project for RMIT, CrashLens lets users investigate accident trends across multiple dimensions — from high-level summaries down to granular demographic and severity breakdowns.

---

## 👥 Team

| Name | Student ID |
|------|------------|
| Laura | S4257196 |
| Ayan Goel | S4252762 |

**Team:** team36

---

## 🎯 Who Is This For?

CrashLens is designed around two user personas:

- **Elda** — A concerned parent who wants to identify accident-prone routes and postcodes to keep her family safe.
- **Kwazimoto** — A public health researcher who needs granular demographic and injury severity data to inform policy recommendations.

---

## 📊 Features

- **Multi-level analysis** across three levels of data depth (Level 1, 2, and 3)
- **People & Injury page** — Overview of accident-related injuries by type and severity
- **People Analysis page** — Demographic breakdowns (age group, gender, road user type)
- **Accident Analysis page** — Spatial and temporal accident trends
- **Interactive filters** — Filter by postcode, date range, age group, severity, and more
- **Sortable data tables** with pagination
- **Charts** powered by Chart.js
- **Dismissible "how to read this" guidance boxes** on each page

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python (`http.server`) |
| Database | SQLite |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Charts | Chart.js |
| Version control | GitHub Classroom |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- SQLite database file (not included in this repository due to size constraints — see below)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd <repo-folder>
   ```

2. **Add the database file:**
   The SQLite `.db` file is not included in this repository due to the 100MB GitHub Classroom limit. Place the database file in the project root as instructed by your course materials.

3. **Run the server:**
   ```bash
   python server.py
   ```

4. **Open in your browser:**
   ```
   http://localhost:8000
   ```

---

## 📁 Project Structure

```
├── server.py              # Main HTTP server and routing
├── db_level1.py           # Database queries — Level 1 analysis
├── db_level2.py           # Database queries — Level 2 analysis
├── db_level3.py           # Database queries — Level 3 analysis
├── people_injury.html     # People & Injury page
├── people_analysis.html   # People Analysis page
├── accident_analysis.html # Accident Analysis page
├── about.html             # About page
├── static/
│   ├── css/               # Stylesheets
│   └── js/                # JavaScript modules
└── README.md
```

---

## 📝 Notes

- All filter state is managed client-side; filter options are loaded via `/api/filter-options`.
- Age group labels have been normalised (e.g. `5-Dec` → `5-12`) via `CASE WHEN` logic in SQL queries.

---

## 📄 License

This project was created for academic purposes at RMIT University. Not for commercial use.
