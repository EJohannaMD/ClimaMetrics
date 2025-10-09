"""
Power BI exporter module for ClimaMetrics.

This module provides functionality to export thermal comfort indicators
in ULTRA-LONG format optimized for Power BI analysis.

OUTPUT FORMAT:
==============
Simulation | Indicator | DateTime | Zone | Value

Features:
- Single consolidated CSV with all indicators
- ULTRA-LONG format (fully normalized)
- Temporal indicators: IOD, ALPHA, HI, DI, HIlevel, DIlevel (hourly values)
- Aggregated indicators: DDH (sum across time), alphatot (global average)
- Environmental indicator: AWD (Zone = "Environment")
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from src.indicators import ThermalIndicators


class PowerBIExporter:
    """Export thermal indicators in Power BI compatible format"""
    
    def __init__(
        self,
        energyplus_csv: str,
        simulation_name: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Power BI exporter.
        
        Args:
            energyplus_csv: Path to EnergyPlus output CSV file
            simulation_name: Name of the simulation
            logger: Optional logger instance
        """
        self.energyplus_csv = energyplus_csv
        self.simulation_name = simulation_name
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize indicators calculator
        self.indicators = ThermalIndicators(
            energyplus_csv=energyplus_csv,
            simulation_name=simulation_name
        )
    
    def _wide_to_long(
        self,
        df_wide: pd.DataFrame,
        indicator_name: str,
        include_datetime: bool = True
    ) -> pd.DataFrame:
        """
        Convert WIDE format DataFrame to LONG format.
        
        Args:
            df_wide: DataFrame in WIDE format (DateTime as index, zones as columns)
            indicator_name: Name of the indicator
            include_datetime: Whether to include DateTime column
            
        Returns:
            DataFrame in LONG format with columns: Simulation, Indicator, DateTime, Zone, Value
        """
        # Reset index to make DateTime a column
        df_wide = df_wide.reset_index()
        
        # Melt to LONG format
        df_long = pd.melt(
            df_wide,
            id_vars=['DateTime'],
            var_name='Zone',
            value_name='Value'
        )
        
        # Add Simulation and Indicator columns
        df_long.insert(0, 'Simulation', self.simulation_name)
        df_long.insert(1, 'Indicator', indicator_name)
        
        # Remove DateTime if not needed (for aggregated indicators)
        if not include_datetime:
            df_long['DateTime'] = ''
        
        # Reorder columns
        df_long = df_long[['Simulation', 'Indicator', 'DateTime', 'Zone', 'Value']]
        
        return df_long
    
    def _calculate_alphatot(self, df_alpha: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate alphatot (global average of all alpha values).
        
        Args:
            df_alpha: WIDE format DataFrame with alpha values
            
        Returns:
            DataFrame with single row: alphatot value
        """
        # Calculate global average across all zones and times
        alphatot_value = df_alpha.mean().mean()
        
        # Create single-row DataFrame
        df_alphatot = pd.DataFrame({
            'Simulation': [self.simulation_name],
            'Indicator': ['alphatot'],
            'DateTime': [''],
            'Zone': ['values'],
            'Value': [alphatot_value]
        })
        
        return df_alphatot
    
    def _aggregate_ddh(self, df_ddh: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate DDH by summing across all time periods.
        
        Args:
            df_ddh: WIDE format DataFrame with DDH hourly values
            
        Returns:
            DataFrame with one row per zone (aggregated DDH)
        """
        # Sum across all time periods (rows)
        ddh_totals = df_ddh.sum(axis=0)
        
        # Create DataFrame
        df_ddh_agg = pd.DataFrame({
            'Simulation': self.simulation_name,
            'Indicator': 'DDH',
            'DateTime': '',
            'Zone': ddh_totals.index,
            'Value': ddh_totals.values
        })
        
        return df_ddh_agg
    
    def _filter_by_date_range(
        self,
        df_wide: pd.DataFrame,
        start_date: Optional[str],
        end_date: Optional[str],
        year: Optional[int]
    ) -> pd.DataFrame:
        """
        Filter WIDE format DataFrame by date range.
        
        Args:
            df_wide: DataFrame with DateTime as index or column
            start_date: Start date in format "MM/DD" (e.g., "06/22")
            end_date: End date in format "MM/DD" (e.g., "08/30")
            year: Year to combine with MM/DD format
            
        Returns:
            Filtered DataFrame
        """
        if not start_date and not end_date:
            return df_wide
        
        # Make a copy to avoid modifying original
        df_filtered = df_wide.copy()
        
        # Ensure DateTime is the index
        if 'DateTime' in df_filtered.columns:
            df_filtered = df_filtered.set_index('DateTime')
        
        # Convert index to datetime if not already
        if not isinstance(df_filtered.index, pd.DatetimeIndex):
            df_filtered.index = pd.to_datetime(df_filtered.index)
        
        # Parse start_date
        if start_date:
            # Format: "MM/DD" -> combine with year
            if '/' in start_date and len(start_date.split('/')[0]) <= 2:
                if year:
                    start_datetime = pd.to_datetime(f"{year}-{start_date.replace('/', '-')}")
                else:
                    # Use year from first row of data
                    year_from_data = df_filtered.index[0].year
                    start_datetime = pd.to_datetime(f"{year_from_data}-{start_date.replace('/', '-')}")
            else:
                # Already in full format "YYYY-MM-DD"
                start_datetime = pd.to_datetime(start_date)
            
            df_filtered = df_filtered[df_filtered.index >= start_datetime]
            self.logger.info(f"  Filtering from: {start_datetime.strftime('%Y-%m-%d')}")
        
        # Parse end_date
        if end_date:
            # Format: "MM/DD" -> combine with year
            if '/' in end_date and len(end_date.split('/')[0]) <= 2:
                if year:
                    end_datetime = pd.to_datetime(f"{year}-{end_date.replace('/', '-')} 23:59:59")
                else:
                    # Use year from first row of data
                    year_from_data = df_filtered.index[0].year
                    end_datetime = pd.to_datetime(f"{year_from_data}-{end_date.replace('/', '-')} 23:59:59")
            else:
                # Already in full format "YYYY-MM-DD"
                end_datetime = pd.to_datetime(f"{end_date} 23:59:59")
            
            df_filtered = df_filtered[df_filtered.index <= end_datetime]
            self.logger.info(f"  Filtering to: {end_datetime.strftime('%Y-%m-%d')}")
        
        return df_filtered
    
    def export_powerbi(
        self,
        zones: List[str],
        output_file: Optional[str] = None,
        indicators: Optional[List[str]] = None,
        comfort_temp: float = 26.5,
        base_temp: float = 18.0,
        year: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Export all indicators in Power BI format (ULTRA-LONG).
        
        Args:
            zones: List of zone names to analyze
            output_file: Output CSV file path (optional)
            indicators: List of indicators to calculate (default: all)
            comfort_temp: Comfort temperature for IOD (default: 26.5°C)
            base_temp: Base temperature for AWD (default: 18°C)
            year: Year to add to DateTime (optional)
            start_date: Start date for filtering in format "MM/DD" (e.g., "06/22")
            end_date: End date for filtering in format "MM/DD" (e.g., "08/30")
            
        Returns:
            Path to the generated CSV file
        """
        if indicators is None:
            indicators = ['IOD', 'AWD', 'ALPHA', 'HI', 'DDH', 'DI', 'DIlevel', 'HIlevel']
        
        self.logger.info(f"Exporting Power BI format for {len(zones)} zones with indicators: {indicators}")
        
        # Set temperatures in indicators calculator
        self.indicators.comfort_temp = comfort_temp
        self.indicators.base_temp = base_temp
        self.indicators.year = year
        
        # Load data from EnergyPlus CSV
        df = self.indicators._load_energyplus_data(zones)
        
        # List to collect all DataFrames
        all_dfs = []
        
        # Calculate IOD and AWD first (needed for ALPHA)
        iod_wide = None
        awd_wide = None
        
        # IOD (temporal, by zone)
        if 'IOD' in indicators or 'ALPHA' in indicators:
            self.logger.info("Processing IOD...")
            iod_wide = self.indicators.calculate_indoor_overheating_degree(df.copy())
            # Apply date filter
            iod_wide = self._filter_by_date_range(iod_wide, start_date, end_date, year)
            if 'IOD' in indicators:
                iod_long = self._wide_to_long(iod_wide, 'IOD', include_datetime=True)
                all_dfs.append(iod_long)
        
        # AWD (temporal, environmental - single column "Environment")
        if 'AWD' in indicators or 'ALPHA' in indicators:
            self.logger.info("Processing AWD...")
            awd_wide = self.indicators.calculate_ambient_warmness_degree(df.copy())
            # Apply date filter
            awd_wide = self._filter_by_date_range(awd_wide, start_date, end_date, year)
            if 'AWD' in indicators:
                awd_long = self._wide_to_long(awd_wide, 'AWD', include_datetime=True)
                all_dfs.append(awd_long)
        
        # ALPHA (temporal, by zone)
        if 'ALPHA' in indicators:
            self.logger.info("Processing ALPHA...")
            alpha_wide = self.indicators.calculate_alpha(iod_wide, awd_wide)
            # Note: alpha_wide is already filtered since iod_wide and awd_wide are filtered
            alpha_long = self._wide_to_long(alpha_wide, 'alpha', include_datetime=True)
            all_dfs.append(alpha_long)
            
            # Calculate alphatot (aggregated) - uses filtered data
            self.logger.info("Calculating alphatot...")
            alphatot_df = self._calculate_alphatot(alpha_wide)
            all_dfs.append(alphatot_df)
        
        # HI (temporal, by zone)
        if 'HI' in indicators:
            self.logger.info("Processing HI...")
            hi_wide = self.indicators.calculate_heat_index(df.copy())
            # Apply date filter
            hi_wide = self._filter_by_date_range(hi_wide, start_date, end_date, year)
            hi_long = self._wide_to_long(hi_wide, 'HI', include_datetime=True)
            all_dfs.append(hi_long)
        
        # HIlevel (temporal, by zone, categorical)
        if 'HIlevel' in indicators:
            self.logger.info("Processing HIlevel...")
            hilevel_wide = self.indicators.calculate_heat_index_levels(df.copy())
            # Apply date filter
            hilevel_wide = self._filter_by_date_range(hilevel_wide, start_date, end_date, year)
            hilevel_long = self._wide_to_long(hilevel_wide, 'HIlevel', include_datetime=True)
            all_dfs.append(hilevel_long)
        
        # DDH (aggregated, by zone)
        if 'DDH' in indicators:
            self.logger.info("Processing DDH...")
            ddh_wide = self.indicators.calculate_degree_weighted_discomfort_hours(df.copy())
            # Apply date filter BEFORE aggregating
            ddh_wide = self._filter_by_date_range(ddh_wide, start_date, end_date, year)
            # Aggregate filtered data
            ddh_agg = self._aggregate_ddh(ddh_wide)
            all_dfs.append(ddh_agg)
        
        # DI (temporal, by zone)
        if 'DI' in indicators:
            self.logger.info("Processing DI...")
            di_wide = self.indicators.calculate_discomfort_index(df.copy())
            # Apply date filter
            di_wide = self._filter_by_date_range(di_wide, start_date, end_date, year)
            di_long = self._wide_to_long(di_wide, 'DI', include_datetime=True)
            all_dfs.append(di_long)
        
        # DIlevel (temporal, by zone, categorical)
        if 'DIlevel' in indicators:
            self.logger.info("Processing DIlevel...")
            dilevel_wide = self.indicators.calculate_discomfort_index_levels(df.copy())
            # Apply date filter
            dilevel_wide = self._filter_by_date_range(dilevel_wide, start_date, end_date, year)
            dilevel_long = self._wide_to_long(dilevel_wide, 'DIlevel', include_datetime=True)
            all_dfs.append(dilevel_long)
        
        # Concatenate all DataFrames
        self.logger.info("Consolidating all indicators...")
        df_final = pd.concat(all_dfs, ignore_index=True)
        
        # Sort by Indicator, Zone, DateTime for better organization
        df_final = df_final.sort_values(['Indicator', 'Zone', 'DateTime']).reset_index(drop=True)
        
        # Generate output file name if not provided
        if output_file is None:
            output_file = f"outputs/powerbi/{self.simulation_name}_powerbi.csv"
        
        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        df_final.to_csv(output_path, index=False)
        
        # Log summary
        total_rows = len(df_final)
        indicators_exported = df_final['Indicator'].unique()
        zones_exported = df_final[df_final['Zone'] != 'values']['Zone'].unique()
        
        self.logger.info(f"✓ Power BI export completed:")
        self.logger.info(f"  - Output file: {output_path}")
        self.logger.info(f"  - Total rows: {total_rows:,}")
        self.logger.info(f"  - Indicators: {len(indicators_exported)} ({', '.join(indicators_exported)})")
        self.logger.info(f"  - Zones: {len(zones_exported)}")
        
        # Log date range info if filtered
        if start_date or end_date:
            date_range_str = ""
            if start_date and end_date:
                date_range_str = f"{start_date} to {end_date}"
            elif start_date:
                date_range_str = f"from {start_date}"
            elif end_date:
                date_range_str = f"to {end_date}"
            self.logger.info(f"  - Date range: {date_range_str}")
            self.logger.info(f"  - Note: alphatot and DDH calculated for filtered period only")
        
        return str(output_path)

