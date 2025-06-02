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
            "Content-Type": "application/json",
            "User-Agent": "MagicPod-TestRail-Integration/1.0"
        }
        self.org_name = org_name
        self.project_name = project_name

    def run_test(self, test_setting_id):
        url = f"{self.base_url}/{self.org_name}/{self.project_name}/batch-run/"
        print(f"🚀 Starting MagicPod test: {url}")
        
        response = requests.post(
            url,
            headers=self.headers,
            json={"test_setting_id": test_setting_id},
            timeout=30
        )
        
        if not response.ok:
            print(f"❌ Failed to start test: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
        
        return response.json()

    def get_test_result(self, batch_run_number):
        url = f"{self.base_url}/{self.org_name}/{self.project_name}/batch-run/{batch_run_number}/"
        
        response = requests.get(url, headers=self.headers, timeout=30)
        
        if not response.ok:
            print(f"❌ Failed to get test result: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
        
        return response.json()

class TestRailAPIWrapper:
    def __init__(self, base_url, user, password):
        self.base_url = base_url.rstrip('/')
        self.user = user
        self.password = password
        self.headers = {'Content-Type': 'application/json'}

    def send_post(self, endpoint, data):
        url = f"{self.base_url}/index.php?/api/v2/{endpoint}"
        
        response = requests.post(
            url,
            auth=(self.user, self.password),
            json=data,
            headers=self.headers,
            timeout=30
        )
        
        if not response.ok:
            print(f"❌ TestRail API error: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
        
        return response.json()

    def add_result_for_case(self, run_id, case_id, status_id, comment, elapsed):
        data = {
            "status_id": status_id,
            "comment": comment[:4000] if comment else "",  # Limit comment length
            "elapsed": f"{elapsed}s" if elapsed and elapsed > 0 else "1s"
        }
        return self.send_post(f"add_result_for_case/{run_id}/{case_id}", data)

def get_run_id_from_testplan(testplan):
    """Extract run_id from test plan structure with better error handling"""
    try:
        print("🔍 Analyzing test plan structure...")
        
        # Handle different possible structures
        if isinstance(testplan, dict):
            # Check for entries with runs
            if 'entries' in testplan and testplan['entries']:
                for i, entry in enumerate(testplan['entries']):
                    print(f"📋 Entry {i}: {entry.get('name', 'Unnamed')}")
                    
                    if 'runs' in entry and entry['runs']:
                        run_id = entry['runs'][0]['id']
                        print(f"✅ Found run_id: {run_id}")
                        return run_id
            
            # Check if testplan itself is a run
            if 'id' in testplan and 'name' in testplan:
                print(f"✅ Using testplan ID as run_id: {testplan['id']}")
                return testplan['id']
        
        # Log the structure for debugging
        print(f"❌ Could not find run_id in structure:")
        print(json.dumps(testplan, indent=2)[:1000] + "..." if len(str(testplan)) > 1000 else json.dumps(testplan, indent=2))
        
        raise ValueError("Could not find run_id in test plan structure")
        
    except Exception as e:
        print(f"❌ Error extracting run_id: {e}")
        raise

def run_magicpod_tests():
    print("🎯 Starting MagicPod-TestRail integration...")
    
    # Validate environment variables
    required_vars = [
        'MAGICPOD_API_TOKEN', 'MAGICPOD_ORGANIZATION_NAME', 
        'MAGICPOD_PROJECT_NAME', 'MAGICPOD_TEST_SETTING_ID',
        'TESTRAIL_URL', 'TESTRAIL_USER', 'TESTRAIL_PASSWORD'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"❌ Missing required environment variables: {missing_vars}")
    
    # Initialize API wrappers
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
        # Start MagicPod test execution
        test_setting_id = os.getenv("MAGICPOD_TEST_SETTING_ID")
        print(f"🧪 Starting MagicPod test with setting ID: {test_setting_id}")
        
        batch_run = magicpod.run_test(test_setting_id)
        batch_run_number = batch_run["batch_run_number"]
        print(f"📊 Batch run started: {batch_run_number}")

        # Wait for test completion with improved polling
        max_wait_time = 1800  # 30 minutes
        wait_time = 0
        poll_interval = 30
        last_status = None
        
        print("⏳ Waiting for test completion...")
        
        while wait_time < max_wait_time:
            try:
                result = magicpod.get_test_result(batch_run_number)
                status = result.get("status", "unknown")
                
                # Only log status changes
                if status != last_status:
                    print(f"📊 Test status: {status} (waited {wait_time}s)")
                    last_status = status
                
                if status in ["succeeded", "failed", "aborted"]:
                    print(f"✅ Test execution completed with status: {status}")
                    break
                    
                time.sleep(poll_interval)
                wait_time += poll_interval
                
            except Exception as e:
                print(f"⚠️  Error polling test status: {e}")
                time.sleep(poll_interval)
                wait_time += poll_interval
        
        if wait_time >= max_wait_time:
            print(f"⏰ Test execution timed out after {max_wait_time} seconds")
            print("⚠️  Proceeding with available results...")

        # Load TestRail test plan
        testplan_file = os.getenv("TESTRAIL_TESTPLAN_JSON_FILENAME", "testplan.json")
        
        if not os.path.exists(testplan_file):
            raise FileNotFoundError(f"❌ Test plan file not found: {testplan_file}")
            
        print(f"📄 Loading test plan from {testplan_file}")
        
        with open(testplan_file, "r", encoding='utf-8') as file:
            testplan = json.load(file)

        # Get run_id from test plan
        run_id = get_run_id_from_testplan(testplan)
        print(f"🎯 Using TestRail run_id: {run_id}")

        # Process and update TestRail with results
        test_results = result.get("test_results", [])
        print(f"📋 Processing {len(test_results)} test results...")
        
        success_count = 0
        error_count = 0
        
        for i, test_result in enumerate(test_results):
            try:
                # Map test case ID (adjust based on your setup)
                case_id = test_result.get("test_case_id")
                if not case_id:
                    # Fallback to sequential numbering
                    case_id = i + 1
                    print(f"⚠️  No test_case_id found, using sequential ID: {case_id}")
                
                # Map status
                test_status = test_result.get("status", "unknown")
                status_id = 1 if test_status == "succeeded" else 5  # 1=Passed, 5=Failed
                
                # Build comprehensive comment
                comment_parts = [
                    f"🤖 MagicPod Automated Test",
                    f"Status: {test_status}",
                    f"Batch Run: {batch_run_number}",
                    f"Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                ]
                
                # Add optional details
                if "test_url" in test_result:
                    comment_parts.append(f"Test URL: {test_result['test_url']}")
                
                if "screenshot_url" in test_result:
                    comment_parts.append(f"Screenshot: {test_result['screenshot_url']}")
                
                if "error_message" in test_result and test_result["error_message"]:
                    comment_parts.append(f"Error: {test_result['error_message']}")
                
                if "test_name" in test_result:
                    comment_parts.append(f"Test Name: {test_result['test_name']}")
                
                comment = "\n".join(comment_parts)
                elapsed = test_result.get("elapsed_time", 0)
                
                print(f"📝 Updating TestRail case {case_id} (status: {test_status})")
                
                testrail.add_result_for_case(run_id, case_id, status_id, comment, elapsed)
                success_count += 1
                
            except Exception as e:
                print(f"❌ Error updating TestRail for test result {i}: {e}")
                error_count += 1
                continue
        
        # Final summary
        print(f"\n🎉 Test execution and reporting completed!")
        print(f"📊 Summary:")
        print(f"   • Total test results: {len(test_results)}")
        print(f"   • Successfully updated: {success_count}")
        print(f"   • Errors: {error_count}")
        print(f"   • TestRail run ID: {run_id}")
        print(f"   • MagicPod batch run: {batch_run_number}")
        
        if error_count > 0:
            print(f"⚠️  {error_count} test results failed to update in TestRail")
        
    except Exception as e:
        print(f"💥 Error during test execution: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        run_magicpod_tests()
    except Exception as e:
        print(f"💥 Script failed: {e}")
        exit(1)