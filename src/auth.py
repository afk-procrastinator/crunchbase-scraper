"""Authentication-related functionality"""

import time
from typing import Optional, Callable
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def find_and_fill_field(driver, selector: str, value: str, field_name: str, random_delay: Callable[[float, float], float]) -> bool:
    """Find and fill a form field with human-like typing"""
    try:
        field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        field.clear()
        for char in value:
            field.send_keys(char)
            random_delay(0.1, 0.2)
        return True
    except TimeoutException:
        print(f"Couldn't find {field_name} field")
        return False

def login(driver, email: str, password: str, random_delay: Callable[[float, float], float]) -> bool:
    """Login to Crunchbase using credentials"""
    try:
        if not email or not password:
            print("No credentials provided")
            return False

        # Fill email field
        if not find_and_fill_field(driver, "input[type='email']", email, "email", random_delay):
            return False
        random_delay(0.5, 1)

        # Fill password field
        if not find_and_fill_field(driver, "input[type='password']", password, "password", random_delay):
            return False
        random_delay(0.5, 1)

        # Click login button
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            login_button.click()
            print("Login credentials submitted...")
        except TimeoutException:
            print("Couldn't find login button")
            return False

        # Wait for redirect after login
        random_delay(3, 5)

        # Verify login success
        if "/login" in driver.current_url:
            print("Login seems to have failed. Please check your credentials.")
            return False

        print("Successfully logged in!")
        return True

    except Exception as e:
        print(f"Error during login: {e}")
        return False 