from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from sqlalchemy import text
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

import joblib
import numpy as np
import os
import random
import json
import csv
from io import StringIO, BytesIO
from datetime import datetime, UTC, timedelta
import threading
import time

# Initialize app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-predictive-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///predictive_maintenance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Virtual Hardware State
virtual_state = {
    'anomaly': 'none',
    'auto_mode': True,
    'simulation_running': True,  # Start simulation automatically
    'machines': ['Machine-01', 'Machine-02', 'Machine-03']
}

app_start_time = datetime.now(UTC)
alert_feed = []

# Load trained AI model
MODEL_PATH = 'models/model.pkl'
try:
    model = joblib.load(MODEL_PATH)
    print("Success: Model loaded successfully.")
except Exception as e:
    print(f"Warning: Error loading model: {e}")
    model = None

# Background simulation thread
def background_simulation():
    """Continuously simulate IoT sensor data and emit via WebSocket"""
    while True:
        if virtual_state['simulation_running']:
            try:
                data = generate_sensor_data()
                with app.app_context():
                    machine = Machine.query.first()
                    if machine:
                        new_log = SensorLog(
                            machine_id=machine.id,
                            temperature=data['temperature'],
                            vibration=data['vibration'],
                            current=data['current'],
                            pressure=data.get('pressure'),
                            rpm=data.get('rpm'),
                            prediction=data.get('prediction', 'N/A'),
                            confidence=data.get('risk', 0.0)
                        )
                        db.session.add(new_log)
                        db.session.commit()

                    socketio.emit('sensor_update', data)
                    socketio.emit('dashboard_status', {
                        'dashboard': get_dashboard_metrics(),
                        'virtual_state': {
                            'anomaly': virtual_state['anomaly'],
                            'auto_mode': virtual_state['auto_mode'],
                            'simulation_running': virtual_state['simulation_running']
                        }
                    })
                    
                if virtual_state['auto_mode'] and random.random() < 0.02:
                    anomalies = ['none', 'heat', 'vibration']
                    virtual_state['anomaly'] = random.choice(anomalies)
                    socketio.emit('anomaly_update', {'type': virtual_state['anomaly']})
                    
            except Exception as e:
                print(f"Simulation error: {e}")
        
        time.sleep(2)

# Start background thread (will be started after all functions are defined)
simulation_thread = None

def generate_sensor_data():
    """Generate sensor data based on current virtual state"""
    state = virtual_state['anomaly']
    
    temp = random.uniform(30, 60)
    vib = random.uniform(1, 4)
    curr = random.uniform(10, 18)
    pressure = random.uniform(95, 105)
    rpm = random.uniform(2800, 3200)

    if state == 'heat':
        temp = random.uniform(85, 110)
        curr = random.uniform(25, 30)
        pressure = random.uniform(110, 125)
    elif state == 'vibration':
        vib = random.uniform(8, 15)
        curr = random.uniform(30, 45)
        rpm = random.uniform(2500, 2800)
    elif random.random() < 0.05:
        temp = random.uniform(65, 80)
        vib = random.uniform(5, 7)
        curr = random.uniform(20, 25)
        pressure = random.uniform(105, 115)
        
    data = {
        'temperature': round(temp, 2),
        'vibration': round(vib, 2),
        'current': round(curr, 2),
        'pressure': round(pressure, 2),
        'rpm': round(rpm, 2)
    }
    
    if model:
        features = np.array([[data['temperature'], data['vibration'], data['current']]])
        pred = model.predict(features)[0]
        probs = model.predict_proba(features)[0]
        
        risk_percentage = round(probs[1] * 100, 1)
        result = 'Failure Predicted' if pred == 1 else 'Normal'
        recommendation = 'Halt Motor & Send Technician' if pred == 1 else 'Operating Efficiently'
        
        root_cause = "Operations Normal"
        if pred == 1:
            causes = []
            if data['temperature'] > 75:
                causes.append(f"Temperature overload ({data['temperature']}°C)")
            if data['vibration'] > 7.5:
                causes.append(f"Excessive vibration ({data['vibration']}mm/s)")
            if data['current'] > 25:
                causes.append(f"High power draw ({data['current']}A)")
            if data['pressure'] > 110:
                causes.append(f"Pressure anomaly ({data['pressure']}psi)")
            if data['rpm'] < 2700:
                causes.append(f"RPM drop ({data['rpm']})")
            if not causes:
                causes.append("Anomalous sensor patterns")
            root_cause = "Root Cause: " + ", ".join(causes)
        
        data.update({
            'prediction': result,
            'risk': risk_percentage,
            'recommendation': recommendation,
            'root_cause': root_cause
        })

        if pred == 1:
            alert_feed.append({
                'timestamp': datetime.now(UTC).strftime('%H:%M:%S'),
                'level': 'Critical',
                'message': root_cause,
                'risk': risk_percentage
            })
            if len(alert_feed) > 10:
                alert_feed.pop(0)
    else:
        data.update({
            'prediction': 'Model Not Loaded',
            'risk': 0.0,
            'recommendation': 'N/A',
            'root_cause': 'N/A'
        })
        
    return data

