import os
import json
import requests
from datetime import datetime

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

    def add_plan(self, project_id, entries):
        data = {
            "name": datetime.now().strftime("%Y-%m-%d-%H-%M") + " MagicPod Test",
            "entries": entries
        }
        return self.send_post(f"add_plan/{project_id}", data)

TESTRAIL_TESTPLAN_ENTRY = {
    "name": "Login_Automation",
    "entries": [
        {
            "suite_id": 1,  # Thay bằng suite_id của bạn
            "include_all": True,
            "config_ids": [2],  # Chrome, Firefox, Edge
            "runs": [
                {"include_all": True, "case_ids": [1], "config_ids": [2]}
            ]
        }
    ]
}

def prepare_testplan():
    print("Preparing test plan")
    client = TestRailAPIWrapper(
        os.getenv("TESTRAIL_URL"),
        os.getenv("TESTRAIL_USER"),
        os.getenv("TESTRAIL_PASSWORD")
    )
    response = client.add_plan(
        os.getenv("TESTRAIL_PROJECT_ID"),
        TESTRAIL_TESTPLAN_ENTRY
    )
    print(json.dumps(response, indent=4))
    with open(os.getenv("TESTRAIL_TESTPLAN_JSON_FILENAME"), "w", encoding='utf-8') as file:
        file.write(json.dumps(response))

if __name__ == "__main__":
    prepare_testplan()