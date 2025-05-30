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
        self.base_url = base_url
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
            "elapsed": f"{elapsed}s"
        }
        return self.send_post(f"add_result_for_case/{run_id}/{case_id}", data)

def run_magicpod_tests():
    print("Running MagicPod tests")
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

    # Run tests in MagicPod
    test_setting_id = os.getenv("MAGICPOD_TEST_SETTING_ID")
    batch_run = magicpod.run_test(test_setting_id)
    batch_run_number = batch_run["batch_run_number"]

    # Wait for test completion
    while True:
        result = magicpod.get_test_result(batch_run_number)
        if result["status"] in ["succeeded", "failed"]:
            break
        time.sleep(10)

    # Load TestRail test plan
    with open(os.getenv("TESTRAIL_TESTPLAN_JSON_FILENAME"), "r") as file:
        testplan = json.load(file)

    # Update TestRail with results
    for test_result in result["test_results"]:
        case_id = test_result["test_case_id"]  # Map to TestRail case_id
        status_id = 1 if test_result["status"] == "succeeded" else 5
        comment = f"MagicPod Test URL: {test_result['test_url']}\nScreenshot: {test_result.get('screenshot_url', '')}"
        elapsed = test_result["elapsed_time"]
        run_id = testplan["entries"][0]["runs"][0]["id"]  # Adjust based on config
        testrail.add_result_for_case(run_id, case_id, status_id, comment, elapsed)

if __name__ == "__main__":
    run_magicpod_tests()