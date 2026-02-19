#!/usr/bin/env node
/**
 * Full Integration Test: Device sends location → Server broadcasts → Users receive
 */
const WebSocket = require('ws');

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testFullFlow() {
  console.log('\n========== FULL INTEGRATION TEST ==========\n');
  console.log('Scenario: Device sends location → Users receive real-time updates\n');

  // Step 1: Connect two user listeners
  console.log('STEP 1: Connect 2 user listeners to /ws/users/1');
  const user1 = new WebSocket('ws://localhost:8000/v1/ws/users/1?token=user-token-1');
  const user2 = new WebSocket('ws://localhost:8000/v1/ws/users/1?token=user-token-2');
  
  let user1Connected = false;
  let user2Connected = false;
  let user1Received = false;
  let user2Received = false;

  user1.on('open', () => {
    user1Connected = true;
    console.log('  ✓ User 1 connected');
  });

  user2.on('open', () => {
    user2Connected = true;
    console.log('  ✓ User 2 connected');
  });

  user1.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'location_update') {
      user1Received = true;
      console.log(`  ✓ User 1 received location: lat=${msg.data.latitude}, lon=${msg.data.longitude}`);
    }
  });

  user2.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'location_update') {
      user2Received = true;
      console.log(`  ✓ User 2 received location: lat=${msg.data.latitude}, lon=${msg.data.longitude}`);
    }
  });

  // Wait for users to connect
  await sleep(1000);
  
  if (!user1Connected || !user2Connected) {
    console.error('✗ Failed to connect users');
    process.exit(1);
  }

  // Step 2: Connect device
  console.log('\nSTEP 2: Connect device to /ws/devices/1');
  const device = new WebSocket('ws://localhost:8000/v1/ws/devices/1?token=device-token');
  let deviceConnected = false;

  device.on('open', () => {
    deviceConnected = true;
    console.log('  ✓ Device connected');

    // Send location update
    console.log('\nSTEP 3: Device sends location update');
    device.send(JSON.stringify({
      type: 'location_update',
      data: {
        device_id: 1,
        latitude: 51.5074,
        longitude: -0.1278,
        speed: 42.5,
        heading: 180
      }
    }));
    console.log('  ✓ Location sent: lat=51.5074, lon=-0.1278');
  });

  device.on('error', (err) => {
    console.error('✗ Device error:', err.message);
  });

  // Wait for all messages to be received
  await sleep(2000);

  device.close();
  user1.close();
  user2.close();

  // Results
  console.log('\n========== RESULTS ==========\n');
  console.log(`Device connected:      ${deviceConnected ? '✓' : '✗'}`);
  console.log(`User 1 connected:      ${user1Connected ? '✓' : '✗'}`);
  console.log(`User 2 connected:      ${user2Connected ? '✓' : '✗'}`);
  console.log(`User 1 received loc:   ${user1Received ? '✓' : '✗'}`);
  console.log(`User 2 received loc:   ${user2Received ? '✓' : '✗'}`);
  console.log();

  if (deviceConnected && user1Connected && user2Connected && user1Received && user2Received) {
    console.log('✓ FULL INTEGRATION TEST PASSED');
    console.log('  Device → Server Broadcast → Multiple Users working correctly!\n');
    process.exit(0);
  } else {
    console.log('✗ FULL INTEGRATION TEST FAILED\n');
    process.exit(1);
  }
}

testFullFlow().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});

// Timeout failsafe
setTimeout(() => {
  console.error('\n✗ Test timeout - no response from server');
  process.exit(1);
}, 10000);
