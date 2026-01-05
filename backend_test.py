import requests
import sys
import json
from datetime import datetime
import uuid

class ArsaEkspertizAPITester:
    def __init__(self, base_url="https://parseldeger.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = f"test-session-{uuid.uuid4()}"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test_name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Response: {data}"
            self.log_test("Root API Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("Root API Endpoint", False, str(e))
            return False

    def test_remaining_credits_new_session(self):
        """Test remaining credits for a new session"""
        try:
            response = requests.get(f"{self.api_url}/remaining-credits/{self.session_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                expected_credits = 5
                actual_credits = data.get('remaining_credits', 0)
                success = actual_credits == expected_credits
                details += f", Credits: {actual_credits}/{data.get('total_credits', 0)}"
                if not success:
                    details += f" (Expected: {expected_credits})"
            
            self.log_test("Remaining Credits - New Session", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Remaining Credits - New Session", False, str(e))
            return False, {}

    def test_property_analysis(self):
        """Test property analysis with valid data"""
        try:
            test_data = {
                "il": "İstanbul",
                "ilce": "Kadıköy",
                "mahalle": "Moda",
                "ada": "123",
                "parsel": "45",
                "session_id": self.session_id
            }
            
            print(f"🔍 Testing property analysis with data: {test_data}")
            response = requests.post(
                f"{self.api_url}/analyze-property", 
                json=test_data, 
                timeout=60  # Longer timeout for AI processing
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                # Check required fields in response
                required_fields = ['analysis', 'remaining_credits', 'search_query']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    success = False
                    details += f", Missing fields: {missing_fields}"
                else:
                    details += f", Analysis length: {len(data.get('analysis', ''))}"
                    details += f", Remaining credits: {data.get('remaining_credits')}"
                    details += f", Search query: {data.get('search_query', '')[:50]}..."
                    
                    # Verify credits decreased
                    if data.get('remaining_credits') != 4:
                        success = False
                        details += f" (Expected 4 remaining credits, got {data.get('remaining_credits')})"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Property Analysis - Valid Data", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Property Analysis - Valid Data", False, str(e))
            return False, {}

    def test_property_analysis_missing_fields(self):
        """Test property analysis with missing required fields"""
        try:
            test_data = {
                "il": "İstanbul",
                "ilce": "Kadıköy",
                # Missing mahalle, ada, parsel
                "session_id": self.session_id
            }
            
            response = requests.post(
                f"{self.api_url}/analyze-property", 
                json=test_data, 
                timeout=30
            )
            
            # Should return 422 for validation error
            success = response.status_code == 422
            details = f"Status: {response.status_code}"
            
            if not success:
                try:
                    error_data = response.json()
                    details += f", Response: {error_data}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Property Analysis - Missing Fields", success, details)
            return success
        except Exception as e:
            self.log_test("Property Analysis - Missing Fields", False, str(e))
            return False

    def test_credits_exhaustion(self):
        """Test behavior when credits are exhausted"""
        try:
            # First, let's use up the remaining credits
            test_data = {
                "il": "Ankara",
                "ilce": "Çankaya",
                "mahalle": "Kızılay",
                "ada": "100",
                "parsel": "1",
                "session_id": self.session_id
            }
            
            # Make multiple requests to exhaust credits (we already used 1, need to use 4 more)
            for i in range(4):
                print(f"🔄 Using credit {i+2}/5...")
                response = requests.post(
                    f"{self.api_url}/analyze-property", 
                    json=test_data, 
                    timeout=60
                )
                if response.status_code != 200:
                    self.log_test("Credits Exhaustion Setup", False, f"Failed to use credit {i+2}")
                    return False
            
            # Now try one more request - should be rejected
            print("🚫 Testing request after credits exhausted...")
            response = requests.post(
                f"{self.api_url}/analyze-property", 
                json=test_data, 
                timeout=30
            )
            
            success = response.status_code == 403
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    error_data = response.json()
                    details += f", Error message: {error_data.get('detail', '')}"
                except:
                    details += ", No JSON response"
            else:
                details += f", Expected 403, got {response.status_code}"
            
            self.log_test("Credits Exhaustion", success, details)
            return success
        except Exception as e:
            self.log_test("Credits Exhaustion", False, str(e))
            return False

    def test_remaining_credits_after_usage(self):
        """Test remaining credits after exhaustion"""
        try:
            response = requests.get(f"{self.api_url}/remaining-credits/{self.session_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                expected_credits = 0
                actual_credits = data.get('remaining_credits', -1)
                success = actual_credits == expected_credits
                details += f", Credits: {actual_credits}/{data.get('total_credits', 0)}"
                if not success:
                    details += f" (Expected: {expected_credits})"
            
            self.log_test("Remaining Credits - After Exhaustion", success, details)
            return success
        except Exception as e:
            self.log_test("Remaining Credits - After Exhaustion", False, str(e))
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting ArsaEkspertizAI Backend API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🆔 Test Session ID: {self.session_id}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.test_root_endpoint,
            self.test_remaining_credits_new_session,
            self.test_property_analysis,
            self.test_property_analysis_missing_fields,
            self.test_credits_exhaustion,
            self.test_remaining_credits_after_usage
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {str(e)}")
                self.tests_run += 1
            print("-" * 40)
        
        # Print summary
        print("\n📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        # Return results
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0,
            "test_details": self.test_results
        }

def main():
    tester = ArsaEkspertizAPITester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if results["failed_tests"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())