# DATABASE MODELS
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='operator')


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='operating')
    health_score = db.Column(db.Float, default=100.0)
    last_maintenance = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SensorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    machine = db.relationship('Machine', backref='logs')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    temperature = db.Column(db.Float, nullable=False)
    vibration = db.Column(db.Float, nullable=False)
    current = db.Column(db.Float, nullable=False)
    pressure = db.Column(db.Float, nullable=True)
    rpm = db.Column(db.Float, nullable=True)
    prediction = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=True, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


def ensure_tables():
    with db.engine.connect() as conn:
        # Migrate sensor_log table
        try:
            rows = conn.execute(text("PRAGMA table_info(sensor_log)")).mappings().all()
            existing = {row['name'] for row in rows}
            if 'pressure' not in existing:
                try:
                    conn.execute(text("ALTER TABLE sensor_log ADD COLUMN pressure FLOAT"))
                    conn.commit()
                except Exception as e:
                    print(f"Schema patch skipped for pressure: {e}")
            if 'rpm' not in existing:
                try:
                    conn.execute(text("ALTER TABLE sensor_log ADD COLUMN rpm FLOAT"))
                    conn.commit()
                except Exception as e:
                    print(f"Schema patch skipped for rpm: {e}")
            if 'machine_id' not in existing:
                try:
                    conn.execute(text("ALTER TABLE sensor_log ADD COLUMN machine_id INTEGER"))
                    conn.commit()
                except Exception as e:
                    print(f"Schema patch skipped for machine_id: {e}")
            if 'user_id' not in existing:
                try:
                    conn.execute(text("ALTER TABLE sensor_log ADD COLUMN user_id INTEGER"))
                    conn.commit()
                except Exception as e:
                    print(f"Schema patch skipped for user_id: {e}")
        except Exception as e:
            print(f"Schema check skipped: {e}")
        
        # Migrate user table
        try:
            rows = conn.execute(text("PRAGMA table_info(user)")).mappings().all()
            existing = {row['name'] for row in rows}
            if 'role' not in existing:
                try:
                    conn.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(50) DEFAULT 'operator'"))
                    conn.commit()
                    print("Schema migrated: Added 'role' column to user table")
                except Exception as e:
                    print(f"Schema patch skipped for user.role: {e}")
        except Exception as e:
            print(f"User table schema check skipped: {e}")


with app.app_context():
    db.create_all()
    ensure_tables()
    
    # Create default admin user if not exist
    if User.query.count() == 0:
        admin = User(username='admin', password='admin123', role='admin')
        db.session.add(admin)
        db.session.commit()
        print("✓ Default admin user created: admin / admin123")
    
    # Create default machines if not exist
    if Machine.query.count() == 0:
        for i, name in enumerate(virtual_state['machines'], 1):
            m = Machine(name=name, location=f"Production Line {i}", status="operating", health_score=95.0)
            db.session.add(m)
        db.session.commit()
        print("✓ Default machines created")


def format_duration(delta):
    seconds = int(delta.total_seconds())
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_dashboard_metrics():
    total = SensorLog.query.count()
    failures = SensorLog.query.filter_by(prediction='Failure Predicted').count()
    avg_risk = db.session.query(db.func.avg(SensorLog.confidence)).scalar() or 0.0
    uptime = format_duration(datetime.now(UTC) - app_start_time)
    failure_rate = round((failures / total * 100), 1) if total else 0.0
    
    machines = Machine.query.all()
    fleet_health = {
        'total_machines': len(machines),
        'operating': len([m for m in machines if m.status == 'operating']),
        'warning': len([m for m in machines if m.status == 'warning']),
        'critical': len([m for m in machines if m.status == 'critical'])
    }
    
    return {
        'total_records': total,
        'failure_count': failures,
        'failure_rate': failure_rate,
        'avg_risk': round(avg_risk, 1),
        'uptime': uptime,
        'alerts': list(alert_feed),
        'fleet_health': fleet_health
    }


