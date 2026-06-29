import datetime
import random
import os
import logging
import telebot
from telebot.types import Message, CallbackQuery
from urllib.parse import urlparse
import html

from config import CLIENT_TOKEN, PANEL_URL, SUB_URL, ADMINS_ID, API_PATH
from UserBot.markups import (
    main_menu_keyboard_markup, cancel_markup, user_info_markup, 
    user_info_non_sub_markup, user_subscriptions_list_markup, 
    plans_list_markup, confirm_buy_plan_markup, send_screenshot_markup,
    wallet_info_markup, wallet_info_specific_markup, servers_list_markup,
    force_join_channel_markup, users_bot_management_settings_panel_manual_markup,
    confirm_payment_by_admin
)
from UserBot.templates import (
    user_info_template, wallet_info_template, plan_info_template, 
    owner_info_template, payment_received_template, renewal_unvalable_template
)
from UserBot.content import MESSAGES, KEY_MARKUP, BOT_COMMANDS

import Utils.utils as utils
from Shared.common import admin_bot
from Database.dbManager import USERS_DB
from Utils import api

bot = telebot.TeleBot(CLIENT_TOKEN, parse_mode="HTML")
bot.remove_webhook()
admin_bot = admin_bot()
BASE_URL = f"{urlparse(PANEL_URL).scheme}://{urlparse(PANEL_URL).netloc}"
selected_server_id = 0

user_charge_state = {}
renew_subscription_dict = {}

def is_it_digit(message: Message, allow_float=False, response=MESSAGES.get('ERROR_INVALID_NUMBER', 'خطا'), markup=main_menu_keyboard_markup()):
    if not message.text:
        bot.send_message(message.chat.id, response, reply_markup=markup)
        return False
    try:
        float(message.text) if allow_float else int(message.text)
        return True
    except ValueError:
        bot.send_message(message.chat.id, response, reply_markup=markup)
        return False

def is_it_cancel(message: Message, response=MESSAGES.get('CANCELED', 'لغو شد')):
    if message.text == KEY_MARKUP.get('CANCEL', 'لغو'):
        bot.send_message(message.chat.id, response, reply_markup=main_menu_keyboard_markup())
        return True
    return False

def is_it_command(message: Message):
    return bool(message.text and message.text.startswith("/"))

def is_user_banned(user_id):
    user = USERS_DB.find_user(telegram_id=user_id)
    if user and user[0]['banned']:
        bot.send_message(user_id, MESSAGES.get('BANNED_USER', 'شما مسدود شده‌اید.'), reply_markup=main_menu_keyboard_markup())
        return True
    return False

def user_channel_status(user_id):
    try:
        settings = utils.all_configs_settings()
        if settings['channel_id']:
            user = bot.get_chat_member(settings['channel_id'], user_id)
            return user.status in ['member', 'administrator', 'creator']
        return True
    except:
        return False

def is_user_in_channel(user_id):
    settings = utils.all_configs_settings()
    if settings.get('force_join_channel') == 1 and settings.get('channel_id'):
        if not user_channel_status(user_id):
            bot.send_message(user_id, MESSAGES.get('REQUEST_JOIN_CHANNEL', 'لطفا در کانال عضو شوید.'), reply_markup=force_join_channel_markup(settings['channel_id']))
            return False
    return True

# ----------------- User Sub Search -----------------
def next_step_user_sub_search_name(message: Message):
    if is_it_cancel(message): return
    search_term = message.text.lower()
    all_subs = (utils.non_order_user_info(message.chat.id) or []) + (utils.order_user_info(message.chat.id) or [])
    results = [sub for sub in all_subs if sub.get('name') and search_term in sub['name'].lower()]
    if not results:
        return bot.send_message(message.chat.id, MESSAGES.get('SUBSCRIPTION_INFO_NOT_FOUND', 'یافت نشد.'), reply_markup=main_menu_keyboard_markup())
    bot.send_message(message.chat.id, "نتیجه جستجو:", reply_markup=user_subscriptions_list_markup(results))

def next_step_user_sub_search_uuid(message: Message):
    if is_it_cancel(message): return
    search_term = message.text.strip()
    all_subs = (utils.non_order_user_info(message.chat.id) or []) + (utils.order_user_info(message.chat.id) or [])
    results = [sub for sub in all_subs if search_term == sub.get('uuid')]
    if not results:
        return bot.send_message(message.chat.id, MESSAGES.get('SUBSCRIPTION_INFO_NOT_FOUND', 'یافت نشد.'), reply_markup=main_menu_keyboard_markup())
    bot.send_message(message.chat.id, "نتیجه جستجو:", reply_markup=user_subscriptions_list_markup(results))

