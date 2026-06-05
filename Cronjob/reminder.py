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
def cron_reminder():
    if not CLIENT_TOKEN:
        return
    if not settings['reminder_notification']:
        return

    telegram_users = USERS_DB.select_users()
    if telegram_users:
        for user in telegram_users:
            user_telegram_id = user['telegram_id']
            user_subscriptions_list = non_order_user_info(user_telegram_id) + order_user_info(user_telegram_id)
            if user_subscriptions_list:
                for user_subscription in user_subscriptions_list:
                    package_days = user_subscription.get('remaining_day', 0)
                    package_gb = user_subscription.get('usage', {}).get('remaining_usage_GB', 0)
                    sub_id = user_subscription.get('sub_id')
                    
                    # استخراج نام و UUID کانفیگ برای نمایش و تمدید
                    sub_name = user_subscription.get('name', 'کاربر')
                    uuid = user_subscription.get('uuid')
                    
                    if package_days == 0:
                        continue
                        
                    # ساخت دکمه شیشه‌ای تمدید مستقیم برای همین کانفیگ
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("🔄 تمدید این اشتراک", callback_data=f"renewal_subscription:{uuid}"))
                    
                    if alert_package_gb(package_gb):
                        msg_text = f"⚠️ <b>هشدار اتمام حجم!</b>\n\nکاربر گرامی، حجم سرویس شما با نام <b>{sub_name}</b> رو به پایان است.\n📊 حجم باقی‌مانده: {package_gb} گیگابایت\n\nجهت جلوگیری از قطعی، می‌توانید از طریق دکمه زیر اقدام به تمدید نمایید."
                        try:
                            bot.send_message(user_telegram_id, msg_text, reply_markup=markup, parse_mode="HTML")
                        except:
                            pass
                            
                    if alert_package_days(package_days):
                        msg_text = f"⚠️ <b>هشدار اتمام زمان!</b>\n\nکاربر گرامی، زمان سرویس شما با نام <b>{sub_name}</b> رو به پایان است.\n⏳ زمان باقی‌مانده: {package_days} روز\n\nجهت جلوگیری از قطعی، می‌توانید از طریق دکمه زیر اقدام به تمدید نمایید."
                        try:
                            bot.send_message(user_telegram_id, msg_text, reply_markup=markup, parse_mode="HTML")
                        except:
                            pass
