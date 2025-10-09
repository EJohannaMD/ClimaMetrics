# Thermal Comfort Indicators - Mathematical Formulas

This document provides detailed mathematical formulas and explanations for all thermal comfort indicators calculated by ClimaMetrics.

---

## 1. IOD (Indoor Overheating Degree)

### Definition
IOD quantifies the average excess indoor temperature above comfort level during occupied periods.

### Formula
```
IOD = Σ(Top - Tcomf)⁺ / Σ(Occupied_hours)
```

### Variables
- **Top** = Operative temperature (°C)
- **Tcomf** = Comfort temperature threshold (default: 26.5°C, configurable via `--comfort-temp`)
- **(x)⁺** = max(x, 0) - only positive temperature excess is counted
- **Σ(Top - Tcomf)⁺** = Sum of positive temperature excess during occupied overheating periods
- **Σ(Occupied_hours)** = Total occupied hours in the analysis period

### Unit
°C (degrees Celsius)

### Interpretation
- **IOD = 0**: No overheating during occupied periods
- **IOD > 0**: Average temperature excess above comfort during occupation
- **Higher IOD** = Worse thermal comfort performance
- **Example**: IOD = 2.5°C means on average, occupied spaces are 2.5°C above comfort level

### Implementation Details
```python
# Only count hours where:
# 1. Space is occupied (Occupancy > 0)
# 2. Temperature exceeds comfort threshold (Top > Tcomf)

excess_temp = max(Top - Tcomf, 0) if Occupancy > 0 else 0
IOD = sum(excess_temp) / sum(Occupied_hours)
```

---

## 2. AWD (Ambient Warmness Degree)

### Definition
AWD quantifies the average excess ambient (outdoor) temperature above base temperature across all time periods.

### Formula
```
AWD = Σ(Tai - Tb)⁺ / N_total
```

### Variables
- **Tai** = Ambient (outdoor) air temperature (°C)
- **Tb** = Base outside temperature (default: 18°C, configurable via `--base-temp`)
- **(x)⁺** = max(x, 0) - only positive temperature excess is counted
- **Σ(Tai - Tb)⁺** = Sum of positive ambient temperature excess
- **N_total** = Total number of time steps (all hours, typically 8760 for annual simulation)

### Unit
°C (degrees Celsius)

### Interpretation
- **AWD = 0**: Average ambient temperature ≤ base temperature (cold climate)
- **AWD > 0**: Average ambient temperature excess above base
- **Higher AWD** = Warmer environmental conditions
- **Environmental indicator**: Same value for all zones (represents external thermal stress)
- **Example**: AWD = 5.2°C means the ambient is on average 5.2°C above base temperature

### Special Note
AWD is exported with column name **"Environment"** instead of zone names, as it represents outdoor conditions.

---

## 3. ALPHA (Overheating Escalator Factor)

### Definition
ALPHA represents the ratio of indoor to ambient overheating, indicating building thermal performance relative to outdoor conditions.

### Formula
```
ALPHA = IOD / AWD
```

### Variables
- **IOD** = Indoor Overheating Degree (°C)
- **AWD** = Ambient Warmness Degree (°C)

### Unit
Dimensionless ratio

### Interpretation
- **ALPHA < 1**: Building performs BETTER than ambient conditions (good thermal performance)
- **ALPHA = 1**: Indoor overheating matches ambient warmness
- **ALPHA > 1**: Building AMPLIFIES outdoor warmth (poor thermal performance)
- **Lower ALPHA** = Better building thermal resilience

### Examples
- **ALPHA = 0.5**: Indoor overheating is half the ambient warmness (excellent performance)
- **ALPHA = 1.2**: Indoor overheating is 20% worse than ambient (poor performance)
- **ALPHA = 0.8**: Building reduces outdoor thermal stress by 20% (good performance)

### Use Cases
- Compare building performance across different climates
- Evaluate passive design strategies
- Assess thermal resilience to climate change

---

## 4. HI (Heat Index - Apparent Temperature)

### Definition
HI represents the "felt" temperature when humidity is factored with actual air temperature, indicating heat stress on occupants.

### Formula

**For T ≤ 26.7°C OR RH < 40%:**
```
HI = T  (simple approximation)
```

**For T > 26.7°C AND RH ≥ 40%:**
```
HI = C1 + C2×T + C3×RH + C4×T×RH + C5×T² + C6×RH² + C7×T²×RH + C8×T×RH² + C9×T²×RH²
```

