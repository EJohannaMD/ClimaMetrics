"""
Column Explorer Module for EnergyPlus CSV Files

This module provides functionality to explore and filter column headers
from EnergyPlus simulation output CSV files.
"""

import pandas as pd
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import click


class ColumnExplorer:
    """
    Class for exploring and filtering column headers from EnergyPlus CSV files.
    """
    
    def __init__(self, csv_file: str):
        """
        Initialize the ColumnExplorer with a CSV file path.
        
        Args:
            csv_file: Path to the EnergyPlus output CSV file
        """
        self.csv_file = Path(csv_file)
        self.logger = logging.getLogger(__name__)
        
        if not self.csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
    
    def get_columns(self, 
                   zone: Optional[str] = None,
                   pattern: Optional[str] = None,
                   limit: Optional[int] = None,
                   format_type: str = "list") -> List[str]:
        """
        Get column headers from the CSV file with optional filtering.
        
        Args:
            zone: Filter columns by zone name (e.g., "0XPLANTABAJA:ZONA4")
            pattern: Filter columns by text pattern (e.g., "Temperature", "Humidity")
            limit: Maximum number of columns to return
            format_type: Output format ("list" or "table")
            
        Returns:
            List of column names matching the criteria
        """
        self.logger.info(f"Loading column headers from: {self.csv_file}")
        
        try:
            # Read only the header row for efficiency
            df = pd.read_csv(self.csv_file, nrows=0)
            columns = df.columns.tolist()
            
            self.logger.info(f"Found {len(columns)} total columns")
            
            # Apply filters
            filtered_columns = columns.copy()
            
            if zone:
                filtered_columns = [col for col in filtered_columns if zone in col]
                self.logger.info(f"Filtered by zone '{zone}': {len(filtered_columns)} columns")
            
            if pattern:
                filtered_columns = [col for col in filtered_columns if pattern.lower() in col.lower()]
                self.logger.info(f"Filtered by pattern '{pattern}': {len(filtered_columns)} columns")
            
            # Apply limit
            if limit and limit > 0:
                filtered_columns = filtered_columns[:limit]
                self.logger.info(f"Limited to {limit} columns")
            
            return filtered_columns
            
        except Exception as e:
            self.logger.error(f"Error reading CSV file: {e}")
            raise
    
    def get_zones(self) -> List[str]:
        """
        Extract all unique zone names from the column headers.
        
        Returns:
            List of unique zone names found in the columns
        """
        try:
            df = pd.read_csv(self.csv_file, nrows=0)
            columns = df.columns.tolist()
            
            zones = set()
            for col in columns:
                if ':' in col:
                    # Extract zone name from column format: "ZONE:VARIABLE"
                    parts = col.split(':')
                    if len(parts) >= 2:
                        zone_name = f"{parts[0]}:{parts[1]}"
                        zones.add(zone_name)
            
            return sorted(list(zones))
            
        except Exception as e:
            self.logger.error(f"Error extracting zones: {e}")
            raise
    
    def get_variable_types(self) -> Dict[str, List[str]]:
        """
        Group columns by variable type (Temperature, Humidity, etc.).
        
        Returns:
            Dictionary with variable types as keys and lists of columns as values
        """
        try:
            df = pd.read_csv(self.csv_file, nrows=0)
            columns = df.columns.tolist()
            
            variable_types = {}
            
            for col in columns:
                col_lower = col.lower()
                
                # Categorize by variable type
                if 'temperature' in col_lower:
                    if 'Temperature' not in variable_types:
                        variable_types['Temperature'] = []
                    variable_types['Temperature'].append(col)
                elif 'humidity' in col_lower:
                    if 'Humidity' not in variable_types:
                        variable_types['Humidity'] = []
                    variable_types['Humidity'].append(col)
                elif 'occupant' in col_lower or 'people' in col_lower:
                    if 'Occupancy' not in variable_types:
                        variable_types['Occupancy'] = []
                    variable_types['Occupancy'].append(col)
                elif 'energy' in col_lower or 'power' in col_lower:
                    if 'Energy' not in variable_types:
                        variable_types['Energy'] = []
                    variable_types['Energy'].append(col)
                elif 'solar' in col_lower or 'radiation' in col_lower:
                    if 'Solar' not in variable_types:
                        variable_types['Solar'] = []
                    variable_types['Solar'].append(col)
                elif 'air' in col_lower and 'flow' in col_lower:
                    if 'Air Flow' not in variable_types:
                        variable_types['Air Flow'] = []
                    variable_types['Air Flow'].append(col)
                else:
                    if 'Other' not in variable_types:
                        variable_types['Other'] = []
                    variable_types['Other'].append(col)
            
            return variable_types
            
        except Exception as e:
            self.logger.error(f"Error categorizing variables: {e}")
            raise
    
    def format_output(self, columns: List[str], format_type: str = "list") -> str:
        """
        Format the column list for display.
        
        Args:
            columns: List of column names
            format_type: Output format ("list" or "table")
            
        Returns:
            Formatted string for display
        """
        if not columns:
            return "No columns found matching the criteria."
        
        if format_type == "table":
            # Create a simple table format
            result = f"Found {len(columns)} columns:\n"
            result += "-" * 50 + "\n"
            for i, col in enumerate(columns, 1):
                result += f"{i:3d}. {col}\n"
            return result
        else:
            # Simple list format
            return "\n".join(columns)
    
    def search_interactive(self, query: str) -> List[str]:
        """
        Interactive search for columns containing the query string.
        
        Args:
            query: Search query string
            
        Returns:
            List of columns matching the query
        """
        try:
            df = pd.read_csv(self.csv_file, nrows=0)
            columns = df.columns.tolist()
            
            # Case-insensitive search
            query_lower = query.lower()
            matching_columns = [col for col in columns if query_lower in col.lower()]
            
            return matching_columns
            
        except Exception as e:
            self.logger.error(f"Error in interactive search: {e}")
            raise
