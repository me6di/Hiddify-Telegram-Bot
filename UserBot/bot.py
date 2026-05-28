import datetime
import random
import os
import logging

import telebot
from telebot.types import Message, CallbackQuery
from config import *
from AdminBot.templates import configs_template
from UserBot.markups import *
from UserBot.templates import *
from UserBot.content import *

import Utils.utils as utils
from Shared.common import admin_bot
from Database.dbManager import USERS_DB
from Utils import api

bot = telebot.TeleBot(CLIENT_TOKEN, parse_mode="HTML")
bot.remove_webhook()
admin_bot = admin_bot()
BASE_URL = f"{urlparse(PANEL_URL).scheme}://{urlparse(PANEL_URL).netloc}"
selected_server_id = 0

# ذخیره وضعیت شارژ و تخفیف برای هر کاربر به صورت مجزا
user_charge_state = {}

def is_it_digit(message: Message,allow_float=False, response=MESSAGES['ERROR_INVALID_NUMBER'], markup=main_menu_keyboard_markup()):
    if not message.text:
        bot.send_message(message.chat.id, response, reply_markup=markup)
        return False
    try:
        value = float(message.text) if allow_float else int(message.text)
        return True
    except ValueError:
        bot.send_message(message.chat.id, response, reply_markup=markup)
        return False

def is_it_cancel(message: Message, response=MESSAGES['CANCELED']):
    if message.text == KEY_MARKUP['CANCEL']:
        bot.send_message(message.chat.id, response, reply_markup=main_menu_keyboard_markup())
        return True
    return False

def is_it_command(message: Message):
    if message.text and message.text.startswith("/"): return True
    return False

def type_of_subscription(text):
    if text.startswith("vmess://"):
        config = text.replace("vmess://", "")
        config = utils.base64decoder(config)
        if not config: return False
        uuid = config['id']
    else:
        uuid = utils.extract_uuid_from_config(text)
    return uuid

def is_user_banned(user_id):
    user = USERS_DB.find_user(telegram_id=user_id)
    if user:
        if user[0]['banned']:
            bot.send_message(user_id, MESSAGES['BANNED_USER'], reply_markup=main_menu_keyboard_markup())
            return True
    return False

def user_channel_status(user_id):
    try:
        settings = utils.all_configs_settings()
        if settings['channel_id']:
            user = bot.get_chat_member(settings['channel_id'], user_id)
            return user.status in ['member', 'administrator', 'creator']
        else: return True
    except: return False

def is_user_in_channel(user_id):
    settings = all_configs_settings()
    if settings['force_join_channel'] == 1:
        if not settings['channel_id']: return True
        if not user_channel_status(user_id):
            bot.send_message(user_id, MESSAGES['REQUEST_JOIN_CHANNEL'], reply_markup=force_join_channel_markup(settings['channel_id']))
            return False
    return True

