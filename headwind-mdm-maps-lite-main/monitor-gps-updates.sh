#!/bin/bash
echo "Monitoring GPS update frequency (Ctrl+C to stop)..."
while true; do
    clear
    echo "=== GPS Updates in Last 10 Minutes ==="
    PGPASSWORD=topsecret psql -h localhost -U hmdm -d hmdm -c "
    SELECT d.number, COUNT(*) as updates_10min,
           CASE 
               WHEN COUNT(*) = 1 THEN 'Perfect 10-min'
               WHEN COUNT(*) > 1 THEN 'Too frequent'
               WHEN COUNT(*) = 0 THEN 'No updates'
           END as status
    FROM devices d
    LEFT JOIN plugin_devicelog_log l ON l.deviceid = d.id 
        AND l.message LIKE '%GPS location update%'
        AND l.createtime > EXTRACT(EPOCH FROM NOW() - INTERVAL '10 minutes') * 1000
    WHERE d.info IS NOT NULL
    GROUP BY d.number
    ORDER BY updates_10min DESC;"
    
    echo ""
    echo "Next check in 60 seconds..."
    sleep 60
done
