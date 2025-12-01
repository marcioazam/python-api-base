/**
 * Smoke Test - Basic load test to verify API is working
 * 
 * Run with: k6 run tests/load/smoke.js
 * 
 * This test verifies:
 * - API is responding
 * - Health endpoints work
 * - Basic CRUD operations work
 * - Response times are acceptable
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const healthCheckDuration = new Trend('health_check_duration');
const itemsListDuration = new Trend('items_list_duration');

// Test configuration
export const options = {
    vus: 1,  // 1 virtual user
    duration: '30s',  // Run for 30 seconds
    thresholds: {
        http_req_duration: ['p(95)<500'],  // 95% of requests should be below 500ms
        errors: ['rate<0.01'],  // Error rate should be below 1%
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
    // Test 1: Health check - liveness
    let liveResponse = http.get(`${BASE_URL}/health/live`);
    healthCheckDuration.add(liveResponse.timings.duration);
    
    let liveCheck = check(liveResponse, {
        'health/live status is 200': (r) => r.status === 200,
        'health/live response time < 200ms': (r) => r.timings.duration < 200,
    });
    errorRate.add(!liveCheck);

    // Test 2: Health check - readiness
    let readyResponse = http.get(`${BASE_URL}/health/ready`);
    healthCheckDuration.add(readyResponse.timings.duration);
    
    let readyCheck = check(readyResponse, {
        'health/ready status is 200': (r) => r.status === 200,
        'health/ready response time < 500ms': (r) => r.timings.duration < 500,
    });
    errorRate.add(!readyCheck);

    // Test 3: List items endpoint
    let itemsResponse = http.get(`${BASE_URL}/api/v1/items`);
    itemsListDuration.add(itemsResponse.timings.duration);
    
    let itemsCheck = check(itemsResponse, {
        'items list status is 200': (r) => r.status === 200,
        'items list response time < 500ms': (r) => r.timings.duration < 500,
        'items list has items array': (r) => {
            try {
                let body = JSON.parse(r.body);
                return Array.isArray(body.items);
            } catch (e) {
                return false;
            }
        },
    });
    errorRate.add(!itemsCheck);

    // Test 4: OpenAPI documentation
    let docsResponse = http.get(`${BASE_URL}/openapi.json`);
    
    let docsCheck = check(docsResponse, {
        'openapi.json status is 200': (r) => r.status === 200,
        'openapi.json is valid JSON': (r) => {
            try {
                JSON.parse(r.body);
                return true;
            } catch (e) {
                return false;
            }
        },
    });
    errorRate.add(!docsCheck);

    sleep(1);  // Wait 1 second between iterations
}

export function handleSummary(data) {
    return {
        'tests/load/smoke-summary.json': JSON.stringify(data, null, 2),
    };
}