### Coefficients (V4 for Celsius)
```python
C1 = -8.784694
C2 = 1.611394
C3 = 2.338548
C4 = -0.146116
C5 = -0.012308
C6 = -0.016424
C7 = 0.002211
C8 = 0.000725
C9 = -0.000003
```

### Variables
- **T** = Operative temperature (°C)
- **RH** = Relative humidity (percentage, 0-100, e.g., 65 = 65%)

### Unit
°C (degrees Celsius)

### Risk Categories
| Heat Index (°C) | Category | Risks |
|-----------------|----------|-------|
| < 27 | Safe Condition | No significant heat stress |
| 27 - 32 | Caution | Fatigue possible with prolonged exposure |
| 32 - 41 | Extreme Caution | Heat cramps and exhaustion possible |
| 41 - 54 | Danger | Heat exhaustion likely, heat stroke possible |
| > 54 | Extreme Danger | Heat stroke highly likely |

### Reference
Rothfusz, L.P. (1990). The Heat Index Equation. NWS Southern Region Technical Attachment, SR/SSD 90-23.

---

## 5. DDH (Degree-weighted Discomfort Hours)

### Definition
DDH quantifies thermal discomfort using an adaptive comfort model, weighting discomfort hours by the magnitude of temperature excess.

### Formula
```
DDH = Σ[(Top - Top_up)⁺ × Occupied_flag]
```

### Adaptive Comfort Limits
```
Top_up = T_op + 4°C                    (Upper limit, Category II)
T_op = 0.33 × θ_rm + 18.8             (Neutral operative temperature)
θ_rm = Weighted running mean outdoor temperature
```

### Running Mean Temperature
```
θ_rm = (T_day-1 + 0.8×T_day-2 + 0.6×T_day-3 + 0.5×T_day-4 + 0.4×T_day-5 + 0.3×T_day-6 + 0.2×T_day-7) / 3.8
```

### Variables
- **Top** = Operative temperature (°C)
- **Top_up** = Upper adaptive comfort limit (°C)
- **T_op** = Neutral operative temperature (°C)
- **θ_rm** = Running mean outdoor temperature (°C)
- **Occupied_flag** = 1 if occupied, 0 otherwise
- **(x)⁺** = max(x, 0) - only positive exceedance

### Validity Ranges
- **10°C ≤ θ_rm ≤ 30°C**: Use adaptive formula
- **θ_rm < 10°C**: Fixed limit Top_up = 18°C (cold climate)
- **θ_rm > 30°C**: Maximum Top_up = 32.7°C (hot climate)

### Unit
°C·hours (degree-hours)

### Interpretation
- **DDH = 0**: No discomfort (all within adaptive comfort zone)
- **Higher DDH** = More severe or prolonged discomfort
- **Example**: DDH = 150°C·h means 150 degree-hours of accumulated overheating

### Standard
EN 15251:2007 - Indoor environmental input parameters for design and assessment of energy performance of buildings

---

## 6. DI (Discomfort Index)

### Definition
DI combines dry bulb and wet bulb temperatures to assess outdoor thermal discomfort, particularly relevant for humid conditions.

### Formula
```
DI = 0.5 × (Ta + Tw)
```

### Wet Bulb Temperature (Stull 2011 Approximation)
```
Tw = Ta × arctan[0.151977 × √(RH + 8.313659)]
     + arctan(Ta + RH)
     - arctan(RH - 1.676331)
     + 0.00391838 × RH^1.5 × arctan(0.023101 × RH)
     - 4.686035
```

### Variables
- **Ta** = Dry bulb (outdoor) temperature (°C)
- **Tw** = Wet bulb temperature (°C)
- **RH** = Relative humidity (%)

### Unit
°C (degrees Celsius)

### Comfort Categories
| DI (°C) | Category | Sensation |
|---------|----------|-----------|
| < 21 | Comfortable | Most people feel comfortable |
| 21 - 24 | Slightly Uncomfortable | Some discomfort |
| 24 - 27 | Uncomfortable | General discomfort |
| 27 - 29 | Very Uncomfortable | Significant discomfort |
| > 29 | Dangerous | Health risks, especially for vulnerable |

