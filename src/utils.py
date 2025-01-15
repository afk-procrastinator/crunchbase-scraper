"""Utility functions for scraping"""

import csv
import time
import random
import re
from difflib import SequenceMatcher
from typing import Optional, List, Callable, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from forex_python.converter import CurrencyRates

from .models import CompanyData
from . import selectors

# Constants
CURRENCY_MULTIPLIERS = {
    'K': 1_000,
    'M': 1_000_000,
    'B': 1_000_000_000
}
NAME_SIMILARITY_THRESHOLD = 0.8

# Currency symbol to code mapping
CURRENCY_SYMBOLS = {
    '$': 'USD',
    '€': 'EUR',
    '£': 'GBP',
    '¥': 'JPY',
    'CN¥': 'CNY',
    '₹': 'INR',
    'A$': 'AUD',
    'C$': 'CAD',
    'HK$': 'HKD',
    '₣': 'CHF',
}

def random_delay(min_delay: float = 2.0, max_delay: float = 5.0) -> float:
    """Add random delay between actions and return the delay value"""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)
    return delay

def detect_currency(amount_str: str) -> Tuple[str, str]:
    """Detect currency from string and return (currency_code, cleaned_amount_str)"""
    amount_str = amount_str.strip()
    
    # Try to match currency symbols at the start of the string
    for symbol, code in CURRENCY_SYMBOLS.items():
        if amount_str.startswith(symbol):
            return code, amount_str.replace(symbol, '', 1).strip()
    
    # Default to USD if no currency symbol found
    return 'USD', amount_str

def parse_currency_amount(amount_str: str, target_currency: str = 'USD') -> Optional[float]:
    """
    Parse a currency amount string into a float and convert to target currency
    
    Args:
        amount_str: String containing amount with currency symbol (e.g., "$1.5M", "CN¥100K")
        target_currency: Target currency code (default: 'USD')
    
    Returns:
        Float value in target currency or None if parsing fails
    """
    try:
        # Skip empty or invalid strings
        if not amount_str or amount_str.lower() in ['n/a', 'unknown', '--']:
            return None
            
        # Detect source currency and clean amount string
        source_currency, cleaned_amount = detect_currency(amount_str)
        
        # Remove commas and other formatting
        cleaned_amount = cleaned_amount.replace(',', '').strip()
        
        # Extract multiplier if present
        multiplier = 1
        for suffix, mult in CURRENCY_MULTIPLIERS.items():
            if suffix in cleaned_amount:
                multiplier = mult
                cleaned_amount = cleaned_amount.replace(suffix, '').strip()
                break
        
        # Convert to float
        amount = float(cleaned_amount) * multiplier
        
        # Convert currency if needed
        if source_currency != target_currency:
            try:
                c = CurrencyRates()
                amount = c.convert(source_currency, target_currency, amount)
            except Exception as e:
                print(f"Currency conversion failed: {e}")
                return None
        
        return amount
        
    except (ValueError, AttributeError) as e:
        print(f"Could not convert amount '{amount_str}': {e}")
        return None

def get_string_similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def get_search_results(driver) -> List[Tuple[str, str]]:
    """Get list of company names and their URLs from search results"""
    try:
        # Wait for results wrapper
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.results-wrapper"))
        )
        
        # Find all company result links, excluding not-initial-search-results sections
        results = driver.find_elements(By.CSS_SELECTOR, 
            "search-results-section:not(.not-initial-search-results) mat-card a"
        )
        
        # Extract names and URLs (limit to first 5 results)
        company_results = []
        for result in results[:5]:
            try:
                # Get the name from the correct span element
                name_element = result.find_element(By.CSS_SELECTOR, "span.row-name")
                name = name_element.text.strip()
                url = result.get_attribute('href')
                if name and url:
                    company_results.append((name, url))
            except NoSuchElementException:
                continue
        
        return company_results
    except Exception as e:
        print(f"Error getting search results: {e}")
        return []