# ----------------- User Sub Search -----------------
def next_step_user_sub_search_name(message: Message):
    if is_it_cancel(message): return
    search_term = message.text.lower()
    non_order_subs = utils.non_order_user_info(message.chat.id) or []
    order_subs = utils.order_user_info(message.chat.id) or []
    all_subs = non_order_subs + order_subs
    results = [sub for sub in all_subs if sub.get('name') and search_term in sub['name'].lower()]
    if not results:
        bot.send_message(message.chat.id, MESSAGES['SUBSCRIPTION_INFO_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
        return
    bot.send_message(message.chat.id, "نتیجه جستجو:", reply_markup=user_subscriptions_list_markup(results))

def next_step_user_sub_search_uuid(message: Message):
    if is_it_cancel(message): return
    search_term = message.text.strip()
    non_order_subs = utils.non_order_user_info(message.chat.id) or []
    order_subs = utils.order_user_info(message.chat.id) or []
    all_subs = non_order_subs + order_subs
    results = [sub for sub in all_subs if search_term == sub.get('uuid')]
    if not results:
        bot.send_message(message.chat.id, MESSAGES['SUBSCRIPTION_INFO_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
        return
    bot.send_message(message.chat.id, "نتیجه جستجو:", reply_markup=user_subscriptions_list_markup(results))

# ----------------- Buy From Wallet Area -----------------
def buy_from_wallet_confirm(message: Message, plan):
    if not plan:
        bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
        return

    wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    if not wallet:
        bot.send_message(message.chat.id, MESSAGES['LACK_OF_WALLET_BALANCE'], reply_markup=wallet_info_markup())
    else:
        wallet = wallet[0]
        if plan['price'] > wallet['balance']:
            bot.send_message(message.chat.id, MESSAGES['LACK_OF_WALLET_BALANCE'], reply_markup=wallet_info_specific_markup(plan['id'], plan['price'] - wallet['balance']))
            return
        else:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message.chat.id, MESSAGES['REQUEST_SEND_NAME'], reply_markup=cancel_markup())
            bot.register_next_step_handler(message, next_step_send_name_for_buy_from_wallet, plan)

def next_step_send_name_for_buy_from_wallet(message: Message, plan):
    if is_it_cancel(message): return
    if not plan: return
    name = message.text
    while is_it_command(message):
        msg = bot.send_message(message.chat.id, MESSAGES['REQUEST_SEND_NAME'])
        bot.register_next_step_handler(msg, next_step_send_name_for_buy_from_wallet, plan)
        return
        
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    paid_amount = plan['price']
    order_id = random.randint(1000000, 9999999)
    server_id = plan['server_id']
    server = USERS_DB.find_server(id=server_id)[0]
    URL = server['url'] + API_PATH
    sub_id = random.randint(1000000, 9999999)
    value = api.insert(URL, name=name, usage_limit_GB=plan['size_gb'], package_days=plan['days'],comment=f"HidyBot:{sub_id}")
    
    if not value:
        bot.send_message(message.chat.id, f"{MESSAGES['UNKNOWN_ERROR']}:Create User Error", reply_markup=main_menu_keyboard_markup())
        return
        
    USERS_DB.add_order_subscription(sub_id, order_id, value, server_id)
    USERS_DB.add_order(order_id, message.chat.id,name, plan['id'], created_at)
        
    wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)[0]
    USERS_DB.edit_wallet(message.chat.id, balance=wallet['balance'] - paid_amount)
            
    bot.send_message(message.chat.id, f"{MESSAGES['PAYMENT_CONFIRMED']}\n{MESSAGES['ORDER_ID']} {order_id}", reply_markup=main_menu_keyboard_markup())
    
    user_info = api.find(URL, value)
    user_info = utils.users_to_dict([user_info])
    user_info = utils.dict_process(URL, user_info)[0]
    api_user_data = user_info_template(sub_id, server, user_info, MESSAGES['INFO_USER'])
    
    base_sub = SUB_URL if SUB_URL.endswith("/") else f"{SUB_URL}/"
    formatted_name = name.replace(' ', '_')
    sub_link = f"{base_sub}{value}/#{formatted_name}"
    qr_code = utils.txt_to_qr(sub_link)
    caption_text = f"{api_user_data}\n\n🔗 لینک سابسکریپشن:\n<code>{sub_link}</code>"
    
    if qr_code:
        bot.send_photo(message.chat.id, photo=qr_code, caption=caption_text, reply_markup=user_info_markup(user_info['uuid']))
    else:
        bot.send_message(message.chat.id, caption_text, reply_markup=user_info_markup(user_info['uuid']))

    bot_user = USERS_DB.find_user(telegram_id=message.chat.id)[0]
    for ADMIN in ADMINS_ID:
        admin_bot.send_message(ADMIN, f"""{MESSAGES['ADMIN_NOTIFY_NEW_SUB']} <a href='{server['url']}/admin'> {name} </a> {MESSAGES['ADMIN_NOTIFY_CONFIRM']}\n{MESSAGES['INFO_ID']} <code>{sub_id}</code>""", reply_markup=notify_to_admin_markup(bot_user))


# ----------------- Advanced Charging & Discounts -----------------
def next_step_increase_wallet_balance(message):
    if is_it_cancel(message): return
    if not is_it_digit(message, markup=cancel_markup()):
        bot.register_next_step_handler(message, next_step_increase_wallet_balance)
        return
        
    amount = utils.toman_to_rial(message.text)
    min_deposit = utils.all_configs_settings()['min_deposit_amount']
    if amount < min_deposit:
        msg = bot.send_message(message.chat.id, f"{MESSAGES['INCREASE_WALLET_BALANCE_AMOUNT']}\n{MESSAGES['MINIMUM_DEPOSIT_AMOUNT']}: {rial_to_toman(min_deposit)} تومان", reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_increase_wallet_balance)
        return

    user_charge_state[message.chat.id] = {'amount': amount, 'plan_id': None, 'id': random.randint(1000000, 9999999)}
    msg = bot.send_message(message.chat.id, "🎁 اگر کد تخفیف/نمایندگی دارید اکنون ارسال کنید.\nدر غیر این صورت روی دکمه /skip کلیک کنید.", reply_markup=cancel_markup())
    bot.register_next_step_handler(msg, next_step_apply_discount)

def increase_wallet_balance_specific(message, plan_id, amount):
    if not USERS_DB.find_wallet(telegram_id=message.chat.id):
        USERS_DB.add_wallet(telegram_id=message.chat.id)
        
    user_charge_state[message.chat.id] = {'amount': amount, 'plan_id': plan_id, 'id': random.randint(1000000, 9999999)}
    # برای خرید پلن مشخص مستقیماً میرویم مرحله پرداخت و کد تخفیف نمیگیریم (چون دقیق حساب شده)
    state = user_charge_state[message.chat.id]
    state['virtual_amount'] = amount
    settings = utils.all_configs_settings()
    bot.send_message(message.chat.id, owner_info_template(settings['card_number'], settings['card_holder'], amount), reply_markup=send_screenshot_markup(state['id']))

def next_step_apply_discount(message: Message):
    if is_it_cancel(message): return
    state = user_charge_state.get(message.chat.id)
    if not state: return
    
    text = message.text.strip()
    state['discount_code'] = "-" # مقدار پیش‌فرض
    state['pay_amount'] = state['amount'] # مبلغی که باید پرداخت کند (پیش‌فرض برابر مبلغ کل)
    
    if text.lower() != '/skip' and text.lower() != 'skip':
        discount = USERS_DB.use_discount_code(text)
        if discount:
            # محاسبه مبلغ پرداختی جدید (درصد تخفیف کسر می‌شود)
            discount_amount = int(state['amount'] * (discount / 100))
            state['pay_amount'] = state['amount'] - discount_amount
            state['discount_code'] = text
            
            bot.send_message(
                message.chat.id, 
                f"🎁 کد تخفیف <b>{text}</b> با موفقیت اعمال شد!\n"
                f"💰 مبلغ شارژ درخواستی: {utils.rial_to_toman(state['amount'])} تومان\n"
                f"🔥 مبلغی که باید پرداخت کنید: <b>{utils.rial_to_toman(state['pay_amount'])}</b> تومان\n"
                f"✨ حساب شما پس از تایید به اندازه کُل مبلغ یعنی <b>{utils.rial_to_toman(state['amount'])}</b> تومان شارژ خواهد شد."
            )
        else:
            bot.send_message(message.chat.id, "❌ کد تخفیف معتبر نیست یا منقضی شده. فرآیند بدون تخفیف ادامه می‌یابد.")
            
    settings = utils.all_configs_settings()
    bot.send_message(message.chat.id, owner_info_template(settings['card_number'], settings['card_holder'], state['pay_amount']), reply_markup=send_screenshot_markup(state['id']))

# ادیت متد ارسال اسکرین شات برای فرستادن اطلاعات کد تخفیف به ادمین
def next_step_send_screenshot(message, payment_id):
    if is_it_cancel(message): return
    state = user_charge_state.get(message.chat.id)
    if not state: return

    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, MESSAGES.get('ERROR_TYPE_SEND_SCREENSHOT', 'لطفاً فقط عکس ارسال کنید.'), reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_send_screenshot, payment_id)
        return

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = f"{message.chat.id}-{state['id']}.jpg"
        
        receiptions_path = os.path.join(os.getcwd(), 'UserBot', 'Receiptions')
        if not os.path.exists(receiptions_path): os.makedirs(receiptions_path)
        path_recp = os.path.join(receiptions_path, file_name)
        with open(path_recp, 'wb') as new_file: new_file.write(downloaded_file)

        # ذخیره اطلاعات در فیلد متد پرداخت به فرمت ساختاریافته برای خواندن ادمین
        # ساختار: Plan:ID|Wallet:مبلغ_شارژ|Code:نام_کد|Pay:مبلغ_پرداختی
        plan_part = f"Plan:{state['plan_id']}" if state.get('plan_id') else f"Wallet:{state['amount']}"
        payment_method = f"{plan_part}|Code:{state.get('discount_code', '-')}|Pay:{state['pay_amount']}"
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status = USERS_DB.add_payment(state['id'], message.chat.id, state['pay_amount'], payment_method, file_name, created_at)
        if status:
            payment = USERS_DB.find_payment(id=state['id'])[0]
            user_data = USERS_DB.find_user(telegram_id=message.chat.id)[0]
            
            # آماده‌سازی متون برای نمایش در ادمین
            admin_caption = f"""
📥 <b>درخواست تراکنش جدید</b>
👤 نام کاربر: {user_data['full_name']}
🆔 آیدی عددی: <code>{user_data['telegram_id']}</code>
---------------------
🎟 کد تخفیف استفاده شده: <b>{state.get('discount_code', '-')}</b>
💵 مبلغ پرداختی کاربر: <code>{utils.rial_to_toman(state['pay_amount'])}</code> تومان
💰 مبلغی که شارژ خواهد شد: <b>{utils.rial_to_toman(state['amount'])}</b> تومان
---------------------
⚠️ لطفاً رسید بالا را با مبلغ دریافتی در حساب خود چک کنید.
"""
            for ADMIN in ADMINS_ID:
                try: admin_bot.send_photo(ADMIN, open(path_recp, 'rb'), caption=admin_caption, reply_markup=confirm_payment_by_admin(state['id']))
                except: pass
            bot.send_message(message.chat.id, "✅ رسید شما با موفقیت ثبت شد و در انتظار تایید ادمین می‌باشد.", reply_markup=main_menu_keyboard_markup())
        else: bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())
    except Exception as e:
        logging.error(f"Error screenshot: {e}")
        bot.send_message(message.chat.id, MESSAGES['UNKNOWN_ERROR'], reply_markup=main_menu_keyboard_markup())

