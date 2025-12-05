"""
🚖 بوت النقل الذكي - نسخة مبسطة وخالية من المشاكل
"""

import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ============================================================================
# إعدادات أساسية
# ============================================================================

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# الحصول على التوكن
BOT_TOKEN = os.environ.get('BOT_TOKEN', 8425005126:AAExDibH8mxVpITuhA98AFfNcUo9Rgdd98A')

# تهيئة التطبيق والبوت
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ============================================================================
# تخزين البيانات (في الذاكرة - لحفظ البساطة)
# ============================================================================

# تخزين بيانات المستخدمين
users = {}
# تخزين الرحلات
rides = {}
# تخزين السائقين النشطين
active_drivers = {}
# تخزين طلبات الرحلات
ride_requests = {}

# ============================================================================
# دوال مساعدة
# ============================================================================

def save_data():
    """حفظ البيانات في ملفات مؤقتة"""
    try:
        with open('users_data.json', 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False)
        with open('rides_data.json', 'w', encoding='utf-8') as f:
            json.dump(rides, f, ensure_ascii=False)
        logger.info("💾 تم حفظ البيانات")
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ البيانات: {e}")

def load_data():
    """تحميل البيانات من الملفات"""
    global users, rides
    try:
        if os.path.exists('users_data.json'):
            with open('users_data.json', 'r', encoding='utf-8') as f:
                users = json.load(f)
        if os.path.exists('rides_data.json'):
            with open('rides_data.json', 'r', encoding='utf-8') as f:
                rides = json.load(f)
        logger.info("📂 تم تحميل البيانات")
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل البيانات: {e}")

def create_ride_keyboard(user_type="customer"):
    """إنشاء لوحة مفاتيح حسب نوع المستخدم"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if user_type == "customer":
        buttons = [
            types.KeyboardButton('🚖 طلب رحلة جديدة'),
            types.KeyboardButton('📍 إرسال موقعي', request_location=True),
            types.KeyboardButton('📋 رحلاتي السابقة'),
            types.KeyboardButton('💰 رصيدي'),
            types.KeyboardButton('⚙️ الإعدادات'),
            types.KeyboardButton('📞 الدعم')
        ]
    else:  # driver
        buttons = [
            types.KeyboardButton('🟢 بدء العمل'),
            types.KeyboardButton('🔴 إنهاء العمل'),
            types.KeyboardButton('📍 تحديث موقعي', request_location=True),
            types.KeyboardButton('📋 رحلاتي'),
            types.KeyboardButton('💰 أرباحي'),
            types.KeyboardButton('📞 الدعم')
        ]
    
    markup.add(*buttons)
    return markup

def create_inline_ride_buttons(ride_id):
    """إنشاء أزرار داخلية للرحلة"""
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    
    buttons = [
        InlineKeyboardButton("✅ قبول الرحلة", callback_data=f"accept_{ride_id}"),
        InlineKeyboardButton("❌ رفض الرحلة", callback_data=f"reject_{ride_id}")
    ]
    
    markup.add(*buttons)
    return markup

# ============================================================================
# معالجات البوت
# ============================================================================

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    """معالجة أمر البدء"""
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name
    username = message.from_user.username or ""
    
    logger.info(f"👋 /start من: {first_name} ({user_id})")
    
    # حفظ بيانات المستخدم
    users[user_id] = {
        'id': user_id,
        'username': username,
        'first_name': first_name,
        'role': None,
        'balance': 0.0,
        'total_rides': 0,
        'created_at': datetime.now().isoformat()
    }
    
    # عرض خيارات التسجيل
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('👤 عميل'),
        types.KeyboardButton('🚖 سائق'),
        types.KeyboardButton('📞 المساعدة')
    )
    
    welcome_msg = f"""🎉 <b>مرحباً {first_name} في بوت النقل الذكي!</b>

🚖 <b>خدمة نقل ذكية توفر لك:</b>
• رحلات سريعة وآمنة
• تتبع مباشر للرحلة
• دفع إلكتروني آمن
• تقييمات موثوقة

📱 <b>اختر دورك للبدء:</b>"""
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ['👤 عميل', '🚖 سائق'])
def handle_role_selection(message):
    """معالجة اختيار الدور"""
    user_id = str(message.from_user.id)
    role_text = message.text
    role = "customer" if role_text == "👤 عميل" else "driver"
    
    logger.info(f"🎭 اختيار دور: {role} من: {user_id}")
    
    # تحديث دور المستخدم
    if user_id in users:
        users[user_id]['role'] = role
    
    # إنشاء القائمة المناسبة
    markup = create_ride_keyboard(role)
    
    role_msg = {
        "customer": "👤 <b>تم تسجيلك كعميل بنجاح!</b>\n\nيمكنك الآن طلب رحلات بسهولة وأمان.",
        "driver": "🚖 <b>تم تسجيلك كسائق بنجاح!</b>\n\nيمكنك الآن بدء العمل واستقبال طلبات الركوب."
    }
    
    bot.send_message(
        message.chat.id,
        role_msg[role] + "\n\n🔧 <b>اختر الخدمة المناسبة:</b>",
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text == '🚖 طلب رحلة جديدة')
def handle_new_ride_request(message):
    """معالجة طلب رحلة جديدة"""
    user_id = str(message.from_user.id)
    
    logger.info(f"🚖 طلب رحلة جديدة من: {user_id}")
    
    # التحقق من أن المستخدم عميل
    if user_id not in users or users[user_id].get('role') != 'customer':
        bot.send_message(message.chat.id, "❌ يجب أن تكون مسجلاً كعميل لطلب رحلة.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('📍 إرسال موقعي', request_location=True),
        types.KeyboardButton('رجوع')
    )
    
    bot.send_message(
        message.chat.id,
        "📍 <b>طلب رحلة جديدة</b>\n\n"
        "الرجاء إرسال موقعك الحالي لتحديد نقطة الانطلاق.",
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text == '🟢 بدء العمل')
def handle_driver_start(message):
    """بدء عمل السائق"""
    user_id = str(message.from_user.id)
    
    logger.info(f"🟢 بدء عمل سائق: {user_id}")
    
    # التحقق من أن المستخدم سائق
    if user_id not in users or users[user_id].get('role') != 'driver':
        bot.send_message(message.chat.id, "❌ يجب أن تكون مسجلاً كسائق لبدء العمل.")
        return
    
    # إضافة السائق إلى القائمة النشطة
    active_drivers[user_id] = {
        'id': user_id,
        'username': users[user_id].get('username', ''),
        'first_name': users[user_id].get('first_name', ''),
        'is_available': True,
        'started_at': datetime.now().isoformat()
    }
    
    bot.send_message(
        message.chat.id,
        "✅ <b>تم تفعيل وضع السائق!</b>\n\n"
        "🎯 أنت الآن تستقبل طلبات الركوب تلقائياً.\n"
        "📍 تأكد من تحديث موقعك بانتظام.\n\n"
        "لإيقاف الخدمة، اضغط '🔴 إنهاء العمل'"
    )

@bot.message_handler(func=lambda msg: msg.text == '🔴 إنهاء العمل')
def handle_driver_stop(message):
    """إنهاء عمل السائق"""
    user_id = str(message.from_user.id)
    
    logger.info(f"🔴 إنهاء عمل سائق: {user_id}")
    
    # إزالة السائق من القائمة النشطة
    if user_id in active_drivers:
        del active_drivers[user_id]
    
    bot.send_message(
        message.chat.id,
        "🔴 <b>تم إيقاف خدمة الاستقبال</b>\n\n"
        "للعودة لاستقبال الطلبات، اضغط '🟢 بدء العمل'"
    )

@bot.message_handler(content_types=['location'])
def handle_location(message):
    """معالجة الموقع المرسل"""
    user_id = str(message.from_user.id)
    location = message.location
    
    logger.info(f"📍 موقع من: {user_id} - {location.latitude}, {location.longitude}")
    
    if user_id not in users:
        bot.send_message(message.chat.id, "❌ يجب البدء باستخدام /start أولاً.")
        return
    
    user = users[user_id]
    
    if user.get('role') == 'customer':
        # إنشاء طلب رحلة جديد
        ride_id = f"ride_{user_id}_{int(datetime.now().timestamp())}"
        
        ride_data = {
            'ride_id': ride_id,
            'customer_id': user_id,
            'customer_name': user.get('first_name', 'عميل'),
            'pickup_location': {
                'lat': location.latitude,
                'lng': location.longitude
            },
            'status': 'pending',
            'fare': 15.0,
            'created_at': datetime.now().isoformat()
        }
        
        # حفظ الرحلة
        rides[ride_id] = ride_data
        
        # إعلام المستخدم
        bot.send_message(
            message.chat.id,
            "📍 <b>تم استلام موقعك بنجاح!</b>\n\n"
            f"• <b>خط العرض:</b> {location.latitude:.6f}\n"
            f"• <b>خط الطول:</b> {location.longitude:.6f}\n\n"
            "🚖 <b>تم إنشاء طلب رحلة!</b>\n"
            "⏳ جاري البحث عن سائق قريب...",
            reply_markup=create_ride_keyboard("customer")
        )
        
        # البحث عن سائقين متاحين
        if active_drivers:
            # إرسال طلب الرحلة للسائقين المتاحين
            for driver_id, driver in active_drivers.items():
                try:
                    markup = create_inline_ride_buttons(ride_id)
                    
                    bot.send_message(
                        driver_id,
                        f"🚖 <b>طلب رحلة جديد</b>\n\n"
                        f"• <b>العميل:</b> {user.get('first_name', 'عميل')}\n"
                        f"• <b>التكلفة:</b> 15 ريال\n\n"
                        f"<b>رقم الرحلة:</b> {ride_id[-8:]}",
                        reply_markup=markup
                    )
                except Exception as e:
                    logger.error(f"❌ فشل إرسال طلب الرحلة للسائق {driver_id}: {e}")
            
            logger.info(f"✅ تم إرسال طلب الرحلة لـ {len(active_drivers)} سائق")
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ <b>لا يوجد سائقون متاحون حالياً</b>\n\n"
                "يرجى المحاولة مرة أخرى لاحقاً.",
                reply_markup=create_ride_keyboard("customer")
            )
    
    elif user.get('role') == 'driver':
        # تحديث موقع السائق
        if user_id in active_drivers:
            active_drivers[user_id]['location'] = {
                'lat': location.latitude,
                'lng': location.longitude
            }
        
        bot.send_message(
            message.chat.id,
            "📍 <b>تم تحديث موقعك بنجاح!</b>\n\n"
            f"• <b>خط العرض:</b> {location.latitude:.6f}\n"
            f"• <b>خط الطول:</b> {location.longitude:.6f}\n\n"
            "✅ <b>تم تحديث موقع السائق</b>",
            reply_markup=create_ride_keyboard("driver")
        )

@bot.message_handler(func=lambda msg: msg.text == '📋 رحلاتي السابقة')
def handle_my_rides(message):
    """عرض رحلات المستخدم السابقة"""
    user_id = str(message.from_user.id)
    
    logger.info(f"📋 طلب رحلات سابقة من: {user_id}")
    
    user_rides = []
    for ride_id, ride in rides.items():
        if ride.get('customer_id') == user_id or ride.get('driver_id') == user_id:
            user_rides.append(ride)
    
    if not user_rides:
        bot.send_message(
            message.chat.id,
            "📭 <b>لا توجد رحلات سابقة</b>",
            reply_markup=create_ride_keyboard("customer")
        )
        return
    
    response = "📋 <b>رحلاتي السابقة</b>\n\n"
    
    for ride in user_rides[:5]:  # عرض آخر 5 رحلات فقط
        status_emoji = {
            'pending': '⏳',
            'accepted': '✅',
            'in_progress': '🚗',
            'completed': '🎉',
            'cancelled': '❌'
        }.get(ride.get('status', 'pending'), '❓')
        
        response += (
            f"{status_emoji} <b>رحلة #{ride.get('ride_id', '')[8:]}</b>\n"
            f"• <b>الحالة:</b> {ride.get('status', 'غير معروف')}\n"
            f"• <b>التكلفة:</b> {ride.get('fare', 0)} ريال\n\n"
        )
    
    bot.send_message(
        message.chat.id,
        response,
        reply_markup=create_ride_keyboard("customer")
    )

@bot.message_handler(func=lambda msg: msg.text == '💰 رصيدي')
def handle_balance(message):
    """عرض رصيد المستخدم"""
    user_id = str(message.from_user.id)
    
    if user_id not in users:
        bot.send_message(message.chat.id, "❌ يجب البدء باستخدام /start أولاً.")
        return
    
    user = users[user_id]
    
    bot.send_message(
        message.chat.id,
        f"💰 <b>رصيدك الحالي:</b> {user.get('balance', 0)} ريال\n\n"
        f"📊 <b>إحصائياتك:</b>\n"
        f"• عدد الرحلات: {user.get('total_rides', 0)}\n",
        reply_markup=create_ride_keyboard("customer")
    )

@bot.message_handler(func=lambda msg: msg.text == '📞 الدعم' or msg.text == '📞 المساعدة')
def handle_support(message):
    """عرض معلومات الدعم"""
    support_msg = """📞 <b>مركز المساعدة والدعم</b>

<b>👤 للعملاء:</b>
• استخدم /start للبدء
• اختر '👤 عميل'
• اضغط '🚖 طلب رحلة جديدة'
• أرسل موقعك

<b>🚖 للسائقين:</b>
• اختر '🚖 سائق'
• اضغط '🟢 بدء العمل'
• أرسل موقعك

<b>📋 الأوامر:</b>
/start - بدء البوت
/help - هذه الرسالة

<b>📞 الدعم الفني:</b>
للشكاوى والاستفسارات، تواصل مع الدعم."""
    
    bot.send_message(
        message.chat.id,
        support_msg,
        reply_markup=create_ride_keyboard("customer")
    )

@bot.message_handler(func=lambda msg: msg.text == 'رجوع')
def handle_back(message):
    """العودة للقائمة الرئيسية"""
    user_id = str(message.from_user.id)
    
    if user_id not in users:
        bot.send_message(message.chat.id, "❌ يجب البدء باستخدام /start أولاً.")
        return
    
    role = users[user_id].get('role', 'customer')
    markup = create_ride_keyboard(role)
    
    bot.send_message(
        message.chat.id,
        "🔙 <b>تم العودة للقائمة الرئيسية</b>",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """معالجة استدعاء الأزرار"""
    user_id = str(call.from_user.id)
    callback_data = call.data
    
    logger.info(f"🔘 ضغط زر: {callback_data} من: {user_id}")
    
    if callback_data.startswith('accept_'):
        # قبول الرحلة
        ride_id = callback_data.split('_')[1]
        
        if ride_id in rides and rides[ride_id]['status'] == 'pending':
            # تحديث حالة الرحلة
            rides[ride_id]['status'] = 'accepted'
            rides[ride_id]['driver_id'] = user_id
            rides[ride_id]['driver_name'] = users.get(user_id, {}).get('first_name', 'سائق')
            rides[ride_id]['accepted_at'] = datetime.now().isoformat()
            
            # إعلام السائق
            bot.answer_callback_query(call.id, "✅ تم قبول الرحلة!")
            bot.edit_message_text(
                f"✅ <b>لقد قبلت الرحلة #{ride_id[8:]}</b>\n\n"
                f"• <b>العميل:</b> {rides[ride_id].get('customer_name', 'عميل')}\n"
                f"• <b>التكلفة:</b> {rides[ride_id].get('fare', 0)} ريال\n\n"
                f"🚗 توجه الآن إلى موقع العميل.",
                call.message.chat.id,
                call.message.message_id
            )
            
            # إعلام العميل
            customer_id = rides[ride_id].get('customer_id')
            if customer_id:
                try:
                    bot.send_message(
                        customer_id,
                        f"✅ <b>تم العثور على سائق!</b>\n\n"
                        f"🎉 تهانينا! سائقنا في طريقه إليك الآن.\n"
                        f"• <b>رقم الرحلة:</b> {ride_id[8:]}\n"
                        f"• <b>التكلفة:</b> {rides[ride_id].get('fare', 0)} ريال\n\n"
                        f"⏳ الرجاء الانتظار، السائق في الطريق..."
                    )
                except Exception as e:
                    logger.error(f"❌ فشل إعلام العميل: {e}")
    
    elif callback_data.startswith('reject_'):
        # رفض الرحلة
        ride_id = callback_data.split('_')[1]
        
        bot.answer_callback_query(call.id, "❌ تم رفض الرحلة")
        bot.edit_message_text(
            f"❌ <b>تم رفض الرحلة #{ride_id[8:]}</b>",
            call.message.chat.id,
            call.message.message_id
        )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """معالجة جميع الرسائل الأخرى"""
    logger.info(f"📩 رسالة عامة: {message.text} من {message.from_user.id}")
    
    bot.reply_to(
        message,
        "🤖 <b>مرحباً!</b>\n\n"
        "استخدم /start لرؤية القائمة الرئيسية.\n"
        "أو اختر من الأزرار في القائمة."
    )

# ============================================================================
# صفحات الويب
# ============================================================================

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    try:
        bot_info = bot.get_me()
        bot_status = f"@{bot_info.username}"
    except:
        bot_status = "❌ غير متصل"
    
    return f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>🚖 بوت النقل الذكي</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                min-height: 100vh;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 20px;
                text-align: center;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: rgba(255, 255, 255, 0.15);
                padding: 15px;
                border-radius: 10px;
            }}
            .stat-number {{
                font-size: 2em;
                font-weight: bold;
                margin: 10px 0;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 8px;
                margin: 10px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚖 بوت النقل الذكي</h1>
            <p>نظام متكامل لإدارة طلبات النقل</p>
            
            <div style="margin: 20px 0;">
                <p>🤖 <strong>حالة البوت:</strong> {bot_status}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div>👥 المستخدمين</div>
                    <div class="stat-number">{len(users)}</div>
                </div>
                <div class="stat-card">
                    <div>🚖 السائقين</div>
                    <div class="stat-number">{sum(1 for u in users.values() if u.get('role') == 'driver')}</div>
                </div>
                <div class="stat-card">
                    <div>📊 الرحلات</div>
                    <div class="stat-number">{len(rides)}</div>
                </div>
                <div class="stat-card">
                    <div>🟢 النشطين</div>
                    <div class="stat-number">{len(active_drivers)}</div>
                </div>
            </div>
            
            <div>
                <a href="/set_webhook" class="btn">⚙️ تعيين ويب هوك</a>
                <a href="/test_bot" class="btn">🧪 اختبار البوت</a>
                <a href="https://t.me/Dhdhdyduudbot" target="_blank" class="btn">💬 فتح البوت</a>
            </div>
            
            <div style="margin-top: 40px; opacity: 0.8;">
                <p>🔗 الرابط: https://dhhfhfjd.onrender.com</p>
                <p>© 2024 بوت النقل الذكي</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/set_webhook')
def set_webhook():
    """تعيين ويب هوك"""
    try:
        webhook_url = f"https://{request.host}/webhook"
        
        logger.info(f"🔄 محاولة تعيين ويب هوك على: {webhook_url}")
        
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        
        bot_info = bot.get_me()
        
        return f'''
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>✅ تم تعيين الويب هوك</title>
            <style>
                body {{
                    padding: 50px;
                    text-align: center;
                    font-family: Arial, sans-serif;
                }}
                .success {{
                    background: #d4edda;
                    color: #155724;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px auto;
                    max-width: 600px;
                }}
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ تم تعيين الويب هوك بنجاح!</h2>
                <p><strong>البوت:</strong> @{bot_info.username}</p>
                <p><strong>الرابط:</strong> {webhook_url}</p>
            </div>
            <div style="margin-top: 30px;">
                <a href="https://t.me/{bot_info.username}" target="_blank" style="padding: 10px 20px; background: #0088cc; color: white; text-decoration: none; border-radius: 5px;">
                    💬 افتح البوت الآن
                </a>
            </div>
            <div style="margin-top: 20px;">
                <a href="/">العودة للصفحة الرئيسية</a>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logger.error(f"❌ خطأ في تعيين الويب هوك: {e}")
        return f'''
        <div style="padding: 50px; text-align: center;">
            <h2 style="color: red;">❌ خطأ في تعيين الويب هوك</h2>
            <p>{str(e)}</p>
            <a href="/">العودة</a>
        </div>
        ''', 500

@app.route('/test_bot')
def test_bot():
    """صفحة اختبار البوت"""
    return '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>🧪 اختبار البوت</title>
        <style>
            body { padding: 30px; font-family: Arial; text-align: center; }
            .instructions { 
                background: #e9f7fe; 
                padding: 20px; 
                border-radius: 10px;
                text-align: right;
                margin: 20px auto;
                max-width: 500px;
            }
        </style>
    </head>
    <body>
        <h1>🧪 اختبار البوت</h1>
        
        <div class="instructions">
            <h3>📱 خطوات الاختبار:</h3>
            <ol>
                <li>افتح تطبيق Telegram على هاتفك</li>
                <li>ابحث عن: <strong>@Dhdhdyduudbot</strong></li>
                <li>أرسل: <code>/start</code></li>
                <li>اضغط على "👤 عميل" أو "🚖 سائق"</li>
                <li>جرب الأزرار المختلفة</li>
            </ol>
        </div>
        
        <div style="margin-top: 30px;">
            <a href="https://t.me/Dhdhdyduudbot" target="_blank" style="padding: 15px 30px; background: #0088cc; color: white; text-decoration: none; border-radius: 8px; font-size: 1.2em;">
                🚀 افتح البوت الآن
            </a>
        </div>
        
        <div style="margin-top: 30px;">
            <a href="/">العودة للصفحة الرئيسية</a>
        </div>
    </body>
    </html>
    '''

@app.route('/webhook', methods=['POST'])
def webhook():
    """نقطة استقبال تحديثات Telegram"""
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            
            logger.info(f"📩 استلام تحديث: {update.update_id}")
            
            bot.process_new_updates([update])
            
            logger.info(f"✅ تم معالجة تحديث: {update.update_id}")
            return 'OK', 200
            
        except Exception as e:
            logger.error(f"❌ خطأ في ويب هوك: {e}")
            return 'Error', 500
    
    return 'Bad Request', 400

@app.route('/health')
def health_check():
    """فحص صحة التطبيق"""
    try:
        bot_info = bot.get_me()
        return jsonify({
            'status': 'healthy',
            'bot': bot_info.username,
            'users_count': len(users),
            'rides_count': len(rides),
            'active_drivers': len(active_drivers),
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============================================================================
# التشغيل الرئيسي
# ============================================================================

# تحميل البيانات عند التشغيل
load_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 بدء التشغيل على منفذ {port}")
    app.run(host='0.0.0.0', port=port, debug=False)