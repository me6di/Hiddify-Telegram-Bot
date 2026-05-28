# Description: This file contains all the templates used in the bot.
from config import LANG, SUB_URL
from UserBot.content import MESSAGES
from Utils.utils import rial_to_toman, toman_to_rial, all_configs_settings
from Database.dbManager import USERS_DB

def user_info_template(sub_id, server, usr, header=""):
    name = usr.get('name', 'User') or 'User'
    formatted_name = name.replace(' ', '_')
    base_sub = SUB_URL if SUB_URL.endswith("/") else f"{SUB_URL}/"
    sub_link = f"{base_sub}{usr['uuid']}/#{formatted_name}"
    
    user_name = f"<a href='{sub_link}'> {name} </a>"

    return f"""
{header}

{MESSAGES.get('USER_NAME', 'نام:')} {user_name}
{MESSAGES.get('SERVER', 'سرور:')} {server['title']}
{MESSAGES.get('INFO_USAGE', 'حجم مصرفی:')} {usr['usage']['current_usage_GB']} {MESSAGES.get('OF', 'از')} {usr['usage']['usage_limit_GB']} {MESSAGES.get('GB', 'گیگ')}
{MESSAGES.get('INFO_REMAINING_DAYS', 'روزهای باقی‌مانده:')} {usr['remaining_day']} {MESSAGES.get('DAY_EXPIRE', 'روز')}
{MESSAGES.get('INFO_ID', 'آیدی:')} <code>{sub_id}</code>
"""

def wallet_info_template(balance):
    if balance == 0:
        return MESSAGES.get('ZERO_BALANCE', 'موجودی شما صفر است.')
    else:
        return f"""
         {MESSAGES.get('WALLET_INFO_PART_1', 'موجودی فعلی شما:')} {rial_to_toman(balance)} {MESSAGES.get('WALLET_INFO_PART_2', 'تومان می‌باشد.')}
         """

def plan_info_template(plan, header="", wallet_balance=None):
    msg = f"""
{header}
{MESSAGES.get('PLAN_INFO', 'اطلاعات پلن')}

{MESSAGES.get('PLAN_INFO_SIZE', 'حجم:')} {plan['size_gb']} {MESSAGES.get('GB', 'گیگ')}
{MESSAGES.get('PLAN_INFO_DAYS', 'مدت زمان:')} {plan['days']} {MESSAGES.get('DAY_EXPIRE', 'روز')}
{MESSAGES.get('PLAN_INFO_PRICE', 'قیمت:')} {rial_to_toman(plan['price'])} {MESSAGES.get('TOMAN', 'تومان')}
"""
    if wallet_balance is not None:
        msg += f"\n💰 موجودی فعلی کیف پول: <b>{rial_to_toman(wallet_balance)}</b> {MESSAGES.get('TOMAN', 'تومان')}\n"

    if plan['description']:
        msg += f"""\n{MESSAGES.get('PLAN_INFO_DESC', 'توضیحات:')} {plan['description']}"""
    return msg
    
def owner_info_template(card_number, card_holder_name, price, header=""):
    card_number = card_number if card_number else "-"
    card_holder_name = card_holder_name if card_holder_name else "-"

    if LANG == 'FA':
        return f"""
{header}

💰لطفا دقیقا مبلغ: <code>{price}</code> {MESSAGES.get('RIAL', 'ریال')}
💴معادل: {rial_to_toman(price)} {MESSAGES.get('TOMAN', 'تومان')}
💳را به شماره کارت: <code>{card_number}</code>
👤به نام <b>{card_holder_name}</b> واریز کنید.

❗️بعد از واریز مبلغ، اسکرین شات از تراکنش را برای ما ارسال کنید.
"""
    elif LANG == 'EN':
        return f"""
{header}

💰Please pay exactly: <code>{price}</code> {MESSAGES.get('TOMAN', 'تومان')}
💳To card number: <code>{card_number}</code>
Card owner <b>{card_holder_name}</b>

❗️After paying the amount, send us a screenshot of the transaction.
"""

