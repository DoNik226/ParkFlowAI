import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = 'http://127.0.0.1:8000';

export const options = {
  vus: 50,
  duration: '1m',

  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

export function setup() {

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      username: 'admin',
      password: 'adminadminadmin',
    }),
    {
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  check(loginRes, {
    'login success': (r) => r.status === 200,
  });

  return {
    token: loginRes.json('access_token'),
  };
}

export default function (data) {

  const res = http.get(
    `${BASE_URL}/parkings`,
    {
      headers: {
        Authorization: `Bearer ${data.token}`,
      },
    }
  );

  check(res, {
    'parkings loaded': (r) => r.status === 200,
  });

  sleep(1);
}