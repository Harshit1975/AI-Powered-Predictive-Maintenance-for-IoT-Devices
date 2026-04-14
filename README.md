# AI-Powered Predictive Maintenance System for IoT Devices

![IoT Predictive Analytics Dashboard](./assets/dashboard_preview.png) *(Add your screenshot here)*

## 1️⃣ Project Overview
This project is an AI-powered system that simulates the monitoring of industrial IoT machines. It uses synthetic sensor data (Temperature, Vibration, Current) to predict imminent machine failures before they happen, allowing plant operators to transition from reactive to *predictive* maintenance.

## 2️⃣ Architecture
The project is built on three main layers:
1. **IoT Simulation Layer**: A background thread generating realistic sensor data telemetry.
2. **AI Layer**: A trained Scikit-Learn Random Forest Classification model predicting failure/normal states.
3. **Application Layer**: A full-stack web dashboard (Flask + Vanilla HTML/CSS/JS) to monitor real-time charts and handle secure User Authentication.

## 3️⃣ Folder Structure
```text
AI-Predictive-Maintenance-IoT/
│
├── data/                    # Generated synthetic dataset (iot_sensor_data.csv)
├── src/                     
│   ├── generate_data.py     # Script to generate synthetic IoT data
│   └── train_model.py       # Script to train RF model
├── models/
│   └── model.pkl            # Pickled Random Forest classifier
├── templates/               # Flask UI templates (Dashboard, Login, History)
├── static/                  # Vanilla CSS, Chart.js logic
├── main.py                  # Main Flask Web Server & Authentication
├── requirements.txt
└── README.md
```

## 4️⃣ How to Run
#### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 2: Generate Data and Train AI Model
(If you downloaded the repo without the `models/model.pkl` file, you need to generate data and train first)
```bash
python src/generate_data.py
python src/train_model.py
```

#### Step 3: Start the UI Dashboard
```bash
python main.py
```
*Visit `http://127.0.0.1:5000` in your browser. Register a new administrative account and watch the IoT console.*

## 5️⃣ GitHub Proof Plan (Portfolio Building Strategy)
If you are learning and building this for your resume, make sure you commit progressively rather than dropping all files at once:
- **Day 1**: Push `generate_data.py` - "Created simulated IoT testbench dataloader"
- **Day 2**: Push `train_model.py` and `notebooks/` - "Trained classification model for vibration/temp thresholds"
- **Day 3**: Push `main.py` and auth templates - "Integrated SQLite login mechanisms for secure operator view"
- **Day 4**: Push `dashboard.html` and `style.css` - "Built dark-mode premium UI with Chart.JS live streams"
- **Day 5**: Add screenshots to README and launch - "Finalized deployment"
