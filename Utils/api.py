# from config import *
# from Utils.utils import *
import json
import logging
from urllib.parse import urlparse
import datetime
import requests
from config import API_PATH
import Utils


# Document: https://github.com/hiddify/hiddify-config/discussions/3209
# It not in uses now, but it will be used in the future.



def select(url, endpoint="/user/"):
    try:
        response = requests.get(url + endpoint)
        res = Utils.utils.dict_process(url, Utils.utils.users_to_dict(response.json()))
        return res
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def find(url, uuid, endpoint="/user/"):
    try:
        response = requests.get(url + endpoint, data={"uuid": uuid})
        jr = response.json()
        if len(jr) != 1:
            # Search for uuid
            for user in jr:
                if user['uuid'] == uuid:
                    return user
            return None
        return jr[0]
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def insert(url, name, usage_limit_GB, package_days, last_reset_time=None, added_by_uuid=None, mode="no_reset",
            last_online="1-01-01 00:00:00", telegram_id=None,
            comment=None, current_usage_GB=0, start_date=None, endpoint="/user/"):
    import uuid
    uuid = str(uuid.uuid4())
    # last_online = '1-01-01 00:00:00'
    # expiry_time = (datetime.datetime.now() + datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    # start_date = None
    # current_usage_GB = 0
    added_by_uuid = urlparse(url).path.split('/')[2]
    last_reset_time = datetime.datetime.now().strftime("%Y-%m-%d")

    data = {
        "uuid": uuid,
        "name": name,
        "usage_limit_GB": usage_limit_GB,
        "package_days": package_days,
        "added_by_uuid": added_by_uuid,
        "last_reset_time": last_reset_time,
        "mode": mode,
        "last_online": last_online,
        "telegram_id": telegram_id,
        "comment": comment,
        "current_usage_GB": current_usage_GB,
        "start_date": start_date
    }
    jdata = json.dumps(data)
    try:
        response = requests.post(url + endpoint, data=jdata, headers={'Content-Type': 'application/json'})
        return uuid
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def update(url, uuid, endpoint="/user/", **kwargs, ):
    try:
        # use api.insert to update, replace new data with old data
        user = find(url, uuid)
        if not user:
            return None
        for key in kwargs:
            user[key] = kwargs[key]
        response = requests.post(url + endpoint, data=json.dumps(user),
                                    headers={'Content-Type': 'application/json'})
        return uuid
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def delete(url, uuid, endpoint="/user/"):
    try:
        # روش اول: حذف با ارسال UUID در انتهای URL (استاندارد پنل هیدیفای)
        response = requests.delete(f"{url}{endpoint}{uuid}/")
        if response.status_code in [200, 204]:
            return True
            
        # روش دوم: ارسال UUID به عنوان بادی (برای سازگاری با نسخه‌های مختلف پنل)
        jdata = json.dumps({"uuid": uuid})
        response = requests.delete(url + endpoint, data=jdata, headers={'Content-Type': 'application/json'})
        return response.status_code in [200, 204]
    except Exception as e:
        logging.error("API delete error: %s" % e)
        return False

# اضافه کردن نام مستعار برای جلوگیری از ارور در صورتی که ربات ادمین از remove استفاده کند
remove = delete

