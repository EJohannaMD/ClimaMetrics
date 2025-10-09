# ClimaMetrics

EnergyPlus simulation management tool with CLI interface.

## Overview

ClimaMetrics is a command-line tool for managing and executing EnergyPlus simulations with support for parallel processing, configuration management, and comprehensive logging.

## Features

- **CLI Interface**: Easy-to-use command-line interface with Click
- **Parallel Processing**: Run multiple simulations in parallel
- **Configuration Management**: YAML-based configuration system
- **Comprehensive Logging**: Structured logging with file and console output
- **File Validation**: Automatic validation of IDF and weather files
- **Data Export**: Extract and export zone-specific thermal data from simulation results with auto-generated filenames
- **Data Consolidation (Pivot)**: Consolidate variables from multiple zones into unified CSV files for comparative analysis
- **Heat Gain Variables**: Export detailed infiltration and internal heat gain/loss variables (sensible, latent, total)
- **Column Mapping**: Automatic display of exported columns with their original EnergyPlus variable names
- **Thermal Indicators**: Calculate thermal comfort indicators (IOD, AWD, ALPHA, HI, DDH, DI) - [Formulas](docs/INDICATORS.md) | [Examples](docs/EXAMPLES.md)
- **Power BI Export**: Export indicators in ULTRA-LONG format optimized for Power BI dashboards and advanced analytics
- **IDF Analysis**: Analyze IDF files to extract building, zone, and material information
- **Column Explorer**: Explore and filter column headers from EnergyPlus CSV output files
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ClimaMetrics
```

2. Use venv in windows
```bash
.\.venv\Scripts\activate.ps1
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install the package in development mode:
```bash
pip install -e .
```

## Configuration

1. Place your IDF files in `data/idf/`
2. Place your weather files in `data/weather/`
3. Configure EnergyPlus paths in `config/energyplus_paths.yaml`
4. Adjust settings in `config/settings.yaml` if needed

## Usage

### Basic Commands

```bash
# List available simulations
energyplus-sim list

# Run all simulations
energyplus-sim run --all

# Run specific simulations by index
energyplus-sim run --select 0,1,2

# Run with specific files
energyplus-sim run --idf file.idf --weather file.epw

# Run sequentially instead of parallel
energyplus-sim run --all --sequential

# Check status
energyplus-sim status

# Clean output directory
energyplus-sim clean

# Analyze IDF file
energyplus-sim analyze building.idf

# Analyze specific aspects
energyplus-sim analyze building.idf --zones --materials

# Export thermal data to CSV (auto-generates output filename)
energyplus-sim export results.csv --zones "ZONE1,ZONE2"

# Calculate thermal comfort indicators
energyplus-sim indicators results.csv --zone-group studyrooms --simulation "Baseline"

# Export indicators for Power BI analysis
energyplus-sim powerbi results.csv --zone-group studyrooms --simulation "Baseline"

# Consolidate variables across zones
energyplus-sim export outputs/results/simulation/results.csv --zones "ZONE1"

# Export with custom output
energyplus-sim export results.csv --zones "ZONE1,ZONE2" --output custom.csv

# Export with date range
energyplus-sim export results.csv --start-date "01/01" --end-date "12/31"

# Export with summary
energyplus-sim export results.csv --summary

# Consolidate variable from multiple zones (pivot)
energyplus-sim pivot --variable "Operative_Temperature"

# Pivot multiple variables with year and simulation
energyplus-sim pivot -v "Operative_Temperature,Air_Temperature" -y 2020 -s "Baseline_TMY2020s"

# Pivot with custom options
energyplus-sim pivot --variable "Air_Temperature" --dir "outputs/exports/" --summary

# Explore column headers
energyplus-sim columns simulation_results.csv

# Filter columns by zone
energyplus-sim columns simulation_results.csv --zone "0XPLANTABAJA:ZONA4"

# Search for specific patterns
energyplus-sim columns simulation_results.csv --pattern "Temperature"

# Calculate thermal comfort indicators
energyplus-sim indicators thermal_data.csv --simulation "Baseline_TMY2020s"

# Calculate specific indicators
energyplus-sim indicators thermal_data.csv --indicators "IOD,AWD,HI"

# Calculate with custom parameters
energyplus-sim indicators thermal_data.csv --comfort-temp 25.0 --base-temp 20.0
```

### Advanced Options

```bash
# Verbose logging
energyplus-sim --verbose run --all

# Quiet mode
energyplus-sim --quiet run --all

# Custom output directory
energyplus-sim run --all --output-dir /path/to/output
```

## Directory Structure

