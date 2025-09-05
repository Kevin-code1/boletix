import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 5,
      duration: '30s',
    },
    purchase: {
      executor: 'constant-vus',
      vus: 50,
      duration: '1m',
      gracefulStop: '10s',
      exec: 'purchaseScenario',
    },
  },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  // smoke test: listar eventos y asientos
  let eventsRes = http.get(`${BASE_URL}/api/events`);
  check(eventsRes, { 'status 200': (r) => r.status === 200 });
  sleep(1);
};

export function purchaseScenario () {
  // login
  const loginRes = http.post(`${BASE_URL}/api/login`, {
    username: 'demo',
    password: 'demo',
  });
  check(loginRes, { 'login status 200': (r) => r.status === 200 });
  // intentar comprar asiento aleatorio
  const eventId = 1;
  const seatId = Math.floor(Math.random() * 20) + 1;
  let purchase = http.post(`${BASE_URL}/api/events/${eventId}/seats/${seatId}/purchase`, {});
  check(purchase, { 'purchase response valid': (r) => r.status === 200 || r.status === 409 });
  sleep(1);
};
