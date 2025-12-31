"""Input layer: parsers and data ingestion."""

from .data_ingestion import DataIngestion
from .parsers import parse_raw

__all__ = ["DataIngestion", "parse_raw"]