### References
- Thom, E.C. (1959). The Discomfort Index. Weatherwise, 12(2), 57-61
- Stull, R. (2011). Wet-Bulb Temperature from Relative Humidity and Air Temperature. Journal of Applied Meteorology and Climatology, 50(11), 2267-2269

---

## 7. DIlevel (Discomfort Index Risk Categories)

Categorical classification of DI values:
- **COMFORTABLE** (< 21°C)
- **SLIGHTLY UNCOMFORTABLE** (21-24°C)
- **UNCOMFORTABLE** (24-27°C)
- **VERY UNCOMFORTABLE** (27-29°C)
- **DANGEROUS** (> 29°C)

---

## 8. HIlevel (Heat Index Risk Categories)

Categorical classification of HI values:
- **SAFE CONDITION** (< 27°C)
- **CAUTION** (27-32°C)
- **EXTREME CAUTION** (32-41°C)
- **DANGER** (41-54°C)
- **EXTREME DANGER** (> 54°C)

---

## Configuration Parameters

### Adjustable Constants

In `config/settings.yaml`:
```yaml
indicators:
  calculations:
    occupancy_watts_per_person: 100.0  # W per person for occupancy calculation
    defaults:
      occupancy: 0
      relative_humidity: 50.0
```

Via CLI:
```bash
--comfort-temp 25.0   # IOD comfort temperature (default: 26.5°C)
--base-temp 19.0      # AWD base temperature (default: 18°C)
--year 2020           # Year for datetime parsing
```

---

## Output Format

All indicators are exported in **WIDE format**:

### Zone-Specific Indicators (IOD, ALPHA, HI, DDH, DI, HIlevel, DIlevel)
```csv
DateTime,Zone1,Zone2,Zone3
2020-01-01 00:00:00,0.0,0.5,0.3
2020-01-01 01:00:00,0.2,0.7,0.4
```

### Environmental Indicator (AWD)
```csv
DateTime,Environment
2020-01-01 00:00:00,0.0
2020-01-01 01:00:00,1.2
```

---

## Usage Example

```bash
# Calculate all indicators with custom parameters
energyplus-sim indicators \
  outputs/results/simulation.csv \
  --zone-group studyrooms \
  --simulation "Baseline_TMY2020s" \
  --comfort-temp 25.0 \
  --base-temp 19.0 \
  --year 2020

# Calculate specific indicators only
energyplus-sim indicators \
  outputs/results/simulation.csv \
  --zones "ZONE1,ZONE2" \
  --indicators "IOD,AWD,ALPHA,HI" \
  --simulation "Future_2050s"
```

---

## Practical Applications

### Building Performance Assessment
- **IOD**: Quantify overheating severity
- **ALPHA**: Compare performance across climates
- **DDH**: Compliance with adaptive comfort standards

### Climate Resilience
- **AWD**: Characterize climate thermal stress
- **ALPHA**: Assess building adaptation effectiveness

### Occupant Comfort & Health
- **HI/HIlevel**: Heat stress risk assessment
- **DI/DIlevel**: Outdoor comfort for naturally ventilated buildings

### Design Optimization
- Use indicators to compare passive design strategies
- Evaluate impact of building envelope modifications
- Optimize shading and ventilation systems

---

## Notes

1. **Operative Temperature**: Preferably read directly from EnergyPlus output (`Zone Operative Temperature [C]`). If unavailable, calculated as (Air Temp + Radiant Temp) / 2.

2. **Occupancy Detection**: Derived from `Zone People Sensible Heating Rate [W]` using configurable conversion factor (default: 100W per person).

3. **Missing Data**: Handled gracefully using configured default values or NaN where appropriate.

4. **Temporal Resolution**: All calculations use hourly data from EnergyPlus simulations.

---

## References

1. EN 15251:2007. Indoor environmental input parameters for design and assessment of energy performance of buildings addressing indoor air quality, thermal environment, lighting and acoustics.

2. Rothfusz, L.P. (1990). The Heat Index Equation (or, More Than You Ever Wanted to Know About Heat Index). NWS Southern Region Technical Attachment, SR/SSD 90-23.

3. Thom, E.C. (1959). The Discomfort Index. Weatherwise, 12(2), 57-61.

4. Stull, R. (2011). Wet-Bulb Temperature from Relative Humidity and Air Temperature. Journal of Applied Meteorology and Climatology, 50(11), 2267-2269.

5. ASHRAE Standard 55-2020. Thermal Environmental Conditions for Human Occupancy.

