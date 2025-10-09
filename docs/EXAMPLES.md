# Ejemplos Prácticos de Cálculo de Indicadores

Este documento proporciona ejemplos paso a paso del cálculo de los indicadores térmicos, con datos numéricos reales para facilitar la comprensión.

---

## 1. DDH (Degree-weighted Discomfort Hours)

### 📚 Concepto

DDH mide el disconfort térmico acumulado basándose en el **modelo adaptativo de confort** (EN 15251). No solo cuenta las horas fuera de confort, sino que **pondera cada hora por la magnitud del exceso** de temperatura.

### 🧮 Fórmula

```
DDH = Σ[(Top - Top_up)⁺ × Occupied_flag]
```

Donde:
- **Top** = Temperatura operativa interior (°C)
- **Top_up** = Límite superior de confort adaptativo (°C)
- **(x)⁺** = max(x, 0) - solo valores positivos
- **Occupied_flag** = 1 si ocupado, 0 si desocupado

### 📊 Ejemplo Paso a Paso

Supongamos una oficina durante una semana de verano. Vamos a calcular DDH para 5 días consecutivos.

#### **Paso 1: Calcular temperatura media móvil (θ_rm)**

La temperatura media móvil pondera los últimos 7 días, dando más peso a los días recientes:

```
θ_rm = (T₀ + 0.8×T₋₁ + 0.6×T₋₂ + 0.5×T₋₃ + 0.4×T₋₄ + 0.3×T₋₅ + 0.2×T₋₆) / 3.8
```

**Temperaturas exteriores medias diarias (últimos 7 días):**
```
Día -6: 20°C
Día -5: 22°C
Día -4: 23°C
Día -3: 25°C
Día -2: 26°C
Día -1: 28°C
Día  0: 30°C (HOY)
```

**Cálculo de θ_rm:**
```
θ_rm = (30×1.0 + 28×0.8 + 26×0.6 + 25×0.5 + 23×0.4 + 22×0.3 + 20×0.2) / 3.8
     = (30 + 22.4 + 15.6 + 12.5 + 9.2 + 6.6 + 4.0) / 3.8
     = 100.3 / 3.8
     = 26.4°C
```

#### **Paso 2: Calcular límite superior adaptativo (Top_up)**

```
T_op = 0.33 × θ_rm + 18.8
     = 0.33 × 26.4 + 18.8
     = 8.71 + 18.8
     = 27.5°C (temperatura neutral de confort)

Top_up = T_op + 4°C (tolerancia Categoría II)
       = 27.5 + 4
       = 31.5°C (límite superior)
```

**Interpretación:** Con una temperatura exterior media de 26.4°C, se espera que las personas se adapten y acepten temperaturas interiores hasta 31.5°C como confortables.

#### **Paso 3: Calcular DDH horario**

Ahora evaluamos cada hora del día. Supongamos este perfil de temperatura operativa y ocupación:

