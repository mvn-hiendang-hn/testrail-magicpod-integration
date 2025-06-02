import os
import json
import requests
from datetime import datetime
import time

class TestRailAPIWrapper:
    def __init__(self, base_url, user, password):
        self.base_url = base_url.rstrip('/')
        self.user = user
        self.password = password
        self.headers = {'Content-Type': 'application/json'}

    def send_post(self, endpoint, data):
        url = f"{self.base_url}/index.php?/api/v2/{endpoint}"
        print(f"Making POST request to: {url}")
        
        response = requests.post(
            url,
            auth=(self.user, self.password),
            json=data,
            headers=self.headers,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if not response.ok:
            print(f"Error response: {response.text}")
            response.raise_for_status()
        
        return response.json()

    def send_get(self, endpoint):
        url = f"{self.base_url}/index.php?/api/v2/{endpoint}"
        print(f"Making GET request to: {url}")
        
        response = requests.get(
            url,
            auth=(self.user, self.password),
            headers=self.headers,
            timeout=30
        )
        
        if not response.ok:
            print(f"Error response: {response.text}")
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

    def get_project(self, project_id):
        return self.send_get(f"get_project/{project_id}")

def prepare_testplan():
    print("🚀 Starting TestRail test plan preparation...")
    
    # Validate environment variables
    required_vars = ['TESTRAIL_URL', 'TESTRAIL_USER', 'TESTRAIL_PASSWORD', 'TESTRAIL_PROJECT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"❌ Missing required environment variables: {missing_vars}")
    
    try:
        project_id = int(os.getenv("TESTRAIL_PROJECT_ID"))
    except (ValueError, TypeError):
        raise ValueError("❌ TESTRAIL_PROJECT_ID must be a valid integer")
    
    print(f"📋 Configuration:")
    print(f"  - Project ID: {project_id}")
    print(f"  - TestRail URL: {os.getenv('TESTRAIL_URL')}")
    print(f"  - TestRail User: {os.getenv('TESTRAIL_USER')}")
    
    client = TestRailAPIWrapper(
        os.getenv("TESTRAIL_URL"),
        os.getenv("TESTRAIL_USER"),
        os.getenv("TESTRAIL_PASSWORD")
    )
    
    try:
        # Test connection and validate project
        print("🔍 Validating project access...")
        try:
            project = client.get_project(project_id)
            print(f"✅ Project found: '{project['name']}'")
        except Exception as e:
            print(f"❌ Failed to access project {project_id}: {e}")
            raise
        
        # Get suites
        print("📁 Fetching test suites...")
        try:
            suites = client.get_suites(project_id)
            print(f"✅ Found {len(suites)} suite(s)")
            
            if not suites:
                raise ValueError("❌ No test suites found in project. Please create at least one test suite.")
            
            # Use the first suite
            suite_id = suites[0]['id']
            suite_name = suites[0]['name']
            print(f"📝 Using suite: ID={suite_id}, Name='{suite_name}'")
            
        except Exception as e:
            print(f"❌ Failed to get suites: {e}")
            raise
        
        # Create test plan with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plan_name = f"MagicPod_Automated_Test_{timestamp}"
        
        entries = [
            {
                "suite_id": suite_id,
                "name": "MagicPod Test Run",
                "include_all": True,
                "assignedto_id": None
            }
        ]
        
        print(f"🏗️  Creating test plan: '{plan_name}'")
        
        try:
            response = client.add_plan(project_id, plan_name, entries)
            
            print("✅ Test plan created successfully!")
            print(f"📊 Plan ID: {response.get('id')}")
            print(f"🔗 Plan URL: {response.get('url', 'N/A')}")
            
            # Save response to file
            filename = os.getenv("TESTRAIL_TESTPLAN_JSON_FILENAME", "testplan.json")
            
            # Ensure we have the data we need
            if 'entries' not in response or not response['entries']:
                raise ValueError("❌ Test plan created but no entries found in response")
            
            with open(filename, "w", encoding='utf-8') as file:
                json.dump(response, file, indent=2, ensure_ascii=False)
            
            print(f"💾 Test plan saved to {filename}")
            
            # Verify the saved file
            with open(filename, "r", encoding='utf-8') as file:
                saved_data = json.load(file)
                print(f"✅ Verified saved data contains {len(saved_data.get('entries', []))} entries")
            
        except Exception as e:
            print(f"❌ Failed to create test plan: {e}")
            raise
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e, 'response'):
            status_code = e.response.status_code
            print(f"📊 Status Code: {status_code}")
            print(f"📝 Response Body: {e.response.text}")
            
            # Error analysis
            if status_code == 400:
                print("\n💡 400 Bad Request - Possible causes:")
                print("   • Invalid project_id or suite_id")
                print("   • Missing required fields")
                print("   • Invalid data format")
            elif status_code == 401:
                print("\n💡 401 Unauthorized - Check credentials")
            elif status_code == 403:
                print("\n💡 403 Forbidden - User lacks permissions")
            elif status_code == 429:
                print("\n💡 429 Rate Limited - Too many requests")
                print("   • Waiting 30 seconds before retry...")
                time.sleep(30)
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        prepare_testplan()
        print("🎉 Test plan preparation completed successfully!")
    except Exception as e:
        print(f"💥 Test plan preparation failed: {e}")
        exit(1)