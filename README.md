<div align="center">
<h1>Crunchbase Company Scraper</h1>
<h4>A Python-based tool for scraping company information from Crunchbase.</h4>
</div>

## Features

- 🔐 Automatic and manual login support
- 📋 Batch scraping from company list
- 🤖 Anti-detection measures with randomized delays
- 💾 CSV export with detailed company information
- 💱 Currency conversion
- 🌐 Proxy support via Selenium

## Data Points Collected

- Company name and legal name
- About/Description
- Funding information
- Location
- Employee count
- Company type (Public/Private)
- Website
- Year founded
- Company ranking
- Acquisitions count
- Investments count
- Exits count
- Stock symbol
- Operating status

## Prerequisites

- Python 3.8+
- Chrome browser
- Crunchbase account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/afk-procrastinator/crunchbase-scraper
cd crunchbase-scraper
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.template .env
```
Edit `.env` with your Crunchbase credentials:
```
CRUNCHBASE_EMAIL=your-email@example.com
CRUNCHBASE_PASSWORD=your-password
```

## Usage

1. Create a list of companies to scrape in `company_list.txt`, separated by newlines:
```
Company Name 1
Company Name 2
```

2. Run the scraper:
```bash
python main.py
```

The script will:
- Log in to Crunchbase
- Process each company in the list
- Save results to `companies.csv`

## Project Structure

```
├── src/
│   ├── auth.py         # Authentication handling
│   ├── models.py       # Data models
│   ├── scraper.py      # Core scraping logic
│   ├── selectors.py    # CSS selectors
│   └── utils.py        # Utility functions
├── main.py             # Entry point
├── requirements.txt    # Dependencies
├── .env.template       # Environment template
└── company_list.txt    # Input companies
```

## Error Handling

- The scraper includes automatic retry logic for failed requests
- Manual login fallback if automatic login fails
- Graceful handling of missing data points

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is for educational purposes only. Please review and comply with Crunchbase's terms of service before use.