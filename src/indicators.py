"""
Thermal comfort indicators module for ClimaMetrics.

This module provides functionality to calculate various thermal comfort indicators
directly from EnergyPlus simulation CSV outputs.

AVAILABLE INDICATORS:
=====================

1. IOD (Indoor Overheating Degree)
   Formula: IOD = Σ(Top - Tcomf)⁺ / Σ(Occupied_hours)
   Where:
   - Top = Operative temperature (°C)
   - Tcomf = Comfort temperature (default: 26.5°C)
   - (x)⁺ = max(x, 0) - only positive values
   - Σ = Sum over all occupied hours
   Unit: °C (degrees Celsius)
   
2. AWD (Ambient Warmness Degree)
   Formula: AWD = Σ(Tai - Tb)⁺ / N_total
   Where:
   - Tai = Ambient (outdoor) air temperature (°C)
   - Tb = Base outside temperature (default: 18°C)
   - (x)⁺ = max(x, 0) - only positive values
   - N_total = Total time steps (all hours)
   Unit: °C (degrees Celsius)
   
3. ALPHA (Overheating Escalator Factor)
   Formula: ALPHA = IOD / AWD
   Where:
   - IOD = Indoor Overheating Degree
   - AWD = Ambient Warmness Degree
   Unit: dimensionless ratio
   Interpretation: ALPHA < 1 means building performs better than ambient conditions
   
4. HI (Heat Index - Apparent Temperature)
   Formula (for T > 26.7°C and RH ≥ 40%):
   HI = C1 + C2×T + C3×RH + C4×T×RH + C5×T² + C6×RH² + C7×T²×RH + C8×T×RH² + C9×T²×RH²
   Where:
   - T = Operative temperature (°C)
   - RH = Relative humidity (percentage, 0-100)
   - C1 to C9 = Regression coefficients (V4 version for °C)
   For T ≤ 26.7°C or RH < 40%: HI = T
   Unit: °C (degrees Celsius)
   Categories: Safe (<27°C), Caution (27-32°C), Extreme Caution (32-41°C), 
               Danger (41-54°C), Extreme Danger (>54°C)
   
5. DDH (Degree-weighted Discomfort Hours)
   Formula: DDH = Σ[(Top - Top_up)⁺ × Occupied_flag]
   Where:
   - Top = Operative temperature (°C)
   - Top_up = Upper adaptive comfort limit (°C)
   - Top_up = T_op + 4°C (Category II tolerance)
   - T_op = 0.33 × θ_rm + 18.8 (Neutral operative temperature)
   - θ_rm = Running mean outdoor temperature (weighted 7-day average)
   - Occupied_flag = 1 if occupied, 0 otherwise
   - (x)⁺ = max(x, 0) - only positive exceedance
   Unit: °C·hours (degree-hours)
   Based on: EN 15251 adaptive comfort model
   
6. DI (Discomfort Index)
   Formula: DI = 0.5 × (Ta + Tw)
   Where:
   - Ta = Dry bulb (outdoor) temperature (°C)
   - Tw = Wet bulb temperature (°C)
   - Tw calculated using Stull (2011) approximation from Ta and RH
   Unit: °C (degrees Celsius)
   Categories: Comfortable (<21), Slightly Uncomfortable (21-24), 
               Uncomfortable (24-27), Very Uncomfortable (27-29), Dangerous (>29)
   
7. DIlevel (Discomfort Index Categories)
   Categorical classification of DI values
   
8. HIlevel (Heat Index Categories)
   Categorical classification of HI values

REFERENCES:
===========
- IOD, AWD, ALPHA: Adaptive thermal comfort methodology
- HI: Rothfusz (1990) Heat Index equation, V4 coefficients for Celsius
- DDH: EN 15251:2007 Adaptive comfort model
- DI: Thom (1959) Discomfort Index
- Tw: Stull (2011) Wet-bulb temperature approximation
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import math


class ThermalIndicators:
    """Calculator for thermal comfort indicators from EnergyPlus simulation data."""
    
    def __init__(self, energyplus_csv: Path, simulation_name: str = "Simulation", year: int = 2020):
        """
        Initialize thermal indicators calculator.
        
        Args:
            energyplus_csv: Path to EnergyPlus output CSV file (the large file with all variables)
            simulation_name: Name of the simulation for output files
            year: Year for datetime parsing (default: 2020)
        """
        self.logger = logging.getLogger("climametrics.indicators")
        self.energyplus_csv = Path(energyplus_csv)
        self.simulation_name = simulation_name
        self.year = year
        
        if not self.energyplus_csv.exists():
            raise FileNotFoundError(f"EnergyPlus CSV file not found: {self.energyplus_csv}")
        
        # Constants
        self.COMFORT_TEMPERATURE = 26.5
        self.BASE_OUTSIDE_TEMPERATURE = 18
        
        # Heat Index coefficients (for °C and RH as percentage 0-100) - V4 version
        self.HI_C1 = -8.784694
        self.HI_C2 = 1.611394
        self.HI_C3 = 2.338548
        self.HI_C4 = -0.146116
        self.HI_C5 = -0.012308
        self.HI_C6 = -0.016424
        self.HI_C7 = 0.002211
        self.HI_C8 = 0.000725
        self.HI_C9 = -0.000003
        
        self.logger.info(f"Initialized thermal indicators calculator with file: {self.energyplus_csv}")
    
    def _find_zone_columns(self, df: pd.DataFrame, zones: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Find and map EnergyPlus columns for each zone using configuration.
        
        Args:
            df: EnergyPlus output DataFrame
            zones: List of zone names to find
        
        Returns:
            Dictionary mapping zone names to their column mappings
        """
        from .config import config
        
        # Get zone variables configuration
        zone_var_config = config.get_indicators_zone_variables()
        
        zone_columns = {}
        
        for zone_name in zones:
            zone_cols = {}
            
            # Iterate over each configured variable
            for var_name, var_config in zone_var_config.items():
                column_found = False
                
                # Try main column pattern
                column_pattern = var_config['column_pattern'].format(zone=zone_name)
                
                if column_pattern in df.columns:
                    zone_cols[var_name] = column_pattern
                    column_found = True
                    self.logger.debug(f"Found {var_name} for {zone_name}: {column_pattern}")
                
                # Try fallback patterns if main pattern not found
                elif 'fallback' in var_config and not column_found:
                    for fallback_pattern in var_config['fallback']:
                        fallback_col = fallback_pattern.format(zone=zone_name)
                        if fallback_col in df.columns:
                            zone_cols[var_name] = fallback_col
                            column_found = True
                            self.logger.debug(f"Found {var_name} for {zone_name} (fallback): {fallback_col}")
                            break
                
                # Check if variable is required
                if not column_found and var_config.get('required', False):
                    self.logger.warning(f"Required variable '{var_name}' not found for zone {zone_name}")
                elif not column_found:
                    self.logger.debug(f"Optional variable '{var_name}' not found for zone {zone_name}")
            
            if zone_cols:
                zone_columns[zone_name] = zone_cols
                self.logger.info(f"Found zone {zone_name} with {len(zone_cols)} variables: {list(zone_cols.keys())}")
            else:
                self.logger.warning(f"Zone {zone_name} not found in EnergyPlus output")
        
        return zone_columns
    
    def _load_energyplus_data(self, zones: List[str]) -> pd.DataFrame:
        """
        Load and prepare data from EnergyPlus CSV for specified zones using configuration.
        
        Args:
            zones: List of zone names to load
            
        Returns:
            DataFrame with thermal data for all zones
        """
        from .config import config
        
        self.logger.info(f"Loading EnergyPlus CSV data for {len(zones)} zones...")
        
        # Load full EnergyPlus CSV
        df = pd.read_csv(self.energyplus_csv, low_memory=False)
        self.logger.info(f"Loaded {len(df)} rows and {len(df.columns)} columns from EnergyPlus output")
        
        # Find columns for each zone
        zone_columns = self._find_zone_columns(df, zones)
        
        if not zone_columns:
            raise ValueError(f"No valid zones found in EnergyPlus output. Requested zones: {zones}")
        
        # Get environmental variables configuration
        env_var_config = config.get_indicators_environmental_variables()
        calc_config = config.get_indicators_calculations_config()
        zone_var_config = config.get_indicators_zone_variables()
        
        # Find environmental columns
        env_columns = {}
        for var_name, var_config in env_var_config.items():
            column_pattern = var_config['column_pattern']
            if column_pattern in df.columns:
                env_columns[var_name] = column_pattern
                self.logger.debug(f"Found environmental variable {var_name}: {column_pattern}")
            elif var_config.get('required', False):
                raise ValueError(f"Required environmental variable '{var_name}' not found: {column_pattern}")
        
        # Prepare combined DataFrame
        all_zone_data = []
        
        for zone_name, cols in zone_columns.items():
            zone_df = pd.DataFrame()
            zone_df['Date/Time'] = df['Date/Time']
            zone_df['Zone'] = zone_name
            
            # Extract zone-specific data using configuration
            # Air Temperature
            if 'air_temperature' in cols:
                zone_df['Air_Temperature'] = pd.to_numeric(df[cols['air_temperature']], errors='coerce')
            else:
                zone_df['Air_Temperature'] = np.nan
            
            # Relative Humidity
            if 'relative_humidity' in cols:
                zone_df['Relative_Humidity'] = pd.to_numeric(df[cols['relative_humidity']], errors='coerce')
            else:
                default_rh = calc_config.get('defaults', {}).get('relative_humidity', 50.0)
                zone_df['Relative_Humidity'] = default_rh
                self.logger.debug(f"Using default relative humidity {default_rh}% for {zone_name}")
            
            # Mean Radiant Temperature (optional, for fallback calculation)
            if 'mean_radiant_temperature' in cols:
                zone_df['Mean_Radiant_Temperature'] = pd.to_numeric(df[cols['mean_radiant_temperature']], errors='coerce')
            else:
                zone_df['Mean_Radiant_Temperature'] = np.nan
            
            # Operative Temperature - PREFER direct column from EnergyPlus
            if 'operative_temperature' in cols:
                # Use EnergyPlus calculated operative temperature (PREFERRED)
                zone_df['Operative_Temperature'] = pd.to_numeric(df[cols['operative_temperature']], errors='coerce')
                self.logger.debug(f"Using EnergyPlus operative temperature for {zone_name}")
            elif calc_config.get('calculate_operative_if_missing', True):
                # Fallback: Calculate as (Tair + Tmrt) / 2
                if 'mean_radiant_temperature' in cols and zone_df['Mean_Radiant_Temperature'].notna().any():
                    zone_df['Operative_Temperature'] = (zone_df['Air_Temperature'] + zone_df['Mean_Radiant_Temperature']) / 2
                    self.logger.debug(f"Calculated operative temperature for {zone_name} from Tair and Tmrt")
                else:
                    zone_df['Operative_Temperature'] = zone_df['Air_Temperature']
                    self.logger.debug(f"Using air temperature as operative temperature for {zone_name}")
            else:
                zone_df['Operative_Temperature'] = zone_df['Air_Temperature']
            
            # Occupancy (convert from W to people count)
            if 'occupancy' in cols:
                occ_config = zone_var_config.get('occupancy', {})
                conversion_factor = occ_config.get('conversion_factor', 0.01)
                zone_df['Occupancy'] = pd.to_numeric(df[cols['occupancy']], errors='coerce') * conversion_factor
                zone_df['Occupancy'] = zone_df['Occupancy'].clip(lower=0)
            else:
                default_occ = calc_config.get('defaults', {}).get('occupancy', 0)
                zone_df['Occupancy'] = default_occ
            
            # Add environmental data (same for all zones)
            if 'outdoor_temperature' in env_columns:
                zone_df['Outdoor_Dry_Bulb_Temperature'] = pd.to_numeric(df[env_columns['outdoor_temperature']], errors='coerce')
            else:
                zone_df['Outdoor_Dry_Bulb_Temperature'] = np.nan
            
            if 'outdoor_dewpoint' in env_columns:
                zone_df['Outdoor_Dewpoint_Temperature'] = pd.to_numeric(df[env_columns['outdoor_dewpoint']], errors='coerce')
            else:
                zone_df['Outdoor_Dewpoint_Temperature'] = np.nan
            
            all_zone_data.append(zone_df)
        
        # Combine all zones
        combined_df = pd.concat(all_zone_data, ignore_index=True)
        
        self.logger.info(f"Prepared data for {len(zone_columns)} zones with {len(combined_df)} total rows")
        
        return combined_df
    
    def _parse_datetime(self, datetime_series: pd.Series) -> pd.Series:
        """
        Parse datetime series with multiple format attempts to avoid warnings.
        
        Args:
            datetime_series: Series containing datetime strings
            
        Returns:
            Series with parsed datetime values
        """
        # First strip leading/trailing whitespace
        cleaned_series = datetime_series.str.strip()
        
        # Handle 24:00:00 time format (convert to 00:00:00 of next day)
        def fix_24_hour(time_str):
            if ' 24:00:00' in time_str:
                # Replace 24:00:00 with 00:00:00 and add one day
                date_part = time_str.split(' 24:00:00')[0]
                try:
                    from datetime import datetime, timedelta
                    # Parse the date part
                    dt = datetime.strptime(date_part, '%m/%d')
                    # Add one day and set time to 00:00:00
                    dt = dt.replace(hour=0, minute=0, second=0) + timedelta(days=1)
                    return dt.strftime('%m/%d %H:%M:%S')
                except:
                    return time_str.replace(' 24:00:00', ' 00:00:00')
            return time_str
        
        # Apply 24-hour fix
        fixed_series = cleaned_series.apply(fix_24_hour)
        
        try:
            # Try specific format for "01/01  01:00:00" style (with double space)
            parsed = pd.to_datetime(fixed_series, format='%m/%d  %H:%M:%S')
            # Set year to specified year
            parsed = parsed.map(lambda x: x.replace(year=self.year) if pd.notna(x) else x)
            return parsed
        except:
            try:
                # Try with single space format
                parsed = pd.to_datetime(fixed_series, format='%m/%d %H:%M:%S')
                # Set year to specified year
                parsed = parsed.map(lambda x: x.replace(year=self.year) if pd.notna(x) else x)
                return parsed
            except:
                try:
                    # Try with dayfirst=True for other formats
                    parsed = pd.to_datetime(fixed_series, dayfirst=True, format='mixed')
                    # Set year to specified year
                    parsed = parsed.map(lambda x: x.replace(year=self.year) if pd.notna(x) else x)
                    return parsed
                except:
                    # Fallback to dateutil parsing (suppress warning)
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        parsed = pd.to_datetime(fixed_series, errors='coerce')
                        # Set year to specified year
                        parsed = parsed.map(lambda x: x.replace(year=self.year) if pd.notna(x) else x)
                        return parsed
    
    def calculate_indoor_overheating_degree(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Indoor Overheating Degree (IOD) for each zone in WIDE format.
        
        Only includes occupied hours. For non-occupied hours, IOD is NaN (excluded from export).
        This ensures the denominator only counts hours when the space is actually in use.

        Returns:
            DataFrame with DateTime as rows and zones as columns
        """
        self.logger.info("Calculating IOD (Indoor Overheating Degree)...")
        
        # Parse datetime
        data_frame['DateTime'] = self._parse_datetime(data_frame['Date/Time'])
        
        # Calculate excess temperature ONLY for occupied periods
        # For non-occupied hours: NaN (will be excluded from Power BI export)
        # For occupied hours with no excess: 0 (valid, will be included)
        data_frame['IOD'] = np.where(
            data_frame['Occupancy'] > 0,
            np.maximum(data_frame['Operative_Temperature'] - self.COMFORT_TEMPERATURE, 0),
            np.nan
        )
        
        # Pivot to WIDE format: DateTime x Zones
        iod_wide = data_frame.pivot_table(
            index='DateTime',
            columns='Zone',
            values='IOD',
            aggfunc='mean'  # Mean in case of duplicate timestamps
        )
        
        return iod_wide
    
    def calculate_ambient_warmness_degree(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Ambient Warmness Degree (AWD) - environmental indicator.
        
        AWD represents outdoor thermal conditions and is calculated for ALL hours of the year,
        not filtered by occupancy. This makes it a true environmental variable.
        
        For Power BI export, AWD is exported as "Environment" (not per zone) with all 8,760 hours,
        while ALPHA is pre-calculated using IOD and a filtered version of AWD.

        Returns:
            DataFrame with DateTime as index and single "Environment" column
        """
        self.logger.info("Calculating AWD (Ambient Warmness Degree)...")
        
        # Parse datetime
        data_frame['DateTime'] = self._parse_datetime(data_frame['Date/Time'])
        
        # Calculate excess ambient temperature for ALL hours (no occupancy filter)
        data_frame['AWD'] = np.maximum(
            data_frame['Outdoor_Dry_Bulb_Temperature'] - self.BASE_OUTSIDE_TEMPERATURE, 
            0
        )
        
        # Take unique DateTime values (outdoor temp is same for all zones)
        awd_data = data_frame.groupby('DateTime')['AWD'].first().to_frame()
        awd_data.columns = ['Environment']
        
        return awd_data
    
    def calculate_alpha(self, iod_wide: pd.DataFrame, awd_wide: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ALPHA (IOD / AWD) for each zone in WIDE format.
        
        ALPHA is calculated by dividing IOD (filtered by occupancy) by AWD (environmental).
        AWD values are aligned with IOD's index (filtered occupied hours).
        This ensures both have the same denominator (occupied hours only).
        
        Returns:
            DataFrame with DateTime as rows and zones as columns
        """
        self.logger.info("Calculating ALPHA (IOD/AWD ratio)...")
        
        # Align AWD with IOD's index (reindex to match occupied hours only)
        # This automatically filters AWD to the same DateTimes as IOD
        awd_aligned = awd_wide.reindex(iod_wide.index)
        
        # Calculate ALPHA for each zone
        alpha_wide = iod_wide.copy()
        
        for zone in alpha_wide.columns:
            # Divide IOD by AWD (Environment column)
            # Where IOD is NaN (not occupied), result will be NaN
            # Where AWD is 0, result will be NaN (avoid division by zero)
            alpha_wide[zone] = np.where(
                (awd_aligned['Environment'] != 0) & (awd_aligned['Environment'].notna()),
                alpha_wide[zone] / awd_aligned['Environment'],
            np.nan
        )

        return alpha_wide

    def calculate_heat_index_category(self, hi_celsius: float) -> str:
        """Categorize Heat Index risk levels"""
        if pd.isna(hi_celsius):
            return "INVALID DATA"
        elif hi_celsius < 27:
            return "SAFE CONDITION"
        elif hi_celsius < 32:
            return "CAUTION"
        elif hi_celsius < 41:
            return "EXTREME CAUTION"
        elif hi_celsius < 54:
            return "DANGER"
        else:
            return "EXTREME DANGER"

    def calculate_heat_index(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Heat Index (Apparent Temperature) combining temperature and humidity.

        Heat Index represents what the temperature "feels like" to the human body when
        relative humidity is factored in with the actual air temperature.

        FORMULA (V4 version):
        For T ≤ 26.7°C or RH < 40%:
        HI = T (simple approximation)

        For T > 26.7°C and RH ≥ 40% (full regression equation):
        HI = C1 + C2×T + C3×RH + C4×T×RH + C5×T² + C6×RH² + C7×T²×RH + C8×T×RH² + C9×T²×RH²

        Where:
        - HI = Heat Index (°C) - V4 version uses Celsius directly
        - T = Dry bulb temperature (°C) ** change for Operative Temperature **
        - RH = Relative humidity (percentage, 0-100)
        - C1 to C9 = V4 regression coefficients

        Returns:
        - DataFrame with Heat Index values and risk categories
        """
        self.logger.info("Calculating HI (Heat Index)...")
        
        # Parse datetime
        data_frame['DateTime'] = self._parse_datetime(data_frame['Date/Time'])
        
        # Ensure RH is in valid range (0-100%)
        data_frame['RH'] = data_frame['Relative_Humidity'].clip(0, 100)
        
        # Calculate Heat Index
        data_frame['HI'] = np.where(
            (data_frame['Operative_Temperature'] <= 26.7) | (data_frame['RH'] < 40),
            data_frame['Operative_Temperature'],
            (self.HI_C1 +
             self.HI_C2 * data_frame['Operative_Temperature'] +
             self.HI_C3 * data_frame['RH'] +
             self.HI_C4 * data_frame['Operative_Temperature'] * data_frame['RH'] +
             self.HI_C5 * (data_frame['Operative_Temperature']**2) +
             self.HI_C6 * (data_frame['RH']**2) +
             self.HI_C7 * (data_frame['Operative_Temperature']**2) * data_frame['RH'] +
             self.HI_C8 * data_frame['Operative_Temperature'] * (data_frame['RH']**2) +
             self.HI_C9 * (data_frame['Operative_Temperature']**2) * (data_frame['RH']**2))
        )
        
        # Pivot to WIDE format
        hi_wide = data_frame.pivot_table(
            index='DateTime',
            columns='Zone',
            values='HI',
            aggfunc='mean'
        ).fillna(0)
        
        return hi_wide
    
    def calculate_heat_index_levels(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Heat Index levels/categories for each zone in WIDE format.
        
        Returns:
            DataFrame with DateTime as rows and zones as columns (categorical values)
        """
        self.logger.info("Calculating HI levels (Heat Index categories)...")
        
        # Parse datetime
        data_frame['DateTime'] = self._parse_datetime(data_frame['Date/Time'])
        
        # Ensure RH is in valid range (0-100%)
        data_frame['RH'] = data_frame['Relative_Humidity'].clip(0, 100)
        
        # Calculate Heat Index
        data_frame['HI'] = np.where(
            (data_frame['Operative_Temperature'] <= 26.7) | (data_frame['RH'] < 40),
            data_frame['Operative_Temperature'],
            (self.HI_C1 +
             self.HI_C2 * data_frame['Operative_Temperature'] +
             self.HI_C3 * data_frame['RH'] +
             self.HI_C4 * data_frame['Operative_Temperature'] * data_frame['RH'] +
             self.HI_C5 * (data_frame['Operative_Temperature']**2) +
             self.HI_C6 * (data_frame['RH']**2) +
             self.HI_C7 * (data_frame['Operative_Temperature']**2) * data_frame['RH'] +
             self.HI_C8 * data_frame['Operative_Temperature'] * (data_frame['RH']**2) +
             self.HI_C9 * (data_frame['Operative_Temperature']**2) * (data_frame['RH']**2))
        )
        
        # Apply categories
        data_frame['HIlevel'] = data_frame['HI'].apply(self.calculate_heat_index_category)
        
        # Pivot to WIDE format
        hilevel_wide = data_frame.pivot_table(
            index='DateTime',
            columns='Zone',
            values='HIlevel',
            aggfunc='first'
        ).fillna("SAFE CONDITION")
        
        return hilevel_wide
    
    def calculate_wet_bulb_temperature(self, Ta: float, RH: float, pressure: float = 101325) -> float:
        """
        Calculate wet bulb temperature using Stull (2011) approximation.

        Args:
            Ta: Dry bulb temperature (°C)
            RH: Relative humidity (%)
            pressure: Atmospheric pressure (Pa), default = 101325 (sea level)

        Returns:
            Tw: Wet bulb temperature (°C)
        """
        # Ensure inputs are arrays
        Ta = np.array(Ta)
        RH = np.array(RH)

        # Stull (2011) formula for wet bulb temperature
        Tw = Ta * np.arctan(0.151977 * np.sqrt(RH + 8.313659)) + \
             np.arctan(Ta + RH) - np.arctan(RH - 1.676331) + \
             0.00391838 * (RH ** 1.5) * np.arctan(0.023101 * RH) - 4.686035

        return Tw

    def calculate_discomfort_index_category(self, di_value: float) -> str:
        """Categorize DI risk levels"""
        if pd.isna(di_value):
            return "INVALID DATA"
        elif di_value < 21:
            return "COMFORTABLE"
        elif di_value < 24:
            return "SLIGHTLY UNCOMFORTABLE"
        elif di_value < 27:
            return "UNCOMFORTABLE"
        elif di_value < 29:
            return "VERY UNCOMFORTABLE"
        else:
            return "DANGEROUS"

    def calculate_discomfort_index(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Discomfort Index (DI) for each zone in WIDE format.
        
        Returns:
            DataFrame with DateTime as rows and zones as columns
        """
        self.logger.info("Calculating DI (Discomfort Index)...")
        
        # Parse datetime
        data_frame['DateTime'] = self._parse_datetime(data_frame['Date/Time'])
        
        # Calculate wet bulb temperature
        valid_mask = data_frame['Outdoor_Dry_Bulb_Temperature'].notna() & data_frame['Relative_Humidity'].notna()
        data_frame['Tw'] = np.nan
        data_frame.loc[valid_mask, 'Tw'] = self.calculate_wet_bulb_temperature(
            data_frame.loc[valid_mask, 'Outdoor_Dry_Bulb_Temperature'],
            data_frame.loc[valid_mask, 'Relative_Humidity']
        )
        
        # Calculate DI
        data_frame['DI'] = 0.5 * (data_frame['Outdoor_Dry_Bulb_Temperature'] + data_frame['Tw'])
        
        # Pivot to WIDE format
        di_wide = data_frame.pivot_table(
            index='DateTime',
            columns='Zone',
            values='DI',
            aggfunc='first'  # DI is environmental, same for all zones
        ).fillna(0)
        
        return di_wide
    
    def calculate_discomfort_index_levels(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Discomfort Index levels/categories for each zone in WIDE format.
        
        Returns:
            DataFrame with DateTime as rows and zones as columns (categorical values)
        """
        self.logger.info("Calculating DI levels (Discomfort Index categories)...")
        
        # Parse datetime
        data_frame['DateTime'] = self._parse_datetime(data_frame['Date/Time'])
        
        # Calculate wet bulb temperature
        valid_mask = data_frame['Outdoor_Dry_Bulb_Temperature'].notna() & data_frame['Relative_Humidity'].notna()
        data_frame['Tw'] = np.nan
        data_frame.loc[valid_mask, 'Tw'] = self.calculate_wet_bulb_temperature(
            data_frame.loc[valid_mask, 'Outdoor_Dry_Bulb_Temperature'],
            data_frame.loc[valid_mask, 'Relative_Humidity']
        )
        
        # Calculate DI
        data_frame['DI'] = 0.5 * (data_frame['Outdoor_Dry_Bulb_Temperature'] + data_frame['Tw'])
        
        # Apply categories
        data_frame['DIlevel'] = data_frame['DI'].apply(self.calculate_discomfort_index_category)
        
        # Pivot to WIDE format
        dilevel_wide = data_frame.pivot_table(
            index='DateTime',
            columns='Zone',
            values='DIlevel',
            aggfunc='first'
        ).fillna("COMFORTABLE")
        
        return dilevel_wide
    
    def calculate_degree_weighted_discomfort_hours(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Degree-weighted Discomfort Hours (DDH) using adaptive comfort model.

        Returns:
            DataFrame with DateTime as rows and zones as columns
        """
        self.logger.info("Calculating DDH (Degree-weighted Discomfort Hours)...")
        
        # Parse datetime
        data_frame['DateTime'] = self._parse_datetime(data_frame['Date/Time'])

        # Calculate daily average external temperature
        temp_by_day = data_frame.groupby([data_frame['DateTime'].dt.floor('D'), 'Zone'])['Outdoor_Dry_Bulb_Temperature'].mean()

        # Running mean calculation (weighted average of previous 7 days)
        average_daily_previous = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.5, 5: 0.4, 6: 0.3, 7: 0.2}

        # Calculate weighted sum for each zone
        data_frame['day'] = data_frame['DateTime'].dt.floor('D')
        
        # Simplified approach: use rolling mean
        data_frame = data_frame.sort_values(['Zone', 'DateTime'])
        data_frame['theta_rm'] = data_frame.groupby('Zone')['Outdoor_Dry_Bulb_Temperature'].transform(
            lambda x: x.rolling(window=7*24, min_periods=1).mean()
        )
        
        # Neutral operative temperature
        data_frame['T_op'] = 0.33 * data_frame['theta_rm'] + 18.8
        
        # Upper comfort limit with +4°C tolerance
        data_frame['Top_up'] = data_frame['T_op'] + 4

        # Handle extreme conditions
        data_frame['Top_up'] = np.where(data_frame['theta_rm'] < 10, 18.0, data_frame['Top_up'])
        data_frame['Top_up'] = data_frame['Top_up'].clip(upper=32.7)
        
        # Calculate exceedance
        data_frame['top_minus_top_up'] = (data_frame['Operative_Temperature'] - data_frame['Top_up']).clip(lower=0)
        
        # DDH for overheating during occupied hours
        data_frame['DDH'] = data_frame['top_minus_top_up'] * (data_frame['Occupancy'] > 0).astype(int)
        
        # Pivot to WIDE format
        ddh_wide = data_frame.pivot_table(
            index='DateTime',
            columns='Zone',
            values='DDH',
            aggfunc='sum'
        ).fillna(0)
        
        return ddh_wide
    
    def _export_dataframe(self, df: pd.DataFrame, output_path: Path, export_format: str) -> Path:
        """
        Export DataFrame to specified format (CSV or XLSX).
        
        Args:
            df: DataFrame to export
            output_path: Output file path (without extension)
            export_format: Export format ('csv' or 'xlsx')
            
        Returns:
            Path: Final output file path with appropriate extension
            
        Raises:
            ImportError: If xlsx format is requested but openpyxl is not installed
        """
        if export_format == 'xlsx':
            # Check if openpyxl is available
            try:
                import openpyxl
            except ImportError:
                self.logger.error("openpyxl library not installed")
                raise ImportError(
                    "Excel export requires openpyxl library. "
                    "Install with: pip install openpyxl"
                )
            
            # Export to Excel
            output_path = output_path.with_suffix('.xlsx')
            df.to_excel(output_path, engine='openpyxl')
            self.logger.debug(f"Exported to Excel: {output_path}")
        else:  # csv (default)
            # Export to CSV
            output_path = output_path.with_suffix('.csv')
            df.to_csv(output_path)
            self.logger.debug(f"Exported to CSV: {output_path}")
        
        return output_path
    
    def export_indicators_wide(
        self,
        output_dir: Path,
        zones: List[str],
        indicators: Optional[List[str]] = None,
        export_format: str = 'csv'
    ) -> None:
        """
        Calculate and export thermal comfort indicators in WIDE format.
        
        Args:
            output_dir: Output directory for indicator files
            zones: List of zone names to analyze
            indicators: List of indicators to calculate. If None, calculates all.
            export_format: Export format - 'csv' (default) or 'xlsx'
        """
        if indicators is None:
            indicators = ['IOD', 'AWD', 'ALPHA', 'HI', 'DDH', 'DI', 'DIlevel', 'HIlevel']
        
        self.logger.info(f"Calculating indicators: {indicators} for {len(zones)} zones")
        
        # Load data from EnergyPlus CSV
        df = self._load_energyplus_data(zones)
        
        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate and export each indicator
        iod_wide = None
        awd_wide = None
        
        # IOD
        if 'IOD' in indicators:
            iod_wide = self.calculate_indoor_overheating_degree(df.copy())
            output_file = output_dir / f"IOD_{self.simulation_name}"
            output_file = self._export_dataframe(iod_wide, output_file, export_format)
            self.logger.info(f"Exported IOD to: {output_file}")
        
        # AWD
        if 'AWD' in indicators:
            awd_wide = self.calculate_ambient_warmness_degree(df.copy())
            output_file = output_dir / f"AWD_{self.simulation_name}"
            output_file = self._export_dataframe(awd_wide, output_file, export_format)
            self.logger.info(f"Exported AWD to: {output_file}")
        
        # ALPHA (requires IOD and AWD)
        if 'ALPHA' in indicators:
            if iod_wide is None:
                iod_wide = self.calculate_indoor_overheating_degree(df.copy())
            if awd_wide is None:
                awd_wide = self.calculate_ambient_warmness_degree(df.copy())
            
            alpha_wide = self.calculate_alpha(iod_wide, awd_wide)
            output_file = output_dir / f"ALPHA_{self.simulation_name}"
            output_file = self._export_dataframe(alpha_wide, output_file, export_format)
            self.logger.info(f"Exported ALPHA to: {output_file}")
        
        # HI
        if 'HI' in indicators:
            hi_wide = self.calculate_heat_index(df.copy())
            output_file = output_dir / f"HI_{self.simulation_name}"
            output_file = self._export_dataframe(hi_wide, output_file, export_format)
            self.logger.info(f"Exported HI to: {output_file}")
        
        # HIlevel
        if 'HIlevel' in indicators:
            hilevel_wide = self.calculate_heat_index_levels(df.copy())
            output_file = output_dir / f"HIlevel_{self.simulation_name}"
            output_file = self._export_dataframe(hilevel_wide, output_file, export_format)
            self.logger.info(f"Exported HIlevel to: {output_file}")
        
        # DDH
        if 'DDH' in indicators:
            ddh_wide = self.calculate_degree_weighted_discomfort_hours(df.copy())
            output_file = output_dir / f"DDH_{self.simulation_name}"
            output_file = self._export_dataframe(ddh_wide, output_file, export_format)
            self.logger.info(f"Exported DDH to: {output_file}")
        
        # DI
        if 'DI' in indicators:
            di_wide = self.calculate_discomfort_index(df.copy())
            output_file = output_dir / f"DI_{self.simulation_name}"
            output_file = self._export_dataframe(di_wide, output_file, export_format)
            self.logger.info(f"Exported DI to: {output_file}")
        
        # DIlevel
        if 'DIlevel' in indicators:
            dilevel_wide = self.calculate_discomfort_index_levels(df.copy())
            output_file = output_dir / f"DIlevel_{self.simulation_name}"
            output_file = self._export_dataframe(dilevel_wide, output_file, export_format)
            self.logger.info(f"Exported DIlevel to: {output_file}")
        
        self.logger.info(f"Successfully exported {len(indicators)} indicators to: {output_dir}")
