#!/usr/bin/env python3
from flask import Flask, jsonify, send_file, request, render_template_string, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import re
import bcrypt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'hmdm'),
    'user': os.getenv('DB_USER', 'hmdm'),
    'password': os.getenv('DB_PASSWORD', 'topsecret')
}

API_KEY = os.getenv("API_KEY")

@app.before_request
def api_key_auth():
    # Only for API routes
    if request.path.startswith("/api/"):
        # Allow if logged in
        if current_user.is_authenticated:
            return
        # Or allow if valid API key
        if API_KEY and request.headers.get("X-API-KEY") == API_KEY:
            return
        # Otherwise block (don’t redirect)
        return jsonify({"error": "Unauthorized"}), 401


# ──────────────────────────────────────────────────────────────────────────────
# Auth (Flask-Login)
# ──────────────────────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, full_name, is_admin=False):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username, full_name, is_admin FROM map_users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        cur.close(); conn.close()
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['full_name'], user_data.get('is_admin', False))
    except Exception:
        pass
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, username, password_hash, full_name, is_admin FROM map_users WHERE username = %s", (username,))
            user_data = cur.fetchone()

            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                user = User(user_data['id'], user_data['username'], user_data['full_name'], user_data.get('is_admin', False))
                login_user(user)
                cur.execute("UPDATE map_users SET last_login = NOW() WHERE id = %s", (user_data['id'],))
                conn.commit()
                cur.close(); conn.close()
                return redirect(url_for('index'))
            else:
                cur.close(); conn.close()
                flash('Invalid username or password')
        except Exception as e:
            flash(f'Login error: {str(e)}')

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # Serve your frontend (keep this file in the same folder)
    return send_file('index-history.html')

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def parse_gps_from_message(message: str):
    """
    Extract lat/lon from:
      • JSON messages: {"lat":..,"lon":..} or {"latitude":..,"longitude":..}
      • Text messages: "lat=.., lon=.." or "latitude=.., longitude=.."
    Returns (lat, lon) or (None, None)
    """
    if not message:
        return None, None

    # Try JSON first
    try:
        j = json.loads(message)
        lat = j.get('lat') if 'lat' in j else j.get('latitude')
        lon = j.get('lon') if 'lon' in j else (j.get('lng') if 'lng' in j else j.get('longitude'))
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    except Exception:
        pass

    # Fallback: key=value in free text
    num = r'(-?\d+(?:\.\d+)?)'
    patterns = [
        (rf'lat\s*[:=]\s*{num}\s*,?\s*lon\s*[:=]\s*{num}', 'latlon'),
        (rf'latitude\s*[:=]\s*{num}\s*,?\s*longitude\s*[:=]\s*{num}', 'latlon'),
        (rf'lon\s*[:=]\s*{num}\s*,?\s*lat\s*[:=]\s*{num}', 'lonlat'),
        (rf'longitude\s*[:=]\s*{num}\s*,?\s*latitude\s*[:=]\s*{num}', 'lonlat'),
    ]
    for pattern, order in patterns:
        m = re.search(pattern, message, re.IGNORECASE)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            return (a, b) if order == 'latlon' else (b, a)

    return None, None

