import datetime
import json
import logging
import os
import sqlite3
from sqlite3 import Error
from version import is_version_less

class UserDBManager:
    def __init__(self, db_file):
        self.conn = self.create_connection(db_file)
        self.create_user_table()

    def __del__(self):
        self.conn.close()
    
    def close(self):
        self.conn.close()

    def create_connection(self, db_file):
        try:
            conn = sqlite3.connect(db_file, check_same_thread=False)
            return conn
        except Error as e:
            logging.error(f"Error while connecting to database \n Error:{e}")
            return None

    def create_user_table(self):
        cur = self.conn.cursor()
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS users ("
                        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                        "telegram_id INTEGER NOT NULL UNIQUE,"
                        "full_name TEXT NULL,"
                        "username TEXT NULL,"
                        "test_subscription BOOLEAN NOT NULL DEFAULT 0,"
                        "banned BOOLEAN NOT NULL DEFAULT 0,"
                        "created_at TEXT NOT NULL)")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS plans ("
                        "id INTEGER PRIMARY KEY,"
                        "size_gb INTEGER NOT NULL,"
                        "days INTEGER NOT NULL,"
                        "price INTEGER NOT NULL,"
                        "server_id INTEGER NOT NULL,"
                        "description TEXT NULL,"
                        "status BOOLEAN NOT NULL,"
                        "FOREIGN KEY (server_id) REFERENCES server (id))")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS orders ("
                        "id INTEGER PRIMARY KEY,"
                        "telegram_id INTEGER NOT NULL,"
                        "plan_id INTEGER NOT NULL,"
                        "user_name TEXT NOT NULL,"
                        "created_at TEXT NOT NULL,"
                        "FOREIGN KEY (telegram_id) REFERENCES user (telegram_id),"
                        "FOREIGN KEY (plan_id) REFERENCES plans (id))")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS order_subscriptions ("
                        "id INTEGER PRIMARY KEY,"
                        "order_id INTEGER NOT NULL,"
                        "uuid TEXT NOT NULL,"
                        "server_id INTEGER NOT NULL,"
                        "FOREIGN KEY (server_id) REFERENCES server (id),"
                        "FOREIGN KEY (order_id) REFERENCES orders (id))")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS non_order_subscriptions ("
                        "id INTEGER PRIMARY KEY,"
                        "telegram_id INTEGER NOT NULL,"
                        "uuid TEXT NOT NULL UNIQUE,"
                        "server_id INTEGER NOT NULL,"
                        "FOREIGN KEY (server_id) REFERENCES server (id),"
                        "FOREIGN KEY (telegram_id) REFERENCES users (telegram_id))")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS str_config ("
                        "key TEXT NOT NULL UNIQUE,"
                        "value TEXT NULL)")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS int_config ("
                        "key TEXT NOT NULL UNIQUE,"
                        "value INTEGER NOT NULL)")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS bool_config ("
                        "key TEXT NOT NULL UNIQUE,"
                        "value BOOLEAN NOT NULL)")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS wallet ("
                        "telegram_id INTEGER NOT NULL UNIQUE,"
                        "balance INTEGER NOT NULL DEFAULT 0,"
                        "FOREIGN KEY (telegram_id) REFERENCES users (telegram_id))")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS payments ("
                        "id INTEGER PRIMARY KEY,"
                        "telegram_id INTEGER NOT NULL,"
                        "payment_amount INTEGER NOT NULL,"
                        "payment_method TEXT NOT NULL,"
                        "payment_image TEXT NOT NULL,"
                        "approved BOOLEAN NULL,"
                        "created_at TEXT NOT NULL,"
                        "FOREIGN KEY (telegram_id) REFERENCES users (telegram_id))")
            self.conn.commit()

            cur.execute("CREATE TABLE IF NOT EXISTS servers ("
                        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                        "url TEXT NOT NULL,"
                        "title TEXT, description TEXT,"
                        "user_limit INTEGER NOT NULL,"
                        "status BOOLEAN NOT NULL,"
                        "default_server BOOLEAN NOT NULL DEFAULT 0)")
            self.conn.commit()
            
            # --- Table for Discount Codes ---
            cur.execute("CREATE TABLE IF NOT EXISTS discount_codes ("
                        "code TEXT PRIMARY KEY,"
                        "discount_percent INTEGER NOT NULL,"
                        "usage_limit INTEGER NOT NULL DEFAULT 1,"
                        "used_count INTEGER NOT NULL DEFAULT 0)")
            self.conn.commit()

        except Error as e:
            logging.error(f"Error while creating user table \n Error:{e}")
            return False
        return True

    # --- Discount Code Methods ---
    def use_discount_code(self, code):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM discount_codes WHERE code=?", (code,))
        row = cur.fetchone()
        if not row: return None
        
        data = dict(zip([key[0] for key in cur.description], row))
        if data['used_count'] < data['usage_limit']:
            cur.execute("UPDATE discount_codes SET used_count = used_count + 1 WHERE code=?", (code,))
            self.conn.commit()
            return data['discount_percent']
        return None

    def add_discount_code(self, code, percent, limit=1):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO discount_codes(code, discount_percent, usage_limit) VALUES(?,?,?)", (code, percent, limit))
            self.conn.commit()
            return True
        except: return False

    # --- Existing Methods ---
    def select_users(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM users")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_user(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM users WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def delete_user(self, **kwargs):
        if len(kwargs) != 1: return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM users WHERE {key}=?", (value,))
                self.conn.commit()
            return True
        except Error as e: return False

    def edit_user(self, telegram_id, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE users SET {key}=? WHERE telegram_id=?", (value, telegram_id))
                self.conn.commit()
            except Error as e: return False
        return True

    def add_user(self, telegram_id, full_name,username, created_at):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO users(telegram_id, full_name,username, created_at) VALUES(?,?,?,?)",
                        (telegram_id, full_name,username, created_at))
            self.conn.commit()
            return True
        except Error as e: return False

    def add_plan(self, plan_id, size_gb, days, price, server_id, description=None, status=True):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO plans(id,size_gb, days, price, server_id, description, status) VALUES(?,?,?,?,?,?,?)",
                        (plan_id, size_gb, days, price, server_id, description, status))
            self.conn.commit()
            return True
        except Error as e: return False

    def select_plans(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM plans ORDER BY price ASC")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_plan(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM plans WHERE {key}=? ORDER BY price ASC", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def delete_plan(self, **kwargs):
        if len(kwargs) != 1: return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM plans WHERE {key}=?", (value,))
                self.conn.commit()
            return True
        except Error as e: return False

    def edit_plan(self, plan_id, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE plans SET {key}=? WHERE id=?", (value, plan_id))
                self.conn.commit()
            except Error as e: return False
        return True
    
    def add_user_plans(self, telegram_id, plan_id):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO user_plans(telegram_id, plan_id) VALUES(?,?)", (telegram_id, plan_id))
            self.conn.commit()
            return True
        except Error as e: return False

    def select_user_plans(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM user_plans")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_user_plans(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM user_plans WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def delete_user_plans(self, **kwargs):
        if len(kwargs) != 1: return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM user_plans WHERE {key}=?", (value,))
                self.conn.commit()
            return True
        except Error as e: return False

    def edit_user_plans(self, user_plans_id, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE user_plans SET {key}=? WHERE id=?", (value, user_plans_id))
                self.conn.commit()
            except Error as e: return False
        return True
    
    def add_order(self, order_id, telegram_id,user_name, plan_id, created_at):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO orders(id,telegram_id, plan_id,user_name,created_at) VALUES(?,?,?,?,?)",
                (order_id, telegram_id, plan_id,user_name, created_at))
            self.conn.commit()
            return True
        except Error as e: return False

    def select_orders(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM orders")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_order(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM orders WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def edit_order(self, order_id, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE orders SET {key}=? WHERE id=?", (value, order_id))
                self.conn.commit()
            except Error as e: return False
        return True

    def add_order_subscription(self, sub_id, order_id, uuid, server_id):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO order_subscriptions(id,order_id,uuid,server_id) VALUES(?,?,?,?)",
                (sub_id, order_id, uuid, server_id))
            self.conn.commit()
            return True
        except Error as e: return False

    def select_order_subscription(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM order_subscriptions")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_order_subscription(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM order_subscriptions WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def edit_order_subscriptions(self, order_id, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE order_subscriptions SET {key}=? WHERE order_id=?", (value, order_id))
                self.conn.commit()
            except Error as e: return False
        return True

    def delete_order_subscription(self, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM order_subscriptions WHERE {key}=?", (value,))
                self.conn.commit()
            return True
        except Error as e: return False

    def add_non_order_subscription(self, non_sub_id, telegram_id, uuid, server_id):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO non_order_subscriptions(id,telegram_id,uuid,server_id) VALUES(?,?,?,?)",
                (non_sub_id, telegram_id, uuid, server_id))
            self.conn.commit()
            return True
        except Error as e: return False

    def select_non_order_subscriptions(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM non_order_subscriptions")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_non_order_subscription(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM non_order_subscriptions WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def delete_non_order_subscription(self, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM non_order_subscriptions WHERE {key}=?", (value,))
                self.conn.commit()
            return True
        except Error as e: return False

    def edit_bool_config(self, key_row, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE bool_config SET {key}=? WHERE key=?", (value, key_row))
                self.conn.commit()
            except Error as e: return False
        return True

    def find_bool_config(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM bool_config WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def add_bool_config(self, key, value):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT or IGNORE INTO bool_config(key,value) VALUES(?,?)", (key, value))
            self.conn.commit()
            return True
        except Error as e: return False
        finally: cur.close()
            
    def select_bool_config(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM bool_config")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def select_str_config(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM str_config")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_str_config(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM str_config WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def edit_str_config(self, key_row, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE str_config SET {key}=? WHERE key=?", (value, key_row))
                self.conn.commit()
            except Error as e: return False
        return True

    def add_str_config(self, key, value):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT or IGNORE INTO str_config(key,value) VALUES(?,?)", (key, value))
            self.conn.commit()
            return True
        except Error as e: return False
        finally: cur.close()

    def select_int_config(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM int_config")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_int_config(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM int_config WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None
        
    def edit_int_config(self, key_row, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():            
            try:
                cur.execute(f"UPDATE int_config SET {key}=? WHERE key=?", (value, key_row))
                self.conn.commit()
            except Error as e: return False
        return True

    def add_int_config(self, key, value):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT or IGNORE INTO int_config(key,value) VALUES(?,?)", (key, value))
            self.conn.commit()
            return True
        except Error as e: return False
        finally: cur.close()

    # --- تابع مورد نیاز خط ۳۲۱ فایل config.py ---
    def set_default_configs(self):
        self.add_bool_config("visible_hiddify_hyperlink", True)
        self.add_bool_config("three_random_num_price", False)
        self.add_bool_config("force_join_channel", False)
        self.add_bool_config("panel_auto_backup", True)
        self.add_bool_config("bot_auto_backup", True)
        self.add_bool_config("test_subscription", True)
        self.add_bool_config("reminder_notification", True)
        self.add_bool_config("renewal_subscription_status", True)
        self.add_bool_config("buy_subscription_status", True)
        self.add_bool_config("visible_conf_dir", False)
        self.add_bool_config("visible_conf_sub_auto", True)
        self.add_bool_config("visible_conf_sub_url", False)
        self.add_bool_config("visible_conf_sub_url_b64", False)
        self.add_bool_config("visible_conf_clash", False)
        self.add_bool_config("visible_conf_hiddify", False)
        self.add_bool_config("visible_conf_sub_sing_box", False)
        self.add_bool_config("visible_conf_sub_full_sing_box", False)
        self.add_str_config("bot_admin_id", None)
        self.add_str_config("bot_token_admin", None)
        self.add_str_config("bot_token_client", None)
        self.add_str_config("bot_lang", None)
        self.add_str_config("card_number", None)
        self.add_str_config("card_holder", None)
        self.add_str_config("support_username", None)
        self.add_str_config("channel_id", None)
        self.add_str_config("msg_user_start", None)
        self.add_str_config("msg_manual_android", None)
        self.add_str_config("msg_manual_ios", None)
        self.add_str_config("msg_manual_windows", None)
        self.add_str_config("msg_manual_mac", None)
        self.add_str_config("msg_manual_linux", None)
        self.add_str_config("msg_faq", None)
        self.add_int_config("min_deposit_amount", 10000)
        self.add_int_config("reminder_notification_days", 3)
        self.add_int_config("reminder_notification_usage", 3)
        self.add_int_config("test_sub_days", 1)
        self.add_int_config("test_sub_size_gb", 1)
        self.add_int_config("advanced_renewal_days", 3)
        self.add_int_config("advanced_renewal_usage", 3)
        self.add_int_config("renewal_method", 1)

    def add_wallet(self, telegram_id):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO wallet(telegram_id) VALUES(?)", (telegram_id,))
            self.conn.commit()
            return True
        except Error as e: return False

    def select_wallet(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM wallet")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def find_wallet(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM wallet WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None

    def edit_wallet(self, telegram_id, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"UPDATE wallet SET {key}=? WHERE telegram_id=?", (value, telegram_id,))
                self.conn.commit()
            return True
        except Error as e: return False

    def add_payment(self, payment_id, telegram_id, payment_amount, payment_method, payment_image, created_at):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO payments(id,telegram_id, payment_amount,payment_method,payment_image,created_at) VALUES(?,?,?,?,?,?)",
                (payment_id, telegram_id, payment_amount, payment_method, payment_image, created_at))
            self.conn.commit()
            return True
        except Error as e: return False

    def edit_payment(self, payment_id, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"UPDATE payments SET {key}=? WHERE id=?", (value, payment_id))
                self.conn.commit()
            return True
        except Error as e: return False

    def find_payment(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM payments WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None
        
    def select_payments(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM payments")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None
    
    def select_servers(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM servers")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None
        
    def add_server(self, url, user_limit, title=None, description=None, status=True, default_server=False):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO servers(url,title,description,user_limit,status,default_server) VALUES(?,?,?,?,?,?)",
                (url, title, description, user_limit, status, default_server))
            self.conn.commit()
            return True
        except Error as e: return False
    
    def edit_server(self, server_id, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"UPDATE servers SET {key}=? WHERE id=?", (value, server_id))
                self.conn.commit()
            return True
        except Error as e: return False
    
    def find_server(self, **kwargs):
        if len(kwargs) != 1: return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM servers WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0: return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e: return None
        
    def delete_server(self, **kwargs):
        if len(kwargs) != 1: return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM servers WHERE {key}=?", (value,))
                self.conn.commit()
            return True
        except Error as e: return False
        
    def backup_to_json(self, backup_dir):
        try:
            backup_data = {}
            tables = ['users', 'plans', 'orders', 'order_subscriptions', 'non_order_subscriptions',
                      'str_config', 'int_config', 'bool_config', 'wallet', 'payments', 'servers', 'discount_codes']
            for table in tables:
                cur = self.conn.cursor()
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                table_data = []
                for row in rows:
                    columns = [column[0] for column in cur.description]
                    table_data.append(dict(zip(columns, row)))
                backup_data[table] = table_data
            return backup_data
        except sqlite3.Error as e: return False
        
    def restore_from_json(self, backup_file):
        try:
            cur = self.conn.cursor()
            with open(backup_file, 'r') as json_file:
                backup_data = json.load(json_file)
            if not isinstance(backup_data, dict): return
            self.conn.execute('BEGIN TRANSACTION')
            for table, data in backup_data.items():
                if table == 'version': continue
                for entry in data:
                    if not isinstance(entry, dict): continue
                    keys = ', '.join(entry.keys())
                    placeholders = ', '.join(['?' for _ in entry.values()])
                    values = tuple(entry.values())
                    query = f"INSERT OR REPLACE INTO {table} ({keys}) VALUES ({placeholders})"
                    try: cur.execute(query, values)
                    except: pass
            self.conn.commit()
            return True
        except sqlite3.Error as e: return False
    
USERS_DB_LOC = os.path.join(os.getcwd(), "Database", "hidyBot.db")
USERS_DB = UserDBManager(USERS_DB_LOC)