# ----------------- Advanced Charging & Discounts -----------------
def next_step_increase_wallet_balance(message, with_discount=False):
    if is_it_cancel(message): return
    if not is_it_digit(message, markup=cancel_markup()):
        msg = bot.send_message(message.chat.id, "⚠️ لطفاً فقط عدد وارد کنید:")
        bot.register_next_step_handler(msg, next_step_increase_wallet_balance, with_discount)
        return
        
    amount = utils.toman_to_rial(message.text)
    min_deposit = utils.all_configs_settings()['min_deposit_amount']
    if amount < min_deposit:
        msg = bot.send_message(message.chat.id, f"{MESSAGES.get('INCREASE_WALLET_BALANCE_AMOUNT', 'مبلغ:')}\n{MESSAGES.get('MINIMUM_DEPOSIT_AMOUNT', 'حداقل:')}: {utils.rial_to_toman(min_deposit)} {MESSAGES.get('TOMAN', 'تومان')}", reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_increase_wallet_balance, with_discount)
        return

    user_charge_state[message.chat.id] = {'amount': amount, 'plan_id': None, 'id': random.randint(1000000, 9999999)}
    
    if with_discount:
        msg = bot.send_message(message.chat.id, "🎁 لطفا کد تخفیف خود را ارسال کنید.\nدر غیر این صورت روی دکمه /skip کلیک کنید.", reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_apply_discount)
    else:
        # پرش مستقیم به ارسال رسید (بدون کد تخفیف)
        state = user_charge_state[message.chat.id]
        state['discount_code'] = "-"
        state['pay_amount'] = state['amount']
        settings = utils.all_configs_settings()
        bot.send_message(message.chat.id, owner_info_template(settings['card_number'], settings['card_holder'], state['pay_amount']), reply_markup=send_screenshot_markup(state['id']))

def increase_wallet_balance_specific(message, plan_id, amount, with_discount=False):
    if not USERS_DB.find_wallet(telegram_id=message.chat.id):
        USERS_DB.add_wallet(telegram_id=message.chat.id)
        
    # ذخیره مخفیانه UUID در صورت منفی بودن آیدی پلن (به معنی تمدید)
    uuid = renew_subscription_dict.get(message.chat.id) if int(plan_id) < 0 else None
    
    user_charge_state[message.chat.id] = {'amount': amount, 'plan_id': plan_id, 'uuid': uuid, 'id': random.randint(1000000, 9999999)}
    
    if with_discount:
        msg = bot.send_message(message.chat.id, "🎁 لطفا کد تخفیف خود را ارسال کنید، در غیر این صورت /skip را بزنید.", reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_apply_discount)
    else:
        state = user_charge_state[message.chat.id]
        state['discount_code'] = "-"
        state['pay_amount'] = state['amount']
        settings = utils.all_configs_settings()
        bot.send_message(message.chat.id, owner_info_template(settings['card_number'], settings['card_holder'], state['pay_amount']), reply_markup=send_screenshot_markup(state['id']))

def next_step_apply_discount(message: Message):
    if is_it_cancel(message): return
    state = user_charge_state.get(message.chat.id)
    if not state: return
    
    text = message.text.strip()
    state['discount_code'] = "-"
    state['pay_amount'] = state['amount']
    
    if text.lower() not in ['/skip', 'skip']:
        discount = USERS_DB.use_discount_code(text)
        if discount:
            discount_amount = int(state['amount'] * (discount / 100))
            state['pay_amount'] = state['amount'] - discount_amount
            state['discount_code'] = text
            bot.send_message(message.chat.id, 
                f"🎁 کد تخفیف <b>{text}</b> اعمال شد!\n"
                f"💰 شارژ درخواستی: {utils.rial_to_toman(state['amount'])} {MESSAGES.get('TOMAN', 'تومان')}\n"
                f"🔥 مبلغ قابل پرداخت: <b>{utils.rial_to_toman(state['pay_amount'])}</b> {MESSAGES.get('TOMAN', 'تومان')}\n"
                f"✨ حساب شما به اندازه کل مبلغ {utils.rial_to_toman(state['amount'])} شارژ خواهد شد."
            )
        else:
            bot.send_message(message.chat.id, "❌ کد نامعتبر یا منقضی است. فرآیند بدون تخفیف ادامه می‌یابد.")
            
    settings = utils.all_configs_settings()
    bot.send_message(message.chat.id, owner_info_template(settings['card_number'], settings['card_holder'], state['pay_amount']), reply_markup=send_screenshot_markup(state['id']))