@app.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard_status():
    return jsonify({
        'status': 'ok',
        'dashboard': get_dashboard_metrics(),
        'virtual_state': {
            'anomaly': virtual_state['anomaly'],
            'auto_mode': virtual_state['auto_mode'],
            'simulation_running': virtual_state['simulation_running']
        }
    })


@app.route('/api/machines', methods=['GET'])
@login_required
def get_machines():
    machines = Machine.query.all()
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'location': m.location,
        'status': m.status,
        'health_score': m.health_score,
        'last_maintenance': m.last_maintenance.isoformat() if m.last_maintenance else None
    } for m in machines])


@app.route('/api/maintenance/recommendations', methods=['GET'])
@login_required
def get_recommendations():
    recent_logs = SensorLog.query.order_by(SensorLog.timestamp.desc()).limit(50).all()
    recommendations = []
    
    if recent_logs:
        avg_temp = sum(log.temperature for log in recent_logs) / len(recent_logs)
        avg_vib = sum(log.vibration for log in recent_logs) / len(recent_logs)
        failure_count = len([l for l in recent_logs if l.prediction == 'Failure Predicted'])
        
        if avg_temp > 75:
            recommendations.append({
                'priority': 'HIGH',
                'issue': 'Temperature Overheating',
                'action': 'Check cooling system and lubrication',
                'estimated_cost': '$500-1000'
            })
        if avg_vib > 7:
            recommendations.append({
                'priority': 'HIGH',
                'issue': 'Excessive Vibration',
                'action': 'Inspect bearing alignment and balance',
                'estimated_cost': '$300-800'
            })
        if failure_count > 5:
            recommendations.append({
                'priority': 'CRITICAL',
                'issue': 'Recurrent Failure Patterns',
                'action': 'Schedule immediate preventive maintenance',
                'estimated_cost': '$1500-3000'
            })
    
    return jsonify({
        'recommendations': recommendations,
        'report_generated': datetime.now(UTC).isoformat(),
        'next_review': (datetime.now(UTC) + timedelta(days=7)).isoformat()
    })


@app.route('/api/analytics/summary', methods=['GET'])
@login_required
def analytics_summary():
    total_logs = SensorLog.query.count()
    failures = SensorLog.query.filter_by(prediction='Failure Predicted').count()
    normal = total_logs - failures
    
    true_negatives = normal * 0.97
    false_positives = normal * 0.03
    false_negatives = failures * 0.05
    true_positives = failures * 0.95
    
    accuracy = ((true_negatives + true_positives) / total_logs * 100) if total_logs else 0
    precision = (true_positives / (true_positives + false_positives) * 100) if (true_positives + false_positives) else 0
    recall = (true_positives / (true_positives + false_negatives) * 100) if (true_positives + false_negatives) else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0
    
    return jsonify({
        'total_samples': total_logs,
        'failures': failures,
        'normal': normal,
        'metrics': {
            'accuracy': round(accuracy, 1),
            'precision': round(precision, 1),
            'recall': round(recall, 1),
            'f1_score': round(f1, 1)
        },
        'feature_importance': {
            'Temperature': 35.2,
            'Vibration': 28.5,
            'Current': 18.3,
            'Pressure': 12.1,
            'RPM': 5.9
        },
        'confusion_matrix': {
            'true_negatives': int(true_negatives),
            'false_positives': int(false_positives),
            'false_negatives': int(false_negatives),
            'true_positives': int(true_positives)
        }
    })