```
ClimaMetrics/
├── src/                    # Source code
│   ├── cli.py             # CLI interface
│   ├── simulation.py      # Simulation logic
│   ├── config.py          # Configuration management
│   ├── utils.py           # Utility functions
│   ├── idf_analyzer.py    # IDF file analysis
│   ├── csv_exporter.py    # CSV data export (zone-specific)
│   ├── csv_pivot.py       # CSV pivot consolidation (multi-zone)
│   ├── column_explorer.py # Column header exploration
│   ├── indicators.py      # Thermal comfort indicators
│   └── powerbi_exporter.py # Power BI format export (ULTRA-LONG)
├── data/                   # Input data
│   ├── idf/               # IDF files
│   └── weather/           # Weather files
├── outputs/                # Output data
│   ├── results/           # Simulation results (EnergyPlus output)
│   ├── exports/           # Exported thermal data (zone-specific CSV)
│   ├── pivots/            # Consolidated data (multi-zone CSV)
│   ├── indicators/        # Thermal comfort indicators (WIDE format)
│   ├── powerbi/           # Power BI exports (ULTRA-LONG format)
│   └── logs/              # Log files
├── config/                 # Configuration files
│   ├── settings.yaml      # Main settings
│   └── energyplus_paths.yaml  # EnergyPlus paths
├── docs/                   # Documentation
│   ├── INDICATORS.md      # Thermal comfort indicators formulas
│   └── EXAMPLES.md        # Practical calculation examples
└── tests/                  # Test files
```

## Output Files Description

EnergyPlus generates several output files for each simulation. Here's a description of each file type:

### Status and Control Files
- **`.end`**: Simulation completion status and summary statistics
- **`.audit`**: Simulation audit information including variable counts and memory usage
- **`.err`**: Error and warning messages generated during simulation
- **`.rvaudit`**: Read variables audit information

### Data Output Files
- **`.csv`**: Main output file containing all hourly time series data (largest file)
- **`.eso`**: EnergyPlus Standard Output file with detailed simulation results
- **`.mtr.csv`**: Energy meter data in CSV format
- **`.mtr`**: Energy meter data in binary format

### Metadata and Reference Files
- **`.rdd`**: Report Data Dictionary - lists all available output variables
- **`.mdd`**: Meter Data Dictionary - lists all available energy meters
- **`.edd`**: EnergyPlus Data Dictionary - comprehensive data dictionary
- **`.eio`**: EnergyPlus Input Output - processed input data summary
- **`.bnd`**: Boundary conditions and HVAC system connections
- **`.mtd`**: Meter details and energy consumption breakdown

### Report Files
- **`.tbl.htm`**: HTML report with annual building performance summary
- **`.tbl.tab`**: Tabular report in text format with key performance metrics

### Visualization Files
- **`.dxf`**: AutoCAD DXF file for 3D building visualization
- **`.shd`**: Shading data for solar analysis and visualization

### File Sizes and Usage
- **Large files** (1GB+): `.csv`, `.eso` - contain detailed time series data
- **Medium files** (50-100MB): `.mtr.csv`, `.mtr` - energy consumption data
- **Small files** (<1MB): Status, metadata, and report files

### Typical Analysis Workflow
1. Check `.end` file for simulation success
2. Review `.err` file for warnings and errors
3. Use `.tbl.htm` for quick performance overview
4. Analyze `.csv` file for detailed time series analysis
5. Use `.rdd` to understand available output variables

## Thermal Analysis Variables

When exporting thermal data for building performance analysis, the following variables are available:

### Core Thermal Variables
- **Date/Time**: Timestamp of the simulation data point (typically hourly)
- **Operative Temperature**: Average of air temperature and mean radiant temperature, representing the actual thermal sensation experienced by occupants
- **Air Temperature**: Temperature of the air within the zone (in Celsius)
- **Relative Humidity**: Percentage of moisture in the air relative to the maximum possible at that temperature
- **Outdoor Dry Bulb Temperature**: External air temperature measured in the shade (in Celsius)
- **Outdoor Dewpoint Temperature**: External air temperature at which condensation occurs, indicating moisture content (in Celsius)

### Occupancy and Usage
- **Occupancy**: Number of people present in the zone at each time step
- **Zone**: Name of the thermal zone being analyzed

### Variable Descriptions
- **Operative Temperature**: This is the most important thermal comfort parameter as it combines both air temperature and radiant temperature effects. It represents the temperature that occupants actually "feel" and is used for thermal comfort analysis.
- **Air Temperature**: The temperature of the air mass within the zone, measured at a standard height (usually 1.1m above floor level).
- **Relative Humidity**: Indicates the moisture content of the air. Values between 30-70% are generally considered comfortable for most people.
- **Outdoor Dry Bulb Temperature**: The external temperature that affects the building's thermal loads and energy consumption.
- **Outdoor Dewpoint Temperature**: The external temperature at which water vapor condenses, indicating the moisture content of outdoor air. Used for condensation analysis and humidity control.
- **Occupancy**: The number of people in the zone affects internal heat gains, ventilation requirements, and thermal comfort.
- **Zone**: Identifies which specific thermal zone the data refers to, allowing analysis of different building areas separately.