| Hora | Top (°C) | Ocupado | Top - Top_up | DDH Horario |
|------|----------|---------|--------------|-------------|
| 00:00 | 26.0 | 0 | 26.0 - 31.5 = -5.5 | 0 × 0 = **0** |
| 01:00 | 25.5 | 0 | 25.5 - 31.5 = -6.0 | 0 × 0 = **0** |
| 02:00 | 25.0 | 0 | 25.0 - 31.5 = -6.5 | 0 × 0 = **0** |
| 03:00 | 24.8 | 0 | 24.8 - 31.5 = -6.7 | 0 × 0 = **0** |
| 04:00 | 24.5 | 0 | 24.5 - 31.5 = -7.0 | 0 × 0 = **0** |
| 05:00 | 24.3 | 0 | 24.3 - 31.5 = -7.2 | 0 × 0 = **0** |
| 06:00 | 24.5 | 0 | 24.5 - 31.5 = -7.0 | 0 × 0 = **0** |
| 07:00 | 25.0 | 0 | 25.0 - 31.5 = -6.5 | 0 × 0 = **0** |
| 08:00 | 26.5 | 1 | 26.5 - 31.5 = -5.0 | 0 × 1 = **0** |
| 09:00 | 28.0 | 1 | 28.0 - 31.5 = -3.5 | 0 × 1 = **0** |
| 10:00 | 29.5 | 1 | 29.5 - 31.5 = -2.0 | 0 × 1 = **0** |
| 11:00 | 31.0 | 1 | 31.0 - 31.5 = -0.5 | 0 × 1 = **0** |
| 12:00 | 32.5 | 1 | 32.5 - 31.5 = +1.0 | **1.0** × 1 = **1.0** |
| 13:00 | 33.2 | 1 | 33.2 - 31.5 = +1.7 | **1.7** × 1 = **1.7** |
| 14:00 | 34.0 | 1 | 34.0 - 31.5 = +2.5 | **2.5** × 1 = **2.5** |
| 15:00 | 34.5 | 1 | 34.5 - 31.5 = +3.0 | **3.0** × 1 = **3.0** |
| 16:00 | 34.2 | 1 | 34.2 - 31.5 = +2.7 | **2.7** × 1 = **2.7** |
| 17:00 | 33.5 | 1 | 33.5 - 31.5 = +2.0 | **2.0** × 1 = **2.0** |
| 18:00 | 32.0 | 0 | 32.0 - 31.5 = +0.5 | 0.5 × 0 = **0** |
| 19:00 | 30.5 | 0 | 30.5 - 31.5 = -1.0 | 0 × 0 = **0** |
| 20:00 | 29.0 | 0 | 29.0 - 31.5 = -2.5 | 0 × 0 = **0** |
| 21:00 | 28.0 | 0 | 28.0 - 31.5 = -3.5 | 0 × 0 = **0** |
| 22:00 | 27.5 | 0 | 27.5 - 31.5 = -4.0 | 0 × 0 = **0** |
| 23:00 | 27.0 | 0 | 27.0 - 31.5 = -4.5 | 0 × 0 = **0** |

#### **Paso 4: Sumar DDH del día**

```
DDH_día = 0 + 0 + ... + 1.0 + 1.7 + 2.5 + 3.0 + 2.7 + 2.0 + 0 + ...
        = 14.9 °C·h
```

**Interpretación:**
- El espacio experimentó disconfort térmico **solo durante 6 horas** (12:00-17:00)
- El disconfort **más severo** fue a las 15:00 (3°C por encima del límite)
- Total acumulado: **14.9 grados-hora** de sobrecalentamiento

### 📈 Ejemplo Extendido: Semana Completa

Si repetimos este análisis para 5 días laborables:

| Día | θ_rm (°C) | Top_up (°C) | Horas Disconfort | DDH Diario (°C·h) |
|-----|-----------|-------------|------------------|-------------------|
| Lunes | 26.4 | 31.5 | 6 | 14.9 |
| Martes | 27.0 | 31.7 | 5 | 11.2 |
| Miércoles | 27.5 | 31.9 | 7 | 18.5 |
| Jueves | 28.0 | 32.0 | 6 | 15.8 |
| Viernes | 28.2 | 32.1 | 5 | 12.0 |

**DDH Semanal Total:**
```
DDH_semana = 14.9 + 11.2 + 18.5 + 15.8 + 12.0 = 72.4 °C·h
```

### 🎯 Casos Especiales

#### **Caso 1: Sin ocupación**
```
Hora: 14:00
Top = 35.0°C (muy caliente)
Top_up = 31.5°C
Ocupado = 0 (fin de semana)

DDH = (35.0 - 31.5) × 0 = 0 °C·h
```
**→ No cuenta porque no hay ocupantes**

#### **Caso 2: Dentro de confort**
```
Hora: 10:00
Top = 29.5°C
Top_up = 31.5°C
Ocupado = 1

DDH = max(29.5 - 31.5, 0) × 1 = 0 °C·h
```
**→ No cuenta porque está dentro de la zona de confort**

#### **Caso 3: Clima frío (θ_rm < 10°C)**
```
θ_rm = 8°C (invierno)
→ Se usa límite fijo: Top_up = 18°C

Top = 20°C, Ocupado = 1
DDH = (20 - 18) × 1 = 2.0 °C·h
```
**→ El modelo adaptativo no aplica en clima muy frío**

#### **Caso 4: Clima muy caluroso (θ_rm > 30°C)**
```
θ_rm = 32°C (ola de calor)
→ Límite máximo: Top_up = 32.7°C

Top = 36°C, Ocupado = 1
DDH = (36 - 32.7) × 1 = 3.3 °C·h
```
**→ Se aplica un límite superior absoluto**

### 📊 Comparación de Escenarios

