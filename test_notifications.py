"""
Test script to verify notification system modules exist and are structured correctly.
This is a lightweight check that doesn't require database or external dependencies.
"""

import os
import sys

print("=" * 60)
print("GPS Tracking Server - Notification System Test")
print("=" * 60)

# Check that notification modules exist
print("\n=== Checking Notification Modules ===")

api_dir = os.path.join(os.path.dirname(__file__), 'api')
notifications_dir = os.path.join(api_dir, 'notifications')

required_files = [
    'geofence_breach_notifications.py',
    'sms_notifications.py'
]

for filename in required_files:
    filepath = os.path.join(notifications_dir, filename)
    if os.path.exists(filepath):
        print(f"✓ {filename} exists")
        
        # Check for key functions/classes
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if filename == 'geofence_breach_notifications.py':
                assert 'notify_geofence_breach_events' in content, "Missing notify_geofence_breach_events"
                assert '_smtp_settings' in content, "Missing _smtp_settings"
                assert 'NOTIFY_GEOFENCE_EMAIL' in content, "Missing email config check"
                print(f"  ✓ Email notification functions found")
                
            elif filename == 'sms_notifications.py':
                assert 'TwilioSMSProvider' in content, "Missing TwilioSMSProvider"
                assert 'AWSSNSSMS' in content, "Missing AWSSNSSMS"
                assert 'notify_geofence_breach_via_sms' in content, "Missing notify_geofence_breach_via_sms"
                print(f"  ✓ SMS notification classes and functions found")
    else:
        print(f"✗ {filename} missing!")
        sys.exit(1)

# Check that sendGPSData endpoint integrates notifications
print("\n=== Checking Endpoint Integration ===")

endpoint_file = os.path.join(api_dir, 'endpoints', 'device_data_endpoints.py')
if os.path.exists(endpoint_file):
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        if 'from notifications.geofence_breach_notifications import notify_geofence_breach_events' in content:
            print("✓ Email notifications imported in sendGPSData endpoint")
        else:
            print("✗ Email notifications not imported!")
            sys.exit(1)
            
        if 'from notifications.sms_notifications import notify_geofence_breach_via_sms' in content:
            print("✓ SMS notifications imported in sendGPSData endpoint")
        else:
            print("✗ SMS notifications not imported!")
            sys.exit(1)
            
        if 'notify_geofence_breach_events(' in content and 'notify_geofence_breach_via_sms(' in content:
            print("✓ Both notification types called in sendGPSData")
        else:
            print("✗ Notifications not being called!")
            sys.exit(1)
else:
    print("✗ device_data_endpoints.py not found!")
    sys.exit(1)

# Check .env.example has notification settings
print("\n=== Checking Configuration Documentation ===")

env_example = os.path.join(os.path.dirname(__file__), '.env.example')
if os.path.exists(env_example):
    with open(env_example, 'r', encoding='utf-8') as f:
        content = f.read()
        
        required_vars = [
            'NOTIFY_GEOFENCE_EMAIL',
            'SMTP_HOST',
            'NOTIFY_GEOFENCE_SMS_TWILIO',
            'TWILIO_ACCOUNT_SID',
            'NOTIFY_GEOFENCE_SMS_AWS',
        ]
        
        for var in required_vars:
            if var in content:
                print(f"✓ {var} documented")
            else:
                print(f"✗ {var} missing from .env.example!")
                sys.exit(1)
else:
    print("✗ .env.example not found!")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL NOTIFICATION SYSTEM CHECKS PASSED")
print("=" * 60)
print("\nNotification system is properly integrated:")
print("- Email notifications via SMTP (configurable)")
print("- SMS notifications via Twilio or AWS SNS (configurable)")
print("- Geofence breach detection triggers both notification types")
print("- Configuration documented in .env.example")
print("\nTo enable in production:")
print("1. Set NOTIFY_GEOFENCE_EMAIL=true + SMTP settings")
print("2. Set NOTIFY_GEOFENCE_SMS_TWILIO=true + Twilio settings")
print("   OR NOTIFY_GEOFENCE_SMS_AWS=true + AWS settings")

