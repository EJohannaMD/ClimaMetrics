"""
CSV export module for ClimaMetrics.

This module provides functionality to export thermal data from EnergyPlus
simulation results into unified CSV files for analysis.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


class CSVExporter:
    """Exporter for EnergyPlus CSV data to unified thermal analysis format."""
    
    def __init__(self, csv_file: Path):
        """
        Initialize CSV exporter.
        
        Args:
            csv_file: Path to EnergyPlus output CSV file
        """
        self.logger = logging.getLogger("climametrics.csv_exporter")
        self.csv_file = Path(csv_file)
        
        if not self.csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")
        
        self.logger.info(f"Initialized CSV exporter with file: {self.csv_file}")
    
    def load_data(self) -> pd.DataFrame:
        """
        Load EnergyPlus CSV data.
        
        Returns:
            DataFrame with simulation data
        """
        self.logger.info("Loading EnergyPlus CSV data...")
        
        try:
            # Load CSV with proper handling of large files
            df = pd.read_csv(self.csv_file, low_memory=False)
            self.logger.info(f"Loaded {len(df)} rows and {len(df.columns)} columns")
            return df
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
            raise
    
    def extract_thermal_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract thermal analysis data from EnergyPlus CSV.
        
        Args:
            df: EnergyPlus CSV DataFrame
            
        Returns:
            DataFrame with thermal analysis data
        """
        self.logger.info("Extracting thermal analysis data...")
        
        # Define required columns mapping
        column_mapping = {
            'Date/Time': 'Date/Time',
            'Outdoor_Dry_Bulb_Temperature': 'Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)',
            'Outdoor_Dewpoint_Temperature': 'Environment:Site Outdoor Air Dewpoint Temperature [C](Hourly)'
        }
        
        # Find available columns
        available_columns = {}
        for target_col, source_pattern in column_mapping.items():
            if target_col in df.columns:
                available_columns[target_col] = target_col
            else:
                # Try to find columns that match the pattern
                matching_cols = [col for col in df.columns if source_pattern in col]
                if matching_cols:
                    available_columns[target_col] = matching_cols[0]
                    self.logger.debug(f"Found {target_col} as {matching_cols[0]}")
                else:
                    self.logger.warning(f"Column not found: {target_col}")
        
        # Check if we have the minimum required columns
        if 'Date/Time' not in available_columns:
            self.logger.error("Date/Time column not found")
            return pd.DataFrame()
        
        # Extract base data
        thermal_data = []
        
        # Get timestamp column
        timestamps = df[available_columns['Date/Time']]
        
        # Get outdoor temperatures (same for all zones)
        outdoor_temp = None
        outdoor_dewpoint_temp = None
        if 'Outdoor_Dry_Bulb_Temperature' in available_columns:
            outdoor_temp = df[available_columns['Outdoor_Dry_Bulb_Temperature']]
        if 'Outdoor_Dewpoint_Temperature' in available_columns:
            outdoor_dewpoint_temp = df[available_columns['Outdoor_Dewpoint_Temperature']]
        
        # Find zone-specific columns
        zone_columns = self._find_zone_columns(df, available_columns)
        self.logger.info(f"Found {len(zone_columns)} zones")
        
        for zone_name, zone_cols in zone_columns.items():
            self.logger.debug(f"Processing zone: {zone_name}")
            
            # Extract zone data
            self.logger.info(f"Extracting data for zone {zone_name} with columns: {list(zone_cols.values())}")
            zone_data = df[list(zone_cols.values())].copy()
            zone_data['Zone'] = zone_name
            zone_data['Date/Time'] = timestamps
            if outdoor_temp is not None:
                zone_data['Outdoor_Dry_Bulb_Temperature'] = outdoor_temp
            if outdoor_dewpoint_temp is not None:
                zone_data['Outdoor_Dewpoint_Temperature'] = outdoor_dewpoint_temp
            
            # Set operative temperature (prefer EnergyPlus calculated, fallback to our calculation)
            if 'Operative_Temperature' in zone_cols:
                # Use EnergyPlus calculated operative temperature
                zone_data['Operative_Temperature'] = zone_data[zone_cols['Operative_Temperature']]
                self.logger.debug(f"Using EnergyPlus calculated operative temperature for zone {zone_name}")
            elif 'Air_Temperature' in zone_cols and 'Mean_Radiant_Temperature' in zone_cols:
                # Calculate operative temperature as fallback
                air_temp = zone_data[zone_cols['Air_Temperature']]
                radiant_temp = zone_data[zone_cols['Mean_Radiant_Temperature']]
                zone_data['Operative_Temperature'] = (air_temp + radiant_temp) / 2
                self.logger.debug(f"Calculated operative temperature for zone {zone_name}")
            else:
                self.logger.warning(f"Cannot determine operative temperature for zone {zone_name}")
                zone_data['Operative_Temperature'] = np.nan
            
            # Rename columns to standard names
            thermal_data.append(self._rename_zone_columns(zone_data, zone_cols))
        
        if not thermal_data:
            self.logger.error("No thermal data extracted")
            return pd.DataFrame()
        
        # Combine all zone data
        result_df = pd.concat(thermal_data, ignore_index=True)
        
        # Select and reorder final columns
        final_columns = [
            'Date/Time',
            'Relative_Humidity',
            'Occupancy',
            'Air_Temperature',
            'Mean_Radiant_Temperature',
            'Operative_Temperature',
            'Outdoor_Dry_Bulb_Temperature',
            'Outdoor_Dewpoint_Temperature',
            'Zone_Infiltration_Sensible_Heat_Gain',
            'Zone_Infiltration_Sensible_Heat_Loss',
            'Zone_Infiltration_Total_Heat_Gain',
            'Zone_Infiltration_Total_Heat_Loss',
            'Zone_Infiltration_Latent_Heat_Gain',
            'Zone_Infiltration_Latent_Heat_Loss',
            'Zone_Total_Internal_Total_Heating_Energy',
            'Zone_Total_Internal_Latent_Gain_Energy',
            'Zone'
        ]
        
        # Only include columns that exist
        available_final_columns = [col for col in final_columns if col in result_df.columns]
        result_df = result_df[available_final_columns]
        
        self.logger.info(f"Extracted thermal data: {len(result_df)} rows, {len(result_df.columns)} columns")
        return result_df
    
    def _find_zone_columns(self, df: pd.DataFrame, available_columns: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Find zone-specific columns in the DataFrame.
        
        Args:
            df: EnergyPlus CSV DataFrame
            available_columns: Available column mappings
            
        Returns:
            Dictionary mapping zone names to their column names
        """
        zone_columns = {}
        
        # Find all zone air temperature columns (prefer hourly over runperiod)
        temp_cols = [col for col in df.columns if 'Zone Mean Air Temperature' in col and 'Hourly:ON' in col]
        if not temp_cols:
            temp_cols = [col for col in df.columns if 'Zone Mean Air Temperature' in col and 'RunPeriod:ON' in col]
        self.logger.info(f"Found {len(temp_cols)} temperature columns")
        
        for temp_col in temp_cols:
            # Extract zone name from column (format: "0XPLANTABAJA:ZONA4:Zone Mean Air Temperature [C](Hourly:ON)")
            if ':' in temp_col:
                parts = temp_col.split(':')
                if len(parts) >= 2:
                    zone_name = f"{parts[0]}:{parts[1]}"
                
                # Find related columns for this zone
                zone_cols = {}
                
                # Air temperature
                zone_cols['Air_Temperature'] = temp_col
                
                # Relative humidity - try hourly first, then runperiod
                rh_col = f"{zone_name}:Zone Air Relative Humidity [%](Hourly:ON)"
                if rh_col not in df.columns:
                    rh_col = f"{zone_name}:Zone Air Relative Humidity [%](RunPeriod:ON)"
                if rh_col in df.columns:
                    zone_cols['Relative_Humidity'] = rh_col
                
                # Mean radiant temperature - try hourly first, then runperiod
                mrt_col = f"{zone_name}:Zone Mean Radiant Temperature [C](Hourly:ON)"
                if mrt_col not in df.columns:
                    mrt_col = f"{zone_name}:Zone Mean Radiant Temperature [C](RunPeriod:ON)"
                if mrt_col in df.columns:
                    zone_cols['Mean_Radiant_Temperature'] = mrt_col
                
                # Operative temperature (prefer EnergyPlus calculated over our calculation)
                op_temp_col = f"{zone_name}:Zone Operative Temperature [C](Hourly:ON)"
                if op_temp_col not in df.columns:
                    op_temp_col = f"{zone_name}:Zone Operative Temperature [C](RunPeriod:ON)"
                if op_temp_col in df.columns:
                    zone_cols['Operative_Temperature'] = op_temp_col
                
                # Occupancy - search for any occupancy column for this zone
                occ_pattern = f"{zone_name}:Zone People Sensible Heating Rate [W](Hourly)"
                occ_cols = [col for col in df.columns if occ_pattern in col]
                if occ_cols:
                    zone_cols['Occupancy'] = occ_cols[0]
                
                # Heat gain variables - search for heat gain columns for this zone
                # People sensible heating rate (already found above, but store as heat gain)
                
                # Infiltration sensible heat gain
                infil_sensible_gain_col = f"{zone_name}:Zone Infiltration Sensible Heat Gain Energy [J](Hourly:ON)"
                if infil_sensible_gain_col in df.columns:
                    zone_cols['Zone_Infiltration_Sensible_Heat_Gain'] = infil_sensible_gain_col
                
                # Infiltration sensible heat loss
                infil_sensible_loss_col = f"{zone_name}:Zone Infiltration Sensible Heat Loss Energy [J](Hourly:ON)"
                if infil_sensible_loss_col in df.columns:
                    zone_cols['Zone_Infiltration_Sensible_Heat_Loss'] = infil_sensible_loss_col
                
                # Infiltration total heat gain
                infil_total_gain_col = f"{zone_name}:Zone Infiltration Total Heat Gain Energy [J](Hourly:ON)"
                if infil_total_gain_col in df.columns:
                    zone_cols['Zone_Infiltration_Total_Heat_Gain'] = infil_total_gain_col
                
                # Infiltration total heat loss
                infil_total_loss_col = f"{zone_name}:Zone Infiltration Total Heat Loss Energy [J](Hourly:ON)"
                if infil_total_loss_col in df.columns:
                    zone_cols['Zone_Infiltration_Total_Heat_Loss'] = infil_total_loss_col
                
                # Infiltration latent heat gain
                infil_latent_gain_col = f"{zone_name}:Zone Infiltration Latent Heat Gain Energy [J](Hourly:ON)"
                if infil_latent_gain_col in df.columns:
                    zone_cols['Zone_Infiltration_Latent_Heat_Gain'] = infil_latent_gain_col
                
                # Infiltration latent heat loss
                infil_latent_loss_col = f"{zone_name}:Zone Infiltration Latent Heat Loss Energy [J](Hourly:ON)"
                if infil_latent_loss_col in df.columns:
                    zone_cols['Zone_Infiltration_Latent_Heat_Loss'] = infil_latent_loss_col
                
                # Total internal heating energy
                total_internal_heating_col = f"{zone_name}:Zone Total Internal Total Heating Energy [J](Hourly:ON)"
                if total_internal_heating_col in df.columns:
                    zone_cols['Zone_Total_Internal_Total_Heating_Energy'] = total_internal_heating_col
                
                # Total internal latent gain energy
                total_internal_latent_col = f"{zone_name}:Zone Total Internal Latent Gain Energy [J](Hourly:ON)"
                if total_internal_latent_col in df.columns:
                    zone_cols['Zone_Total_Internal_Latent_Gain_Energy'] = total_internal_latent_col
                
                zone_columns[zone_name] = zone_cols
                self.logger.info(f"Found zone {zone_name} with {len(zone_cols)} variables: {list(zone_cols.keys())}")
        
        return zone_columns
    
    def _rename_zone_columns(self, zone_data: pd.DataFrame, zone_cols: Dict[str, str]) -> pd.DataFrame:
        """
        Rename zone-specific columns to standard names.
        
        Args:
            zone_data: Zone data DataFrame
            zone_cols: Zone column mappings
            
        Returns:
            DataFrame with renamed columns
        """
        rename_mapping = {
            zone_cols.get('Air_Temperature', ''): 'Air_Temperature',
            zone_cols.get('Relative_Humidity', ''): 'Relative_Humidity',
            zone_cols.get('Mean_Radiant_Temperature', ''): 'Mean_Radiant_Temperature',
            zone_cols.get('Occupancy', ''): 'Occupancy',
            zone_cols.get('Zone_Infiltration_Sensible_Heat_Gain', ''): 'Zone_Infiltration_Sensible_Heat_Gain',
            zone_cols.get('Zone_Infiltration_Sensible_Heat_Loss', ''): 'Zone_Infiltration_Sensible_Heat_Loss',
            zone_cols.get('Zone_Infiltration_Total_Heat_Gain', ''): 'Zone_Infiltration_Total_Heat_Gain',
            zone_cols.get('Zone_Infiltration_Total_Heat_Loss', ''): 'Zone_Infiltration_Total_Heat_Loss',
            zone_cols.get('Zone_Infiltration_Latent_Heat_Gain', ''): 'Zone_Infiltration_Latent_Heat_Gain',
            zone_cols.get('Zone_Infiltration_Latent_Heat_Loss', ''): 'Zone_Infiltration_Latent_Heat_Loss',
            zone_cols.get('Zone_Total_Internal_Total_Heating_Energy', ''): 'Zone_Total_Internal_Total_Heating_Energy',
            zone_cols.get('Zone_Total_Internal_Latent_Gain_Energy', ''): 'Zone_Total_Internal_Latent_Gain_Energy',
        }
        
        # Remove empty keys
        rename_mapping = {k: v for k, v in rename_mapping.items() if k}
        
        return zone_data.rename(columns=rename_mapping)
    
    def export_thermal_summary(self, output_file: Path, 
                             zones: Optional[List[str]] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> None:
        """
        Export thermal summary data to CSV file.
        
        Args:
            output_file: Output CSV file path
            zones: List of zones to include (None for all)
            start_date: Start date filter (YYYY-MM-DD format)
            end_date: End date filter (YYYY-MM-DD format)
        """
        self.logger.info("Starting thermal data export...")
        
        # Load data
        df = self.load_data()
        
        # Extract thermal data
        thermal_df = self.extract_thermal_data(df)
        
        # Store column mapping for summary (get first zone as reference)
        zone_columns = self._find_zone_columns(df, {
            'Date/Time': 'Date/Time',
            'Outdoor_Dry_Bulb_Temperature': 'Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)',
            'Outdoor_Dewpoint_Temperature': 'Environment:Site Outdoor Air Dewpoint Temperature [C](Hourly)'
        })
        
        # Build reverse mapping from standardized names to original names
        column_mapping = {
            'Date/Time': 'Date/Time',
            'Zone': 'Zone'
        }
        
        # Get outdoor columns
        if 'Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)' in df.columns:
            column_mapping['Outdoor_Dry_Bulb_Temperature'] = 'Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)'
        if 'Environment:Site Outdoor Air Dewpoint Temperature [C](Hourly)' in df.columns:
            column_mapping['Outdoor_Dewpoint_Temperature'] = 'Environment:Site Outdoor Air Dewpoint Temperature [C](Hourly)'
        
        # Get zone-specific columns (use first zone as reference)
        if zone_columns:
            first_zone_cols = next(iter(zone_columns.values()))
            for std_name, orig_col in first_zone_cols.items():
                # Simplify the original column name by removing zone prefix
                simplified = orig_col.split(':', 2)[-1] if ':' in orig_col else orig_col
                column_mapping[std_name] = simplified
        
        if thermal_df.empty:
            self.logger.error("No thermal data to export")
            return
        
        # Apply filters
        if zones:
            thermal_df = thermal_df[thermal_df['Zone'].isin(zones)]
            self.logger.info(f"Filtered to zones: {zones}")
        
        if start_date or end_date:
            thermal_df['Date/Time'] = pd.to_datetime(thermal_df['Date/Time'])
            if start_date:
                thermal_df = thermal_df[thermal_df['Date/Time'] >= start_date]
            if end_date:
                thermal_df = thermal_df[thermal_df['Date/Time'] <= end_date]
            self.logger.info(f"Applied date filter: {start_date} to {end_date}")
        
        # Create output directory
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV with semicolon separator
        thermal_df.to_csv(output_file, sep=';', index=False, encoding='utf-8')
        
        self.logger.info(f"Thermal data exported to: {output_file}")
        self.logger.info(f"Exported {len(thermal_df)} rows for {thermal_df['Zone'].nunique()} zones")
        
        # Display exported columns summary in table format
        self.logger.info("\n=== COLUMNS SUMMARY ===")
        header = f"{'#':<4}| {'Exported Column Name':<40}| {'Original EnergyPlus Variable':<70}| {'Values':<15}"
        separator = "-" * 4 + "+" + "-" * 41 + "+" + "-" * 71 + "+" + "-" * 15
        self.logger.info(header)
        self.logger.info(separator)
        
        for i, col in enumerate(thermal_df.columns, 1):
            non_null_count = thermal_df[col].notna().sum()
            percentage = (non_null_count / len(thermal_df)) * 100
            
            # Get original column name from mapping
            original_name = column_mapping.get(col, col)
            
            # Format values string
            values_str = f"{non_null_count}/{len(thermal_df)} ({percentage:.0f}%)"
            
            # Print table row
            row = f"{i:<4}| {col:<40}| {original_name:<70}| {values_str:<15}"
            self.logger.info(row)
    
    def get_available_zones(self) -> List[str]:
        """
        Get list of available zones in the simulation data.
        
        Returns:
            List of zone names
        """
        df = self.load_data()
        temp_cols = [col for col in df.columns if 'Zone Air Temperature' in col]
        zones = [col.split(':')[0].strip() for col in temp_cols if ':' in col]
        return zones
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get summary of available data.
        
        Returns:
            Dictionary with data summary
        """
        df = self.load_data()
        zones = self.get_available_zones()
        
        return {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'available_zones': zones,
            'date_range': {
                'start': df['Date/Time'].iloc[0] if 'Date/Time' in df.columns else None,
                'end': df['Date/Time'].iloc[-1] if 'Date/Time' in df.columns else None
            }
        }