### Typical Use Cases
- **Thermal Comfort Analysis**: Using operative temperature and relative humidity to assess comfort conditions
- **Energy Performance**: Analyzing temperature differences between zones and outdoor conditions
- **Occupancy Impact**: Understanding how occupancy affects thermal conditions
- **HVAC Sizing**: Using peak temperatures and occupancy patterns for system design
- **Building Diagnostics**: Identifying thermal issues and performance problems
- **Condensation Analysis**: Using dewpoint temperature to assess condensation risk and humidity control
- **Humidity Control**: Analyzing outdoor dewpoint vs indoor conditions for moisture management

## Export Command

The `export` command allows you to extract and export specific thermal data from EnergyPlus simulation results into a unified CSV file.

### Basic Usage

```bash
# Export thermal data from simulation results
# The --output parameter is OPTIONAL, auto-generated by default
energyplus-sim export outputs/results/TR9_Baseline__2020s_TMY_TerrassaCST/TR9_Baseline__2020s_TMY_TerrassaCSTout.csv

# Export specific zone (auto-generates filename based on zone)
energyplus-sim export outputs/results/simulation_results.csv --zones "2XPLANTA2:STUDYROOM"

# Specify custom output file
energyplus-sim export simulation_results.csv --zones "ZONE1" --output outputs/exports/custom_name.csv
```

### Automatic Filenames

By default, files are exported to `outputs/exports/` with auto-generated names:

```bash
# Without specifying zones (all zones)
# Generates: outputs/exports/TR9_Baseline_ALL_ZONES.csv

# With a specific zone
# Generates: outputs/exports/TR9_Baseline_2XPLANTA2_STUDYROOM.csv

# With multiple zones
# Generates: outputs/exports/TR9_Baseline_MULTIPLE_ZONES.csv
```

### Zone Filtering

```bash
# Export data for specific zones
energyplus-sim export results.csv --zones "ZONE1,ZONE2"

# Export single zone
energyplus-sim export results.csv --zones "2XPLANTA2:STUDYROOM"
```

### Date Range Filtering

```bash
# Export data for specific date range
energyplus-sim export results.csv --start-date "01/01" --end-date "12/31"

# Export data for a specific month
energyplus-sim export results.csv --start-date "06/01" --end-date "06/30"
```

### Output Options

```bash
# Show data summary before export
energyplus-sim export results.csv --summary
```

### Export Command Options

- `CSV_FILE`: Path to EnergyPlus output CSV file (required positional argument)
- `--output, -o`: Output CSV file path (optional, auto-generated by default)
- `--zones`: Comma-separated list of zone names to include (optional, all zones by default)
- `--start-date`: Start date for filtering (MM/DD format)
- `--end-date`: End date for filtering (MM/DD format)
- `--summary`: Display data summary before export

### Output Format

The exported CSV file contains the following columns:

#### Basic Columns
- **Date/Time**: Timestamp of each data point
- **Zone**: Name of the thermal zone
- **Air_Temperature**: Zone air temperature (°C)
- **Relative_Humidity**: Zone relative humidity (%)
- **Mean_Radiant_Temperature**: Mean radiant temperature (°C)
- **Operative_Temperature**: Calculated operative temperature (°C)
- **Occupancy**: Number of people in the zone

#### Outdoor Conditions
- **Outdoor_Dry_Bulb_Temperature**: Outdoor air temperature (°C)
- **Outdoor_Dewpoint_Temperature**: Outdoor dewpoint temperature (°C)

#### Infiltration Heat Gain Variables
- **Zone_Infiltration_Sensible_Heat_Gain**: Sensible heat gain from infiltration [J]
- **Zone_Infiltration_Sensible_Heat_Loss**: Sensible heat loss from infiltration [J]
- **Zone_Infiltration_Total_Heat_Gain**: Total heat gain from infiltration [J]
- **Zone_Infiltration_Total_Heat_Loss**: Total heat loss from infiltration [J]
- **Zone_Infiltration_Latent_Heat_Gain**: Latent heat gain from infiltration [J]
- **Zone_Infiltration_Latent_Heat_Loss**: Latent heat loss from infiltration [J]

#### Internal Gain Variables
- **Zone_Total_Internal_Total_Heating_Energy**: Total internal heating energy [J]
- **Zone_Total_Internal_Latent_Gain_Energy**: Internal latent gain energy [J]

### Columns Summary

At the end of export, a summary table is displayed with:
- Column number
- Exported column name
- Original EnergyPlus variable name
- Number of values and availability percentage

```
=== COLUMNS SUMMARY ===
#   | Exported Column Name                    | Original EnergyPlus Variable                                          | Values         
----+-----------------------------------------+-----------------------------------------------------------------------+---------------
1   | Date/Time                               | Date/Time                                                             | 8760/8760 (100%)
2   | Relative_Humidity                       | Zone Air Relative Humidity [%](Hourly:ON)                             | 8760/8760 (100%)
3   | Occupancy                               | Zone People Sensible Heating Rate [W](Hourly)                         | 8760/8760 (100%)
...
```

### Examples