# ──────────────────────────────────────────────────────────────────────────────
# APIs
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/locations')
@login_required
def get_locations():
    """Return current device locations from devices.info JSON."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, number, description, imei, info
            FROM devices
            WHERE info IS NOT NULL
            ORDER BY number
        """)
        devices = cur.fetchall()
        cur.close(); conn.close()

        result = []
        for d in devices:
            try:
                info_json = json.loads(d['info'])
                loc = (info_json or {}).get('location') or {}
                lat, lon = loc.get('lat'), loc.get('lon')
                ts = loc.get('ts')

                if lat is not None and lon is not None and float(lat) != 0 and float(lon) != 0:
                    if ts:
                        try:
                            dt = datetime.fromtimestamp(int(ts) / 1000)
                        except Exception:
                            dt = datetime.utcnow()
                    else:
                        dt = datetime.utcnow()

                    result.append({
                        'id': d['id'],
                        'number': d['number'],
                        'description': d['description'] or 'Unknown Device',
                        'imei': d['imei'],
                        'lat': float(lat),
                        'lon': float(lon),
                        'time': dt.isoformat(),
                        'battery': info_json.get('batteryLevel', 'Unknown'),
                        'status': 'active'
                    })
            except Exception:
                continue

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/device/<device_number>/history')
@login_required
def get_device_history(device_number):
    """Build history from GPS/Network logs + location_history; append current if newer."""
    days = int(request.args.get('days', 7))

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Device lookup
        cur.execute("""
            SELECT id, number, description
            FROM devices
            WHERE number = %s
        """, (device_number,))
        device = cur.fetchone()
        if not device:
            return jsonify({"error": "Device not found"}), 404

        # Time window
        since_ms = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        window_start = datetime.utcnow() - timedelta(days=days)
        history_points = []

        # A) GPS/Network logs (within window)
        cur.execute("""
            SELECT createtime, message
            FROM plugin_devicelog_log
            WHERE deviceid = %s
              AND (
                    message ILIKE '%%GPS location update%%'
                 OR message ILIKE '%%Network location update%%'
                 OR message ILIKE '%%location update%%'
              )
              AND createtime > %s
            ORDER BY createtime ASC
        """, (device['id'], since_ms))

        for entry in cur.fetchall():
            msg = entry['message'] or ''
            lat, lon = parse_gps_from_message(msg)
            if lat is not None and lon is not None:
                t = datetime.fromtimestamp(entry['createtime'] / 1000.0)
                provider = (
                    'gps' if 'gps' in msg.lower()
                    else 'network' if 'network' in msg.lower()
                    else 'log'
                )
                history_points.append({
                    'lat': float(lat),
                    'lon': float(lon),
                    'time': t.isoformat(),
                    'type': 'log',
                    'provider': provider
                })

        # B) location_history points (fills gaps)
        cur.execute("""
            SELECT lat, lon, recorded_at, source
            FROM location_history
            WHERE device_id = %s
              AND recorded_at >= %s
            ORDER BY recorded_at ASC
        """, (device['id'], window_start))

        for row in cur.fetchall():
            try:
                history_points.append({
                    'lat': float(row['lat']),
                    'lon': float(row['lon']),
                    'time': row['recorded_at'].isoformat(),
                    'type': 'history',
                    'provider': (row.get('source') if isinstance(row, dict) else 'history') or 'history'
                })
            except (TypeError, ValueError):
                continue

        # C) Append live current from devices.info if newer & within window,
	#    and PERSIST it into location_history (once per ~2 minutes)
        last_ts = None
        if history_points:
            try:
                last_ts = max(datetime.fromisoformat(p['time']) for p in history_points)
            except Exception:
                last_ts = None

        cur.execute("SELECT info FROM devices WHERE id = %s", (device['id'],))
        row = cur.fetchone()
        if row and row.get('info'):
            try:
                info_json = json.loads(row['info']) or {}
                loc = info_json.get('location') or {}
                cur_lat = loc.get('lat')
                cur_lon = loc.get('lon')
                cur_ts_ms = loc.get('ts')

                if cur_lat is not None and cur_lon is not None:
                    cur_dt = datetime.fromtimestamp(cur_ts_ms / 1000.0) if cur_ts_ms else datetime.utcnow()

                    if cur_dt >= window_start and (last_ts is None or cur_dt > last_ts):
                        # 1) Return it in the API response
                        history_points.append({
                            'lat': float(cur_lat),
                            'lon': float(cur_lon),
                            'time': cur_dt.isoformat(),
                            'type': 'current',
                            'provider': 'current'
                        })

                        # 2) Also PERSIST it into location_history if we haven't recently
                        #    stored a point for this device (<= ~2 minutes window)
                        try:
                            cur.execute("""
                                INSERT INTO location_history (device_id, lat, lon, recorded_at, source)
                                SELECT %s, %s, %s, %s, %s
                                WHERE NOT EXISTS (
                                  SELECT 1
                                  FROM location_history
                                  WHERE device_id = %s
                                    AND recorded_at >= %s::timestamp - INTERVAL '2 minutes'
                                )
                            """, (
                                device['id'], float(cur_lat), float(cur_lon), cur_dt, 'snapshot',
                                device['id'], cur_dt
                            ))
                            conn.commit()
                        except Exception as _e:
                            # don't break the API if insert fails; just log
                            print(f"[history snapshot insert skipped] {str(_e)}")
            except Exception:
                pass

        # D) Sort and de-duplicate
        history_points.sort(key=lambda p: p['time'])
        seen = set()
        dedup = []
        for p in history_points:
            key = (round(p['lat'], 6), round(p['lon'], 6), p['time'])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(p)

        cur.close()
        conn.close()

        return jsonify({
            'device': {
                'number': device['number'],
                'description': device['description']
            },
            'history': dedup,
            'total_points': len(dedup)
        })

    except Exception as e:
        print(f"Error getting device history: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/devices')
@login_required
def get_devices():
    """
    List devices and show how many *usable* location points they have,
    combining:
      - recent location logs (any message containing 'location')
      - recent location_history rows (last 30 days)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                d.number,
                d.description,
                COALESCE(lc.log_updates, 0) + COALESCE(hc.hist_updates, 0) AS gps_updates,
                COALESCE(lc.log_updates, 0) AS log_updates,
                COALESCE(hc.hist_updates, 0) AS hist_updates
            FROM devices d
            LEFT JOIN (
                SELECT deviceid, COUNT(*) AS log_updates
                FROM plugin_devicelog_log
                WHERE message ILIKE '%%location%%'
                GROUP BY deviceid
            ) lc ON lc.deviceid = d.id
            LEFT JOIN (
                SELECT device_id, COUNT(*) AS hist_updates
                FROM location_history
                WHERE recorded_at >= NOW() - INTERVAL '30 days'
                GROUP BY device_id
            ) hc ON hc.device_id = d.id
            WHERE d.info IS NOT NULL
            ORDER BY d.description, d.number
        """)

        devices = cur.fetchall()
        cur.close()
        conn.close()

        result = []
        for d in devices:
            total = d['gps_updates'] or 0
            name_display = d['description'] or d['number']
            if total > 0:
                name_display += f" ({total} points: {d['hist_updates'] or 0} history, {d['log_updates'] or 0} logs)"
            else:
                name_display += " (No location points yet)"

            result.append({
                'number': d['number'],
                'name': name_display,
                'gps_count': total,
                'log_count': d['log_updates'] or 0,
                'history_count': d['hist_updates'] or 0,
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot endpoint (persist current GPS from all devices)
# ──────────────────────────────────────────────────────────────────────────────
@app.route("/api/snapshot_all", methods=["POST"])
def snapshot_all_devices():
    """
    For each device:
      - read devices.info -> location.{lat,lon,ts}
      - if newer than ~2 minutes, insert into location_history
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, number, info FROM devices WHERE info IS NOT NULL")
        devices = cur.fetchall()

        inserted = 0
        now_utc = datetime.utcnow()

        for d in devices:
            try:
                info_json = json.loads(d.get("info") or "{}")
                loc = (info_json or {}).get("location") or {}
                lat = loc.get("lat")
                lon = loc.get("lon")
                ts_ms = loc.get("ts")

                if lat is None or lon is None:
                    continue

                cur_dt = datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else now_utc

                cur.execute("""
                    INSERT INTO location_history (device_id, lat, lon, recorded_at, source)
                    SELECT %s, %s, %s, %s, %s
                    WHERE NOT EXISTS (
                      SELECT 1 FROM location_history
                      WHERE device_id = %s
                        AND recorded_at >= %s::timestamp - INTERVAL '2 minutes'
                    )
                """, (d["id"], float(lat), float(lon), cur_dt, "snapshot_all", d["id"], cur_dt))

                if cur.rowcount > 0:
                    inserted += 1

            except Exception as _e:
                print(f"[snapshot_all skip device {d.get('number')}] {_e}")

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "inserted": inserted}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Admin UI (users CRUD)
# ──────────────────────────────────────────────────────────────────────────────
from functools import wraps
from flask import abort

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.path))
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

@app.route('/admin')
@login_required
@admin_required
def admin_home():
    return redirect(url_for('admin_users'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, username, full_name, is_admin, created_at, last_login
            FROM map_users
            ORDER BY username
        """)
        users = cur.fetchall()
        cur.close(); conn.close()
        return render_template_string(USER_MANAGEMENT_TEMPLATE, users=users)
    except Exception as e:
        flash(f"Error loading users: {e}")
        return render_template_string(USER_MANAGEMENT_TEMPLATE, users=[]), 500

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_users_add():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        full_name = (request.form.get('full_name') or '').strip()
        is_admin = True if request.form.get('is_admin') == 'on' else False

        if not username or not password:
            flash('Username and password are required')
            return render_template_string(ADD_USER_TEMPLATE)

        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # ensure unique username
            cur.execute("SELECT 1 FROM map_users WHERE username=%s", (username,))
            if cur.fetchone():
                cur.close(); conn.close()
                flash('Username already exists')
                return render_template_string(ADD_USER_TEMPLATE)

            pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("""
                INSERT INTO map_users (username, password_hash, full_name, is_admin, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING id
            """, (username, pw_hash, full_name, is_admin))
            conn.commit()
            cur.close(); conn.close()
            flash(f'User "{username}" created')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Error creating user: {e}')
            return render_template_string(ADD_USER_TEMPLATE), 500

    # GET
    return render_template_string(ADD_USER_TEMPLATE)

@app.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def admin_users_reset_password(user_id):
    new_pw = request.form.get('new_password') or ''
    if len(new_pw) < 6:
        flash('Password must be at least 6 characters')
        return redirect(url_for('admin_users'))
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        pw_hash = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("UPDATE map_users SET password_hash=%s WHERE id=%s", (pw_hash, user_id))
        conn.commit()
        cur.close(); conn.close()
        flash('Password updated')
    except Exception as e:
        flash(f'Error resetting password: {e}')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_users_delete(user_id):
    # prevent deleting yourself
    if user_id == getattr(current_user, "id", None):
        flash("You can't delete your own account")
        return redirect(url_for('admin_users'))
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM map_users WHERE id=%s", (user_id,))
        conn.commit()
        cur.close(); conn.close()
        flash('User deleted')
    except Exception as e:
        flash(f'Error deleting user: {e}')
    return redirect(url_for('admin_users'))



# ──────────────────────────────────────────────────────────────────────────────
# Inline templates (login + admin)
# ──────────────────────────────────────────────────────────────────────────────
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Headwind MDM Maps</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
        .login-container { background:white; padding:40px; border-radius:10px; box-shadow:0 10px 25px rgba(0,0,0,0.2); width:100%; max-width:400px; }
        h1 { text-align:center; color:#333; margin-bottom:30px; }
        .form-group { margin-bottom:20px; }
        label { display:block; margin-bottom:5px; color:#555; font-weight:bold; }
        input[type="text"], input[type="password"] { width:100%; padding:12px; border:1px solid #ddd; border-radius:5px; box-sizing:border-box; font-size:14px; }
        input[type="text"]:focus, input[type="password"]:focus { outline:none; border-color:#667eea; }
        button { width:100%; padding:12px; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; border:none; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer; transition:transform .2s; }
        button:hover { transform: translateY(-2px); }
        .alert { padding:12px; margin-bottom:20px; border-radius:5px; background:#f8d7da; color:#721c24; border:1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🗺️ MDM Maps Login</h1>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
'''

USER_MANAGEMENT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>User Management - MDM Maps</title>
    <style>
        body { font-family: Arial, sans-serif; margin:0; padding:20px; background:#f5f5f5; }
        .container { max-width:1200px; margin:0 auto; background:white; padding:30px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1); }
        h1 { color:#333; margin-bottom:20px; }
        .header { display:flex; justify-content:space-between; align-items:center; margin-bottom:30px; }
        .btn { padding:10px 20px; border:none; border-radius:5px; cursor:pointer; text-decoration:none; display:inline-block; font-size:14px; }
        .btn-primary { background:#667eea; color:white; }
        .btn-danger { background:#e74c3c; color:white; }
        .btn-secondary { background:#95a5a6; color:white; }
        .btn:hover { opacity:.9; }
        table { width:100%; border-collapse:collapse; margin-top:20px; }
        th,td { padding:12px; text-align:left; border-bottom:1px solid #ddd; }
        th { background:#f8f9fa; font-weight:bold; color:#333; }
        tr:hover { background:#f8f9fa; }
        .badge { padding:4px 8px; border-radius:3px; font-size:12px; font-weight:bold; }
        .badge-admin { background:#3498db; color:white; }
        .badge-user { background:#95a5a6; color:white; }
        .alert { padding:12px; margin-bottom:20px; border-radius:5px; background:#d1ecf1; color:#0c5460; border:1px solid #bee5eb; }
        .actions { display:flex; gap:10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👥 User Management</h1>
            <div>
                <a href="/" class="btn btn-secondary">← Back to Maps</a>
                <a href="/admin/users/add" class="btn btn-primary">+ Add User</a>
            </div>
        </div>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <table>
            <thead>
                <tr>
                    <th>Username</th>
                    <th>Full Name</th>
                    <th>Role</th>
                    <th>Created</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for user in users %}
                <tr>
                    <td>{{ user.username }}</td>
                    <td>{{ user.full_name or '-' }}</td>
                    <td>
                        {% if user.is_admin %}
                            <span class="badge badge-admin">Admin</span>
                        {% else %}
                            <span class="badge badge-user">User</span>
                        {% endif %}
                    </td>
                    <td>{{ user.created_at.strftime('%Y-%m-%d') if user.created_at else '-' }}</td>
                    <td>{{ user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never' }}</td>
                    <td>
                        <div class="actions">
                            <button onclick="resetPassword({{ user.id }}, '{{ user.username }}')" class="btn btn-primary" style="font-size:12px; padding:6px 12px;">Reset Password</button>
                            <form method="POST" action="/admin/users/{{ user.id }}/delete" style="display:inline;" onsubmit="return confirm('Delete user {{ user.username }}?')">
                                <button type="submit" class="btn btn-danger" style="font-size:12px; padding:6px 12px;">Delete</button>
                            </form>
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
        function resetPassword(userId, username) {
            const newPassword = prompt(`Enter new password for ${username}:`);
            if (newPassword) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/admin/users/${userId}/reset-password`;

                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'new_password';
                input.value = newPassword;

                form.appendChild(input);
                document.body.appendChild(form);
                form.submit();
            }
        }
    </script>
</body>
</html>
'''

ADD_USER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Add User - MDM Maps</title>
    <style>
        body { font-family: Arial, sans-serif; background:#f5f5f5; display:flex; justify-content:center; align-items:center; min-height:100vh; margin:0; padding:20px; }
        .form-container { background:white; padding:40px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1); width:100%; max-width:500px; }
        h1 { color:#333; margin-bottom:30px; }
        .form-group { margin-bottom:20px; }
        label { display:block; margin-bottom:5px; color:#555; font-weight:bold; }
        input[type="text"], input[type="password"] { width:100%; padding:12px; border:1px solid #ddd; border-radius:5px; box-sizing:border-box; font-size:14px; }
        input[type="text"]:focus, input[type="password"]:focus { outline:none; border-color:#667eea; }
        .checkbox-group { display:flex; align-items:center; gap:10px; }
        input[type="checkbox"] { width:20px; height:20px; cursor:pointer; }
        .btn { padding:12px 24px; border:none; border-radius:5px; cursor:pointer; font-size:16px; margin-right:10px; }
        .btn-primary { background:#667eea; color:white; }
        .btn-secondary { background:#95a5a6; color:white; text-decoration:none; display:inline-block; }
        .btn:hover { opacity:.9; }
        .alert { padding:12px; margin-bottom:20px; border-radius:5px; background:#f8d7da; color:#721c24; border:1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>➕ Add New User</h1>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div class="form-group">
                <label for="username">Username *</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>

            <div class="form-group">
                <label for="password">Password *</label>
                <input type="password" id="password" name="password" required>
            </div>

            <div class="form-group">
                <label for="full_name">Full Name</label>
                <input type="text" id="full_name" name="full_name">
            </div>

            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="is_admin" name="is_admin">
                    <label for="is_admin" style="margin:0;">Admin User (can manage other users)</label>
                </div>
            </div>

            <div>
                <button type="submit" class="btn btn-primary">Create User</button>
                <a href="/admin/users" class="btn btn-secondary">Cancel</a>
            </div>
        </form>
    </div>
</body>
</html>
'''

# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint (dev only; gunicorn will import app)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 5003))

    print("=" * 50)
    print("🗺️  Headwind MDM Maps - Secure Edition")
    print("=" * 50)
    print(f"Server: http://{host}:{port}")
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("=" * 50)
    print("\n⚠️  Login required to access maps\n")

    app.run(debug=app.config['DEBUG'], host=host, port=port)
