#!/usr/bin/env node
/**
 * WebSocket Endpoint Test - Device and User connections
 */
const WebSocket = require('ws');

async function testDeviceEndpoint() {
  console.log('\n--- Testing Device WebSocket Endpoint ---');
  
  return new Promise((resolve) => {
    const ws = new WebSocket('ws://localhost:8000/v1/ws/devices/1?token=test-device-token');
    
    let connected = false;
    
    ws.on('open', () => {
      connected = true;
      console.log('✓ Connected to /ws/devices/1');
      
      // Send ping
      ws.send(JSON.stringify({ type: 'ping' }));
      console.log('✓ Sent ping');
      
      // Send location update
      setTimeout(() => {
        ws.send(JSON.stringify({
          type: 'location_update',
          data: {
            device_id: 1,
            latitude: 40.7128,
            longitude: -74.0060,
            speed: 45.5,
            heading: 90
          }
        }));
        console.log('✓ Sent location_update');
      }, 500);
    });
    
    ws.on('message', (data) => {
      const msg = JSON.parse(data);
      console.log(`✓ Received: ${JSON.stringify(msg).substring(0, 60)}...`);
      
      // Close after first message
      setTimeout(() => {
        ws.close();
        resolve(connected);
      }, 500);
    });
    
    ws.on('error', (err) => {
      console.error('✗ Error:', err.message);
      resolve(false);
    });
    
    setTimeout(() => {
      if (!connected) {
        console.error('✗ Connection timeout');
        ws.close();
        resolve(false);
      }
    }, 3000);
  });
}

async function testUserEndpoint() {
  console.log('\n--- Testing User WebSocket Endpoint ---');
  
  return new Promise((resolve) => {
    const ws = new WebSocket('ws://localhost:8000/v1/ws/users/1?token=test-user-token');
    
    let connected = false;
    
    ws.on('open', () => {
      connected = true;
      console.log('✓ Connected to /ws/users/1');
      
      // Send ping
      ws.send(JSON.stringify({ type: 'ping' }));
      console.log('✓ Sent ping');
    });
    
    ws.on('message', (data) => {
      const msg = JSON.parse(data);
      console.log(`✓ Received: ${JSON.stringify(msg).substring(0, 60)}...`);
      
      // Close after first message
      setTimeout(() => {
        ws.close();
        resolve(connected);
      }, 500);
    });
    
    ws.on('error', (err) => {
      console.error('✗ Error:', err.message);
      resolve(false);
    });
    
    setTimeout(() => {
      if (!connected) {
        console.error('✗ Connection timeout');
        ws.close();
        resolve(false);
      }
    }, 3000);
  });
}

async function testGeofenceEndpoint() {
  console.log('\n--- Testing Geofence WebSocket Endpoint ---');
  
  return new Promise((resolve) => {
    const ws = new WebSocket('ws://localhost:8000/v1/ws/geofence/1?token=test-user-token');
    
    let connected = false;
    
    ws.on('open', () => {
      connected = true;
      console.log('✓ Connected to /ws/geofence/1');
      
      // Send ping
      ws.send(JSON.stringify({ type: 'ping' }));
      console.log('✓ Sent ping');
    });
    
    ws.on('message', (data) => {
      const msg = JSON.parse(data);
      console.log(`✓ Received: ${JSON.stringify(msg).substring(0, 60)}...`);
      
      // Close after first message
      setTimeout(() => {
        ws.close();
        resolve(connected);
      }, 500);
    });
    
    ws.on('error', (err) => {
      console.error('✗ Error:', err.message);
      resolve(false);
    });
    
    setTimeout(() => {
      if (!connected) {
        console.error('✗ Connection timeout');
        ws.close();
        resolve(false);
      }
    }, 3000);
  });
}

async function main() {
  console.log('========================================');
  console.log('WebSocket Endpoint Testing');
  console.log('========================================');
  
  const device = await testDeviceEndpoint();
  const user = await testUserEndpoint();
  const geofence = await testGeofenceEndpoint();
  
  console.log('\n========================================');
  console.log('Results:');
  console.log(`  Device Endpoint:    ${device ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`  User Endpoint:      ${user ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`  Geofence Endpoint:  ${geofence ? '✓ PASS' : '✗ FAIL'}`);
  console.log('========================================\n');
  
  process.exit(device && user && geofence ? 0 : 1);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
