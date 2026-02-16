
import requests
import sys

BASE_URL = "http://localhost:8000"

def check_endpoint(method, endpoint, expected_status=200):
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url)
        
        status_code = response.status_code
        
        if status_code == expected_status:
            print(f"✅ {method} {endpoint} - {status_code} OK")
            return True
        elif status_code == 401 and "api" in endpoint:
             print(f"✅ {method} {endpoint} - {status_code} Unauthorized (Protected endpoint reachable)")
             return True
        else:
            print(f"❌ {method} {endpoint} - {status_code} (Expected {expected_status})")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ {method} {endpoint} - Connection Refused (Is backend running?)")
        return False
    except Exception as e:
        print(f"❌ {method} {endpoint} - Error: {e}")
        return False

def main():
    print(f"🔍 Checking FocusFlow API Endpoints at {BASE_URL}...\n")
    
    # 1. Core Endpoints
    print("--- Core Endpoints ---")
    check_endpoint("GET", "/", 200)
    check_endpoint("GET", "/health", 200)
    check_endpoint("GET", "/docs", 200)
    check_endpoint("GET", "/redoc", 200)
    
    # 2. Config Endpoint
    print("\n--- Configuration ---")
    check_endpoint("GET", "/api/config", 200)
    
    # 3. Auth Endpoints (Should be reachable)
    print("\n--- Auth Endpoints ---")
    # Signup/Login expect data, so 422 Unprocessable Entity is expected if reachable
    check_endpoint("POST", "/api/auth/login", 422) 
    check_endpoint("POST", "/api/auth/signup", 422)
    
    # 4. Protected Endpoints (Should return 401)
    print("\n--- Protected Endpoints (Expect 401) ---")
    check_endpoint("GET", "/api/sessions/history", 401)
    check_endpoint("GET", "/api/sessions/active", 401)
    check_endpoint("POST", "/api/sessions/start", 401) # Post needs auth
    
    # 5. ML Endpoints
    print("\n--- ML Endpoints ---")
    check_endpoint("GET", "/api/ml/status", 200) # Should be public or 401? Likely 200 or 401
    
    print("\n✅ Endpoint check complete.")

if __name__ == "__main__":
    main()
