import json
import os
from Utils.utils import *
from UserBot.bot import bot
from config import CLIENT_TOKEN
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from UserBot.templates import package_size_end_soon_template, package_days_expire_soon_template
try:
    bot.remove_webhook()
except:
    pass

settings = all_configs_settings()
ALERT_PACKAGE_GB = settings.get('reminder_notification_usage', 3)
ALERT_PACKAGE_DAYS = settings.get('reminder_notification_days', 3)


def alert_package_gb(package_remaining_gb):
    if package_remaining_gb <= ALERT_PACKAGE_GB:
        return True
    return False


def alert_package_days(package_remaining_days):
    if package_remaining_days <= ALERT_PACKAGE_DAYS:
        return True
    return False


# Send a reminder to users about their packages
WARNINGS_FILE = os.path.join(os.getcwd(), 'warnings_state.json')

def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        try:
            with open(WARNINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_warnings(data):
    with open(WARNINGS_FILE, 'w') as f:
        json.dump(data, f)

def cron_reminder():
    if not CLIENT_TOKEN:
        return
    if not settings['reminder_notification']:
        return
        
    warnings_state = load_warnings()
    state_changed = False

    telegram_users = USERS_DB.select_users()
    if telegram_users:
        for user in telegram_users:
            user_telegram_id = user['telegram_id']
            user_subscriptions_list = non_order_user_info(user_telegram_id) + order_user_info(user_telegram_id)
            if user_subscriptions_list:
                for user_subscription in user_subscriptions_list:
                    package_days = user_subscription.get('remaining_day', 0)
                    package_gb = user_subscription.get('usage', {}).get('remaining_usage_GB', 0)
                    
                    sub_name = user_subscription.get('name', 'کاربر')
                    uuid = user_subscription.get('uuid')
                    
                    if package_days == 0:
                        continue
                        
                    # مقداردهی اولیه وضعیت هشدار برای این کانفیگ در فایل حافظه
                    if uuid not in warnings_state:
                        warnings_state[uuid] = {"data_warned": False, "time_warned": False}
                        
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("🔄 تمدید این اشتراک", callback_data=f"renewal_subscription:{uuid}"))
                    
                    # ----------- بررسی و هشدار اتمام حجم -----------
                    if package_gb > ALERT_PACKAGE_GB:
                        # اگر کاربر تمدید کرده باشد و حجمش بیشتر از حد هشدار شود، حافظه را ریست می‌کنیم
                        if warnings_state[uuid]["data_warned"]:
                            warnings_state[uuid]["data_warned"] = False
                            state_changed = True
                    elif alert_package_gb(package_gb):
                        # فقط در صورتی پیام می‌دهیم که قبلا هشدار نداده باشیم
                        if not warnings_state[uuid]["data_warned"]:
                            msg_text = f"⚠️ <b>هشدار اتمام حجم!</b>\n\nکاربر گرامی، حجم سرویس شما با نام <b>{sub_name}</b> رو به پایان است.\n📊 حجم باقی‌مانده: {package_gb} گیگابایت\n\nجهت جلوگیری از قطعی، می‌توانید از طریق دکمه زیر اقدام به تمدید نمایید."
                            try:
                                bot.send_message(user_telegram_id, msg_text, reply_markup=markup, parse_mode="HTML")
                                warnings_state[uuid]["data_warned"] = True
                                state_changed = True
                            except:
                                pass
                                
                    # ----------- بررسی و هشدار اتمام زمان -----------
                    if package_days > ALERT_PACKAGE_DAYS:
                        # ریست کردن حافظه هشدار در صورت تمدید زمان
                        if warnings_state[uuid]["time_warned"]:
                            warnings_state[uuid]["time_warned"] = False
                            state_changed = True
                    elif alert_package_days(package_days):
                        # فقط در صورتی پیام می‌دهیم که قبلا هشدار نداده باشیم
                        if not warnings_state[uuid]["time_warned"]:
                            msg_text = f"⚠️ <b>هشدار اتمام زمان!</b>\n\nکاربر گرامی، زمان سرویس شما با نام <b>{sub_name}</b> رو به پایان است.\n⏳ زمان باقی‌مانده: {package_days} روز\n\nجهت جلوگیری از قطعی، می‌توانید از طریق دکمه زیر اقدام به تمدید نمایید."
                            try:
                                bot.send_message(user_telegram_id, msg_text, reply_markup=markup, parse_mode="HTML")
                                warnings_state[uuid]["time_warned"] = True
                                state_changed = True
                            except:
                                pass

    # ذخیره تغییرات جدید در فایل حافظه فقط در صورتی که تغییری رخ داده باشد
    if state_changed:
        save_warnings(warnings_state)