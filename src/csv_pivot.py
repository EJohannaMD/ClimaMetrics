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
    
    def validate_variable(self, csv_files: List[Path], variables: str) -> bool:
        """
        Validate that the variables exist in at least one CSV file.
        
        Args:
            csv_files: List of CSV file paths
            variables: Variable name(s) to check (comma-separated for multiple)
            
        Returns:
            True if at least one variable exists in at least one file
        """
        # Parse variables
        variable_list = [v.strip() for v in variables.split(',')]
        
        # Track which variables are found
        found_vars = set()
        
        for csv_file in csv_files:
            try:
                # Read first row to get headers
                df = pd.read_csv(csv_file, sep=';', nrows=0)
                
                # Check which variables exist in this file
                for var in variable_list:
                    if var in df.columns:
                        found_vars.add(var)
                        
            except Exception as e:
                self.logger.error(f"Error reading {csv_file.name}: {e}")
                return False
        
        # Check if at least one variable was found
        if not found_vars:
            self.logger.error(f"None of the requested variables found in any file: {variable_list}")
            # Show available columns from first file
            try:
                df = pd.read_csv(csv_files[0], sep=';', nrows=0)
                self.logger.info(f"Available columns in {csv_files[0].name}: {list(df.columns)}")
            except:
                pass
            return False
        
        # Warn about missing variables
        missing_vars = set(variable_list) - found_vars
        if missing_vars:
            self.logger.warning(f"Variables not found in any file: {list(missing_vars)}")
        
        self.logger.info(f"Variables that will be extracted: {list(found_vars)}")
        
        return True
    
    def _add_year_to_datetime(self, date_series: pd.Series, year: int) -> pd.Series:
        """
        Convert Date/Time from ' 01/01  01:00:00' format to '2020-01-01 01:00:00'.
        Handles special case of 24:00:00 (midnight) by converting to 00:00:00 of next day.
        
        Args:
            date_series: Series with dates in format ' MM/DD  HH:MM:SS'
            year: Year to add to dates
            
        Returns:
            Series with datetime objects formatted as ISO 8601 strings
        """
        try:
            # Clean up the date string and add year
            # Format: ' 01/01  01:00:00' -> '2020-01-01 01:00:00'
            
            def parse_date(date_str):
                try:
                    # Remove extra spaces and split
                    cleaned = ' '.join(date_str.strip().split())
                    
                    # Handle 24:00:00 (midnight of next day) -> convert to 00:00:00 of next day
                    if '24:00:00' in cleaned:
                        # Split date and time
                        date_part, time_part = cleaned.rsplit(' ', 1)
                        # Parse the date
                        month, day = date_part.split('/')
                        # Convert to datetime for the current day
                        dt = pd.to_datetime(f"{year}/{month}/{day} 00:00:00", format='%Y/%m/%d %H:%M:%S')
                        # Add one day to get midnight of next day
                        dt = dt + pd.Timedelta(days=1)
                        # Return as ISO 8601 string
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        # Normal parsing
                        # Add year prefix: '01/01 01:00:00' -> '2020/01/01 01:00:00'
                        with_year = f"{year}/{cleaned}"
                        # Parse to datetime
                        dt = pd.to_datetime(with_year, format='%Y/%m/%d %H:%M:%S')
                        # Return as ISO 8601 string
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    # If parsing fails, return original string
                    return date_str
            
            result = date_series.apply(parse_date)
            self.logger.info(f"Successfully converted {len(result)} dates to year {year}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error adding year to dates: {e}")
            return date_series
    
    def pivot_variable(self, csv_files: List[Path], variables: str, year: Optional[int] = None, simulation: Optional[str] = None) -> pd.DataFrame:
        """
        Extract and consolidate variables from multiple CSV files.
        
        Args:
            csv_files: List of CSV file paths
            variables: Variable name(s) to extract (comma-separated for multiple)
            year: Optional year to add to Date/Time column
            simulation: Optional simulation name to add as a column
            
        Returns:
            Consolidated DataFrame with columns: Date/Time, Zone, Indicator, Value, [Simulation]
        """
        # Parse variables (support comma-separated list)
        variable_list = [v.strip() for v in variables.split(',')]
        self.logger.info(f"Variables to extract: {variable_list}")
        
        all_data = []
        
        for csv_file in csv_files:
            try:
                self.logger.info(f"Processing: {csv_file.name}")
                
                # Read CSV with semicolon separator
                df = pd.read_csv(csv_file, sep=';')
                
                # Check required columns
                if 'Date/Time' not in df.columns or 'Zone' not in df.columns:
                    self.logger.warning(f"  - Skipping {csv_file.name}: missing Date/Time or Zone columns")
                    continue
                
                # Extract columns that exist
                columns_to_extract = ['Date/Time', 'Zone']
                available_vars = []
                
                for var in variable_list:
                    if var in df.columns:
                        columns_to_extract.append(var)
                        available_vars.append(var)
                    else:
                        self.logger.warning(f"  - Variable '{var}' not found in {csv_file.name}")
                
                if not available_vars:
                    self.logger.warning(f"  - Skipping {csv_file.name}: no requested variables found")
                    continue
                
                # Extract data
                extracted = df[columns_to_extract].copy()
                
                # Convert to LONG format: Date/Time, Zone, Indicator, Value
                # Using pd.melt to transform from wide to long format
                melted = extracted.melt(
                    id_vars=['Date/Time', 'Zone'],
                    value_vars=available_vars,
                    var_name='Indicator',
                    value_name='Value'
                )
                
                all_data.append(melted)
                self.logger.info(f"  - Extracted {len(melted)} rows ({len(available_vars)} variables) for zone: {df['Zone'].iloc[0]}")
                    
            except Exception as e:
                self.logger.error(f"Error processing {csv_file.name}: {e}")
                continue
        
        if not all_data:
            self.logger.error("No data extracted from any files")
            return pd.DataFrame()
        
        # Concatenate all data
        result_df = pd.concat(all_data, ignore_index=True)
        
        # Add year to Date/Time if specified
        if year:
            self.logger.info(f"Adding year {year} to Date/Time column...")
            result_df['Date/Time'] = self._add_year_to_datetime(result_df['Date/Time'], year)
        
        # Add simulation column if specified
        if simulation:
            self.logger.info(f"Adding Simulation column with value: '{simulation}'")
            result_df['Simulation'] = simulation
        
        # Sort by Date/Time, Zone, and Indicator for better readability
        result_df = result_df.sort_values(['Date/Time', 'Zone', 'Indicator'])
        
        self.logger.info(f"Consolidated {len(result_df)} total rows from {len(all_data)} zones")
        self.logger.info(f"Variables in output: {result_df['Indicator'].unique().tolist()}")
        
        return result_df
    
    def export_pivot(self, 
                     output_file: Path,
                     directory: Path = None,
                     pattern: str = None,
                     variable: str = 'Operative_Temperature',
                     year: Optional[int] = None,
                     simulation: Optional[str] = None) -> None:
        """
        Export pivoted data to CSV file.
        
        Args:
            output_file: Output CSV file path
            directory: Directory with CSV files
            pattern: Glob pattern for file matching
            variable: Variable to extract
            year: Optional year to add to Date/Time column
            simulation: Optional simulation name to add as a column
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
        
        # Validate variables exist in files
        self.logger.info(f"Validating variables: {variable}")
        if not self.validate_variable(csv_files, variable):
            return
        
        # Pivot the variables
        variable_list = [v.strip() for v in variable.split(',')]
        if len(variable_list) == 1:
            self.logger.info(f"Extracting variable: {variable}")
        else:
            self.logger.info(f"Extracting {len(variable_list)} variables: {variable_list}")
        
        if year:
            self.logger.info(f"Year will be added: {year}")
        
        if simulation:
            self.logger.info(f"Simulation name will be added: '{simulation}'")
        
        result_df = self.pivot_variable(csv_files, variable, year, simulation)
        
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

