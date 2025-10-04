"""
Thermal comfort indicators module for ClimaMetrics.

This module provides functionality to calculate various thermal comfort indicators
from EnergyPlus simulation results, including IOD, AWD, ALPHA, HI, DDH, and DI.
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import math


class ThermalIndicators:
    """Calculator for thermal comfort indicators from EnergyPlus simulation data."""
    
    def __init__(self, csv_file: Path, simulation_name: str = "Simulation", year: int = 2020):
        """
        Initialize thermal indicators calculator.
        
        Args:
            csv_file: Path to exported thermal data CSV file
            simulation_name: Name of the simulation for output
            year: Year for datetime parsing (default: 2020)
        """
        self.logger = logging.getLogger("climametrics.indicators")
        self.csv_file = Path(csv_file)
        self.simulation_name = simulation_name
        self.year = year
        
        if not self.csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")
        
        # Constants
        self.COMFORT_TEMPERATURE = 26.5
        self.BASE_OUTSIDE_TEMPERATURE = 18
        
        # Heat Index coefficients (for °C and RH as decimal) - V4 version
        self.HI_C1 = -8.784694
        self.HI_C2 = 1.611394
        self.HI_C3 = 2.338548
        self.HI_C4 = -0.146116
        self.HI_C5 = -0.012308
        self.HI_C6 = -0.016424
        self.HI_C7 = 0.002211
        self.HI_C8 = 0.000725
        self.HI_C9 = -0.000003
        
        self.logger.info(f"Initialized thermal indicators calculator with file: {self.csv_file}")
    
    def load_data(self) -> pd.DataFrame:
        """
        Load thermal data from CSV file.
        
        Returns:
            DataFrame with thermal data
        """
        self.logger.info("Loading thermal data...")
        
        try:
            df = pd.read_csv(self.csv_file, sep=';', low_memory=False)
            self.logger.info(f"Loaded {len(df)} rows and {len(df.columns)} columns")
            return df
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
            raise
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for calculations by ensuring required columns exist.
        
        Args:
            df: DataFrame with thermal data
            
        Returns:
            DataFrame prepared for calculations
        """
        df_prepared = df.copy()
        
        # Add ZONE column if not present (for compatibility with existing functions)
        if 'ZONE' not in df_prepared.columns and 'Zone' in df_prepared.columns:
            df_prepared['ZONE'] = df_prepared['Zone']
        elif 'ZONE' not in df_prepared.columns and 'ZONE_NAME' in df_prepared.columns:
            df_prepared['ZONE'] = df_prepared['ZONE_NAME']
        
        # Add ZONE_NAME column if not present (for compatibility with existing functions)
        if 'ZONE_NAME' not in df_prepared.columns and 'Zone' in df_prepared.columns:
            df_prepared['ZONE_NAME'] = df_prepared['Zone']
        
        return df_prepared
    
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
    
    def calculate_indoor_overheating_degree(self, data_frame: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calculate Indoor Overheating Degree (IOD) for each zone.
        IOD = Average excess temperature above comfort during occupied hours

        FORMULA:
        IOD = Σ(Top - Tcomf) / Σ(Occupied_hours)

        Where:
        - Top = Operative temperature (°C)
        - Tcomf = Comfort temperature (26.5°C)
        - Σ(Top - Tcomf) = Sum of positive temperature excess during occupied overheating periods
        - Σ(Occupied_hours) = Total occupied hours in the analysis period
        - Only periods where Top > Tcomf AND Occupied > 0 are considered for the numerator
        - All occupied hours (regardless of overheating) are considered for the denominator

        Units: °C (degrees Celsius)

        Interpretation:
        - IOD = 0: No overheating during occupied periods
        - IOD > 0: Average temperature excess above comfort during occupation
        - Higher IOD values indicate worse thermal comfort performance

        Returns:
        - data_frame_iod: Detailed hourly data with overheating calculations
        - iod_by_zone: Summary with IOD values per zone
        """
        data_frame_iod = pd.DataFrame()
        data_frame_iod['i'] = self._parse_datetime(data_frame['Date/Time'])
        data_frame_iod['Top'] = data_frame['Operative_Temperature']
        data_frame_iod['Tcomf'] = self.COMFORT_TEMPERATURE
        data_frame_iod['Top_minus_Tcomf'] = data_frame_iod['Top'] - data_frame_iod['Tcomf']
        data_frame_iod['Occupied'] = data_frame['Occupancy']
        data_frame_iod['ZONE'] = data_frame['ZONE']
        data_frame_iod['ZONE_NAME'] = data_frame['ZONE_NAME']

        # Create flag for overheating during occupied hours
        data_frame_iod['overheating_flag'] = np.where(
            (data_frame_iod['Top_minus_Tcomf'] > 0) & (data_frame['Occupancy'] > 0),
            1, 0
        )  # Only count positive excess over comfort temperature during occupied periods

        # Set excess temperature to 0 when not overheating or not occupied
        data_frame_iod['excess_temp'] = np.where(
            data_frame_iod['overheating_flag'] == 1,
            data_frame_iod['Top_minus_Tcomf'],
            np.nan
        )

        # Calculate IOD by zone (average excess temperature during occupied hours)
        iod_by_zone = data_frame_iod.groupby(['ZONE', 'ZONE_NAME']).agg({
            'excess_temp': 'sum',           # Total excess temperature
            'Occupied': 'sum'               # Total occupied hours
        }).reset_index()

        # Calculate IOD = Total excess / Total occupied hours
        iod_by_zone['IOD'] = np.where(
            iod_by_zone['Occupied'] > 0,
            iod_by_zone['excess_temp'] / iod_by_zone['Occupied'],
            0  # IOD = 0 if never occupied
        )

        return data_frame_iod, iod_by_zone
    
    def calculate_ambient_warmness_degree(self, data_frame: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calculate Ambient Warmness Degree (AWD) for environmental conditions.
        AWD = Average excess ambient temperature above base temperature

        FORMULA:
        AWD = Σ(Tai - Tb) / N_total

        Where:
        - Tai = Ambient air temperature (°C)
        - Tb = Base outside temperature (18°C)
        - Σ(Tai - Tb) = Sum of positive temperature excess above base temperature
        - N_total = Total number of time steps in the analysis period (all hours)
        - Only periods where Tai > Tb contribute to the numerator
        - All time steps (regardless of warmness) are considered for the denominator

        Units: °C (degrees Celsius)

        Interpretation:
        - AWD = 0: No ambient warmness (average temperature ≤ base temperature)
        - AWD > 0: Average ambient temperature excess above base temperature
        - Higher AWD values indicate warmer environmental conditions
        - AWD is environmental (same value for all zones in a simulation)

        Note: AWD represents the external thermal stress that buildings must cope with

        Returns:
        - data_frame_awd: Detailed hourly data with warmness calculations
        - awd_summary: Summary with AWD values (typically one value per simulation)
        """
        data_frame_awd = pd.DataFrame()
        data_frame_awd['i'] = self._parse_datetime(data_frame['Date/Time'])
        data_frame_awd['Tai'] = data_frame['Outdoor_Dry_Bulb_Temperature']
        data_frame_awd['Tb'] = self.BASE_OUTSIDE_TEMPERATURE
        data_frame_awd['Tai_minus_Tb'] = data_frame_awd['Tai'] - data_frame_awd['Tb']
        data_frame_awd['ZONE'] = data_frame['ZONE']
        data_frame_awd['ZONE_NAME'] = data_frame['ZONE_NAME']

        # Create flag for warmness periods
        data_frame_awd['warmness_flag'] = np.where(
            (data_frame_awd['Tai_minus_Tb'] > 0),
            1, 0
        )

        # Set excess temperature to 0 when not warm
        data_frame_awd['excess_temp'] = np.where(
            data_frame_awd['warmness_flag'] == 1,
            data_frame_awd['Tai_minus_Tb'],
            np.nan
        )

        # Calculate AWD (ambient is same for all zones, so take total)
        total_excess_temp = data_frame_awd['excess_temp'].sum()
        total_time_steps = len(data_frame_awd)  # All time steps

        awd_value = total_excess_temp / total_time_steps if total_time_steps > 0 else 0

        # Create summary (AWD is environmental, same for all zones)
        awd_summary = pd.DataFrame({
            'AWD': [awd_value],
            'total_excess_temp': [total_excess_temp],
            'total_time_steps': [total_time_steps]
        })

        return data_frame_awd, awd_summary
    
    def calculate_alfa_data_frame_v2(self, data_frame_iod: pd.DataFrame, data_frame_awd: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ALFA as IOD / AWD.
        Conditions:
        - Only calculate when AWD != 0
        - If IOD or AWD are NaN → result = NaN
        - Invalid periods return NaN
        """
        df_alfa_data_frame = pd.DataFrame()

        # Copy key columns (assuming both DFs are aligned by index)
        df_alfa_data_frame['i'] = data_frame_iod['i']  # Already parsed datetime
        df_alfa_data_frame['ZONE'] = data_frame_iod['ZONE']
        df_alfa_data_frame['ZONE_NAME'] = data_frame_iod['ZONE_NAME']

        # Calculate ALFA safely
        df_alfa_data_frame['alpha_hourly'] = np.where(
            (data_frame_awd['excess_temp'].notna()) &
            (data_frame_iod['excess_temp'].notna()) &
            (data_frame_awd['excess_temp'] != 0),
            data_frame_iod['excess_temp'] / data_frame_awd['excess_temp'],
            np.nan
        )

        return df_alfa_data_frame
    
    def celsius_to_fahrenheit(self, celsius: float) -> float:
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9/5) + 32

    def fahrenheit_to_celsius(self, fahrenheit: float) -> float:
        """Convert Fahrenheit to Celsius"""
        return (fahrenheit - 32) * 5/9

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
        - T = Dry bulb temperature (°C)
        - RH = Relative humidity (decimal, 0.0-1.0)
        - C1 to C9 = V4 regression coefficients

        Returns:
        - DataFrame with Heat Index values and risk categories
        """
        data_frame_hi = pd.DataFrame()
        data_frame_hi['i'] = self._parse_datetime(data_frame['Date/Time'])
        data_frame_hi['T_celsius'] = data_frame['Outdoor_Dry_Bulb_Temperature']
        data_frame_hi['RH_percent'] = data_frame['Relative_Humidity']
        data_frame_hi['ZONE'] = data_frame['ZONE']
        data_frame_hi['ZONE_NAME'] = data_frame['ZONE_NAME']

        # Validate input data
        data_frame_hi['T_celsius'] = pd.to_numeric(data_frame_hi['T_celsius'], errors='coerce')
        data_frame_hi['RH_percent'] = pd.to_numeric(data_frame_hi['RH_percent'], errors='coerce')

        # Clip humidity to valid range (0-100%)
        data_frame_hi['RH_percent'] = data_frame_hi['RH_percent'].clip(0, 100)

        # Convert humidity to decimal (0.0-1.0) for formula
        data_frame_hi['RH_decimal'] = data_frame_hi['RH_percent'] / 100.0

        # Apply Heat Index formula (V4 version - using Celsius directly)
        data_frame_hi['HI'] = np.where(
            (data_frame_hi['T_celsius'] <= 26.7) | (data_frame_hi['RH_percent'] < 40),
            data_frame_hi['T_celsius'],  # Simple approximation for low temp/humidity
            (self.HI_C1 +
             self.HI_C2 * data_frame_hi['T_celsius'] +
             self.HI_C3 * data_frame_hi['RH_decimal'] +
             self.HI_C4 * data_frame_hi['T_celsius'] * data_frame_hi['RH_decimal'] +
             self.HI_C5 * (data_frame_hi['T_celsius']**2) +
             self.HI_C6 * (data_frame_hi['RH_decimal']**2) +
             self.HI_C7 * (data_frame_hi['T_celsius']**2) * data_frame_hi['RH_decimal'] +
             self.HI_C8 * data_frame_hi['T_celsius'] * (data_frame_hi['RH_decimal']**2) +
             self.HI_C9 * (data_frame_hi['T_celsius']**2) * (data_frame_hi['RH_decimal']**2))
        )

        # Handle invalid cases (NaN values)
        data_frame_hi['HI'] = np.where(
            data_frame_hi['T_celsius'].isna() | data_frame_hi['RH_percent'].isna(),
            np.nan,
            data_frame_hi['HI']
        )

        data_frame_hi['HAZARD_CATEGORY'] = data_frame_hi['HI'].apply(self.calculate_heat_index_category)

        return data_frame_hi
    
    def calculate_wet_bulb_temperature(self, Ta: float, RH: float, pressure: float = 101325) -> float:
        """
        Calculate wet bulb temperature using Stull (2011) approximation.

        This is a simplified but accurate formula for calculating wet bulb temperature
        from dry bulb temperature and relative humidity.

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

    def calculate_di_levels(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Discomfort Index (DI) levels/categories for outdoor thermal comfort assessment.
        
        Returns:
        - DataFrame with DI level categories
        """
        data_frame_di = self.calculate_discomfort_index(data_frame)
        
        # Add level categories
        data_frame_di['DIlevel'] = data_frame_di['DI'].apply(self.calculate_discomfort_index_category)
        
        # Create result DataFrame with levels
        result_df = data_frame_di[['i', 'ZONE_NAME', 'DIlevel']].copy()
        result_df['Value'] = result_df['DIlevel']
        result_df['Indicator'] = 'DIlevel'
        result_df['Simulation'] = self.simulation_name
        result_df = result_df[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
        
        return result_df
    
    def calculate_hi_levels(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Heat Index (HI) levels/categories for apparent temperature assessment.
        
        Returns:
        - DataFrame with HI level categories
        """
        data_frame_hi = self.calculate_heat_index(data_frame)
        
        # Add level categories
        data_frame_hi['HIlevel'] = data_frame_hi['HI'].apply(self.calculate_heat_index_category)
        
        # Create result DataFrame with levels
        result_df = data_frame_hi[['i', 'ZONE_NAME', 'HIlevel']].copy()
        result_df['Value'] = result_df['HIlevel']
        result_df['Indicator'] = 'HIlevel'
        result_df['Simulation'] = self.simulation_name
        result_df = result_df[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
        
        return result_df

    def calculate_discomfort_index(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Discomfort Index (DI) for outdoor thermal comfort assessment.

        DI combines dry bulb temperature and wet bulb temperature to assess human thermal discomfort.

        Formula: DI = 0.5 × (Ta + Tw)
        Where:
        - Ta = Dry bulb temperature (°C)
        - Tw = Wet bulb temperature (°C)

        Returns:
        - DataFrame with DI values and comfort categories
        """
        data_frame_di = pd.DataFrame()
        data_frame_di['i'] = self._parse_datetime(data_frame['Date/Time'])

        # Input data validation
        data_frame_di['Ta'] = pd.to_numeric(data_frame['Outdoor_Dry_Bulb_Temperature'], errors='coerce')  # Dry bulb
        data_frame_di['Td'] = pd.to_numeric(data_frame['Outdoor_Dewpoint_Temperature'], errors='coerce')  # Dew point
        data_frame_di['RH'] = pd.to_numeric(data_frame['Relative_Humidity'], errors='coerce')  # Relative humidity
        data_frame_di['ZONE'] = data_frame['ZONE']
        data_frame_di['ZONE_NAME'] = data_frame['ZONE_NAME']

        # Validate input ranges
        invalid_ta_mask = (data_frame_di['Ta'] < -40) | (data_frame_di['Ta'] > 60)
        invalid_td_mask = (data_frame_di['Td'] < -50) | (data_frame_di['Td'] > 50)
        invalid_rh_mask = (data_frame_di['RH'] < 0) | (data_frame_di['RH'] > 100)

        if invalid_ta_mask.any():
            self.logger.warning(f"{invalid_ta_mask.sum()} invalid dry bulb temperatures found (outside -40°C to 60°C)")
            data_frame_di.loc[invalid_ta_mask, 'Ta'] = np.nan

        if invalid_td_mask.any():
            self.logger.warning(f"{invalid_td_mask.sum()} invalid dew point temperatures found (outside -50°C to 50°C)")
            data_frame_di.loc[invalid_td_mask, 'Td'] = np.nan

        if invalid_rh_mask.any():
            self.logger.warning(f"{invalid_rh_mask.sum()} invalid relative humidity values found (outside 0-100%)")
            data_frame_di.loc[invalid_rh_mask, 'RH'] = np.nan

        # Check physical constraint: Td should be <= Ta
        invalid_physics_mask = data_frame_di['Td'] > data_frame_di['Ta']
        if invalid_physics_mask.any():
            self.logger.warning(f"{invalid_physics_mask.sum()} cases where dew point > dry bulb temperature (physically impossible)")
            data_frame_di.loc[invalid_physics_mask, ['Ta', 'Td']] = np.nan

        # Calculate wet bulb temperature using existing relative humidity
        valid_mask = data_frame_di['Ta'].notna() & data_frame_di['RH'].notna()
        data_frame_di['Tw_calculated'] = np.nan
        data_frame_di.loc[valid_mask, 'Tw_calculated'] = self.calculate_wet_bulb_temperature(
            data_frame_di.loc[valid_mask, 'Ta'],
            data_frame_di.loc[valid_mask, 'RH']
        )

        # Calculate Discomfort Index using correct formula
        data_frame_di['DI'] = 0.5 * (data_frame_di['Ta'] + data_frame_di['Tw_calculated'])

        data_frame_di['HAZARD_CATEGORY'] = data_frame_di['DI'].apply(self.calculate_discomfort_index_category)

        return data_frame_di
    
    def calculate_degree_weighted_discomfort_hours(self, data_frame: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calculate Degree-weighted Discomfort Hours (DDH) using adaptive comfort model.

        DDH quantifies thermal discomfort by weighting hours of overheating by the
        magnitude of temperature excess above adaptive comfort limits.

        Returns:
        - data_frame_ddh: Detailed hourly data with DDH calculations
        - ddh_summary: DDH totals by zone
        """
        data_frame_ddh = pd.DataFrame()
        data_frame_ddh['i'] = self._parse_datetime(data_frame['Date/Time'])

        # Input data validation
        data_frame_ddh['Occ'] = pd.to_numeric(data_frame['Occupancy'], errors='coerce').fillna(0)
        data_frame_ddh['T_ext'] = pd.to_numeric(data_frame['Outdoor_Dry_Bulb_Temperature'], errors='coerce')
        data_frame_ddh['Top'] = pd.to_numeric(data_frame['Operative_Temperature'], errors='coerce')
        data_frame_ddh['ZONE'] = data_frame['ZONE']
        data_frame_ddh['ZONE_NAME'] = data_frame['ZONE_NAME']

        # Validate external temperature range (-20°C to 50°C)
        invalid_temp_mask = (data_frame_ddh['T_ext'] < -20) | (data_frame_ddh['T_ext'] > 50)
        if invalid_temp_mask.any():
            self.logger.warning(f"{invalid_temp_mask.sum()} invalid external temperatures found (outside -20°C to 50°C)")
            data_frame_ddh.loc[invalid_temp_mask, 'T_ext'] = np.nan

        # Calculate daily average external temperature
        T_daily_average = (data_frame_ddh.set_index('i')['T_ext']
                          .resample('D')
                          .mean()
                          .rename('T_daily_average'))

        # Running mean calculation (weighted average of previous 7 days)
        # Weights according to EN 15251: [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]
        average_daily_previous = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.5, 5: 0.4, 6: 0.3, 7: 0.2}

        # Calculate weighted sum of previous days
        average_daily_previous_by_day = sum(
            T_daily_average.shift(k) * average_daily_previous[k]
            for k in average_daily_previous
        )

        # Running mean temperature (θ_rm)
        theta_rm = (average_daily_previous_by_day / 3.8).rename('theta_rm')

        # Neutral operative temperature (EN 15251 formula)
        T_op = (0.33 * theta_rm + 18.8).rename('T_op')

        # Upper comfort limit with +4°C tolerance (Category II)
        Top_up_raw = (T_op + 4).rename('Top_up_raw')

        # Apply validity ranges and extreme condition handling
        mask_10_between_30 = theta_rm.between(10, 30, inclusive='both')

        # Handle extreme conditions
        Top_up_daily = Top_up_raw.copy()

        # For θ_rm < 10°C: Use fixed limit of 18°C (cold climate)
        Top_up_daily = Top_up_daily.where(theta_rm >= 10, 18.0)

        # For θ_rm > 30°C: Limit to maximum 32.7°C (hot climate)
        Top_up_daily = Top_up_daily.clip(upper=32.7)

        # For normal range (10-30°C): Use adaptive formula
        Top_up_daily = Top_up_daily.where(
            mask_10_between_30 | (theta_rm < 10) | (theta_rm > 30)
        )

        Top_up_daily = Top_up_daily.rename('Top_up_daily')

        # Optional: Calculate lower comfort limit for future use
        Top_low_daily = (T_op - 4).rename('Top_low_daily')
        Top_low_daily = Top_low_daily.where(theta_rm >= 10, 18.0)  # Fixed lower limit for cold
        Top_low_daily = Top_low_daily.where(mask_10_between_30 | (theta_rm < 10))

        # Merge daily limits with hourly data
        data_frame_ddh['day'] = data_frame_ddh['i'].dt.floor('D')
        data_frame_ddh = data_frame_ddh.merge(
            Top_up_daily.to_frame(name='Top_up_d'),
            left_on='day',
            right_index=True,
            how='left'
        )
        data_frame_ddh = data_frame_ddh.merge(
            Top_low_daily.to_frame(name='Top_low_d'),
            left_on='day',
            right_index=True,
            how='left'
        )

        # Add running mean for reference
        data_frame_ddh = data_frame_ddh.merge(
            theta_rm.to_frame(name='theta_rm'),
            left_on='day',
            right_index=True,
            how='left'
        )

        # Occupancy flag
        data_frame_ddh['Occ_flag'] = (data_frame_ddh['Occ'] > 0).astype(int)

        # Calculate exceedance above upper limit (only positive values)
        data_frame_ddh['top_minus_top_up'] = (
            data_frame_ddh['Top'] - data_frame_ddh['Top_up_d']
        ).clip(lower=0)

        # DDH for overheating (upper limit exceedance during occupied hours)
        data_frame_ddh['HDDH_upper'] = (
            data_frame_ddh['top_minus_top_up'] * data_frame_ddh['Occ_flag']
        )

        # Optional: DDH for overcooling (lower limit exceedance during occupied hours)
        data_frame_ddh['top_low_minus_top'] = (
            data_frame_ddh['Top_low_d'] - data_frame_ddh['Top']
        ).clip(lower=0)
        data_frame_ddh['DDH_lower'] = (
            data_frame_ddh['top_low_minus_top'] * data_frame_ddh['Occ_flag']
        )

        # Legacy column names for backward compatibility
        data_frame_ddh['HDDH_UP'] = data_frame_ddh['HDDH_upper']

        # Calculate DDH summary by zone
        ddh_summary = data_frame_ddh.groupby(['ZONE', 'ZONE_NAME']).agg({
            'HDDH_upper': 'sum',          # Total DDH for overheating
            'DDH_lower': 'sum',          # Total DDH for overcooling
            'Occ_flag': 'sum',           # Total occupied hours
            'top_minus_top_up': 'sum',   # Total temperature excess
            'theta_rm': 'mean'           # Average running mean temperature
        }).reset_index()

        # Calculate average exceedance when overheating occurs
        ddh_summary['avg_exceedance_when_hot'] = np.where(
            ddh_summary['HDDH_upper'] > 0,
            ddh_summary['top_minus_top_up'] / ddh_summary['HDDH_upper'],
            0
        )

        return data_frame_ddh, ddh_summary
    
    def calculate_all_indicators(self, indicators: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Calculate all thermal comfort indicators and return consolidated results.
        
        Args:
            indicators: List of indicators to calculate. If None, calculates all.
            
        Returns:
            DataFrame with columns: DateTime, Zone, Value, Simulation, Indicator
        """
        if indicators is None:
            indicators = ['IOD', 'AWD', 'ALPHA', 'HI', 'DDH', 'DI', 'DIlevel', 'HIlevel']
        
        self.logger.info(f"Calculating indicators: {indicators}")
        
        # Load and prepare data
        df = self.load_data()
        df_prepared = self._prepare_data(df)
        
        all_results = []
        
        # Calculate IOD
        if 'IOD' in indicators:
            self.logger.info("Calculating IOD...")
            data_frame_iod, iod_by_zone = self.calculate_indoor_overheating_degree(df_prepared)
            
            # Create hourly IOD data
            iod_hourly = data_frame_iod[['i', 'ZONE_NAME', 'excess_temp']].copy()
            iod_hourly['Value'] = iod_hourly['excess_temp']
            iod_hourly['Indicator'] = 'IOD'
            iod_hourly['Simulation'] = self.simulation_name
            iod_hourly = iod_hourly[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
            all_results.append(iod_hourly)
        
        # Calculate AWD
        if 'AWD' in indicators:
            self.logger.info("Calculating AWD...")
            data_frame_awd, awd_summary = self.calculate_ambient_warmness_degree(df_prepared)
            
            # Create hourly AWD data
            awd_hourly = data_frame_awd[['i', 'ZONE_NAME', 'excess_temp']].copy()
            awd_hourly['Value'] = awd_hourly['excess_temp']
            awd_hourly['Indicator'] = 'AWD'
            awd_hourly['Simulation'] = self.simulation_name
            awd_hourly = awd_hourly[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
            all_results.append(awd_hourly)
        
        # Calculate ALPHA
        if 'ALPHA' in indicators and 'IOD' in indicators and 'AWD' in indicators:
            self.logger.info("Calculating ALPHA...")
            data_frame_alfa = self.calculate_alfa_data_frame_v2(data_frame_iod, data_frame_awd)
            
            # Create hourly ALPHA data
            alfa_hourly = data_frame_alfa[['i', 'ZONE_NAME', 'alpha_hourly']].copy()
            alfa_hourly['Value'] = alfa_hourly['alpha_hourly']
            alfa_hourly['Indicator'] = 'ALPHA'
            alfa_hourly['Simulation'] = self.simulation_name
            alfa_hourly = alfa_hourly[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
            all_results.append(alfa_hourly)
        
        # Calculate HI
        if 'HI' in indicators:
            self.logger.info("Calculating HI...")
            data_frame_hi = self.calculate_heat_index(df_prepared)
            
            # Create hourly HI data
            hi_hourly = data_frame_hi[['i', 'ZONE_NAME', 'HI']].copy()
            hi_hourly['Value'] = hi_hourly['HI']
            hi_hourly['Indicator'] = 'HI'
            hi_hourly['Simulation'] = self.simulation_name
            hi_hourly = hi_hourly[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
            all_results.append(hi_hourly)
        
        # Calculate DDH
        if 'DDH' in indicators:
            self.logger.info("Calculating DDH...")
            data_frame_ddh, ddh_summary = self.calculate_degree_weighted_discomfort_hours(df_prepared)
            
            # Create hourly DDH data
            ddh_hourly = data_frame_ddh[['i', 'ZONE_NAME', 'HDDH_UP']].copy()
            ddh_hourly['Value'] = ddh_hourly['HDDH_UP']
            ddh_hourly['Indicator'] = 'DDH'
            ddh_hourly['Simulation'] = self.simulation_name
            ddh_hourly = ddh_hourly[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
            all_results.append(ddh_hourly)
        
        # Calculate DI
        if 'DI' in indicators:
            self.logger.info("Calculating DI...")
            data_frame_di = self.calculate_discomfort_index(df_prepared)
            
            # Create hourly DI data
            di_hourly = data_frame_di[['i', 'ZONE_NAME', 'DI']].copy()
            di_hourly['Value'] = di_hourly['DI']
            di_hourly['Indicator'] = 'DI'
            di_hourly['Simulation'] = self.simulation_name
            di_hourly = di_hourly[['i', 'ZONE_NAME', 'Value', 'Simulation', 'Indicator']].rename(columns={'i': 'DateTime', 'ZONE_NAME': 'Zone'})
            all_results.append(di_hourly)
        
        # Calculate DI levels
        if 'DIlevel' in indicators:
            self.logger.info("Calculating DI levels...")
            di_levels = self.calculate_di_levels(df_prepared)
            all_results.append(di_levels)
        
        # Calculate HI levels
        if 'HIlevel' in indicators:
            self.logger.info("Calculating HI levels...")
            hi_levels = self.calculate_hi_levels(df_prepared)
            all_results.append(hi_levels)
        
        # Combine all results
        if all_results:
            final_df = pd.concat(all_results, ignore_index=True)
            final_df = final_df.dropna(subset=['Value'])  # Remove rows with invalid values
            
            self.logger.info(f"Calculated {len(final_df)} indicator values")
            return final_df
        else:
            self.logger.warning("No indicators calculated")
            return pd.DataFrame(columns=['DateTime', 'Zone', 'Value', 'Simulation', 'Indicator'])
    
    def export_indicators(self, output_file: Path, indicators: Optional[List[str]] = None) -> None:
        """
        Export thermal comfort indicators to CSV file.
        
        Args:
            output_file: Output CSV file path
            indicators: List of indicators to calculate. If None, calculates all.
        """
        self.logger.info("Starting indicators export...")
        
        # Calculate indicators
        indicators_df = self.calculate_all_indicators(indicators)
        
        if indicators_df.empty:
            self.logger.error("No indicators to export")
            return
        
        # Create output directory
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        indicators_df.to_csv(output_file, index=False)
        
        self.logger.info(f"Indicators exported to: {output_file}")
        self.logger.info(f"Exported {len(indicators_df)} records for {indicators_df['Indicator'].nunique()} indicators")