# ----------------- Support Settings Modified -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: CallbackQuery):
    bot.answer_callback_query(call.id, MESSAGES['WAIT'])
    bot.clear_step_handler(call.message)
    if is_user_banned(call.message.chat.id): return
    data = call.data.split(':')
    key = data[0]
    value = data[1] if len(data) > 1 else None

    global selected_server_id

    if key == "user_sub_page":
        page = int(value)
        non_order_subs = utils.non_order_user_info(call.message.chat.id) or []
        order_subs = utils.order_user_info(call.message.chat.id) or []
        all_subs = non_order_subs + order_subs
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=user_subscriptions_list_markup(all_subs, page))

    elif key == "user_sub_info":
        sub = utils.find_order_subscription_by_uuid(value)
        if not sub:
            bot.send_message(call.message.chat.id, MESSAGES['UNKNOWN_ERROR'])
            return
        server = USERS_DB.find_server(id=sub['server_id'])[0]
        URL = server['url'] + API_PATH
        user = api.find(URL, uuid=value)
        if not user:
            bot.send_message(call.message.chat.id, MESSAGES['UNKNOWN_ERROR'])
            return
        user = utils.dict_process(URL, utils.users_to_dict([user]))[0]
        markup = user_info_non_sub_markup(value) if sub.get('telegram_id', None) else user_info_markup(value)
        msg = user_info_template(sub['id'], server, user, MESSAGES['INFO_USER'])
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif key == "user_sub_search_name":
        bot.send_message(call.message.chat.id, MESSAGES['REQUEST_SEND_NAME'], reply_markup=cancel_markup())
        bot.register_next_step_handler(call.message, next_step_user_sub_search_name)

    elif key == "user_sub_search_uuid":
        bot.send_message(call.message.chat.id, "لطفاً UUID اشتراک خود را بفرستید:", reply_markup=cancel_markup())
        bot.register_next_step_handler(call.message, next_step_user_sub_search_uuid)

    elif key == 'server_selected':
        if value == 'False': return bot.send_message(call.message.chat.id, MESSAGES['SERVER_IS_FULL'], reply_markup=main_menu_keyboard_markup())
        selected_server_id = int(value)
        plans = USERS_DB.find_plan(server_id=int(value))
        if not plans: return bot.send_message(call.message.chat.id, MESSAGES['PLANS_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
        bot.edit_message_text(MESSAGES['PLANS_LIST'], call.message.chat.id, call.message.message_id, reply_markup=plans_list_markup(plans))
        
    elif key == 'plan_selected':
        plan = USERS_DB.find_plan(id=value)[0]
        wallet = USERS_DB.find_wallet(telegram_id=call.message.chat.id)
        wallet_balance = wallet[0]['balance'] if wallet else 0
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=plan_info_template(plan, wallet_balance=wallet_balance), reply_markup=confirm_buy_plan_markup(plan['id']))

    elif key == 'confirm_buy_from_wallet':
        plan = USERS_DB.find_plan(id=value)[0]
        buy_from_wallet_confirm(call.message, plan)

    elif key == 'increase_wallet_balance':
        msg = bot.send_message(call.message.chat.id, MESSAGES['INCREASE_WALLET_BALANCE_AMOUNT'], reply_markup=cancel_markup())
        bot.register_next_step_handler(msg, next_step_increase_wallet_balance)
        
    elif key == 'increase_wallet_balance_specific':
        plan_id = data[1]
        amount = int(data[2])
        bot.delete_message(call.message.chat.id, call.message.message_id)
        increase_wallet_balance_specific(call.message, plan_id, amount)

    elif key == 'send_screenshot':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, MESSAGES.get('REQUEST_SEND_SCREENSHOT', 'لطفاً رسید واریزی را ارسال کنید:'))
        bot.register_next_step_handler(msg, next_step_send_screenshot, value)

    elif key == "conf_sub_url":
        sub_info = utils.find_order_subscription_by_uuid(value)
        if not sub_info:
            non_order = USERS_DB.find_non_order_subscription(uuid=value)
            if non_order: sub_info = non_order[0]
            else: return bot.send_message(call.message.chat.id, MESSAGES['UNKNOWN_ERROR'])
        server = USERS_DB.find_server(id=sub_info['server_id'])[0]
        URL = server['url'] + API_PATH
        user = api.find(URL, uuid=value)
        user_name = user.get('name', 'User') or 'User'
        base_sub = SUB_URL if SUB_URL.endswith("/") else f"{SUB_URL}/"
        my_sub_link = f"{base_sub}{value}/#{user_name.replace(' ', '_')}"
        qr_code = utils.txt_to_qr(my_sub_link)
        if qr_code: bot.send_photo(call.message.chat.id, photo=qr_code, caption=f"🔗 لینک سابسکریپشن:\n<code>{my_sub_link}</code>", reply_markup=main_menu_keyboard_markup())

    elif key == "back_to_user_panel":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=user_info_markup(value))
    elif key == "back_to_plans":
        plans = USERS_DB.find_plan(server_id=selected_server_id)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=MESSAGES['PLANS_LIST'], reply_markup=plans_list_markup(plans))
    elif key == "back_to_servers":
        servers = USERS_DB.select_servers()
        server_list = []
        for server in servers:
            users_list = api.select(server['url'] + API_PATH)
            server_list.append([server, True if server['user_limit'] > len(users_list or []) else False])
        bot.edit_message_text(reply_markup=servers_list_markup(server_list), chat_id=call.message.chat.id, message_id=call.message.message_id, text=MESSAGES['SERVERS_LIST'])
    elif key == "del_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start_bot(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    if USERS_DB.find_user(telegram_id=message.chat.id):
        USERS_DB.edit_user(telegram_id=message.chat.id,full_name=message.from_user.full_name)
        USERS_DB.edit_user(telegram_id=message.chat.id,username=message.from_user.username)
        bot.send_message(message.chat.id, MESSAGES.get('WELCOME', 'خوش آمدید!'), reply_markup=main_menu_keyboard_markup())
    else:
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        USERS_DB.add_user(telegram_id=message.chat.id,username=message.from_user.username, full_name=message.from_user.full_name, created_at=created_at)
        USERS_DB.add_wallet(telegram_id=message.chat.id)
        bot.send_message(message.chat.id, MESSAGES.get('WELCOME', 'خوش آمدید!'), reply_markup=main_menu_keyboard_markup())

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['SUBSCRIPTION_STATUS'])
def subscription_status(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    all_subs = (utils.non_order_user_info(message.chat.id) or []) + (utils.order_user_info(message.chat.id) or [])
    if not all_subs: return bot.send_message(message.chat.id, MESSAGES['SUBSCRIPTION_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
    bot.send_message(message.chat.id, "📋 لیست اشتراک‌های شما:\n\nبرای مدیریت، روی نام اشتراک کلیک کنید:", reply_markup=user_subscriptions_list_markup(all_subs))

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['BUY_SUBSCRIPTION'])
def buy_subscription(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    servers = USERS_DB.select_servers()
    if not servers: return bot.send_message(message.chat.id, MESSAGES['SERVERS_NOT_FOUND'], reply_markup=main_menu_keyboard_markup())
    server_list = []
    for server in servers:
        users_list = api.select(server['url'] + API_PATH)
        server_list.append([server, True if server['user_limit'] > len(users_list or []) else False])
    bot.send_message(message.chat.id, MESSAGES['SERVERS_LIST'], reply_markup=servers_list_markup(server_list))

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['SEND_TICKET'])
def send_ticket(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    support = utils.all_configs_settings().get('support_username', '-')
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data="del_msg:None"))
    bot.send_message(message.chat.id, f"جهت ارسال پیام به پشتیبانی به آی دی تلگرام زیر پیام بدهید:\n{support}", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['WALLET'])
def wallet_balance(message: Message):
    if is_user_banned(message.chat.id) or not is_user_in_channel(message.chat.id): return
    wallet = USERS_DB.find_wallet(telegram_id=message.chat.id)
    if not wallet: USERS_DB.add_wallet(telegram_id=message.chat.id)
    balance = USERS_DB.find_wallet(telegram_id=message.chat.id)[0]['balance']
    bot.send_message(message.chat.id, wallet_info_template(balance), reply_markup=wallet_info_markup())

@bot.message_handler(func=lambda message: message.text == KEY_MARKUP['CANCEL'])
def cancel(message: Message):
    bot.send_message(message.chat.id, MESSAGES['CANCELED'], reply_markup=main_menu_keyboard_markup())

def start():
    bot.enable_save_next_step_handlers()
    bot.load_next_step_handlers()
    bot.infinity_polling()