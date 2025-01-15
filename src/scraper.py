"""Core scraper functionality"""

import time
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from .models import CompanyData
from . import auth
from . import utils
from . import selectors

class CrunchbaseScraper:
    """Main scraper class"""
    
    BASE_URL = "https://www.crunchbase.com"
    
    def __init__(self, email: str, password: str, headless: bool = False):
        self.headless = headless
        self.driver = None
        self.email = email
        self.password = password
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Selenium WebDriver with Chrome"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Add common Chrome options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize the Chrome WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_window_size(1920, 1080)
    
    def access_homepage(self) -> bool:
        """Access the Crunchbase homepage and ensure we're logged in"""
        try:
            print("Attempting automatic login...")
            # Go to login page
            login_url = f"{self.BASE_URL}/login"
            self.driver.get(login_url)
            utils.random_delay(2, 3)
            
            if not auth.login(self.driver, self.email, self.password, utils.random_delay):
                print("\nAutomatic login failed.")
                print("Please log in manually to your Crunchbase account.")
                input("Press Enter once you've logged in and are ready to proceed...")
            
            # Try accessing the home page to verify login
            self.driver.get(f"{self.BASE_URL}/home")
            utils.random_delay(2, 3)
            
            # Check if we got redirected back (indicating login issues)
            if self.driver.current_url == self.BASE_URL:
                print("Warning: Unable to access homepage. Please verify you're logged in.")
                input("Press Enter once you've verified login status...")
            
            return True
            
        except WebDriverException as e:
            print(f"Error accessing site: {e}")
            return False
    
    def search_company(self, company_name: str) -> bool:
        """Search for a company and click the first result"""
        return utils.search_and_click_first_result(self.driver, company_name, utils.random_delay)
    
    def get_company_data(self) -> Optional[CompanyData]:
        """Scrape company data from the current page"""
        return utils.scrape_company_data(self.driver, utils.random_delay)
    
    def save_to_csv(self, companies: List[CompanyData], filename: str = "companies.csv"):
        """Save company data to CSV file"""
        utils.save_companies_to_csv(companies, filename)
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit() 