```bash
# Export all thermal data (auto-generates filename)
energyplus-sim export outputs/results/simulation/results.csv

# Export specific zone
energyplus-sim export outputs/results/simulation/results.csv --zones "2XPLANTA2:STUDYROOM"

# Export multiple zones with summary
energyplus-sim export outputs/results/simulation/results.csv --zones "ZONE1,ZONE2" --summary

# Export with custom date range
energyplus-sim export outputs/results/simulation/results.csv --start-date "06/01" --end-date "08/31"

# Export with custom filename
energyplus-sim export outputs/results/simulation/results.csv --zones "ZONE1" --output custom_export.csv
```

## Columns Command

The `columns` command allows you to explore and filter column headers from EnergyPlus simulation output CSV files, making it easier to find specific variables and zones.

### Basic Usage

```bash
# Show all column headers
energyplus-sim columns simulation_results.csv

# Show columns in table format
energyplus-sim columns simulation_results.csv --format table
```

### Zone Filtering

```bash
# Filter columns by specific zone
energyplus-sim columns simulation_results.csv --zone "0XPLANTABAJA:ZONA4"

# Show all available zones
energyplus-sim columns simulation_results.csv --zones
```

### Pattern Search

```bash
# Search for columns containing specific text
energyplus-sim columns simulation_results.csv --pattern "Temperature"

# Search for humidity-related columns
energyplus-sim columns simulation_results.csv --pattern "Humidity"

# Interactive search
energyplus-sim columns simulation_results.csv --search "Solar"
```

### Variable Type Grouping

```bash
# Group columns by variable type
energyplus-sim columns simulation_results.csv --types
```

### Output Control

```bash
# Limit number of results
energyplus-sim columns simulation_results.csv --zone "ZONE1" --limit 10

# Combine filters
energyplus-sim columns simulation_results.csv --pattern "Temperature" --limit 5 --format table
```

### Column Options

- `--zone ZONE_NAME`: Filter columns by zone name (e.g., "0XPLANTABAJA:ZONA4")
- `--pattern PATTERN`: Filter columns by text pattern (e.g., "Temperature", "Humidity")
- `--limit N`: Maximum number of columns to display
- `--format [list|table]`: Output format (default: list)
- `--zones`: Show all available zones in the CSV file
- `--types`: Group columns by variable type (Temperature, Humidity, Energy, etc.)
- `--search QUERY`: Interactive search for columns containing the query string

### Features

- **Zone Discovery**: Automatically extract and list all unique zones from column headers
- **Pattern Matching**: Case-insensitive search for columns containing specific text patterns
- **Variable Categorization**: Group columns by type (Temperature, Humidity, Energy, Solar, etc.)
- **Efficient Processing**: Read only header row for fast processing of large CSV files
- **Flexible Output**: Support for both list and table output formats
- **Interactive Search**: Real-time search functionality for exploring large datasets

### Examples

```bash
# Find all temperature columns for a specific zone
energyplus-sim columns results.csv --zone "0XPLANTABAJA:ZONA4" --pattern "Temperature"

# Discover all available zones
energyplus-sim columns results.csv --zones

# Group all columns by variable type
energyplus-sim columns results.csv --types

# Search for energy-related columns
energyplus-sim columns results.csv --search "Energy" --limit 20
```

## Indicators Command

The `indicators` command calculates thermal comfort indicators from exported thermal data, providing comprehensive analysis of building thermal performance.

📊 **[View Detailed Mathematical Formulas →](docs/INDICATORS.md)** | 💡 **[See Practical Examples →](docs/EXAMPLES.md)**

### Basic Usage

```bash
# Calculate all thermal comfort indicators
energyplus-sim indicators thermal_data.csv --simulation "Baseline_TMY2020s"

# Calculate specific indicators only
energyplus-sim indicators thermal_data.csv --indicators "IOD,AWD,HI"

# Specify custom output file
energyplus-sim indicators thermal_data.csv --output "my_indicators.csv"
```

### Available Indicators

- **IOD**: Indoor Overheating Degree - Average excess temperature above comfort during occupied hours
- **AWD**: Ambient Warmness Degree - Average excess ambient temperature above base temperature
- **ALPHA**: Overheating Escalator Factor - Ratio of indoor to ambient overheating (IOD/AWD)
- **HI**: Heat Index - Apparent temperature considering humidity effects
- **DDH**: Degree-weighted Discomfort Hours - Thermal discomfort weighted by intensity using adaptive comfort model
- **DI**: Discomfort Index - Outdoor thermal comfort assessment combining temperature and humidity

### Configuration Options

```bash
# Custom comfort temperature for IOD calculation
energyplus-sim indicators thermal_data.csv --comfort-temp 25.0

# Custom base temperature for AWD calculation
energyplus-sim indicators thermal_data.csv --base-temp 20.0

# Custom simulation name
energyplus-sim indicators thermal_data.csv --simulation "My_Simulation_2024"
```

### Indicator Options

