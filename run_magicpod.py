import os
import json
import requests
import time
from datetime import datetime

class MagicPodAPIWrapper:
    def __init__(self, token, org_name, project_name):
        self.base_url = "https://app.magicpod.com/api/v1.0"
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
        self.org_name = org_name
        self.project_name = project_name

    def run_test(self, test_setting_id):
        response = requests.post(
            f"{self.base_url}/{self.org_name}/{self.project_name}/batch-run/",
            headers=self.headers,
            json={"test_setting_id": test_setting_id}
        )
        response.raise_for_status()
        return response.json()

    def get_test_result(self, batch_run_number):
        response = requests.get(
            f"{self.base_url}/{self.org_name}/{self.project_name}/batch-run/{batch_run_number}/",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

class TestRailAPIWrapper:
    def __init__(self, base_url, user, password):
        self.base_url = base_url.rstrip('/')
        self.user = user
        self.password = password
        self.headers = {'Content-Type': 'application/json'}

    def send_post(self, endpoint, data):
        response = requests.post(
            f"{self.base_url}/index.php?/api/v2/{endpoint}",
            auth=(self.user, self.password),
            json=data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def add_result_for_case(self, run_id, case_id, status_id, comment, elapsed):
        data = {
            "status_id": status_id,  # 1=Passed, 5=Failed
            "comment": comment,
            "elapsed": f"{elapsed}s" if elapsed else "1s"
        }
        return self.send_post(f"add_result_for_case/{run_id}/{case_id}", data)

def get_run_id_from_testplan(testplan):
    """Extract run_id from test plan structure"""
    try:
        # Check if entries exist and have runs
        if 'entries' in testplan and testplan['entries']:
            for entry in testplan['entries']:
                if 'runs' in entry and entry['runs']:
                    return entry['runs'][0]['id']
        
        # If no nested structure, check if it's directly a run
        if 'id' in testplan:
            return testplan['id']
            
        raise ValueError("Could not find run_id in test plan structure")
    except Exception as e:
        print(f"Error extracting run_id: {e}")
        print(f"Test plan structure: {json.dumps(testplan, indent=2)}")
        raise

def run_magicpod_tests():
    print("Running MagicPod tests")
    
    # Validate environment variables
    required_vars = ['MAGICPOD_API_TOKEN', 'MAGICPOD_ORGANIZATION_NAME', 
                    'MAGICPOD_PROJECT_NAME', 'MAGICPOD_TEST_SETTING_ID',
                    'TESTRAIL_URL', 'TESTRAIL_USER', 'TESTRAIL_PASSWORD']
    
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")
    
    magicpod = MagicPodAPIWrapper(
        os.getenv("MAGICPOD_API_TOKEN"),
        os.getenv("MAGICPOD_ORGANIZATION_NAME"),
        os.getenv("MAGICPOD_PROJECT_NAME")
    )
    testrail = TestRailAPIWrapper(
        os.getenv("TESTRAIL_URL"),
        os.getenv("TESTRAIL_USER"),
        os.getenv("TESTRAIL_PASSWORD")
    )

    try:
        # Run tests in MagicPod
        test_setting_id = os.getenv("MAGICPOD_TEST_SETTING_ID")
        print(f"Starting MagicPod test with setting ID: {test_setting_id}")
        
        batch_run = magicpod.run_test(test_setting_id)
        batch_run_number = batch_run["batch_run_number"]
        print(f"Started batch run: {batch_run_number}")

        # Wait for test completion with timeout
        max_wait_time = 1800  # 30 minutes
        wait_time = 0
        poll_interval = 30  # 30 seconds
        
        while wait_time < max_wait_time:
            result = magicpod.get_test_result(batch_run_number)
            status = result.get("status", "unknown")
            print(f"Test status: {status} (waited {wait_time}s)")
            
            if status in ["succeeded", "failed", "aborted"]:
                break
                
            time.sleep(poll_interval)
            wait_time += poll_interval
        
        if wait_time >= max_wait_time:
            raise TimeoutError(f"Test execution timed out after {max_wait_time} seconds")

        # Load TestRail test plan
        testplan_file = os.getenv("TESTRAIL_TESTPLAN_JSON_FILENAME", "testplan.json")
        if not os.path.exists(testplan_file):
            raise FileNotFoundError(f"Test plan file not found: {testplan_file}")
            
        with open(testplan_file, "r") as file:
            testplan = json.load(file)

        print(f"Loaded test plan from {testplan_file}")
        
        # Get run_id from test plan
        run_id = get_run_id_from_testplan(testplan)
        print(f"Using TestRail run_id: {run_id}")

        # Update TestRail with results
        test_results = result.get("test_results", [])
        print(f"Processing {len(test_results)} test results")
        
        for i, test_result in enumerate(test_results):
            try:
                # Map MagicPod test case to TestRail case
                # You may need to adjust this mapping based on your setup
                case_id = test_result.get("test_case_id", i + 1)  # Default to sequential IDs
                
                status = test_result.get("status", "unknown")
                status_id = 1 if status == "succeeded" else 5  # 1=Passed, 5=Failed
                
                # Prepare comment with test details
                comment_parts = [f"MagicPod Test Status: {status}"]
                
                if "test_url" in test_result:
                    comment_parts.append(f"Test URL: {test_result['test_url']}")
                
                if "screenshot_url" in test_result:
                    comment_parts.append(f"Screenshot: {test_result['screenshot_url']}")
                
                if "error_message" in test_result:
                    comment_parts.append(f"Error: {test_result['error_message']}")
                
                comment = "\n".join(comment_parts)
                elapsed = test_result.get("elapsed_time", 0)
                
                print(f"Updating TestRail case {case_id} with status {status_id}")
                testrail.add_result_for_case(run_id, case_id, status_id, comment, elapsed)
                
            except Exception as e:
                print(f"Error updating TestRail for test result {i}: {e}")
                continue
        
        print("Test execution and reporting completed successfully!")
        
    except Exception as e:
        print(f"Error during test execution: {e}")
        raise

if __name__ == "__main__":
    run_magicpod_tests()