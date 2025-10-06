"""
CSV pivot module for ClimaMetrics.

This module provides functionality to consolidate multiple exported CSV files
into a single file with selected variables across all zones.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Optional
import glob


class CSVPivot:
    """Consolidates multiple zone CSV exports into a unified format."""
    
    def __init__(self):
        """Initialize CSV pivot."""
        self.logger = logging.getLogger("climametrics.csv_pivot")
    
    def find_csv_files(self, directory: Path = None, pattern: str = None) -> List[Path]:
        """
        Find CSV files to process.
        
        Args:
            directory: Directory to search for CSV files
            pattern: Glob pattern for file matching
            
        Returns:
            List of CSV file paths
        """
        if pattern:
            # Use glob pattern
            files = glob.glob(pattern)
            csv_files = [Path(f) for f in files if f.endswith('.csv')]
        elif directory:
            # Search directory
            csv_files = list(directory.glob('*.csv'))
        else:
            # Default to outputs/exports/
            csv_files = list(Path('outputs/exports').glob('*.csv'))
        
        # Sort for consistent ordering
        csv_files.sort()
        
        self.logger.info(f"Found {len(csv_files)} CSV files to process")
        return csv_files
    
    def validate_variable(self, csv_files: List[Path], variable: str) -> bool:
        """
        Validate that the variable exists in all CSV files.
        
        Args:
            csv_files: List of CSV file paths
            variable: Variable name to check
            
        Returns:
            True if variable exists in all files
        """
        for csv_file in csv_files:
            try:
                # Read first row to get headers
                df = pd.read_csv(csv_file, sep=';', nrows=0)
                if variable not in df.columns:
                    self.logger.error(f"Variable '{variable}' not found in {csv_file.name}")
                    self.logger.info(f"Available columns: {list(df.columns)}")
                    return False
            except Exception as e:
                self.logger.error(f"Error reading {csv_file.name}: {e}")
                return False
        
        return True
    
    def pivot_variable(self, csv_files: List[Path], variable: str) -> pd.DataFrame:
        """
        Extract and consolidate a variable from multiple CSV files.
        
        Args:
            csv_files: List of CSV file paths
            variable: Variable name to extract
            
        Returns:
            Consolidated DataFrame
        """
        all_data = []
        
        for csv_file in csv_files:
            try:
                self.logger.info(f"Processing: {csv_file.name}")
                
                # Read CSV with semicolon separator
                df = pd.read_csv(csv_file, sep=';')
                
                # Extract only needed columns
                if 'Date/Time' in df.columns and 'Zone' in df.columns and variable in df.columns:
                    extracted = df[['Date/Time', 'Zone', variable]].copy()
                    all_data.append(extracted)
                    self.logger.info(f"  - Extracted {len(extracted)} rows for zone: {df['Zone'].iloc[0]}")
                else:
                    self.logger.warning(f"  - Skipping {csv_file.name}: missing required columns")
                    
            except Exception as e:
                self.logger.error(f"Error processing {csv_file.name}: {e}")
                continue
        
        if not all_data:
            self.logger.error("No data extracted from any files")
            return pd.DataFrame()
        
        # Concatenate all data
        result_df = pd.concat(all_data, ignore_index=True)
        
        # Sort by Date/Time and Zone for better readability
        result_df = result_df.sort_values(['Date/Time', 'Zone'])
        
        self.logger.info(f"Consolidated {len(result_df)} total rows from {len(all_data)} zones")
        
        return result_df
    
    def export_pivot(self, 
                     output_file: Path,
                     directory: Path = None,
                     pattern: str = None,
                     variable: str = 'Operative_Temperature') -> None:
        """
        Export pivoted data to CSV file.
        
        Args:
            output_file: Output CSV file path
            directory: Directory with CSV files
            pattern: Glob pattern for file matching
            variable: Variable to extract
        """
        self.logger.info("Starting pivot operation...")
        
        # Find CSV files
        csv_files = self.find_csv_files(directory, pattern)
        
        if not csv_files:
            self.logger.error("No CSV files found")
            return
        
        # Display files found
        self.logger.info(f"Found {len(csv_files)} files to process:")
        for csv_file in csv_files:
            # Get file size
            size_mb = csv_file.stat().st_size / (1024 * 1024)
            self.logger.info(f"  - {csv_file.name} ({size_mb:.1f} MB)")
        
        # Validate variable exists in all files
        self.logger.info(f"Validating variable: {variable}")
        if not self.validate_variable(csv_files, variable):
            return
        
        # Pivot the variable
        self.logger.info(f"Extracting variable: {variable}")
        result_df = self.pivot_variable(csv_files, variable)
        
        if result_df.empty:
            self.logger.error("No data to export")
            return
        
        # Get unique zones
        zones = result_df['Zone'].unique()
        self.logger.info(f"Zones found: {len(zones)}")
        for zone in zones:
            zone_rows = len(result_df[result_df['Zone'] == zone])
            self.logger.info(f"  - {zone}: {zone_rows} rows")
        
        # Create output directory
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV with semicolon separator
        result_df.to_csv(output_file, sep=';', index=False, encoding='utf-8')
        
        self.logger.info(f"Pivot data exported to: {output_file}")
        self.logger.info(f"Total rows: {len(result_df)}")
        self.logger.info(f"Columns: {list(result_df.columns)}")