- `--output, -o`: Output CSV file path (default: input_file_indicators.csv)
- `--simulation, -s`: Simulation name for output (default: "Simulation")
- `--indicators, -i`: Comma-separated list of indicators to calculate (IOD,AWD,ALPHA,HI,DDH,DI)
- `--comfort-temp`: Comfort temperature for IOD calculation (default: 26.5°C)
- `--base-temp`: Base outside temperature for AWD calculation (default: 18.0°C)

### Output Format

The indicators CSV file contains the following columns:
- **DateTime**: Timestamp of each data point
- **Zone**: Name of the thermal zone
- **Value**: Calculated indicator value
- **Simulation**: Name of the simulation
- **Indicator**: Type of indicator (IOD, AWD, ALPHA, HI, DDH, DI)

### Examples

```bash
# Calculate all indicators for baseline simulation
energyplus-sim indicators baseline_data.csv --simulation "Baseline_TMY2020s"

# Calculate only overheating indicators
energyplus-sim indicators data.csv --indicators "IOD,AWD,ALPHA"

# Calculate with custom thermal parameters
energyplus-sim indicators data.csv --comfort-temp 24.0 --base-temp 19.0

# Calculate specific indicators with custom output
energyplus-sim indicators data.csv --indicators "HI,DI" --output "comfort_analysis.csv"
```

### Thermal Comfort Analysis

The indicators provide comprehensive thermal comfort analysis:

- **IOD**: Quantifies indoor overheating during occupied periods
- **AWD**: Measures environmental thermal stress
- **ALPHA**: Evaluates building thermal performance (lower is better)
- **HI**: Assesses apparent temperature with humidity effects
- **DDH**: Uses adaptive comfort model for naturally ventilated buildings
- **DI**: Evaluates outdoor thermal comfort conditions

### Use Cases

- **Building Performance Assessment**: Evaluate thermal comfort across different scenarios
- **Climate Adaptation Analysis**: Compare performance under different climate conditions
- **HVAC System Design**: Use indicators for system sizing and optimization
- **Comfort Standards Compliance**: Verify compliance with thermal comfort standards
- **Research and Development**: Support academic and professional research

## Power BI Export Command

The `powerbi` command exports thermal comfort indicators in **ULTRA-LONG format**, optimized for Power BI analysis and advanced data modeling. This format consolidates all indicators into a single CSV file with a fully normalized structure.

📊 **[View Indicator Formulas](docs/INDICATORS.md)** | 📖 **[See Examples](docs/EXAMPLES.md)** | 💡 **Perfect for dashboards, DAX calculations, and multi-dimensional analysis**

### Output Format

The Power BI export uses a 5-column structure:

```csv
Simulation,Indicator,DateTime,Zone,Value
Baseline_TMY2020s,IOD,2020-01-01 00:00:00,Zone1,0.5
Baseline_TMY2020s,ALPHA,2020-01-01 00:00:00,Zone1,0.7
Baseline_TMY2020s,AWD,2020-01-01 00:00:00,Environment,5.2
Baseline_TMY2020s,alphatot,,,0.562
Baseline_TMY2020s,DDH,,Zone1,84.25
```

### Key Features

- ✅ **Single consolidated CSV** with all indicators
- ✅ **Fully normalized** (ULTRA-LONG format) for Power BI
- ✅ **Temporal indicators**: IOD, ALPHA, HI, DI, HIlevel, DIlevel (hourly values)
- ✅ **Aggregated indicators**: DDH (sum across time), alphatot (global average)
- ✅ **Environmental indicator**: AWD (Zone = "Environment")
- ✅ **Ready for Power BI** data modeling and DAX calculations

### Basic Usage

```bash
# Export all indicators for a zone group
energyplus-sim powerbi outputs/results/simulation.csv \
    --zone-group studyrooms \
    --simulation "Baseline_TMY2020s"

# Export specific indicators
energyplus-sim powerbi outputs/results/simulation.csv \
    --zones "ZONE1,ZONE2,ZONE3" \
    --indicators "IOD,AWD,ALPHA,DDH" \
    --simulation "Future_2050s"

# Customize output file and parameters
energyplus-sim powerbi outputs/results/simulation.csv \
    --zone-group all \
    --simulation "Test_Run" \
    --output outputs/powerbi/my_analysis.csv \
    --comfort-temp 25.0 \
    --base-temp 19.0 \
    --year 2025
```

### Available Indicators

#### Temporal Indicators (hourly values with DateTime)
- **IOD**: Indoor Overheating Degree (by zone)
- **AWD**: Ambient Warmness Degree (environmental, Zone = "Environment")
- **ALPHA**: Overheating Escalator Factor (IOD/AWD ratio, by zone)
- **HI**: Heat Index - Apparent Temperature (by zone)
- **HIlevel**: Heat Index Risk Categories (by zone, categorical)
- **DI**: Discomfort Index (by zone)
- **DIlevel**: Discomfort Index Risk Categories (by zone, categorical)

#### Aggregated Indicators (single values, DateTime empty)
- **alphatot**: Global ALPHA average across all zones and time periods (Zone = "values")
- **DDH**: Degree-weighted Discomfort Hours - Sum across entire simulation period (by zone)

### Command Options

