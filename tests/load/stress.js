/**
 * Stress Test - Load test to find breaking points
 * 
 * Run with: k6 run tests/load/stress.js
 * 
 * This test:
 * - Gradually increases load
 * - Finds the breaking point
 * - Tests recovery after high load
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const requestDuration = new Trend('request_duration');
const rateLimitHits = new Counter('rate_limit_hits');

// Stress test stages
export const options = {
    stages: [
        { duration: '1m', target: 10 },   // Ramp up to 10 users over 1 minute
        { duration: '2m', target: 10 },   // Stay at 10 users for 2 minutes
        { duration: '1m', target: 50 },   // Ramp up to 50 users over 1 minute
        { duration: '2m', target: 50 },   // Stay at 50 users for 2 minutes
        { duration: '1m', target: 100 },  // Ramp up to 100 users over 1 minute
        { duration: '2m', target: 100 },  // Stay at 100 users for 2 minutes
        { duration: '2m', target: 0 },    // Ramp down to 0 users
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'],  // 95% of requests should be below 2s
        errors: ['rate<0.1'],  // Error rate should be below 10%
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Scenarios to test
const scenarios = [
    { name: 'health_live', path: '/health/live', method: 'GET' },
    { name: 'health_ready', path: '/health/ready', method: 'GET' },
    { name: 'items_list', path: '/api/v1/items', method: 'GET' },
    { name: 'items_list_paginated', path: '/api/v1/items?page=1&size=10', method: 'GET' },
];

export default function () {
    // Randomly select a scenario
    const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
    
    let response;
    const url = `${BASE_URL}${scenario.path}`;
    
    if (scenario.method === 'GET') {
        response = http.get(url);
    } else if (scenario.method === 'POST') {
        response = http.post(url, JSON.stringify(scenario.body), {
            headers: { 'Content-Type': 'application/json' },
        });
    }
    
    requestDuration.add(response.timings.duration);
    
    // Check for rate limiting
    if (response.status === 429) {
        rateLimitHits.add(1);
        
        // Check rate limit response format (RFC 7807)
        check(response, {
            'rate limit response has Retry-After header': (r) => r.headers['Retry-After'] !== undefined,
            'rate limit response is RFC 7807 format': (r) => {
                try {
                    let body = JSON.parse(r.body);
                    return body.type && body.title && body.status === 429;
                } catch (e) {
                    return false;
                }
            },
        });
    } else {
        // Normal response checks
        let passed = check(response, {
            'status is 2xx': (r) => r.status >= 200 && r.status < 300,
            'response time < 2000ms': (r) => r.timings.duration < 2000,
        });
        errorRate.add(!passed);
    }
    
    // Small random sleep to simulate real user behavior
    sleep(Math.random() * 0.5);
}

export function handleSummary(data) {
    console.log('\n=== Stress Test Summary ===');
    console.log(`Total requests: ${data.metrics.http_reqs.values.count}`);
    console.log(`Error rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%`);
    console.log(`Rate limit hits: ${data.metrics.rate_limit_hits ? data.metrics.rate_limit_hits.values.count : 0}`);
    console.log(`P95 response time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
    console.log(`Max response time: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms`);
    
    return {
        'tests/load/stress-summary.json': JSON.stringify(data, null, 2),
    };
}