def next_step_send_screenshot(message, payment_id):
    if is_it_cancel(message): return
    state = user_charge_state.get(message.chat.id)
    if not state: 
        return bot.send_message(message.chat.id, MESSAGES.get('UNKNOWN_ERROR', 'خطا در یافتن سشن.'), reply_markup=main_menu_keyboard_markup())

    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, MESSAGES.get('ERROR_TYPE_SEND_SCREENSHOT', 'فقط عکس بفرستید.'), reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_send_screenshot, payment_id)
        return

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = f"{message.chat.id}-{state['id']}.jpg"
        
        receiptions_path = os.path.join(os.getcwd(), 'UserBot', 'Receiptions')
        if not os.path.exists(receiptions_path): os.makedirs(receiptions_path)
        
        file_path = os.path.join(receiptions_path, file_name)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        plan_part = f"Plan:{state['plan_id']}" if state.get('plan_id') else f"Wallet:{state['amount']}"
        uuid_part = f"|UUID:{state['uuid']}" if state.get('uuid') else ""
        payment_method = f"{plan_part}{uuid_part}|Code:{state.get('discount_code', '-')}|Pay:{state['pay_amount']}|Charge:{state['amount']}"
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if USERS_DB.add_payment(state['id'], message.chat.id, state['pay_amount'], payment_method, file_name, created_at):
            user_data = USERS_DB.find_user(telegram_id=message.chat.id)[0]
            
            # فیلتر کردن اسم کاربر برای جلوگیری از خطای تلگرام
            safe_name = html.escape(user_data['full_name']) if user_data['full_name'] else str(user_data['telegram_id'])
            
            username_text = f"@{user_data['username']}" if user_data.get('username') else "تنظیم نشده ❌"
            admin_caption = f"📥 <b>درخواست تراکنش جدید</b>\n👤 نام کاربر: {safe_name}\n🆔 آیدی عددی: <code>{user_data['telegram_id']}</code>\n💬 یوزرنیم: {username_text}\n---------------------\n🎟 کد تخفیف: <b>{state.get('discount_code', '-')}</b>\n💵 پرداختی: <code>{utils.rial_to_toman(state['pay_amount'])}</code> {MESSAGES.get('TOMAN', 'تومان')}\n💰 شارژ دیتابیس: <b>{utils.rial_to_toman(state['amount'])}</b> {MESSAGES.get('TOMAN', 'تومان')}"
            
            # ارسال ایمن رسید برای ادمین‌ها با هندلینگ خطا
            
            for ADMIN in ADMINS_ID:
                try: 
                    with open(file_path, 'rb') as photo_file:
                        admin_bot.send_photo(ADMIN, photo_file, caption=admin_caption, reply_markup=confirm_payment_by_admin(state['id']))
                except Exception as admin_err: 
                    logging.error(f"Error sending receipt to ADMIN {ADMIN}: {admin_err}")
                    
            bot.send_message(message.chat.id, "✅ رسید شما با موفقیت ثبت شد و در انتظار تایید ادمین است.", reply_markup=main_menu_keyboard_markup())
            
            # پاک کردن حافظه موقت پس از اتمام
            if message.chat.id in user_charge_state:
                del user_charge_state[message.chat.id]
        else: 
            bot.send_message(message.chat.id, MESSAGES.get('UNKNOWN_ERROR', 'خطا در ثبت دیتابیس.'), reply_markup=main_menu_keyboard_markup())
    except Exception as e:
        logging.error(f"Screenshot Error: {e}")
        bot.send_message(message.chat.id, MESSAGES.get('UNKNOWN_ERROR', 'خطای سیستمی رخ داد.'), reply_markup=main_menu_keyboard_markup())