- `--zones, -z`: Comma-separated list of zone names to analyze
- `--zone-group, -g`: Zone group name from settings.yaml (alternative to --zones)
- `--output, -o`: Output CSV file path (default: `outputs/powerbi/{simulation}_powerbi.csv`)
- `--simulation, -s`: Simulation name (required, used in output)
- `--indicators, -i`: Comma-separated list of indicators to calculate (default: all)
- `--comfort-temp`: Comfort temperature for IOD calculation (default: 26.5°C)
- `--base-temp`: Base outside temperature for AWD calculation (default: 18.0°C)
- `--year, -y`: Year for datetime parsing (default: 2020)
- `--start-date`: Start date for filtering in format "MM/DD" (e.g., "06/22")
- `--end-date`: End date for filtering in format "MM/DD" (e.g., "08/30")

### Power BI Data Model

The ULTRA-LONG format enables powerful Power BI features:

#### 1. **Star Schema Design**
```
Fact Table: PowerBI_Data (your CSV)
├─ Dimension: Simulation
├─ Dimension: Indicator
├─ Dimension: DateTime
├─ Dimension: Zone
└─ Measure: Value
```

#### 2. **DAX Measures Examples**
```dax
-- Average IOD across all zones
IOD_Average = 
CALCULATE(
    AVERAGE(PowerBI_Data[Value]),
    PowerBI_Data[Indicator] = "IOD"
)

-- Max Heat Index per zone
HI_Max_By_Zone = 
CALCULATE(
    MAX(PowerBI_Data[Value]),
    PowerBI_Data[Indicator] = "HI"
)

-- Count of dangerous heat index hours
HI_Danger_Hours = 
CALCULATE(
    COUNTROWS(PowerBI_Data),
    PowerBI_Data[Indicator] = "HIlevel",
    PowerBI_Data[Value] = "DANGER"
)
```

#### 3. **Dynamic Visualizations**
- **Slicers**: Filter by Simulation, Indicator, Zone, Date Range
- **Line Charts**: Show temporal trends for any indicator across zones
- **Heatmaps**: DateTime (rows) × Zone (columns) with Value as color
- **Comparatives**: Multiple simulations side-by-side
- **KPI Cards**: Display alphatot, total DDH, max HI

### Workflow Example

#### Full Year Analysis
```bash
# Step 1: Run EnergyPlus simulation
energyplus-sim run --all

# Step 2: Export full year to Power BI format
energyplus-sim powerbi outputs/results/TR9_Baseline/TR9_Baselineout.csv \
    --zone-group all_zones \
    --simulation "Baseline_TMY2020s" \
    --year 2020

# Step 3: Import outputs/powerbi/Baseline_TMY2020s_powerbi.csv into Power BI

# Step 4: Create relationships and measures in Power BI

# Step 5: Build dashboards with slicers, charts, and KPIs
```

#### Summer Period Comparison (Recommended for Comparative Studies)
```bash
# Export multiple simulations with SAME date range for comparison
# Date range: June 22 to August 30 (summer period, 70 days)

# Baseline scenario
energyplus-sim powerbi outputs/results/Baseline/out.csv \
    --zone-group studyrooms \
    --simulation "Baseline_Summer_2020s" \
    --start-date "06/22" \
    --end-date "08/30" \
    --year 2020

# Future climate scenario
energyplus-sim powerbi outputs/results/Future_2050s/out.csv \
    --zone-group studyrooms \
    --simulation "Future_Summer_2050s" \
    --start-date "06/22" \
    --end-date "08/30" \
    --year 2050

# Improved design scenario
energyplus-sim powerbi outputs/results/Improved/out.csv \
    --zone-group studyrooms \
    --simulation "Improved_Summer_2020s" \
    --start-date "06/22" \
    --end-date "08/30" \
    --year 2020

# In Power BI: Combine all files and compare DDH and alphatot values
# ✅ All scenarios use same date range → DDH values are directly comparable
```

### Output File Statistics

For a typical simulation with 2 zones and all indicators over 1 year:

| Indicator | Rows | Calculation |
|-----------|------|-------------|
| IOD | 17,520 | 8,760 hours × 2 zones |
| AWD | 8,760 | 8,760 hours × 1 (Environment) |
| ALPHA | 17,520 | 8,760 hours × 2 zones |
| HI | 17,520 | 8,760 hours × 2 zones |
| HIlevel | 17,520 | 8,760 hours × 2 zones |
| DI | 17,520 | 8,760 hours × 2 zones |
| DIlevel | 17,520 | 8,760 hours × 2 zones |
| DDH | 2 | 1 aggregated value × 2 zones |
| alphatot | 1 | 1 global value |
| **TOTAL** | **131,881** | **+ 1 header = 131,882 rows** |

### Advantages for Power BI

1. ✅ **Single Data Source**: One file for all indicators and zones
2. ✅ **Scalability**: Easy to add more simulations (just append rows)
3. ✅ **Flexibility**: Filter and slice data dynamically
4. ✅ **Performance**: Optimized for Power BI's columnar engine
5. ✅ **Relationships**: Natural star schema for data modeling
6. ✅ **Comparisons**: Multiple simulations/scenarios in one dataset

