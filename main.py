"""Main entry point for the Crunchbase scraper"""

import os
from typing import List
from dotenv import load_dotenv
from src.scraper import CrunchbaseScraper

def read_company_list(filename: str = "company_list.txt") -> List[str]:
    """Read company names from file"""
    try:
        if not os.path.exists(filename):
            print(f"Company list file '{filename}' not found.")
            return []
            
        with open(filename, 'r', encoding='utf-8') as f:
            # Read lines and strip whitespace
            companies = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(companies)} companies from {filename}")
        return companies
    except Exception as e:
        print(f"Error reading company list: {e}")
        return []

def main():
    # Load environment variables
    load_dotenv()
    email = os.getenv('CRUNCHBASE_EMAIL')
    password = os.getenv('CRUNCHBASE_PASSWORD')
    
    if not email or not password:
        print("Please set CRUNCHBASE_EMAIL and CRUNCHBASE_PASSWORD in .env file")
        return
    
    scraper = CrunchbaseScraper(email=email, password=password, headless=False)
    companies = []
    
    try:
        print("\n========= Crunchbase Scraper Activating... =========")
        print("Made with ❤️ by afk-procrastinator")
        
        if scraper.access_homepage():
            print("\nReady to start searching!")
            
            # Ask user for search mode
            print("\nSearch modes:")
            print("1. Search individual companies")
            print("2. Process companies from company_list.txt")
            
            while True:
                mode = input("\nSelect mode (1 or 2): ").strip()
                if mode in ('1', '2'):
                    break
                print("Invalid choice. Please enter 1 or 2.")
            
            if mode == '1':
                # Individual company search mode
                while True:
                    company_name = input("\nEnter company name to search (or 'quit' to exit): ").strip()
                    if company_name.lower() == 'quit':
                        break
                    
                    print(f"\nSearching for '{company_name}'...")
                    if scraper.search_company(company_name):
                        print("Successfully opened company page")
                        
                        # Scrape company data
                        company_data = scraper.get_company_data()
                        if company_data:
                            companies.append(company_data)
                        else:
                            print("Failed to scrape company data")
                    else:
                        print("Failed to search/open company")
            else:
                # Batch processing mode
                company_list = read_company_list()
                if company_list:
                    total = len(company_list)
                    for i, company_name in enumerate(company_list, 1):
                        print(f"\nProcessing company {i}/{total}: '{company_name}'")
                        
                        if scraper.search_company(company_name):
                            print("Successfully opened company page")
                            
                            # Scrape company data
                            company_data = scraper.get_company_data()
                            if company_data:
                                companies.append(company_data)
                            else:
                                print("Failed to scrape company data")
                        else:
                            print("Failed to search/open company")
                        
                        # Save progress after each company
                        if companies:
                            scraper.save_to_csv(companies, "companies_progress.csv")
                else:
                    print("No companies to process. Please check company_list.txt")
        else:
            print("Failed to access homepage")
    finally:
        if companies:
            save = input("\nWould you like to save the final data to CSV? (y/n): ").strip().lower()
            if save == 'y':
                scraper.save_to_csv(companies)
        
        scraper.close()

if __name__ == "__main__":
    main() 