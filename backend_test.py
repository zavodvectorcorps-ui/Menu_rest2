#!/usr/bin/env python3
"""
Backend API Testing for Restaurant Management System
Tests all endpoints for the Russian restaurant management application
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

class RestaurantAPITester:
    def __init__(self, base_url="https://restaurant-dash-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_data = {}

    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Dict = None, headers: Dict = None) -> tuple:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
                return False, {}

        except requests.exceptions.Timeout:
            self.log(f"❌ {name} - Request timeout", "ERROR")
            self.failed_tests.append({'name': name, 'error': 'Timeout'})
            return False, {}
        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "ERROR")
            self.failed_tests.append({'name': name, 'error': str(e)})
            return False, {}

    def test_seed_data(self):
        """Test data seeding"""
        success, response = self.run_test("Seed Data", "POST", "seed", 200)
        return success

    def test_restaurant_endpoints(self):
        """Test restaurant information endpoints"""
        self.log("=== Testing Restaurant Endpoints ===")
        
        # Get restaurant info
        success, restaurant = self.run_test("Get Restaurant", "GET", "restaurant", 200)
        if success:
            self.test_data['restaurant'] = restaurant
            
        # Update restaurant info
        update_data = {
            "name": "Мята Спортивная Тест",
            "description": "Тестовое описание"
        }
        success, updated = self.run_test("Update Restaurant", "PUT", "restaurant", 200, update_data)
        
        return success

    def test_categories_endpoints(self):
        """Test menu categories endpoints"""
        self.log("=== Testing Categories Endpoints ===")
        
        # Get categories
        success, categories = self.run_test("Get Categories", "GET", "categories", 200)
        if success and categories:
            self.test_data['categories'] = categories
            
        # Create new category
        new_category = {
            "name": "Тестовая категория",
            "sort_order": 99,
            "is_active": True
        }
        success, created_cat = self.run_test("Create Category", "POST", "categories", 200, new_category)
        if success:
            self.test_data['test_category'] = created_cat
            
            # Update category
            update_data = {"name": "Обновлённая категория", "sort_order": 100}
            success, updated = self.run_test(
                "Update Category", "PUT", f"categories/{created_cat['id']}", 200, update_data
            )
            
            # Delete category
            success, deleted = self.run_test(
                "Delete Category", "DELETE", f"categories/{created_cat['id']}", 200
            )
        
        return success

    def test_menu_items_endpoints(self):
        """Test menu items endpoints"""
        self.log("=== Testing Menu Items Endpoints ===")
        
        # Get menu items
        success, items = self.run_test("Get Menu Items", "GET", "menu-items", 200)
        if success:
            self.test_data['menu_items'] = items
            
        # Get items by category
        if self.test_data.get('categories'):
            cat_id = self.test_data['categories'][0]['id']
            success, cat_items = self.run_test(
                "Get Items by Category", "GET", f"menu-items?category_id={cat_id}", 200
            )
            
        # Create new menu item
        if self.test_data.get('categories'):
            new_item = {
                "category_id": self.test_data['categories'][0]['id'],
                "name": "Тестовое блюдо",
                "description": "Описание тестового блюда",
                "price": 500.0,
                "weight": "200 г",
                "is_available": True,
                "is_hit": True
            }
            success, created_item = self.run_test("Create Menu Item", "POST", "menu-items", 200, new_item)
            if success:
                self.test_data['test_item'] = created_item
                
                # Update menu item
                update_data = {"price": 550.0, "is_new": True}
                success, updated = self.run_test(
                    "Update Menu Item", "PUT", f"menu-items/{created_item['id']}", 200, update_data
                )
                
                # Delete menu item
                success, deleted = self.run_test(
                    "Delete Menu Item", "DELETE", f"menu-items/{created_item['id']}", 200
                )
        
        return success

    def test_tables_endpoints(self):
        """Test tables management endpoints"""
        self.log("=== Testing Tables Endpoints ===")
        
        # Get tables
        success, tables = self.run_test("Get Tables", "GET", "tables", 200)
        if success:
            self.test_data['tables'] = tables
            
        # Create new table
        new_table = {
            "number": 999,
            "name": "Тестовый стол",
            "is_active": True
        }
        success, created_table = self.run_test("Create Table", "POST", "tables", 200, new_table)
        if success:
            self.test_data['test_table'] = created_table
            
            # Update table
            update_data = {"name": "Обновлённый стол", "is_active": False}
            success, updated = self.run_test(
                "Update Table", "PUT", f"tables/{created_table['id']}", 200, update_data
            )
            
            # Regenerate table code
            success, regenerated = self.run_test(
                "Regenerate Table Code", "POST", f"tables/{created_table['id']}/regenerate-code", 200
            )
            
            # Delete table
            success, deleted = self.run_test(
                "Delete Table", "DELETE", f"tables/{created_table['id']}", 200
            )
        
        return success

    def test_orders_endpoints(self):
        """Test orders management endpoints"""
        self.log("=== Testing Orders Endpoints ===")
        
        # Get orders
        success, orders = self.run_test("Get Orders", "GET", "orders", 200)
        if success:
            self.test_data['orders'] = orders
            
        # Get orders by status
        success, new_orders = self.run_test("Get New Orders", "GET", "orders?status=new", 200)
        
        # Create order (requires table code)
        if self.test_data.get('tables') and self.test_data.get('menu_items'):
            table_code = self.test_data['tables'][0]['code']
            menu_item = self.test_data['menu_items'][0]
            
            new_order = {
                "table_code": table_code,
                "items": [{
                    "menu_item_id": menu_item['id'],
                    "name": menu_item['name'],
                    "quantity": 2,
                    "price": menu_item['price']
                }],
                "notes": "Тестовый заказ"
            }
            success, created_order = self.run_test("Create Order", "POST", "orders", 200, new_order)
            if success:
                self.test_data['test_order'] = created_order
                
                # Update order status
                status_update = {"status": "in_progress"}
                success, updated = self.run_test(
                    "Update Order Status", "PUT", f"orders/{created_order['id']}/status", 200, status_update
                )
        
        return success

    def test_staff_calls_endpoints(self):
        """Test staff calls endpoints"""
        self.log("=== Testing Staff Calls Endpoints ===")
        
        # Get staff calls
        success, calls = self.run_test("Get Staff Calls", "GET", "staff-calls", 200)
        if success:
            self.test_data['staff_calls'] = calls
            
        # Create staff call
        if self.test_data.get('tables'):
            table_code = self.test_data['tables'][0]['code']
            new_call = {"table_code": table_code}
            success, created_call = self.run_test("Create Staff Call", "POST", "staff-calls", 200, new_call)
            if success:
                self.test_data['test_call'] = created_call
                
                # Update call status
                success, updated = self.run_test(
                    "Update Call Status", "PUT", f"staff-calls/{created_call['id']}/status?status=acknowledged", 200
                )
        
        return success

    def test_employees_endpoints(self):
        """Test employees management endpoints"""
        self.log("=== Testing Employees Endpoints ===")
        
        # Get employees
        success, employees = self.run_test("Get Employees", "GET", "employees", 200)
        if success:
            self.test_data['employees'] = employees
            
        # Create employee
        new_employee = {
            "name": "Тестовый Сотрудник",
            "role": "Тестер",
            "telegram_id": "123456789",
            "is_active": True
        }
        success, created_emp = self.run_test("Create Employee", "POST", "employees", 200, new_employee)
        if success:
            self.test_data['test_employee'] = created_emp
            
            # Update employee
            update_data = {"role": "Старший тестер", "is_active": False}
            success, updated = self.run_test(
                "Update Employee", "PUT", f"employees/{created_emp['id']}", 200, update_data
            )
            
            # Delete employee
            success, deleted = self.run_test(
                "Delete Employee", "DELETE", f"employees/{created_emp['id']}", 200
            )
        
        return success

    def test_settings_endpoints(self):
        """Test settings endpoints"""
        self.log("=== Testing Settings Endpoints ===")
        
        # Get settings
        success, settings = self.run_test("Get Settings", "GET", "settings", 200)
        if success:
            self.test_data['settings'] = settings
            
        # Update settings
        update_data = {
            "online_menu_enabled": True,
            "staff_call_enabled": True,
            "theme": "light"
        }
        success, updated = self.run_test("Update Settings", "PUT", "settings", 200, update_data)
        
        return success

    def test_statistics_endpoints(self):
        """Test statistics endpoints"""
        self.log("=== Testing Statistics Endpoints ===")
        
        success, stats = self.run_test("Get Statistics", "GET", "stats", 200)
        if success:
            self.test_data['stats'] = stats
            
        return success

    def test_support_endpoints(self):
        """Test support endpoints"""
        self.log("=== Testing Support Endpoints ===")
        
        # Get support tickets
        success, tickets = self.run_test("Get Support Tickets", "GET", "support-tickets", 200)
        
        # Create support ticket
        new_ticket = {
            "subject": "Техническая проблема",
            "description": "Тестовое обращение в поддержку",
            "contact_email": "test@example.com"
        }
        success, created_ticket = self.run_test("Create Support Ticket", "POST", "support-tickets", 200, new_ticket)
        if success:
            self.test_data['test_ticket'] = created_ticket
            
        return success

    def test_faq_endpoints(self):
        """Test FAQ endpoints"""
        self.log("=== Testing FAQ Endpoints ===")
        
        success, faqs = self.run_test("Get FAQ", "GET", "faq", 200)
        if success:
            self.test_data['faqs'] = faqs
            
        return success

    def test_public_menu_endpoints(self):
        """Test public menu endpoints for clients"""
        self.log("=== Testing Public Menu Endpoints ===")
        
        if self.test_data.get('tables'):
            table_code = self.test_data['tables'][0]['code']
            success, menu_data = self.run_test(
                "Get Public Menu", "GET", f"public/menu/{table_code}", 200
            )
            if success:
                self.test_data['public_menu'] = menu_data
                
            # Test with invalid table code
            success, error = self.run_test(
                "Get Menu Invalid Code", "GET", "public/menu/INVALID", 404
            )
            
        return success

    def run_all_tests(self):
        """Run all API tests"""
        self.log("🚀 Starting Restaurant API Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Seed data first
        self.test_seed_data()
        
        # Run all endpoint tests
        test_methods = [
            self.test_restaurant_endpoints,
            self.test_categories_endpoints,
            self.test_menu_items_endpoints,
            self.test_tables_endpoints,
            self.test_orders_endpoints,
            self.test_staff_calls_endpoints,
            self.test_employees_endpoints,
            self.test_settings_endpoints,
            self.test_statistics_endpoints,
            self.test_support_endpoints,
            self.test_faq_endpoints,
            self.test_public_menu_endpoints
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log(f"❌ Test method {test_method.__name__} failed: {str(e)}", "ERROR")
        
        # Print results
        self.print_results()
        
        return self.tests_passed == self.tests_run

    def print_results(self):
        """Print test results summary"""
        self.log("=" * 50)
        self.log(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            self.log("❌ Failed Tests:")
            for test in self.failed_tests:
                error_msg = test.get('error', f"Expected {test.get('expected')}, got {test.get('actual')}")
                self.log(f"   - {test['name']}: {error_msg}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 Excellent! API is working well")
        elif success_rate >= 70:
            self.log("⚠️  Good, but some issues need attention")
        else:
            self.log("🚨 Critical issues found - needs immediate attention")

def main():
    """Main test execution"""
    tester = RestaurantAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': tester.tests_run,
        'passed_tests': tester.tests_passed,
        'failed_tests': tester.failed_tests,
        'success_rate': (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0,
        'test_data_samples': {k: str(v)[:100] + '...' if len(str(v)) > 100 else v 
                             for k, v in tester.test_data.items()}
    }
    
    with open('/app/backend_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())