# ----------------- Subscriptions Area -----------------
def renewal_from_wallet_confirm(message: Message, plan, uuid):
    if not plan: return bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
    wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    if not wallet: USERS_DB.add_wallet(telegram_id=message.chat.id); wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    
    if plan['price'] > wallet[0]['balance']:
        shortage = plan['price'] - wallet[0]['balance']
        error_msg = f"❌ موجودی کیف پول شما برای تمدید این پلن کافی نیست.\n\n💳 مبلغ کسری جهت تمدید: <b>{utils.rial_to_toman(shortage)}</b> {MESSAGES.get('TOMAN', 'تومان')}\n\nجهت پرداخت کسری، روی یکی از دکمه‌های زیر کلیک کنید."
        bot.send_message(message.chat.id, error_msg, reply_markup=wallet_info_specific_markup(plan['id'], shortage, is_renewal=True))
    else:
        bot.delete_message(message.chat.id, message.message_id)
        msg_wait = bot.send_message(message.chat.id, MESSAGES['WAIT'])
        
        sub = utils.find_order_subscription_by_uuid(uuid)
        if not sub:
            bot.delete_message(message.chat.id, msg_wait.message_id)
            return bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
            
        server = USERS_DB.find_server(id=sub['server_id'])[0]
        URL = server['url'] + API_PATH
        
        # --- سیستم محاسبه و انتقال حجم باقیمانده ---
        panel_user = api.find(URL, uuid)
        if not panel_user:
            bot.delete_message(message.chat.id, msg_wait.message_id)
            return bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
            
        # محاسبه حجم باقیمانده (جلوگیری از منفی شدن با max)
        remaining_gb = max(0, panel_user.get('usage_limit_GB', 0) - panel_user.get('current_usage_GB', 0))
        new_total_gb = plan['size_gb'] + remaining_gb
        # ------------------------------------------
        
        last_reset_time = datetime.datetime.now().strftime("%Y-%m-%d")
        # استفاده از new_total_gb به جای حجم خامِ پلن
        status = api.update(URL, uuid=uuid, package_days=plan['days'], usage_limit_GB=new_total_gb, current_usage_GB=0, start_date=last_reset_time)
        
        if not status:
            bot.delete_message(message.chat.id, msg_wait.message_id)
            return bot.send_message(message.chat.id, MESSAGES.get('UNKNOWN_ERROR', 'خطا در ارتباط با سرور'), reply_markup=main_menu_keyboard_markup())
            
        USERS_DB.edit_wallet(message.chat.id, balance=wallet[0]['balance'] - plan['price'])
        order_id = random.randint(1000000, 9999999)
        name_for_db = api.find(URL, uuid).get('name', 'تمدیدی')
        USERS_DB.add_order(order_id, message.chat.id, f"تمدید: {name_for_db}", plan['id'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        bot.delete_message(message.chat.id, msg_wait.message_id)
        bot.send_message(message.chat.id, f"✅ تمدید سرویس با موفقیت انجام شد!\nحجم و زمان شما ریست و طبق پلن جدید تنظیم گردید.\n{MESSAGES.get('ORDER_ID', 'شناسه')} {order_id}", reply_markup=main_menu_keyboard_markup())
        
        user_info = utils.dict_process(URL, utils.users_to_dict([api.find(URL, uuid)]))[0]
        mrkup = user_info_non_sub_markup(uuid) if sub.get('telegram_id') else user_info_markup(uuid)
        bot.send_message(message.chat.id, user_info_template(sub['id'], server, user_info, MESSAGES.get('INFO_USER', '')), reply_markup=mrkup)

def buy_from_wallet_confirm(message: Message, plan):
    if not plan: return bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
    wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    if not wallet: USERS_DB.add_wallet(telegram_id=message.chat.id); wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    
    if plan['price'] > wallet[0]['balance']:
        shortage = plan['price'] - wallet[0]['balance']
        error_msg = f"❌ موجودی کیف پول شما برای خرید پلن انتخابی کافی نیست.\n\n💳 مبلغ کسری جهت خرید این پلن: <b>{utils.rial_to_toman(shortage)}</b> {MESSAGES.get('TOMAN', 'تومان')}\n\nجهت پرداخت کسری و صدور خودکار، روی دکمه شارژ دقیق کلیک کنید."
        bot.send_message(message.chat.id, error_msg, reply_markup=wallet_info_specific_markup(plan['id'], shortage))
    else:
        bot.delete_message(message.chat.id, message.message_id)
        msg = bot.send_message(message.chat.id, MESSAGES['REQUEST_SEND_NAME'], reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_send_name_for_buy_from_wallet, plan)
def next_step_send_name_for_buy_from_wallet(message: Message, plan):
    if is_it_cancel(message): return
    if is_it_command(message):
        msg = bot.send_message(message.chat.id, MESSAGES['REQUEST_SEND_NAME'])
        return bot.register_next_step_handler(msg, next_step_send_name_for_buy_from_wallet, plan)
        
    name = message.text
    order_id = random.randint(1000000, 9999999)
    server = USERS_DB.find_server(id=plan['server_id'])[0]
    URL = server['url'] + API_PATH
    sub_id = random.randint(1000000, 9999999)
    
    value = api.insert(URL, name=name, usage_limit_GB=plan['size_gb'], package_days=plan['days'], comment=f"HidyBot:{sub_id}")
    if not value: return bot.send_message(message.chat.id, MESSAGES.get('UNKNOWN_ERROR', 'خطا'), reply_markup=main_menu_keyboard_markup())
        
    USERS_DB.add_order_subscription(sub_id, order_id, value, server['id'])
    USERS_DB.add_order(order_id, message.chat.id, name, plan['id'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
    wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)[0]
    USERS_DB.edit_wallet(message.chat.id, balance=wallet['balance'] - plan['price'])
            
    bot.send_message(message.chat.id, f"{MESSAGES.get('PAYMENT_CONFIRMED', 'تایید شد')}\n{MESSAGES.get('ORDER_ID', 'شناسه')} {order_id}", reply_markup=main_menu_keyboard_markup())
    
    user_info = utils.dict_process(URL, utils.users_to_dict([api.find(URL, value)]))[0]
    # بررسی لینک اختصاصی سرور
    dynamic_sub_url = server.get('sub_url') if server.get('sub_url') else SUB_URL
    base_sub = dynamic_sub_url if dynamic_sub_url.endswith("/") else f"{dynamic_sub_url}/"
    sub_link = f"{base_sub}{value}/#{name.replace(' ', '_')}"
    qr_code = utils.txt_to_qr(sub_link)
    
    caption_text = f"{user_info_template(sub_id, server, user_info, MESSAGES.get('INFO_USER', ''))}\n\n🔗 لینک:\n<code>{sub_link}</code>"
    if qr_code: bot.send_photo(message.chat.id, photo=qr_code, caption=caption_text, reply_markup=user_info_markup(user_info['uuid']))
    else: bot.send_message(message.chat.id, caption_text, reply_markup=user_info_markup(user_info['uuid']))

def next_step_send_name_for_get_free_test(message: Message, server_id):
    if is_it_cancel(message): return
    if is_it_command(message):
        msg = bot.send_message(message.chat.id, MESSAGES['REQUEST_SEND_NAME'])
        return bot.register_next_step_handler(msg, next_step_send_name_for_get_free_test, server_id)

    settings = utils.all_configs_settings()
    server = USERS_DB.find_server(id=server_id)[0]
    URL = server['url'] + API_PATH
    uuid = api.insert(URL, name=message.text, usage_limit_GB=settings['test_sub_size_gb'], package_days=settings['test_sub_days'], comment="HidyBot:FreeTest")
    if not uuid:
        return bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
        
    non_order_id = random.randint(10000000, 99999999)
    USERS_DB.add_non_order_subscription(non_order_id, message.chat.id, uuid, server_id)
    USERS_DB.edit_user(message.chat.id, test_subscription=True)
    bot.send_message(message.chat.id, MESSAGES['GET_FREE_CONFIRMED'], reply_markup=main_menu_keyboard_markup())
    
    user_info = utils.dict_process(URL, utils.users_to_dict([api.find(URL, uuid)]))[0]
    # بررسی لینک اختصاصی سرور
    dynamic_sub_url = server.get('sub_url') if server.get('sub_url') else SUB_URL
    base_sub = dynamic_sub_url if dynamic_sub_url.endswith("/") else f"{dynamic_sub_url}/"
    sub_link = f"{base_sub}{uuid}/#{message.text.replace(' ', '_')}"
    qr_code = utils.txt_to_qr(sub_link)
    caption_text = f"{user_info_template(non_order_id, server, user_info, MESSAGES['INFO_USER'])}\n\n🔗 لینک:\n<code>{sub_link}</code>"
    
    if qr_code: bot.send_photo(message.chat.id, photo=qr_code, caption=caption_text, reply_markup=user_info_markup(user_info['uuid']))
    else: bot.send_message(message.chat.id, caption_text, reply_markup=user_info_markup(user_info['uuid']))

def next_step_to_qr(message: Message):
    if is_it_cancel(message): return
    is_it_valid = utils.is_it_config_or_sub(message.text)
    if is_it_valid:
        qr_code = utils.txt_to_qr(message.text)
        if qr_code: bot.send_photo(message.chat.id, qr_code, reply_markup=main_menu_keyboard_markup())
    else:
        bot.send_message(message.chat.id, MESSAGES['REQUEST_SEND_TO_QR_ERROR'], reply_markup=main_menu_keyboard_markup())

def update_info_subscription(message: Message, uuid, markup=None):
    sub = utils.find_order_subscription_by_uuid(uuid)
    if not sub: return bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
    server = USERS_DB.find_server(id=sub['server_id'])[0]
    
    user_api = api.find(server['url'] + API_PATH, uuid=sub['uuid'])
    if not user_api:
        return bot.send_message(message.chat.id, "❌ این سرویس در پنل سرور یافت نشد (احتمالا حذف شده است).", reply_markup=main_menu_keyboard_markup())
        
    user = utils.dict_process(server['url'] + API_PATH, utils.users_to_dict([user_api]))[0]
    
    # ترکیب شرط‌ها: اشتراک فقط در صورتی "فعال" است که هم Enable باشد، هم زمان داشته باشد و هم حجم
    is_active = user.get('enable', True) and user.get('remaining_day', 1) > 0 and user['usage'].get('remaining_usage_GB', 1) > 0
    
    mrkup = markup or (user_info_non_sub_markup(sub['uuid'], is_active) if sub.get('telegram_id') else user_info_markup(sub['uuid'], is_active))
    
    try: bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=user_info_template(sub['id'], server, user, MESSAGES['INFO_USER']), reply_markup=mrkup)
    except: pass

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: CallbackQuery):
    bot.clear_step_handler(call.message)
    if is_user_banned(call.message.chat.id): return
    data = call.data.split(':')
    key, value = data[0], data[1] if len(data) > 1 else None
    global selected_server_id

    if key == "user_sub_page":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=user_subscriptions_list_markup((utils.non_order_user_info(call.message.chat.id) or []) + (utils.order_user_info(call.message.chat.id) or []), int(value)))
    elif key == "user_sub_info":
        sub = utils.find_order_subscription_by_uuid(value)
        if not sub: return bot.answer_callback_query(call.id, MESSAGES['UNKNOWN_ERROR'])
        server = USERS_DB.find_server(id=sub['server_id'])[0]
        
        user_api = api.find(server['url'] + API_PATH, uuid=value)
        if not user_api:
            return bot.answer_callback_query(call.id, "❌ سرویس در پنل یافت نشد.", show_alert=True)
            
        user = utils.dict_process(server['url'] + API_PATH, utils.users_to_dict([user_api]))[0]
        
        # ترکیب شرط‌ها: اشتراک فقط در صورتی "فعال" است که هم Enable باشد، هم زمان داشته باشد و هم حجم
        is_active = user.get('enable', True) and user.get('remaining_day', 1) > 0 and user['usage'].get('remaining_usage_GB', 1) > 0
        
        mrkup = user_info_non_sub_markup(value, is_active) if sub.get('telegram_id') else user_info_markup(value, is_active)
        bot.edit_message_text(user_info_template(sub['id'], server, user, MESSAGES['INFO_USER']), call.message.chat.id, call.message.message_id, reply_markup=mrkup)
    elif key == "toggle_sub":
        action, uuid = data[1], data[2]
        sub = utils.find_order_subscription_by_uuid(uuid)
        if not sub: return bot.answer_callback_query(call.id, MESSAGES['UNKNOWN_ERROR'])
        
        server = USERS_DB.find_server(id=sub['server_id'])[0]
        URL = server['url'] + API_PATH
        
        # استفاده از تابع update برای تغییر وضعیت در پنل
        new_enable_status = True if action == "enable" else False
        status = api.update(URL, uuid=uuid, enable=new_enable_status)
        
        if status:
            bot.answer_callback_query(call.id, f"✅ اشتراک با موفقیت { 'فعال' if action == 'enable' else 'غیرفعال' } شد.", show_alert=True)
            # رفرش کردن صفحه اطلاعات
            update_info_subscription(call.message, uuid)
        else:
            bot.answer_callback_query(call.id, "❌ خطا در تغییر وضعیت در پنل.", show_alert=True)
    elif key == "delete_expired_sub":
        sub = utils.find_order_subscription_by_uuid(value)
        if not sub: return bot.answer_callback_query(call.id, MESSAGES['UNKNOWN_ERROR'])
        
        server = USERS_DB.find_server(id=sub['server_id'])[0]
        URL = server['url'] + API_PATH
        
        user_api = api.find(URL, uuid=value)
        if not user_api:
            USERS_DB.delete_order_subscription(uuid=value)
            USERS_DB.delete_non_order_subscription(uuid=value)
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            return bot.answer_callback_query(call.id, "✅ سرویس از سرور حذف شده بود و از ربات هم پاک شد.", show_alert=True)
            
        # منطق جدید: اگر اشتراک enable نیست، اجازه حذف بده
        if user_api.get('enable', True):
            return bot.answer_callback_query(call.id, "❌ این سرویس فعال است. ابتدا آن را غیرفعال کنید.", show_alert=True)
            
        status = api.delete(URL, uuid=value)
            
        USERS_DB.delete_order_subscription(uuid=value)
        USERS_DB.delete_non_order_subscription(uuid=value)
        
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        
        confirm_msg = bot.send_message(call.message.chat.id, "✅ اشتراک غیرفعال با موفقیت حذف شد.")
        import time
        time.sleep(3)
        try: bot.delete_message(call.message.chat.id, confirm_msg.message_id)
        except: pass
        
        all_subs = (utils.non_order_user_info(call.message.chat.id) or []) + (utils.order_user_info(call.message.chat.id) or [])
        if not all_subs: bot.send_message(call.message.chat.id, MESSAGES.get('SUBSCRIPTION_NOT_FOUND', 'اشتراکی یافت نشد.'), reply_markup=main_menu_keyboard_markup())
        else: bot.send_message(call.message.chat.id, "📋 لیست اشتراک‌های شما:", reply_markup=user_subscriptions_list_markup(all_subs))
    elif key == "user_sub_inactive":
        all_subs = (utils.non_order_user_info(call.message.chat.id) or []) + (utils.order_user_info(call.message.chat.id) or [])
        
        # فیلتر جامع: پیدا کردن اشتراک‌هایی که یا دستی غیرفعال شده‌اند، یا زمانشان تمام شده، یا حجمشان صفر است
        inactive_subs = []
        for sub in all_subs:
            is_manual_disabled = not sub.get('enable', True)
            is_time_expired = sub.get('remaining_day', 1) == 0
            is_data_expired = sub.get('usage', {}).get('remaining_usage_GB', 1) <= 0
            
            if is_manual_disabled or is_time_expired or is_data_expired:
                inactive_subs.append(sub)
        
        if not inactive_subs:
            return bot.answer_callback_query(call.id, "✅ اشتراک منقضی یا غیرفعالی ندارید.", show_alert=True)
            
        bot.edit_message_text("📋 لیست اشتراک‌های منقضی یا غیرفعال:", call.message.chat.id, call.message.message_id, reply_markup=user_subscriptions_list_markup(inactive_subs, int(value)))
    elif key == "user_sub_search_name":
        msg = bot.send_message(call.message.chat.id, MESSAGES['REQUEST_SEND_NAME'], reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_user_sub_search_name)
    elif key == "user_sub_search_uuid":
        msg = bot.send_message(call.message.chat.id, "لطفاً UUID اشتراک خود را بفرستید:", reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_user_sub_search_uuid)
    elif key == 'server_selected':
        if value == 'False': return bot.send_message(call.message.chat.id, MESSAGES['SERVER_IS_FULL'], reply_markup=main_menu_keyboard_markup())
        selected_server_id = int(value)
        bot.edit_message_text(MESSAGES['PLANS_LIST'], call.message.chat.id, call.message.message_id, reply_markup=plans_list_markup(USERS_DB.find_plan(server_id=int(value))))
    elif key == 'free_test_server_selected':
        if value == 'False': return bot.send_message(call.message.chat.id, MESSAGES['SERVER_IS_FULL'], reply_markup=main_menu_keyboard_markup())
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, MESSAGES['REQUEST_SEND_NAME'], reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_send_name_for_get_free_test, value)
    elif key == 'renewal_subscription':
        sub = utils.find_order_subscription_by_uuid(value)
        if not sub:
            return bot.answer_callback_query(call.id, MESSAGES.get('UNKNOWN_ERROR', 'خطا'))
        
        # ذخیره موقت UUID برای مرحله بعدی
        renew_subscription_dict[call.message.chat.id] = value 
        
        plans = USERS_DB.find_plan(server_id=sub['server_id'])
        
        warning_msg = (
            "♻️ <b>تمدید اشتراک</b>\n\n"
            "کاربر گرامی، با تمدید سرویس، <b>حجم باقیمانده شما نسوخته و مستقیماً به حجم پلن جدید اضافه خواهد شد!</b> 🎁\n\n"
            "⚠️ توجه داشته باشید که زمان سرویس شما از همین لحظه ریست شده و بر اساس مدت زمان پلن جدید محاسبه می‌شود.\n\n"
            "👇 در صورتی که مایل به ادامه هستید، لطفاً پلن مورد نظر خود را انتخاب کنید:"
        )
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=warning_msg, 
                              reply_markup=plans_list_markup(plans, renewal=True, uuid=value))
    elif key == 'renewal_plan_selected':
        plan = USERS_DB.find_plan(id=value)[0]
        wallet = USERS_DB.find_wallet(telegram_id=call.message.chat.id)
        uuid = renew_subscription_dict.get(call.message.chat.id)
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=plan_info_template(plan, wallet_balance=wallet[0]['balance'] if wallet else 0), 
                              reply_markup=confirm_buy_plan_markup(plan['id'], renewal=True, uuid=uuid))
    elif key == 'plan_selected':
        plan = USERS_DB.find_plan(id=value)[0]
        wallet = USERS_DB.find_wallet(telegram_id=call.message.chat.id)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=plan_info_template(plan, wallet_balance=wallet[0]['balance'] if wallet else 0), reply_markup=confirm_buy_plan_markup(plan['id']))
    elif key == 'confirm_buy_from_wallet':
        buy_from_wallet_confirm(call.message, USERS_DB.find_plan(id=value)[0])
    elif key == 'send_screenshot':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, MESSAGES.get('REQUEST_SEND_SCREENSHOT', 'رسید را بفرستید:'))
        bot.register_next_step_handler(msg, next_step_send_screenshot, value)
    elif key == 'unlink_subscription':
        if USERS_DB.delete_non_order_subscription(uuid=value): bot.delete_message(call.message.chat.id, call.message.message_id); bot.send_message(call.message.chat.id, MESSAGES['SUBSCRIPTION_UNLINKED'], reply_markup=main_menu_keyboard_markup())
    elif key == 'update_info_subscription':
        update_info_subscription(call.message, value)
    elif key == 'increase_wallet_balance':
        msg = bot.send_message(call.message.chat.id, MESSAGES['INCREASE_WALLET_BALANCE_AMOUNT'], reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_increase_wallet_balance, False)
    elif key == 'increase_wallet_balance_discount':
        msg = bot.send_message(call.message.chat.id, MESSAGES['INCREASE_WALLET_BALANCE_AMOUNT'], reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_increase_wallet_balance, True)
    elif key == 'increase_wallet_balance_specific':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        increase_wallet_balance_specific(call.message, data[1], int(data[2]), False)
    elif key == 'increase_wallet_balance_specific_discount':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        increase_wallet_balance_specific(call.message, data[1], int(data[2]), True)
    elif key == 'confirm_renewal_from_wallet':
        uuid = renew_subscription_dict.get(call.message.chat.id)
        if not uuid:
            return bot.answer_callback_query(call.id, "❌ خطای نشست. لطفا مجدداً از منوی وضعیت اشتراک اقدام کنید.", show_alert=True)
        plan = USERS_DB.find_plan(id=value)[0]
        renewal_from_wallet_confirm(call.message, plan, uuid)    
    elif key == 'direct_card_payment':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        plan_id_val = int(value)
        plan = USERS_DB.find_plan(id=abs(plan_id_val))[0]
        increase_wallet_balance_specific(call.message, plan_id_val, plan['price'], False)
    elif key == 'cancel_increase_wallet_balance':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, MESSAGES['CANCEL_INCREASE_WALLET_BALANCE'], reply_markup=main_menu_keyboard_markup())
    elif key == "conf_sub_url":
        sub_info = utils.find_order_subscription_by_uuid(value) or USERS_DB.find_non_order_subscription(uuid=value)
        if not sub_info: return bot.answer_callback_query(call.id, MESSAGES['UNKNOWN_ERROR'])
        sub_info = sub_info[0] if isinstance(sub_info, list) else sub_info
        server = USERS_DB.find_server(id=sub_info['server_id'])[0]
        
        # هندل کردن دریافت نام در صورت پاک شدن کانفیگ از پنل
        panel_user = api.find(server['url'] + API_PATH, uuid=value)
        user_name = panel_user.get('name', 'User') if panel_user else 'User'
        
        # بررسی لینک اختصاصی سرور
        dynamic_sub_url = server.get('sub_url') if server.get('sub_url') else SUB_URL
        base_sub = dynamic_sub_url if dynamic_sub_url.endswith("/") else f"{dynamic_sub_url}/"
        my_sub_link = f"{base_sub}{value}/#{user_name.replace(' ', '_')}"
        qr_code = utils.txt_to_qr(my_sub_link)
        if qr_code: bot.send_photo(call.message.chat.id, photo=qr_code, caption=f"🔗 لینک سابسکریپشن:\n<code>{my_sub_link}</code>", reply_markup=main_menu_keyboard_markup())
        else: bot.send_message(call.message.chat.id, f"🔗 لینک:\n<code>{my_sub_link}</code>", reply_markup=main_menu_keyboard_markup())
    elif key == "back_to_user_panel":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=user_info_markup(value))
    elif key == "back_to_plans":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=MESSAGES['PLANS_LIST'], reply_markup=plans_list_markup(USERS_DB.find_plan(server_id=selected_server_id)))
    elif key == "back_to_servers":
        server_list = [[s, True if s['user_limit'] > len(api.select(s['url'] + API_PATH) or []) else False] for s in USERS_DB.select_servers()]
        bot.edit_message_text(reply_markup=servers_list_markup(server_list), chat_id=call.message.chat.id, message_id=call.message.message_id, text=MESSAGES['SERVERS_LIST'])
    elif key == "del_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start_bot(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    if not USERS_DB.find_user(telegram_id=message.chat.id):
        USERS_DB.add_user(telegram_id=message.chat.id, username=message.from_user.username, full_name=message.from_user.full_name, created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        USERS_DB.add_wallet(telegram_id=message.chat.id)
    else:
        USERS_DB.edit_user(telegram_id=message.chat.id, full_name=message.from_user.full_name, username=message.from_user.username)
    bot.send_message(message.chat.id, utils.all_configs_settings().get('msg_user_start') or MESSAGES.get('WELCOME', 'خوش آمدید'), reply_markup=main_menu_keyboard_markup())

@bot.message_handler(func=lambda message: not USERS_DB.find_user(telegram_id=message.chat.id))
def not_in_users_table(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    bot.send_message(message.chat.id, MESSAGES.get('REQUEST_START', '/start'), reply_markup=main_menu_keyboard_markup())

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['SUBSCRIPTION_STATUS'])
def subscription_status(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    all_subs = (utils.non_order_user_info(message.chat.id) or []) + (utils.order_user_info(message.chat.id) or [])
    if not all_subs: return bot.send_message(message.chat.id, MESSAGES['SUBSCRIPTION_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
    bot.send_message(message.chat.id, "📋 لیست اشتراک‌های شما:\n\nبرای مدیریت، روی نام اشتراک کلیک کنید:", reply_markup=user_subscriptions_list_markup(all_subs))

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['BUY_SUBSCRIPTION'])
def buy_subscription(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    if not utils.all_configs_settings()['buy_subscription_status']: return bot.send_message(message.chat.id, MESSAGES['BUY_SUBSCRIPTION_CLOSED'], reply_markup=main_menu_keyboard_markup())
    if not USERS_DB.find_wallet(telegram_id=message.chat.id): USERS_DB.add_wallet(message.chat.id)
    servers = USERS_DB.select_servers()
    if not servers: return bot.send_message(message.chat.id, MESSAGES['SERVERS_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
    server_list = [[s, True if s['user_limit'] > len(api.select(s['url'] + API_PATH) or []) else False] for s in servers]
    bot.send_message(message.chat.id, MESSAGES['SERVERS_LIST'], reply_markup=servers_list_markup(server_list))

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['MANUAL'])
def help_guide(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    bot.send_message(message.chat.id, MESSAGES['MANUAL_HDR'], reply_markup=users_bot_management_settings_panel_manual_markup())
    
@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['FAQ'])
def faq(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    bot.send_message(message.chat.id, utils.all_configs_settings().get('msg_faq') or MESSAGES.get('UNKNOWN_ERROR'), reply_markup=main_menu_keyboard_markup())

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['SEND_TICKET'])
def send_ticket(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    support_username = utils.all_configs_settings().get('support_username', '-') or "-"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data="del_msg:None"))
    bot.send_message(message.chat.id, f"جهت ارسال پیام به پشتیبانی به آی دی تلگرام زیر پیام بدهید:\n{support_username}", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['WALLET'])
def wallet_balance(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    if not wallet: USERS_DB.add_wallet(telegram_id=message.chat.id); wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    bot.send_message(message.chat.id, wallet_info_template(wallet[0]['balance']), reply_markup=wallet_info_markup())

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['FREE_TEST'])
def free_test(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    if not utils.all_configs_settings()['test_subscription']: return bot.send_message(message.chat.id, MESSAGES['FREE_TEST_NOT_AVAILABLE'], reply_markup=main_menu_keyboard_markup())
    users = USERS_DB.find_user(telegram_id=message.chat.id)
    if users and users[0]['test_subscription']: return bot.send_message(message.chat.id, MESSAGES['ALREADY_RECEIVED_FREE'], reply_markup=main_menu_keyboard_markup())
    msg_wait = bot.send_message(message.chat.id, MESSAGES['WAIT'])
    servers = USERS_DB.select_servers()
    if not servers: return bot.send_message(message.chat.id, MESSAGES['SERVERS_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
    server_list = [[s, True if s['user_limit'] > len(api.select(s['url'] + API_PATH) or []) else False] for s in servers]
    bot.delete_message(message.chat.id, msg_wait.message_id)
    bot.send_message(message.chat.id, MESSAGES['SERVERS_LIST'], reply_markup=servers_list_markup(server_list, True))

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['CANCEL'])
def cancel(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    bot.send_message(message.chat.id, MESSAGES['CANCELED'], reply_markup=main_menu_keyboard_markup())

def start():
    try: bot.set_my_commands([telebot.types.BotCommand("/start", BOT_COMMANDS['START'])])
    except: pass
    bot.infinity_polling()