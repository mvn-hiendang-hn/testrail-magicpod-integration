import os
import json
import requests
from datetime import datetime

class TestRailAPIWrapper:
    def __init__(self, base_url, user, password):
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.user = user
        self.password = password
        self.headers = {'Content-Type': 'application/json'}

    def send_post(self, endpoint, data):
        url = f"{self.base_url}/index.php?/api/v2/{endpoint}"
        print(f"Making request to: {url}")
        print(f"Request data: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            url,
            auth=(self.user, self.password),
            json=data,
            headers=self.headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if not response.ok:
            print(f"Error response: {response.text}")
        
        response.raise_for_status()
        return response.json()

    def send_get(self, endpoint):
        url = f"{self.base_url}/index.php?/api/v2/{endpoint}"
        response = requests.get(
            url,
            auth=(self.user, self.password),
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def add_plan(self, project_id, name, entries):
        data = {
            "name": name,
            "entries": entries
        }
        return self.send_post(f"add_plan/{project_id}", data)

    def get_suites(self, project_id):
        return self.send_get(f"get_suites/{project_id}")

def prepare_testplan():
    print("Preparing test plan")
    
    # Validate environment variables
    required_vars = ['TESTRAIL_URL', 'TESTRAIL_USER', 'TESTRAIL_PASSWORD', 'TESTRAIL_PROJECT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    try:
        project_id = int(os.getenv("TESTRAIL_PROJECT_ID"))
    except (ValueError, TypeError):
        raise ValueError("TESTRAIL_PROJECT_ID must be a valid integer")
    
    print(f"Using project_id: {project_id}")
    print(f"TestRail URL: {os.getenv('TESTRAIL_URL')}")
    print(f"TestRail User: {os.getenv('TESTRAIL_USER')}")
    
    client = TestRailAPIWrapper(
        os.getenv("TESTRAIL_URL"),
        os.getenv("TESTRAIL_USER"),
        os.getenv("TESTRAIL_PASSWORD")
    )
    
    try:
        # Test connection by getting suites
        print("Testing connection by getting suites...")
        suites = client.get_suites(project_id)
        print(f"Found {len(suites)} suite(s)")
        
        if not suites:
            print("WARNING: No test suites found. Creating plan anyway with suite_id=1")
            suite_id = 1
        else:
            suite_id = suites[0]['id']
            print(f"Using first suite: ID={suite_id}, Name={suites[0]['name']}")
        
        # Create simple test plan
        plan_name = datetime.now().strftime("%Y-%m-%d-%H-%M") + " MagicPod Test"
        
        # Minimal entry structure
        entries = [
            {
                "suite_id": suite_id,
                "name": "MagicPod Tests",
                "include_all": True
            }
        ]
        
        print(f"Creating test plan: '{plan_name}'")
        print(f"Plan entries: {json.dumps(entries, indent=2)}")
        
        response = client.add_plan(project_id, plan_name, entries)
        
        print("✅ Test plan created successfully!")
        print(f"Plan ID: {response.get('id')}")
        print(f"Plan URL: {response.get('url', 'N/A')}")
        
        # Save response to file
        filename = os.getenv("TESTRAIL_TESTPLAN_JSON_FILENAME", "testplan.json")
        with open(filename, "w", encoding='utf-8') as file:
            json.dump(response, file, indent=4)
        
        print(f"✅ Test plan saved to {filename}")
        print(f"Full response: {json.dumps(response, indent=2)}")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e, 'response'):
            print(f"Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
            
            # Common error analysis
            if e.response.status_code == 400:
                print("\n🔍 400 Bad Request - Possible causes:")
                print("- Invalid suite_id (suite doesn't exist)")
                print("- Invalid project_id")
                print("- Missing required fields in request")
                print("- Invalid data format")
            elif e.response.status_code == 401:
                print("\n🔍 401 Unauthorized - Check credentials")
            elif e.response.status_code == 403:
                print("\n🔍 403 Forbidden - User lacks permissions")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    prepare_testplan()