### Date Range Filtering

**Important Notes:**

- ✅ **alphatot**: Calculated as average over filtered period (always comparable as a ratio)
- ⚠️ **DDH**: Calculated as sum over filtered period (only comparable when using SAME date range)
- 💡 **Best Practice**: Use consistent date ranges (e.g., "06/22" to "08/30") across all simulations for valid comparisons
- 📊 **Typical Use**: Filter summer months to focus on overheating periods

**Example - Valid DDH Comparison:**
```bash
# All simulations use 06/22 to 08/30 (70 days)
Baseline_Summer:    DDH = 270.5 °C·h
Future_2050s:       DDH = 450.8 °C·h  (67% worse)
Improved_Design:    DDH = 180.2 °C·h  (33% better)
✅ Valid comparison - same period
```

**Example - Invalid DDH Comparison:**
```bash
# Different periods - NOT comparable!
Baseline (full year):  DDH = 1,850 °C·h  (365 days)
Summer_Only:           DDH = 620 °C·h    (70 days)
❌ Cannot compare - different time periods
```

### Use Cases

- **Interactive Dashboards**: Build comprehensive thermal comfort dashboards
- **Scenario Comparison**: Compare multiple climate scenarios or design alternatives
- **Time Series Analysis**: Analyze temporal patterns with Power BI time intelligence
- **Spatial Analysis**: Compare thermal performance across different zones
- **Regulatory Compliance**: Generate reports for building standards compliance
- **Client Presentations**: Create professional visualizations for stakeholders

## Pivot Command

The `pivot` command consolidates a specific variable from multiple exported CSV files (one per zone) into a single CSV file with LONG format, facilitating comparative analysis between zones.

### Basic Usage

```bash
# Consolidate a specific variable from all zones
energyplus-sim pivot --variable "Operative_Temperature"

# The command automatically searches in outputs/exports/ and generates:
# outputs/pivots/Operative_Temperature_All_Zones.csv
```

### Specify Input Directory

```bash
# Use a specific directory to search for CSV files
energyplus-sim pivot --variable "Air_Temperature" --dir "outputs/exports/"

# Use a specific search pattern
energyplus-sim pivot --variable "Relative_Humidity" --input "outputs/exports/*STUDYROOM*.csv"
```

### Custom Output File

```bash
# Specify custom output filename
energyplus-sim pivot --variable "Operative_Temperature" --output "outputs/pivots/custom_name.csv"
```

### Pivot Command Options

- `--variable, -v`: Variable(s) to extract (required). Single or comma-separated. Example: "Operative_Temperature" or "Operative_Temperature,Air_Temperature"
- `--year, -y`: Year to add to Date/Time column (optional). Example: 2020, 2025
- `--simulation, -s`: Simulation name to add as a column (optional). Example: "Baseline_TMY2020s", "Future_2050s"
- `--dir`: Directory containing exported CSV files (default: `outputs/exports/`)
- `--input`: Glob pattern for input files (e.g., `"outputs/exports/*STUDYROOM*.csv"`)
- `--output, -o`: Output CSV file path (optional, auto-generated by default)
- `--summary`: Show detailed processing summary

### Available Variables for Pivot

All variables available in exported files can be consolidated:

#### Basic Thermal Variables
- `Operative_Temperature` - Operative temperature (°C)
- `Air_Temperature` - Air temperature (°C)
- `Relative_Humidity` - Relative humidity (%)
- `Mean_Radiant_Temperature` - Mean radiant temperature (°C)
- `Occupancy` - Occupancy (number of people)

#### Outdoor Variables
- `Outdoor_Dry_Bulb_Temperature` - Outdoor temperature (°C)
- `Outdoor_Dewpoint_Temperature` - Outdoor dewpoint temperature (°C)

#### Infiltration Variables
- `Zone_Infiltration_Sensible_Heat_Gain` - Sensible heat gain from infiltration [J]
- `Zone_Infiltration_Sensible_Heat_Loss` - Sensible heat loss from infiltration [J]
- `Zone_Infiltration_Total_Heat_Gain` - Total heat gain from infiltration [J]
- `Zone_Infiltration_Total_Heat_Loss` - Total heat loss from infiltration [J]
- `Zone_Infiltration_Latent_Heat_Gain` - Latent heat gain from infiltration [J]
- `Zone_Infiltration_Latent_Heat_Loss` - Latent heat loss from infiltration [J]

#### Internal Gain Variables
- `Zone_Total_Internal_Total_Heating_Energy` - Total internal heating energy [J]
- `Zone_Total_Internal_Latent_Gain_Energy` - Internal latent gain energy [J]

### Output Format (LONG)

The consolidated CSV file uses LONG format with columns: `Date/Time`, `Zone`, `Indicator`, `Value`, and optionally `Simulation`.

