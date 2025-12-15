#!/usr/bin/env python3
from flask import Flask, jsonify, send_file
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
import random

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
        
        # For testing - get devices and assign random locations
        cur.execute("SELECT id, number, description, imei FROM devices LIMIT 10")
        devices = cur.fetchall()
        
        result = []
        base_lat, base_lon = 40.7128, -74.0060  # New York as example
        
        for i, device in enumerate(devices):
            # Create test locations around a central point
            lat_offset = (random.random() - 0.5) * 0.1  # ~5km radius
            lon_offset = (random.random() - 0.5) * 0.1
            
            result.append({
                'id': device['id'],
                'number': device['number'],
                'description': device['description'] or 'Test Device',
                'imei': device['imei'],
                'lat': base_lat + lat_offset,
                'lon': base_lon + lon_offset,
                'time': datetime.now().isoformat(),
                'status': 'test'
            })
        
        cur.close()
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-db')
def test_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM devices")
        device_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM plugin_deviceinfo_deviceparams_gps")
        gps_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "device_count": device_count,
            "gps_records": gps_count,
            "message": "Database connection successful!"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("🗺️  Starting Headwind MDM Maps Test Server")
    print("📍 Visit: http://localhost:5000")
    print("🔧 Test DB: http://localhost:5000/api/test-db")
    print("⚠️  Note: Using test locations since no GPS data found")
    app.run(debug=True, host='0.0.0.0', port=5000)
