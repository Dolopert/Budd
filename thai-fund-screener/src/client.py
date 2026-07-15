import os
import time

import requests

BASE_URL = "https://api.sec.or.th"
MIN_INTERVAL = 1.0 / 5  # ~5 req/s


class SECClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SEC_API_KEY")
        if not self.api_key:
            raise RuntimeError("SEC_API_KEY environment variable is not set")
        self.session = requests.Session()
        self.session.headers.update({"Ocp-Apim-Subscription-Key": self.api_key})
        self._last_request_at = 0.0
        self.request_count = 0

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

    def get(self, path: str, params: dict | None = None, max_retries: int = 3) -> dict | None:
        url = f"{BASE_URL}{path}"
        for attempt in range(max_retries):
            self._throttle()
            resp = self.session.get(url, params=params, timeout=30)
            self._last_request_at = time.monotonic()
            self.request_count += 1

            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 204:
                return None
            if resp.status_code == 404:
                return None
            if resp.status_code == 429:
                time.sleep(5)
                continue
            resp.raise_for_status()
        return None