#### Without --simulation (4 columns):
```csv
Date/Time;Zone;Indicator;Value
2020-01-01 01:00:00;1XPLANTA1:STUDYROOM;Operative_Temperature;17.466152264563284
2020-01-01 01:00:00;1XPLANTA1:STUDYROOM;Air_Temperature;16.953795517354813
2020-01-01 01:00:00;2XPLANTA2:STUDYROOM;Operative_Temperature;17.397706170964163
2020-01-01 01:00:00;2XPLANTA2:STUDYROOM;Air_Temperature;17.06869062927361
...
```

#### With --simulation (5 columns):
```csv
Date/Time;Zone;Indicator;Value;Simulation
2020-01-01 01:00:00;1XPLANTA1:STUDYROOM;Operative_Temperature;17.46;Baseline_TMY2020s
2020-01-01 01:00:00;1XPLANTA1:STUDYROOM;Air_Temperature;16.95;Baseline_TMY2020s
2020-01-01 01:00:00;2XPLANTA2:STUDYROOM;Operative_Temperature;17.39;Baseline_TMY2020s
2020-01-01 01:00:00;2XPLANTA2:STUDYROOM;Air_Temperature;17.07;Baseline_TMY2020s
...
```

Where:
- **Date/Time**: Data timestamp (with year if `--year` specified, format: YYYY-MM-DD HH:MM:SS)
- **Zone**: Zone name
- **Indicator**: Variable name (e.g., "Operative_Temperature", "Air_Temperature")
- **Value**: Numeric value of the variable
- **Simulation**: Simulation name (only if `--simulation` specified)

### Typical Workflow

```bash
# Step 1: Export data for each zone individually
energyplus-sim export results.csv --zones "ZONE1"
energyplus-sim export results.csv --zones "ZONE2"
energyplus-sim export results.csv --zones "ZONE3"

# Files are generated in outputs/exports/:
# - outputs/exports/SimulationName_ZONE1.csv
# - outputs/exports/SimulationName_ZONE2.csv
# - outputs/exports/SimulationName_ZONE3.csv

# Step 2: Consolidate a specific variable from all zones
energyplus-sim pivot --variable "Operative_Temperature"

# Generates: outputs/pivots/Operative_Temperature_All_Zones.csv
# Contains operative temperature from all zones in LONG format
```

### Examples

```bash
# Consolidate single variable from all zones
energyplus-sim pivot --variable "Operative_Temperature"

# Consolidate multiple variables in one file
energyplus-sim pivot --variable "Operative_Temperature,Air_Temperature,Relative_Humidity"

# Add year to Date/Time column
energyplus-sim pivot --variable "Operative_Temperature" --year 2020

# Add year and simulation name
energyplus-sim pivot -v "Operative_Temperature,Air_Temperature" -y 2020 -s "Baseline_TMY2020s"

# Consolidate with detailed summary
energyplus-sim pivot --variable "Air_Temperature" --summary

# Consolidate only STUDYROOM files with year and simulation
energyplus-sim pivot --variable "Operative_Temperature" --input "outputs/exports/*STUDYROOM*.csv" -y 2025 -s "Future_2050s"

# Consolidate with custom output filename
energyplus-sim pivot --variable "Occupancy" --output "outputs/pivots/occupancy_analysis.csv"

# Multi-variable with all options
energyplus-sim pivot -v "Operative_Temperature,Air_Temperature" -y 2020 -s "Baseline_2020s" -o outputs/pivots/baseline_full.csv
```

### LONG Format Advantages

- **Multi-variable support**: Store multiple variables in a single file using the `Indicator` column
- **Statistical analysis**: Ideal for tools like R, Python pandas, or Excel pivot tables
- **Visualization**: Easy to use with visualization libraries (matplotlib, seaborn, ggplot2)
- **Multi-zone comparison**: Allows easy comparison of values between zones
- **Flexible filtering**: Easy to filter by zone, variable, time range, or simulation
- **Scalability**: Works well with any number of zones and variables
- **Temporal analysis**: Add year to Date/Time for proper datetime handling (handles 24:00:00 correctly)
- **Scenario comparison**: Use `Simulation` column to compare multiple scenarios in one dataset

### Use Cases

- **Comparative analysis**: Compare multiple variables between different zones
- **Pattern identification**: Detect zones with similar thermal behavior
- **Temporal analysis**: Study evolution of variables over time with proper datetime format
- **Model validation**: Verify consistency of results between zones
- **Scenario comparison**: Compare multiple simulations (baseline vs. future scenarios)
- **Multi-variable analysis**: Analyze relationships between multiple thermal variables
- **Reporting**: Generate consolidated reports for multiple spaces and variables
- **Climate impact assessment**: Compare performance across different climate scenarios

## Requirements

- Python 3.8+
- EnergyPlus (9.0.0 or later)
- Click 8.0.0+
- PyYAML 6.0+
- eppy 0.5.60+ (for IDF file analysis)
- pandas 1.5.0+ (for data processing)
- tabulate 0.9.0+ (for formatted output)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

