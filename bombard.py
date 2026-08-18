import os
import sys
import requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

BASE_URL = os.environ.get("TARGET_URL", "http://127.0.0.1:8005").rstrip("/")

def send_request(url: str, method: str = "GET", json_data: dict = None):
    try:
        if method == "POST":
            response = requests.post(url, json=json_data, timeout=3)
        else:
            response = requests.get(url, timeout=3)
        return response.status_code
    except requests.exceptions.RequestException:
        return "ERROR"


def run_rate_limit_test(target_url: str, total_requests: int = 100, concurrent_threads: int = 10, method: str = "GET", json_data: dict = None):
    print(f"🚀 Wysyłanie {total_requests} równoległych zapytań do: {target_url}\n" + "=" * 55)

    results = []
    with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        futures = [executor.submit(send_request, target_url, method, json_data) for _ in range(total_requests)]
        for future in as_completed(futures):
            results.append(future.result())

    # Zliczanie wyników kodów HTTP
    counts = Counter(results)

    print("📊 PODSUMOWANIE KODÓW ODPOWIEDZI HTTP:")
    print("-" * 55)
    for code, count in counts.items():
        if code == 200:
            print(f"  [200 OK]                    : {count} zapytań (Przepuszczone)")
        elif code == 401:
            print(f"  [401 Unauthorized]          : {count} zapytań (Nieautoryzowane)")
        elif code == 429:
            print(f"  [429 Too Many Requests]     : {count} zapytań (Zablokowane przez FastAPI Rate Limiter)")
        elif code == 503:
            print(f"  [503 Service Unavailable]   : {count} zapytań (Zablokowane przez Nginx)")
        else:
            print(f"  [{code}]                      : {count} zapytań")

    print("=" * 55)
    blocked_count = counts.get(429, 0) + counts.get(503, 0)
    if blocked_count > 0:
        print(f"✅ SUKCES: Rate Limiter działa i poprawnie odrzucił {blocked_count} nadmiarowych zapytań!")
    else:
        print("⚠️  UWAGA: Żadne zapytanie nie zostało zablokowane kodem 429 ani 503.")
    print("\n")


if __name__ == "__main__":
    # Test 1: Bombardowanie endpointu głównego / (limit 60/min)
    print("--- TEST 1: ENDPOINT GŁÓWNY (GET /) ---")
    run_rate_limit_test(f"{BASE_URL}/", total_requests=100, concurrent_threads=10, method="GET")

    # Test 2: Bombardowanie endpointu logowania /login (limit 5/min)
    print("--- TEST 2: ENDPOINT LOGOWANIA (POST /login) ---")
    run_rate_limit_test(f"{BASE_URL}/login", total_requests=20, concurrent_threads=5, method="POST", json_data={"password": "test"})
