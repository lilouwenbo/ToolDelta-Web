import os
import json
import time
import re
import threading
from werkzeug.security import generate_password_hash, check_password_hash

USER_FILE = None
LOGIN_FAIL_MAP = {}
BAN_MAP = {}
_lock = threading.Lock()

ROLES = {"admin": 10, "user": 1, "guest": 0}

def init_app(app):
    global USER_FILE
    USER_FILE = os.path.join(app.instance_path, "user.json")
    os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)

def _read():
    with _lock:
        return _read_locked()

def _read_locked():
    if not USER_FILE or not os.path.isfile(USER_FILE):
        return []
    try:
        with open(USER_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return [data]
        return data
    except:
        return []

def _write(users):
    with _lock:
        _write_locked(users)

def _write_locked(users):
    # 原子写：先写临时文件再替换，避免写一半崩溃导致用户数据丢失
    tmp = USER_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    os.replace(tmp, USER_FILE)

def validate_password(password):
    if len(password) < 1 or len(password) > 64:
        return False, "密码长度需1-64位"
    return True, ""

def is_configured():
    users = _read()
    return len(users) > 0

def get_users():
    return _read()

def get_user(username):
    for u in _read():
        if u.get("username") == username:
            return u
    return None

def verify_username_password(username, password):
    u = get_user(username)
    if u and check_password_hash(u.get("password_hash", ""), password):
        return u
    return None

def verify_password(password):
    users = _read()
    for u in users:
        if u.get("role") == 10 and check_password_hash(u.get("password_hash", ""), password):
            return u
    return None

def setup_user(username, password, role=10):
    with _lock:
        users = _read_locked()
        users.append({
            "username": username,
            "password_hash": generate_password_hash(password),
            "role": role,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "login_at": ""
        })
        _write_locked(users)

def create_user(username, password, role=1):
    with _lock:
        users = _read_locked()
        if any(u.get("username") == username for u in users):
            return False, "用户名已存在"
        users.append({
            "username": username,
            "password_hash": generate_password_hash(password),
            "role": role,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "login_at": ""
        })
        _write_locked(users)
    return True, ""

def delete_user(username):
    with _lock:
        users = _read_locked()
        users = [u for u in users if u.get("username") != username]
        _write_locked(users)
    return True

def change_password(username, old_password, new_password):
    with _lock:
        users = _read_locked()
        u = next((u for u in users if u.get("username") == username), None)
        if old_password is not None:
            if not u or not check_password_hash(u.get("password_hash", ""), old_password):
                return False, "旧密码错误"
        for u in users:
            if u.get("username") == username:
                u["password_hash"] = generate_password_hash(new_password)
        _write_locked(users)
    return True, ""

def admin_reset_password(username, new_password):
    with _lock:
        users = _read_locked()
        found = False
        for u in users:
            if u.get("username") == username:
                u["password_hash"] = generate_password_hash(new_password)
                found = True
        if found:
            _write_locked(users)
        return found

def reset_panel():
    if USER_FILE and os.path.isfile(USER_FILE):
        os.remove(USER_FILE)

def update_login_time(username):
    with _lock:
        users = _read_locked()
        for u in users:
            if u.get("username") == username:
                u["login_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _write_locked(users)

def get_admin_username():
    for u in _read():
        if u.get("role") == 10:
            return u.get("username", "")
    return ""

# ─── Login rate limiting ───

def check_login_rate(ip):
    with _lock:
        now = time.time()
        if ip in BAN_MAP:
            if now - BAN_MAP[ip] < 600:
                return False, "IP已被临时封禁，请10分钟后重试"
            del BAN_MAP[ip]
        fails = LOGIN_FAIL_MAP.get(ip, [])
        fails = [t for t in fails if now - t < 300]
        if len(fails) >= 10:
            BAN_MAP[ip] = now
            LOGIN_FAIL_MAP[ip] = []
            return False, "登录失败次数过多，IP已被封禁10分钟"
        LOGIN_FAIL_MAP[ip] = fails
        return True, ""

def record_login_fail(ip):
    with _lock:
        now = time.time()
        fails = LOGIN_FAIL_MAP.get(ip, [])
        fails.append(now)
        LOGIN_FAIL_MAP[ip] = fails

def clear_login_fails(ip):
    with _lock:
        LOGIN_FAIL_MAP.pop(ip, None)
