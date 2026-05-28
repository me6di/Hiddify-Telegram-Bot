# Description: This file contains all the reply and inline keyboard markups used in the bot.
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from UserBot.content import KEY_MARKUP, MESSAGES
from Utils.utils import rial_to_toman, all_configs_settings
from Utils.api import *

def main_menu_keyboard_markup():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # جابجایی دکمه خرید به بالا و حذف دکمه اتصال اشتراک
    markup.add(KeyboardButton(KEY_MARKUP['BUY_SUBSCRIPTION']))
    markup.add(KeyboardButton(KEY_MARKUP['SUBSCRIPTION_STATUS']))
    
    settings = all_configs_settings()
    
    if settings.get('test_subscription', False):
        markup.add(KeyboardButton(KEY_MARKUP['FREE_TEST']), KeyboardButton(KEY_MARKUP['WALLET']))
    else:
        markup.add(KeyboardButton(KEY_MARKUP['WALLET']))
        
    if settings.get('msg_faq', False):
        markup.add(KeyboardButton(KEY_MARKUP['SEND_TICKET']),
                   KeyboardButton(KEY_MARKUP['MANUAL']), KeyboardButton(KEY_MARKUP['FAQ']))
    else:
        markup.add(KeyboardButton(KEY_MARKUP['SEND_TICKET']),
                   KeyboardButton(KEY_MARKUP['MANUAL']))
    return markup

def user_info_markup(uuid):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    # تغییر نام به دریافت مستقیم لینک 
    markup.add(InlineKeyboardButton("🔗 دریافت لینک سابسکریپشن", callback_data=f"conf_sub_url:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['RENEWAL_SUBSCRIPTION'], callback_data=f"renewal_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['UPDATE_SUBSCRIPTION_INFO'], callback_data=f"update_info_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data="user_sub_page:1"))
    return markup

def user_info_non_sub_markup(uuid):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("🔗 دریافت لینک سابسکریپشن", callback_data=f"conf_sub_url:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['RENEWAL_SUBSCRIPTION'], callback_data=f"renewal_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['UPDATE_SUBSCRIPTION_INFO'], callback_data=f"update_info_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['UNLINK_SUBSCRIPTION'], callback_data=f"unlink_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data="user_sub_page:1"))
    return markup

def confirm_subscription_markup(uuid):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(KEY_MARKUP['YES'], callback_data=f"confirm_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['NO'], callback_data=f"cancel_subscription:{uuid}"))
    return markup

def confirm_buy_plan_markup(plan_id, renewal=False, uuid=None):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    callback = "confirm_buy_from_wallet" if not renewal else "confirm_renewal_from_wallet"
    markup.add(InlineKeyboardButton(KEY_MARKUP['BUY_FROM_WALLET'], callback_data=f"{callback}:{plan_id}"))
    if renewal:
        markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"back_to_renewal_plans:{uuid}"))
    else:
        markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"back_to_plans:None"))
    return markup

def send_screenshot_markup(plan_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(KEY_MARKUP['SEND_SCREENSHOT'], callback_data=f"send_screenshot:{plan_id}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['CANCEL'], callback_data=f"cancel_increase_wallet_balance:{plan_id}"))
    return markup

def plans_list_markup(plans, renewal=False, uuid=None):
    markup = InlineKeyboardMarkup(row_width=1)
    callback = "renewal_plan_selected" if renewal else "plan_selected"
    keys = []
    for plan in plans:
        if plan['status']:
            keys.append(InlineKeyboardButton(
                f"{plan['size_gb']}{MESSAGES['GB']} | {plan['days']}{MESSAGES['DAY_EXPIRE']} | {rial_to_toman(plan['price'])} {MESSAGES['TOMAN']}",
                callback_data=f"{callback}:{plan['id']}"))
    if len(keys) == 0:
        return None
    if renewal:
        keys.append(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"back_to_user_panel:{uuid}"))
    else:
        keys.append(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"back_to_servers:None"))
    markup.add(*keys)
    return markup

def servers_list_markup(servers, free_test=False):
    markup = InlineKeyboardMarkup(row_width=1)
    callback = "free_test_server_selected" if free_test else "server_selected"
    keys = []
    if servers:
        for server in servers:
            server_title = server[0]['title'] if server[1] else f"{server[0]['title']}⛔️"
            callback_2 = f"{server[0]['id']}" if server[1] else "False"
            keys.append(InlineKeyboardButton(f"{server_title}", callback_data=f"{callback}:{callback_2}"))
        keys.append(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"del_msg:None"))
    if len(keys) == 0: return None
    markup.add(*keys)
    return markup

def cancel_markup():
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(KeyboardButton(KEY_MARKUP['CANCEL']))
    return markup

def wallet_info_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(KEY_MARKUP['INCREASE_WALLET_BALANCE'], callback_data=f"increase_wallet_balance:wallet"))
    return markup

# اضافه شدن دو دکمه همزمان در صورت کمبود موجودی
def wallet_info_specific_markup(amount):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(f"💳 افزایش موجودی (دقیقاً {rial_to_toman(amount)} {MESSAGES['TOMAN']})", callback_data=f"increase_wallet_balance_specific:{amount}"))
    markup.add(InlineKeyboardButton("➕ افزایش موجودی (مبلغ دلخواه)", callback_data="increase_wallet_balance:wallet"))
    return markup

def force_join_channel_markup(channel_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    channel_id = channel_id.replace("@", "")
    markup.add(InlineKeyboardButton(KEY_MARKUP['JOIN_CHANNEL'], url=f"https://t.me/{channel_id}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['FORCE_JOIN_CHANNEL_ACCEPTED'], callback_data=f"force_join_status:None"))
    return markup

def users_bot_management_settings_panel_manual_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(KEY_MARKUP['MANUAL_ANDROID'], callback_data=f"msg_manual:android"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['MANUAL_IOS'], callback_data=f"msg_manual:ios"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['MANUAL_WIN'], callback_data=f"msg_manual:win"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['MANUAL_MAC'], callback_data=f"msg_manual:mac"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['MANUAL_LIN'], callback_data=f"msg_manual:lin"))
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"del_msg:None"))
    return markup

def user_subscriptions_list_markup(subs, page=1):
    markup = InlineKeyboardMarkup(row_width=2)
    PER_PAGE = 20
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    keys = []
    
    for sub in subs[start:end]:
        name = sub.get('name', 'User') or 'User'
        if len(name) > 15: name = name[:15] + ".."
        keys.append(InlineKeyboardButton(f"👤 {name}", callback_data=f"user_sub_info:{sub['uuid']}"))
    
    markup.add(*keys)
    
    nav_keys = []
    if page > 1:
        nav_keys.append(InlineKeyboardButton(KEY_MARKUP['PREV_PAGE'], callback_data=f"user_sub_page:{page - 1}"))
    if page < len(subs) / PER_PAGE:
        nav_keys.append(InlineKeyboardButton(KEY_MARKUP['NEXT_PAGE'], callback_data=f"user_sub_page:{page + 1}"))
    if nav_keys:
        markup.add(*nav_keys)
        
    markup.add(
        InlineKeyboardButton("🔍 با نام", callback_data="user_sub_search_name:None"),
        InlineKeyboardButton("🔍 با UUID", callback_data="user_sub_search_uuid:None")
    )
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"del_msg:None"))
    return markup