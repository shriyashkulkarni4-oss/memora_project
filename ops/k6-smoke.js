import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 10,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const baseUrl = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const params = __ENV.HOST_HEADER
    ? { headers: { Host: __ENV.HOST_HEADER } }
    : undefined;
  const response = http.get(`${baseUrl}/health`, params);
  check(response, { "health is 200": (result) => result.status === 200 });
  sleep(0.2);
}