| Escenario | DDH Anual | Interpretación |
|-----------|-----------|----------------|
| **Edificio A** (buena inercia térmica) | 45 °C·h | Excelente desempeño |
| **Edificio B** (ventilación natural) | 180 °C·h | Aceptable |
| **Edificio C** (sin protección solar) | 520 °C·h | Deficiente, requiere intervención |
| **Edificio D** (sin climatización) | 1,250 °C·h | Muy deficiente |

### 💡 Ventajas del DDH

1. **Pondera por severidad**: 1 hora a 35°C (DDH=3.5) cuenta más que 1 hora a 32°C (DDH=0.5)
2. **Modelo adaptativo**: Considera que las personas se adaptan al clima exterior
3. **Solo horas ocupadas**: No penaliza disconfort cuando no hay nadie
4. **Comparable**: DDH más bajo = mejor desempeño térmico

### 🔗 Referencias

- EN 15251:2007 - Indoor environmental input parameters
- ASHRAE Standard 55 - Thermal Environmental Conditions
- CEN (2007). EN 15251:2007 Indoor environmental input parameters for design and assessment of energy performance of buildings

---

## 2. IOD (Indoor Overheating Degree)

### 📚 Concepto

IOD mide cuánto excede la temperatura interior un umbral de confort durante las horas ocupadas.

### 🧮 Fórmula Simple

```
IOD = Promedio de (Top - Tcomf)⁺ durante horas ocupadas
```

Donde:
- **Top** = Temperatura operativa (°C)
- **Tcomf** = Temperatura de confort (default: 26.5°C)
- **(x)⁺** = solo valores positivos

### 📊 Ejemplo

**Oficina durante un día de verano (horario 9:00-18:00):**

| Hora | Top (°C) | Ocupado | Top - 26.5 | Contribución |
|------|----------|---------|------------|--------------|
| 09:00 | 24.0 | 1 | -2.5 | 0 |
| 10:00 | 25.5 | 1 | -1.0 | 0 |
| 11:00 | 27.0 | 1 | +0.5 | **0.5** |
| 12:00 | 28.5 | 1 | +2.0 | **2.0** |
| 13:00 | 29.0 | 1 | +2.5 | **2.5** |
| 14:00 | 30.0 | 1 | +3.5 | **3.5** |
| 15:00 | 30.5 | 1 | +4.0 | **4.0** |
| 16:00 | 29.5 | 1 | +3.0 | **3.0** |
| 17:00 | 28.0 | 1 | +1.5 | **1.5** |
| 18:00 | 27.0 | 1 | +0.5 | **0.5** |

**Cálculo:**
```
IOD = (0 + 0 + 0.5 + 2.0 + 2.5 + 3.5 + 4.0 + 3.0 + 1.5 + 0.5) / 10
    = 17.5 / 10
    = 1.75°C
```

**Interpretación:** En promedio, durante las horas ocupadas, la temperatura excedió el confort en **1.75°C**.

---

## 3. AWD (Ambient Warmness Degree)

### 📚 Concepto

AWD mide cuánto excede la temperatura exterior un umbral base durante TODO el período (24 horas).

### 🧮 Fórmula

```
AWD = Promedio de (Text - Tbase)⁺ durante todas las horas
```

Donde:
- **Text** = Temperatura exterior (°C)
- **Tbase** = Temperatura base (default: 18°C)

### 📊 Ejemplo

**Día completo (24 horas):**

| Hora | Text (°C) | Text - 18 | Contribución |
|------|-----------|-----------|--------------|
| 00:00 | 16.0 | -2.0 | 0 |
| 03:00 | 14.5 | -3.5 | 0 |
| 06:00 | 15.0 | -3.0 | 0 |
| 09:00 | 20.0 | +2.0 | **2.0** |
| 12:00 | 25.0 | +7.0 | **7.0** |
| 15:00 | 28.0 | +10.0 | **10.0** |
| 18:00 | 24.0 | +6.0 | **6.0** |
| 21:00 | 19.0 | +1.0 | **1.0** |

**Suma total de 24 horas: 78.0°C**

**Cálculo:**
```
AWD = 78.0 / 24 = 3.25°C
```

**Interpretación:** En promedio, la temperatura exterior estuvo **3.25°C por encima** de la base de 18°C.

---

## 4. ALPHA (Overheating Escalator Factor)

### 📚 Concepto

ALPHA compara el sobrecalentamiento interior (IOD) con el calor ambiental (AWD).

### 🧮 Fórmula