def analyze_search_results(driver, search_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Analyze search results and return best match (if any)
    Returns: Tuple of (company_name, company_url) or (None, None) if no match
    """
    results = get_search_results(driver)
    
    if not results:
        print(f"No results found for '{search_name}'")
        return None, None
    
    # Check for exact or similar matches
    best_match = None
    best_similarity = 0
    
    for name, url in results:
        similarity = get_string_similarity(search_name, name)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = (name, url)
    
    if best_match:
        name, url = best_match
        if best_similarity >= NAME_SIMILARITY_THRESHOLD:
            print(f"Found match: '{name}' (similarity: {best_similarity:.2f})")
            return name, url
        else:
            # Show options to user
            print(f"\nMultiple potential matches found for '{search_name}':")
            for i, (name, url) in enumerate(results, 1):
                similarity = get_string_similarity(search_name, name)
                print(f"{i}. {name} (similarity: {similarity:.2f})")
            
            while True:
                choice = input("\nEnter number to select company (or 's' to skip): ").strip().lower()
                if choice == 's':
                    return None, None
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(results):
                        return results[idx]
                except ValueError:
                    pass
                print("Invalid choice. Please try again.")
    
    return None, None

def search_and_click_first_result(driver, company_name: str, random_delay: Callable[[float, float], float]) -> bool:
    """Search for a company and click the first result"""
    try:
        # Wait for the page to be fully loaded
        random_delay(3, 5)
        
        # Try different search box selectors
        search_selectors = [
            "input[placeholder*='Search']",
            "input[type='search']",
            "input[aria-label*='search']",
            "input[class*='search']"
        ]
        
        search_box = None
        for selector in search_selectors:
            try:
                search_box = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if search_box.is_displayed():
                    break
            except:
                continue
        
        if not search_box:
            print("Could not find search box. Please locate it manually...")
            input("Press Enter once you've clicked the search box...")
            # Try to find the active element
            search_box = driver.switch_to.active_element
        
        # Focus and click the search box
        driver.execute_script("arguments[0].focus();", search_box)
        search_box.click()
        random_delay(0.5, 1)
        
        # Clear any existing text
        search_box.clear()
        random_delay(0.3, 0.5)
        
        # Type the search query with human-like delays
        for char in company_name:
            search_box.send_keys(char)
            random_delay(0.1, 0.3)
        
        random_delay(1, 2)
        
        # Press Enter to search
        search_box.send_keys(Keys.RETURN)
        
        # Wait for search results
        print("Waiting for search results...")
        random_delay(2, 3)
        
        # Analyze results and get best match
        name, url = analyze_search_results(driver, company_name)
        if url:
            print(f"Navigating to company page...")
            driver.get(url)
            return True
        else:
            print(f"No suitable match found for '{company_name}'")
            return False
            
    except Exception as e:
        print(f"Error during search: {e}")
        return False

def get_clean_company_name(driver) -> Optional[str]:
    """Get clean company name without extra elements"""
    try:
        name_element = driver.find_element(By.CSS_SELECTOR, "h1.profile-name")
        name = driver.execute_script("""
            var element = arguments[0];
            var text = '';
            for (var i = 0; i < element.childNodes.length; i++) {
                if (element.childNodes[i].nodeType === 3) {  // Text node
                    text += element.childNodes[i].textContent;
                }
            }
            return text;
        """, name_element)
        return name.strip()
    except Exception as e:
        print(f"Error getting clean company name: {e}")
        return None

def get_funding_amount(driver) -> tuple[Optional[float], Optional[float]]:
    """Get funding amount in both USD and CNY"""
    try:
        funding_elements = driver.find_elements(By.XPATH, 
            "//span[contains(text(), 'Total Funding Amount')]"
            "/ancestor::div[contains(@class, 'info')]"
            "//span[contains(@class, 'field-type-money')]"
        )
        
        if not funding_elements:
            funding_elements = driver.find_elements(By.XPATH,
                "//span[contains(@class, 'field-type-money')]"
                "[contains(text(), '$') or contains(text(), '¥') or contains(text(), 'CN¥')]"
            )
        
        if funding_elements:
            funding_text = funding_elements[0].get_attribute('title') or funding_elements[0].text
            funding_text = funding_text.strip()
            print(f"Found raw funding amount: {funding_text}")
            
            amount = parse_currency_amount(funding_text)
            if amount:
                if '$' in funding_text:
                    return amount, amount * CNY_TO_USD_RATE
                else:  # CNY
                    return amount / CNY_TO_USD_RATE, amount
        
        return None, None
        
    except Exception as e:
        print(f"Error getting funding amount: {e}")
        return None, None

def get_funding_info(driver) -> Optional[str]:
    """Get complete funding information text"""
    try:
        funding_elements = driver.find_elements(By.XPATH,
            "//markup-block[contains(., 'has raised') or contains(., 'total of')]"
        )
        
        if funding_elements:
            funding_info = driver.execute_script(r"""
                function getAllText(element) {
                    let text = '';
                    
                    function extractText(node) {
                        if (node.nodeType === 3) { // Text node
                            text += node.textContent;
                        } else if (node.nodeType === 1) { // Element node
                            // Special handling for links and spans
                            if (node.tagName === 'A' || node.tagName === 'SPAN') {
                                text += node.textContent;
                            } else {
                                // Recursively process child nodes
                                for (let child of node.childNodes) {
                                    extractText(child);
                                }
                            }
                        }
                    }
                    
                    extractText(element);
                    return text.replace(/\s+/g, ' ').trim();
                }
                return getAllText(arguments[0]);
            """, funding_elements[0])
            
            return funding_info.strip()
        return None
    except Exception as e:
        print(f"Error getting funding info: {e}")
        return None

def format_currency(amount: float) -> str:
    """Format currency in shorter format (K, M, B)"""
    if amount is None:
        return ''
    
    if amount >= 1_000_000_000:
        return f"{amount/1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"{amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"{amount/1_000:.1f}K"
    else:
        return f"{amount:.0f}"

def save_companies_to_csv(companies: List[CompanyData], filename: str = "companies.csv"):
    """Save company data to CSV file"""
    try:
        # Define which fields to include and their order
        fields = [
            'name',
            'location',
            'company_type',
            'total_funding_usd',
            'total_funding_cny',
            'employee_count',
            'year_founded',
            'website'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write headers
            headers = [field.replace('_', ' ').title() for field in fields]
            writer.writerow(headers)
            
            # Write data
            for company in companies:
                row = []
                for field in fields:
                    value = getattr(company, field)
                    if field in ['total_funding_usd', 'total_funding_cny'] and value is not None:
                        value = format_currency(value)
                    row.append(value if value is not None else '')
                writer.writerow(row)
                
        print(f"Successfully saved data to {filename}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def get_field_by_svg(driver, svg_path: str) -> Optional[str]:
    """Get field value by matching SVG path in the element"""
    try:
        # First, find all SVG paths on the page
        paths = driver.find_elements(By.TAG_NAME, "path")
        
        matching_path = None
        for path in paths:
            try:
                path_d = path.get_attribute('d')
                if path_d and path_d.startswith(svg_path[:30]):  # Match first 30 chars
                    matching_path = path
                    break
            except:
                continue
        
        if not matching_path:
            print("No matching SVG path found")
            return None
            
        # Find the parent li element
        current = matching_path
        max_iterations = 10  # Prevent infinite loop
        iterations = 0
        
        while current and iterations < max_iterations:
            if current.tag_name == 'li':
                # Found the li element, now get the text content
                spans = current.find_elements(By.TAG_NAME, "span")
                for span in spans:
                    try:
                        text = span.text.strip()
                        if text and not text.startswith('svg'):
                            return text
                    except:
                        continue
                break
            current = current.find_element(By.XPATH, '..')
            iterations += 1
        
        return None
    except Exception as e:
        print(f"Error finding element by SVG: {e}")
        return None

def get_field_by_label(driver, label_text: str) -> Optional[str]:
    """Get field value by matching the label text"""
    try:
        # Split the label text into words
        words = label_text.split()
        first_word, last_word = words[0], words[-1]
        
        # Build XPath to find li element containing both parts of the label
        xpath_base = f"//li[.//span[contains(text(), '{first_word}')] and .//span[contains(text(), '{last_word}')]]"
        
        # Different field types use different formatter classes
        field_type_mapping = {
            'Founded Date': 'field-type-date_precision',
            'Stock Symbol': 'link-formatter',
            'Legal Name': 'blob-formatter',
            'Operating Status': 'field-type-enum'
        }
        
        field_type = field_type_mapping.get(label_text, 'field-formatter')
        
        # Try to find the value using the appropriate class
        if label_text == 'Legal Name':
            # Legal Name is in a blob-formatter span
            xpath = f"{xpath_base}//blob-formatter//span"
        elif label_text == 'Operating Status':
            # Operating Status is in a field-type-enum span
            xpath = f"{xpath_base}//span[contains(@class, 'field-type-enum')]"
        elif label_text == 'Founded Date':
            # Founded Date is in a field-type-date_precision span
            xpath = f"{xpath_base}//span[contains(@class, 'field-type-date_precision')]"
        elif label_text == 'Stock Symbol':
            # Stock Symbol is in a link-formatter anchor tag
            xpath = f"{xpath_base}//link-formatter//a"
        else:
            # Default to field-formatter
            xpath = f"{xpath_base}//*[contains(@class, '{field_type}')]"
        
        element = driver.find_element(By.XPATH, xpath)
        # For stock symbol, get the title attribute which contains just the symbol
        if label_text == 'Stock Symbol':
            value = element.get_attribute('title')
        else:
            value = element.get_attribute('title') or element.text.strip()
        return value
        
    except Exception as e:
        print(f"Error finding element by label '{label_text}': {e}")
        return None

def get_numeric_field_by_label(driver, label_text: str) -> Optional[int]:
    """Get numeric value by matching the label text in links"""
    try:
        # Find the link containing the label text
        xpath = f"//a[.//span[text()='{label_text}']]//span[contains(@class, 'field-type-integer')]"
        element = driver.find_element(By.XPATH, xpath)
        value = element.get_attribute('title') or element.text.strip()
        if value and value.isdigit():
            return int(value)
        return None
    except Exception as e:
        print(f"Error finding {label_text} count: {e}")
        return None

# SVG path constants
SVG_PATHS = {
    'location': "M12,2C8.1,2,5,5.1,5,9c0,5.2,7,13,7,13s7-7.8,7-13C19,5.1,15.9,2,12,2z M12,11.5c-1.4,0-2.5-1.1-2.5-2.5s1.1-2.5,2.5-2.5s2.5,1.1,2.5,2.5S13.4,11.5,12,11.5z",
    'employees': "M16.36,10.91a3.28,3.28,0,1,0-3.27-3.27A3.26,3.26,0,0,0,16.36,10.91Zm-8.72,0A3.28,3.28,0,1,0,4.36,7.64,3.26,3.26,0,0,0,7.64,10.91Zm0,2.18C5.09,13.09,0,14.37,0,16.91v2.73H15.27V16.91C15.27,14.37,10.18,13.09,7.64,13.09Zm8.72,0a10.24,10.24,0,0,0-1,.06,4.59,4.59,0,0,1,2.14,3.76v2.73H24V16.91C24,14.37,18.91,13.09,16.36,13.09Z",
    'company_type': "M14.4,6L14,4H5v17h2v-7h5.6l0.4,2h7V6H14.4z",
    'website': "M12,2C6.5,2,2,6.5,2,12s4.5,10,10,10s10-4.5,10-10S17.5,2,12,2z M11,19.9c-3.9-0.5-7-3.9-7-7.9c0-0.6,0.1-1.2,0.2-1.8L9,15v1c0,1.1,0.9,2,2,2V19.9z M17.9,17.4c-0.3-0.8-1-1.4-1.9-1.4h-1v-3c0-0.6-0.4-1-1-1H8v-2h2c0.6,0,1-0.4,1-1V7h2c1.1,0,2-0.9,2-2V4.6c2.9,1.2,5,4.1,5,7.4C20,14.1,19.2,16,17.9,17.4z",
    'ranking': "M21.3,0H2.7C1.2,0,0,1.2,0,2.7v18.7C0,22.8,1.2,24,2.7,24h18.7c1.5,0,2.7-1.2,2.7-2.7V2.7C24,1.2,22.8,0,21.3,0z M21.3,21.3H2.7V2.7h18.7V21.3z M5.3,14.7h2.7v6.7H5.3V14.7z M10.7,10.7h2.7v10.7h-2.7V10.7z M16,5.3h2.7v16H16V5.3z",
    'funding_type': "M12.52,10.53c-3-.78-4-1.6-4-2.86,0-1.46,1.35-2.47,3.6-2.47S15.37,6.33,15.45,8H18.4a5.31,5.31,0,0,0-4.28-5.08V0h-4V2.88c-2.59.56-4.67,2.24-4.67,4.81,0,3.08,2.55,4.62,6.27,5.51,3.33.8,4,2,4,3.21,0,.92-.65,2.39-3.6,2.39-2.75,0-3.83-1.23-4-2.8H5.21c.16,2.92,2.35,4.56,4.91,5.11V24h4V21.13c2.6-.49,4.67-2,4.67-4.73C18.79,12.61,15.55,11.32,12.52,10.53Z"
}

def get_company_description(driver) -> Optional[str]:
    """Get company description from the description-card element"""
    try:
        # Try to find the description using the specific class
        description = driver.find_element(By.CSS_SELECTOR, "description-card .description")
        return description.text.strip()
    except NoSuchElementException:
        try:
            # Fallback: try to find any description element
            description = driver.find_element(By.CSS_SELECTOR, ".description")
            return description.text.strip()
        except NoSuchElementException:
            print("Could not find company description")
            return None
    except Exception as e:
        print(f"Error getting company description: {e}")
        return None

def scrape_company_data(driver, random_delay: Callable[[float, float], float]) -> Optional[CompanyData]:
    """Scrape all company data from the current page"""
    try:
        random_delay(3, 5)
        print("Scraping company data...")
        
        name = get_clean_company_name(driver)
        if not name:
            print("Could not find company name")
            return None
            
        company_data = CompanyData(name=name)
        print(f"\nCompany: {name}")
        
        # Get company description
        description = get_company_description(driver)
        if description:
            company_data.about = description
            print(f"Description: {description[:100]}...")
        else:
            print("Description: Not found")
        
        # Get data using SVG paths
        field_mapping = {
            'location': SVG_PATHS['location'],
            'employee_count': SVG_PATHS['employees'],
            'company_type': SVG_PATHS['company_type'],
            'website': SVG_PATHS['website'],
            'ranking': SVG_PATHS['ranking'],
            'last_funding_type': SVG_PATHS['funding_type']
        }
        
        for field, svg_path in field_mapping.items():
            value = get_field_by_svg(driver, svg_path)
            if value:
                if field == 'website':
                    # For website, we need to find the actual href
                    try:
                        element = driver.find_element(By.XPATH, f"//li[.//path[@d='{svg_path}']]//a")
                        value = element.get_attribute('href')
                    except:
                        pass
                elif field == 'ranking' and value.isdigit():
                    value = int(value)
                
                setattr(company_data, field, value)
                print(f"{field.replace('_', ' ').title()}: {value}")
            else:
                print(f"{field.replace('_', ' ').title()}: Not found")
        
        # Get numeric fields
        numeric_fields = {
            'acquisitions_count': 'Acquisitions',
            'investments_count': 'Investments',
            'exits_count': 'Exits'
        }
        
        for field, label in numeric_fields.items():
            value = get_numeric_field_by_label(driver, label)
            if value is not None:
                setattr(company_data, field, value)
                print(f"{field.replace('_', ' ').title()}: {value}")
            else:
                print(f"{field.replace('_', ' ').title()}: Not found")
        
        # Get fields by label text
        label_fields = {
            'founded_date': 'Founded Date',
            'stock_symbol': 'Stock Symbol',
            'legal_name': 'Legal Name',
            'operating_status': 'Operating Status'
        }
        
        for field, label in label_fields.items():
            value = get_field_by_label(driver, label)
            if value:
                if field == 'founded_date':
                    try:
                        # Extract year from the date string
                        year = int(value.split(',')[-1].strip())
                        company_data.year_founded = year
                        print(f"Founded Date: {value} (Year: {year})")
                    except:
                        print(f"\nCouldn't parse founded date: {value}")
                else:
                    setattr(company_data, field, value)
                    print(f"{field.replace('_', ' ').title()}: {value}")
            else:
                print(f"{field.replace('_', ' ').title()}: Not found")
        
        # Get funding amounts 
        # usd_amount, cny_amount = get_funding_amount(driver)
        # if usd_amount and cny_amount:
        #     company_data.total_funding_usd = usd_amount
        #     company_data.total_funding_cny = cny_amount
        #     print(f"\nTotal Funding:")
        #     print(f"USD: ${usd_amount:,.2f}")
        #     print(f"CNY: ¥{cny_amount:,.2f}")
        
        # Get funding info from financials tab
        current_url = driver.current_url
        financials_url = current_url + "/company_financials"
        driver.get(financials_url)
        random_delay(3, 5)
        
        funding_info = get_funding_info(driver)
        if funding_info:
            company_data.funding_info = funding_info
            print(f"Funding Information: {funding_info}")
        
        # Return to main page
        driver.get(current_url)
        random_delay(2, 3)
        
        print("\n" + "="*50 + "\n")
        return company_data
        
    except Exception as e:
        print(f"Error scraping company data: {e}")
        return None 