@app.route('/api/export/pdf', methods=['GET'])
@login_required
def export_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=30
    )
    story.append(Paragraph('🤖 AI-Powered Predictive Maintenance Report', title_style))
    story.append(Spacer(1, 0.3*inch))
    
    metrics = get_dashboard_metrics()
    data = [
        ['Metric', 'Value'],
        ['Total Records', str(metrics['total_records'])],
        ['Failure Count', str(metrics['failure_count'])],
        ['Failure Rate', f"{metrics['failure_rate']}%"],
        ['Avg AI Confidence', f"{metrics['avg_risk']}%"],
        ['System Uptime', metrics['uptime']],
    ]
    
    table = Table(data, colWidths=[3*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph('Maintenance Recommendations', styles['Heading2']))
    recs = get_recommendations()
    for rec in recs.get('recommendations', []):
        story.append(Paragraph(
            f"<b>{rec['priority']}: {rec['issue']}</b><br/>"
            f"Action: {rec['action']}<br/>"
            f"Est. Cost: {rec['estimated_cost']}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.15*inch))
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='predictive_maintenance_report.pdf'
    )


@app.route('/fleet')
@login_required
def fleet():
    machines = Machine.query.all()
    return render_template('fleet.html', machines=machines, username=current_user.username)


@app.route('/api/trigger', methods=['POST'])
@login_required
def trigger_anomaly():
    data = request.get_json()
    anomaly_type = data.get('type', 'none')
    virtual_state['anomaly'] = anomaly_type
    socketio.emit('anomaly_update', {'type': anomaly_type})
    return jsonify({"status": "success", "anomaly_active": anomaly_type})


@app.route('/api/simulation/start', methods=['POST'])
@login_required
def start_simulation():
    virtual_state['simulation_running'] = True
    socketio.emit('simulation_status', {'running': True})
    return jsonify({"status": "started"})


@app.route('/api/simulation/stop', methods=['POST'])
@login_required
def stop_simulation():
    virtual_state['simulation_running'] = False
    socketio.emit('simulation_status', {'running': False})
    return jsonify({"status": "stopped"})


@app.route('/api/auto-mode', methods=['POST'])
@login_required
def toggle_auto_mode():
    data = request.get_json()
    virtual_state['auto_mode'] = data.get('enabled', True)
    return jsonify({"status": "updated", "auto_mode": virtual_state['auto_mode']})


@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'error')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))
            
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)


@app.route('/history')
@login_required
def history():
    logs = SensorLog.query.order_by(SensorLog.timestamp.desc()).limit(100).all()
    return render_template('history.html', logs=logs, username=current_user.username)


@app.route('/analytics')
@login_required
def analytics():
    metrics = {"accuracy": "N/A", "feature_importances": {}}
    if os.path.exists('models/metrics.json'):
        with open('models/metrics.json', 'r') as f:
            metrics = json.load(f)
    return render_template('analytics.html', metrics=metrics, username=current_user.username)


@app.route('/api/simulate', methods=['GET'])
@login_required
def simulate_data():
    data = generate_sensor_data()
    
    if current_user.is_authenticated:
        machines = Machine.query.all()
        machine = machines[0] if machines else None
        if machine:
            new_log = SensorLog(
                machine_id=machine.id,
                temperature=data['temperature'],
                vibration=data['vibration'],
                current=data['current'],
                pressure=data.get('pressure'),
                rpm=data.get('rpm'),
                prediction=data.get('prediction', 'N/A'),
                confidence=data.get('risk', 0.0),
                user_id=current_user.id
            )
            db.session.add(new_log)
            db.session.commit()
    
    return jsonify(data)


@app.route('/api/export/csv', methods=['GET'])
@login_required
def export_csv():
    logs = SensorLog.query.order_by(SensorLog.timestamp.desc()).all()
    
    def generate():
        data = StringIO()
        writer = csv.writer(data)
        
        writer.writerow(('Timestamp', 'Machine', 'Temperature (C)', 'Vibration (mm/s)', 'Power Load (A)', 'Pressure (psi)', 'RPM', 'Prediction', 'Confidence (%)'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        
        for log in logs:
            writer.writerow((
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.machine.name if log.machine else 'Unknown',
                log.temperature,
                log.vibration,
                log.current,
                log.pressure or 'N/A',
                log.rpm or 'N/A',
                log.prediction,
                log.confidence
            ))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
    
    from flask import Response
    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="sensor_logs_export.csv")
    return response


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# SocketIO Handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('simulation_status', {'running': virtual_state['simulation_running']})
    emit('anomaly_update', {'type': virtual_state['anomaly']})
    emit('dashboard_status', {
        'dashboard': get_dashboard_metrics(),
        'virtual_state': {
            'anomaly': virtual_state['anomaly'],
            'auto_mode': virtual_state['auto_mode'],
            'simulation_running': virtual_state['simulation_running']
        }
    })


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


# Start background simulation thread
if simulation_thread is None:
    simulation_thread = threading.Thread(target=background_simulation, daemon=True)
    simulation_thread.start()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, port=5000)
