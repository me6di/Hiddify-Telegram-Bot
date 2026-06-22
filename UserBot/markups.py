# Description: This file contains all the reply and inline keyboard markups used in the bot.
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from UserBot.content import KEY_MARKUP, MESSAGES
from Utils.utils import rial_to_toman, all_configs_settings
from Utils.api import *

def main_menu_keyboard_markup():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
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

def user_info_markup(uuid, is_expired=False):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("🔗 دریافت لینک سابسکریپشن", callback_data=f"conf_sub_url:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['RENEWAL_SUBSCRIPTION'], callback_data=f"renewal_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['UPDATE_SUBSCRIPTION_INFO'], callback_data=f"update_info_subscription:{uuid}"))
    if is_expired:
        markup.add(InlineKeyboardButton("🗑 حذف این سرویس", callback_data=f"delete_expired_sub:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data="user_sub_page:1"))
    return markup

def user_info_non_sub_markup(uuid, is_expired=False):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("🔗 دریافت لینک سابسکریپشن", callback_data=f"conf_sub_url:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['RENEWAL_SUBSCRIPTION'], callback_data=f"renewal_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['UPDATE_SUBSCRIPTION_INFO'], callback_data=f"update_info_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['UNLINK_SUBSCRIPTION'], callback_data=f"unlink_subscription:{uuid}"))
    if is_expired:
        markup.add(InlineKeyboardButton("🗑 حذف این سرویس", callback_data=f"delete_expired_sub:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data="user_sub_page:1"))
    return markup
    
def confirm_subscription_markup(uuid):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(KEY_MARKUP['YES'], callback_data=f"confirm_subscription:{uuid}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['NO'], callback_data=f"cancel_subscription:{uuid}"))
    return markup


def send_screenshot_markup(payment_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(KEY_MARKUP['SEND_SCREENSHOT'], callback_data=f"send_screenshot:{payment_id}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['CANCEL'], callback_data=f"cancel_increase_wallet_balance:{payment_id}"))
    return markup

def plans_list_markup(plans, renewal=False, uuid=None):
    markup = InlineKeyboardMarkup(row_width=1)
    callback = "renewal_plan_selected" if renewal else "plan_selected"
    keys = []
    for plan in plans:
        if plan['status']:
            keys.append(InlineKeyboardButton(
                f"{plan['size_gb']}{MESSAGES.get('GB', 'گیگ')} | {plan['days']}{MESSAGES.get('DAY_EXPIRE', 'روز')} | {rial_to_toman(plan['price'])} {MESSAGES.get('TOMAN', 'تومان')}",
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

def confirm_payment_by_admin(order_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton(KEY_MARKUP.get('CONFIRM_PAYMENT', '✅ تایید پرداخت'), callback_data=f"confirm_payment_by_admin:{order_id}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('NO', '❌ رد تراکنش'), callback_data=f"cancel_payment_by_admin:{order_id}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('SEND_MESSAGE', '✉️ ارسال پیام'), callback_data=f"send_message_by_admin:{order_id}"))
    return markup

def notify_to_admin_markup(user):
    name = user['full_name'] if user['full_name'] else user['telegram_id']
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(f"{name}", callback_data=f"bot_user_info:{user['telegram_id']}"))
    return markup

def send_ticket_to_admin():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton(KEY_MARKUP['SEND_TICKET_TO_SUPPORT'], callback_data=f"send_ticket_to_support:None"))
    markup.add(
        InlineKeyboardButton(KEY_MARKUP['CANCEL'], callback_data=f"del_msg:None"))
    return markup

def answer_to_user_markup(user, user_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    name = user['full_name'] if user['full_name'] else user['telegram_id']
    markup.add(InlineKeyboardButton(f"{name}", callback_data=f"bot_user_info:{user['telegram_id']}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['ANSWER'], callback_data=f"users_bot_send_message_by_admin:{user_id}"))
    return markup

def cancel_markup():
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(KeyboardButton(KEY_MARKUP['CANCEL']))
    return markup

def wallet_info_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("💳 افزایش موجودی", callback_data="increase_wallet_balance:wallet"))
    markup.add(InlineKeyboardButton("🎁 افزایش موجودی با کد تخفیف", callback_data="increase_wallet_balance_discount:wallet"))
    return markup

def confirm_buy_plan_markup(plan_id, renewal=False, uuid=None):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    callback = "confirm_buy_from_wallet" if not renewal else "confirm_renewal_from_wallet"
    
    # ترفند: اگر تمدید باشد، آیدی پلن را منفی می‌فرستیم
    card_plan_id = -int(plan_id) if renewal else plan_id
    
    markup.add(InlineKeyboardButton("💳 پرداخت مستقیم (کارت به کارت)", callback_data=f"direct_card_payment:{card_plan_id}"))
    markup.add(InlineKeyboardButton(KEY_MARKUP['BUY_FROM_WALLET'], callback_data=f"{callback}:{plan_id}"))
    if renewal:
        markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"back_to_renewal_plans:{uuid}"))
    else:
        markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"back_to_plans:None"))
    return markup

def wallet_info_specific_markup(plan_id, amount, is_renewal=False):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    
    # ترفند: در صورت تمدید، پلن آیدی منفی ذخیره می‌شود
    target_plan_id = -int(plan_id) if is_renewal else plan_id
    
    markup.add(InlineKeyboardButton(f"💳 شارژ دقیق ( {rial_to_toman(amount)} {MESSAGES.get('TOMAN', 'تومان')} )", callback_data=f"increase_wallet_balance_specific:{target_plan_id}:{amount}"))
    markup.add(InlineKeyboardButton("🎁 شارژ دقیق با کد تخفیف", callback_data=f"increase_wallet_balance_specific_discount:{target_plan_id}:{amount}"))
    
    back_callback = f"renewal_plan_selected:{plan_id}" if is_renewal else f"plan_selected:{plan_id}"
    markup.add(InlineKeyboardButton("🔙 برگشت", callback_data=back_callback))
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
        nav_keys.append(InlineKeyboardButton(KEY_MARKUP.get('PREV_PAGE', 'قبلی'), callback_data=f"user_sub_page:{page - 1}"))
    if page < len(subs) / PER_PAGE:
        nav_keys.append(InlineKeyboardButton(KEY_MARKUP.get('NEXT_PAGE', 'بعدی'), callback_data=f"user_sub_page:{page + 1}"))
    if nav_keys:
        markup.add(*nav_keys)
        
    markup.add(
        InlineKeyboardButton("🔍 با نام", callback_data="user_sub_search_name:None"),
        InlineKeyboardButton("🔍 با UUID", callback_data="user_sub_search_uuid:None")
    )
    markup.add(InlineKeyboardButton(KEY_MARKUP.get('BACK', 'برگشت'), callback_data=f"del_msg:None"))
    return markup