# اینجا ارور اصلی قالب را حل کردیم تا امن شود
def payment_received_template(payment,user, header="", footer=""):
    username = f"@{user['username']}" if user['username'] else MESSAGES.get('NOT_SET', 'ثبت نشده')
    name = user['full_name'] if user['full_name'] else user['telegram_id']

    if LANG == 'FA':
        return f"""
{header}

شناسه تراکنش: <code>{payment['id']}</code>
مبلغ تراکنش: <b>{rial_to_toman(payment['payment_amount'])}</b> {MESSAGES.get('TOMAN', 'تومان')}
{MESSAGES.get('INFO_USER_NAME', 'نام کاربر:')} <b>{name}</b>
{MESSAGES.get('INFO_USER_USERNAME', 'یوزرنیم:')} {username}
{MESSAGES.get('INFO_USER_NUM_ID', 'آیدی عددی:')} {user['telegram_id']}
---------------------
⬇️درخواست افزایش موجودی کیف پول⬇️

{footer}
"""
    elif LANG == 'EN':
        return f"""
{header}

Payment number: <b>{payment['id']}</b>
Paid amount: <b>{payment['payment_amount']}</b> {MESSAGES.get('TOMAN', 'تومان')}
{MESSAGES.get('INFO_USER_NAME', 'نام کاربر:')} <b>{name}</b>
{MESSAGES.get('INFO_USER_USERNAME', 'یوزرنیم:')} {username}
{MESSAGES.get('INFO_USER_NUM_ID', 'آیدی عددی:')} {user['telegram_id']}
---------------------
⬇️Request to increase wallet balance⬇️

"""

def connection_help_template(header=""):
    if LANG == 'FA':
        return f"""
{header}

⭕️ نرم افزار های مورد نیاز برای اتصال به کانفیگ
    
📥اندروید:
<a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>V2RayNG</a>
<a href='https://play.google.com/store/apps/details?id=ang.hiddify.com'>HiddifyNG</a>

📥آی او اس:
<a href='https://apps.apple.com/us/app/streisand/id6450534064'>Streisand</a>
<a href='https://apps.apple.com/us/app/foxray/id6448898396'>Foxray</a>
<a href='https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690'>V2box</a>

📥ویندوز:
<a href='https://github.com/MatsuriDayo/nekoray/releases'>Nekoray</a>
<a href='https://github.com/2dust/v2rayN/releases'>V2rayN</a>
<a href='https://github.com/hiddify/HiddifyN/releases'>HiddifyN</a>

📥مک و لینوکس:
<a href='https://github.com/MatsuriDayo/nekoray/releases'>Nekoray</a>
"""
    elif LANG == 'EN':
        return f"""
{header}

⭕️Required software for connecting to config

📥Android:
<a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>V2RayNG</a>
...
"""

def package_days_expire_soon_template(sub_id, remaining_days):
    if LANG == 'FA':
        return f"""
تنها {remaining_days} روز تا اتمام اعتبار پکیج شما باقی مانده است.
لطفا برای تمدید پکیج اقدام کنید.
شناسه پکیج شما: <code>{sub_id}</code>
"""
    elif LANG == 'EN':
        return f"""
Only {remaining_days} days left until your package expires.
...
"""

def package_size_end_soon_template(sub_id, remaining_size):
    if LANG == 'FA':
        return f"""
تنها {remaining_size} گیگابایت تا اتمام اعتبار پکیج شما باقی مانده است.
لطفا برای تمدید پکیج اقدام کنید.

شناسه پکیج شما: <code>{sub_id}</code>
"""
    elif LANG == 'EN':
        return f"""
Only {remaining_size} GB left until your package expires.
...
"""

def renewal_unvalable_template(settings):
    if LANG == 'FA':
        return f"""
🛑در حال حاضر شما امکان تمدید اشتراک خود را ندارید.
جهت تمدید اشتراک باید یکی از شروط زیر برقرار باشد:
1- کمتر از {settings['advanced_renewal_days']} روز تا اتمام اشتراک شما باقی مانده باشد.
2- حجم باقی مانده اشتراک شما کمتر از {settings['advanced_renewal_usage']} گیگابایت باشد.
"""
    elif LANG == 'EN':
        return f"""
🛑You cannot renew your subscription at this time.
...
"""