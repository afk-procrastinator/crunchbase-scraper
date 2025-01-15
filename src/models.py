"""Data models for the scraper"""

from dataclasses import dataclass
from typing import Optional, List

@dataclass
class CompanyData:
    name: str
    about: Optional[str] = None
    quantum_general: Optional[str] = None
    quantum_computing: Optional[str] = None
    bis_list: Optional[bool] = None
    qedc_list: Optional[bool] = None
    total_funding_cny: Optional[float] = None
    total_funding_usd: Optional[float] = None
    funding_info: Optional[str] = None
    last_funding_type: Optional[str] = None
    location: Optional[str] = None
    employee_count: Optional[str] = None
    company_type: Optional[str] = None  # Public or Private
    website: Optional[str] = None
    year_founded: Optional[int] = None
    ranking: Optional[int] = None
    acquisitions_count: Optional[int] = None
    investments_count: Optional[int] = None
    exits_count: Optional[int] = None
    stock_symbol: Optional[str] = None
    legal_name: Optional[str] = None
    operating_status: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def to_csv_row(self) -> List[str]:
        """Convert to CSV row with all fields"""
        return [
            str(getattr(self, field.name, ''))
            for field in self.__class__.__dataclass_fields__.values()
        ]

    @staticmethod
    def get_csv_headers() -> List[str]:
        """Get CSV headers based on field names"""
        return [
            field.name.replace('_', ' ').title()
            for field in CompanyData.__dataclass_fields__.values()
        ] 