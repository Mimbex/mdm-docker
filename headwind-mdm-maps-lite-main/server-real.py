#!/usr/bin/env python3
from flask import Flask, jsonify, send_file
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'hmdm',
    'user': 'hmdm', 
    'password': 'topsecret'
}

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/locations')
def get_locations():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get devices with JSON info
        cur.execute("""
            SELECT id, number, description, imei, info 
            FROM devices 
            WHERE info IS NOT NULL 
            ORDER BY number
        """)
        devices = cur.fetchall()
        
        result = []
        
        for device in devices:
            try:
                # Parse the JSON info
                info_json = json.loads(device['info'])
                
                # Try different possible location field structures
                lat, lon = None, None
                
                # Check various possible JSON structures for coordinates
                if 'location' in info_json and info_json['location']:
                    loc = info_json['location']
                    if isinstance(loc, dict):
                        lat = loc.get('latitude') or loc.get('lat')
                        lon = loc.get('longitude') or loc.get('lon')
                
                # Check root level coordinates
                if not lat:
                    lat = info_json.get('latitude') or info_json.get('lat')
                    lon = info_json.get('longitude') or info_json.get('lon')
                
                # Check GPS object
                if not lat and 'gps' in info_json:
                    gps = info_json['gps']
                    if isinstance(gps, dict):
                        lat = gps.get('latitude') or gps.get('lat')
                        lon = gps.get('longitude') or gps.get('lon')
                
                # Only include devices with valid coordinates
                if lat and lon and lat != 0 and lon != 0:
                    result.append({
                        'id': device['id'],
                        'number': device['number'],
                        'description': device['description'] or 'Unknown Device',
                        'imei': device['imei'],
                        'lat': float(lat),
                        'lon': float(lon),
                        'time': datetime.now().isoformat(),
                        'status': 'active'
                    })
                    
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print(f"Error parsing device {device['number']}: {e}")
                continue
        
        cur.close()
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug')
def debug_json():
    """Debug endpoint to examine JSON structure"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT number, info FROM devices WHERE number='MC050'")
        device = cur.fetchone()
        
        if device:
            info_json = json.loads(device['info'])
            # Return just the top-level keys for debugging
            return jsonify({
                'device': device['number'],
                'json_keys': list(info_json.keys()),
                'has_location': 'location' in info_json,
                'has_gps': 'gps' in info_json,
                'location_sample': str(info_json.get('location', 'Not found'))[:200]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({"error": "Device not found"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Headwind MDM Maps - Real GPS Data")
    print("Visit: http://localhost:5001")
    print("Debug: http://localhost:5001/api/debug")
    app.run(debug=True, host='0.0.0.0', port=5002)
