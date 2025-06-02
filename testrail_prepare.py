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
        print(f"Response content: {response.text}")
        
        if not response.ok:
            print(f"Error details: {response.status_code} - {response.text}")
        
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

    def get_configs(self, project_id):
        return self.send_get(f"get_configs/{project_id}")

def prepare_testplan():
    print("Preparing test plan")
    
    # Validate environment variables
    required_vars = ['TESTRAIL_URL', 'TESTRAIL_USER', 'TESTRAIL_PASSWORD', 'TESTRAIL_PROJECT_ID']
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")
    
    try:
        project_id = int(os.getenv("TESTRAIL_PROJECT_ID"))
    except (ValueError, TypeError):
        raise ValueError("TESTRAIL_PROJECT_ID must be a valid integer")
    
    client = TestRailAPIWrapper(
        os.getenv("TESTRAIL_URL"),
        os.getenv("TESTRAIL_USER"),
        os.getenv("TESTRAIL_PASSWORD")
    )
    
    try:
        # Get available suites and configs for validation
        print("Getting available suites...")
        suites = client.get_suites(project_id)
        print(f"Available suites: {[{'id': s['id'], 'name': s['name']} for s in suites]}")
        
        print("Getting available configs...")
        try:
            configs = client.get_configs(project_id)
            print(f"Available configs: {[{'id': c['id'], 'name': c['name']} for c in configs]}")
        except:
            print("No configs available or error getting configs")
            configs = []
        
        # Use the first available suite if exists
        if not suites:
            raise ValueError("No test suites found in the project")
        
        suite_id = suites[0]['id']
        print(f"Using suite_id: {suite_id}")
        
        # Prepare test plan entries
        plan_name = datetime.now().strftime("%Y-%m-%d-%H-%M") + " MagicPod Test"
        
        # Simple entry structure without configs if none available
        entries = [
            {
                "suite_id": suite_id,
                "name": "MagicPod Automation Tests",
                "include_all": True
            }
        ]
        
        # Add config_ids only if configs are available
        if configs:
            entries[0]["config_ids"] = [configs[0]['id']]
        
        print(f"Creating test plan: {plan_name}")
        response = client.add_plan(project_id, plan_name, entries)
        
        print("Test plan created successfully!")
        print(json.dumps(response, indent=4))
        
        # Save response to file
        filename = os.getenv("TESTRAIL_TESTPLAN_JSON_FILENAME", "testplan.json")
        with open(filename, "w", encoding='utf-8') as file:
            json.dump(response, file, indent=4)
        
        print(f"Test plan saved to {filename}")
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    prepare_testplan()