```
ALPHA = IOD / AWD
```

### 📊 Ejemplo con los casos anteriores

```
IOD = 1.75°C
AWD = 3.25°C

ALPHA = 1.75 / 3.25 = 0.54
```

### 🎯 Interpretación

| ALPHA | Significado |
|-------|-------------|
| **< 1.0** | ✅ El edificio funciona MEJOR que el ambiente |
| **= 1.0** | El edificio replica las condiciones exteriores |
| **> 1.0** | ❌ El edificio AMPLIFICA el calor exterior |

**En nuestro ejemplo (ALPHA = 0.54):**
- El edificio está reduciendo el sobrecalentamiento exterior en un **46%**
- **Buen desempeño térmico** (probablemente con buena inercia, ventilación o sombreado)

### 📊 Ejemplos Comparativos

| Edificio | IOD | AWD | ALPHA | Evaluación |
|----------|-----|-----|-------|------------|
| **Con alta inercia** | 0.8 | 3.2 | **0.25** | Excelente (75% reducción) |
| **Con ventilación natural** | 1.5 | 3.0 | **0.50** | Bueno (50% reducción) |
| **Estándar** | 2.4 | 3.0 | **0.80** | Aceptable (20% reducción) |
| **Sin protección solar** | 3.8 | 3.0 | **1.27** | Deficiente (amplifica +27%) |
| **Invernadero** | 8.5 | 3.0 | **2.83** | Muy deficiente (amplifica +183%) |

---

## 5. HI (Heat Index)

### 📚 Concepto

HI combina temperatura y humedad para calcular la "sensación térmica" o "temperatura aparente".

### 🧮 Fórmula Simplificada

**Para T ≤ 26.7°C o RH < 40%:**
```
HI = T
```

**Para T > 26.7°C y RH ≥ 40%:**
```
HI = C1 + C2×T + C3×RH + C4×T×RH + C5×T² + C6×RH² + C7×T²×RH + C8×T×RH² + C9×T²×RH²
```

### 📊 Ejemplo

**Condiciones:**
- T = 30°C
- RH = 65%

**Cálculo:**
```
HI = -8.78 + 1.61×30 + 2.34×65 + (-0.15)×30×65 + (-0.01)×30² + ...
   = -8.78 + 48.33 + 152.07 + (-292.50) + (-11.08) + ...
   ≈ 36.0°C
```

**Interpretación:** 
- La temperatura real es **30°C**
- Pero se siente como **36°C** debido a la humedad
- Categoría: **Extreme Caution** (precaución extrema)

### 📊 Tabla de Referencia

| T (°C) | RH=40% | RH=60% | RH=80% |
|--------|--------|--------|--------|
| 27 | 27°C | 28°C | 30°C |
| 30 | 30°C | 34°C | 38°C |
| 33 | 35°C | 41°C | 49°C |
| 36 | 41°C | 50°C | 62°C |

---

## 📖 Uso Práctico

### Flujo de Trabajo Típico

```bash
# 1. Calcular todos los indicadores
energyplus-sim indicators simulation.csv --zone-group studyrooms

# 2. Los resultados muestran:
# - IOD_Simulation.csv: Sobrecalentamiento interior promedio
# - AWD_Simulation.csv: Calor ambiental exterior
# - ALPHA_Simulation.csv: Ratio de desempeño
# - DDH_Simulation.csv: Disconfort acumulado ponderado
# - HI_Simulation.csv: Sensación térmica real

# 3. Exportar para Power BI (análisis comparativo)
energyplus-sim powerbi simulation.csv \
    --simulation "Baseline" \
    --start-date "06/22" \
    --end-date "08/30"
```

### Interpretación Conjunta

Para evaluar el desempeño térmico de un edificio:

1. **DDH** → ¿Cuánto disconfort acumulado? (objetivo: < 100 °C·h/año)
2. **ALPHA** → ¿El edificio mejora o empeora el ambiente? (objetivo: < 0.7)
3. **IOD** → ¿Cuánto sobrecalentamiento promedio? (objetivo: < 1.5°C)
4. **HI** → ¿Cuál es la sensación térmica real? (objetivo: < 32°C máximo)

---

## 🔗 Ver También

- [INDICATORS.md](./INDICATORS.md) - Fórmulas matemáticas detalladas
- [README.md](../README.md) - Guía de uso del CLI
- EN 15251:2007 - Estándar de confort adaptativo

