# DG-6201: Maximo Monitor functions and alert rules

Device type `STANDBY_DIESEL_GENSET`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### LOAD_PCT

```python
LOAD_PCT =
    (OUTPUT_KW / 1650) * 100
```

### KVA

```python
KVA =
    np.sqrt(OUTPUT_KW ** 2 + OUTPUT_KVAR ** 2)
```

### FUEL_EXPECTED_LPH

```python
FUEL_EXPECTED_LPH =
    (48 + 0.168242424 * OUTPUT_KW + 2.9385e-05 * OUTPUT_KW ** 2)
```

### FUEL_RATIO

```python
FUEL_RATIO =
    (FUEL_RATE_LPH / FUEL_EXPECTED_LPH)
```

### SFC_G_KWH

```python
SFC_G_KWH =
    FUEL_RATE_LPH * 840 / np.maximum(OUTPUT_KW, 1)
```

### EXH_MEAN_C

```python
EXH_MEAN_C =
    ((EXHAUST_TEMP_A_C + EXHAUST_TEMP_B_C) / 2)
```

### EXH_EXPECTED_C

```python
EXH_EXPECTED_C =
    (140 + 300 * (OUTPUT_KW / 1650) + 1 * (AMBIENT_C - 25))
```

### EXH_RESIDUAL_K

```python
EXH_RESIDUAL_K =
    EXH_MEAN_C - EXH_EXPECTED_C
```

### EXH_BANK_DIFF_K

```python
EXH_BANK_DIFF_K =
    EXHAUST_TEMP_A_C - EXHAUST_TEMP_B_C
```

### EXH_CYL_SPREAD_K

```python
EXH_CYL_SPREAD_K =
    (EXHAUST_CYL_MAX_C - EXHAUST_CYL_MIN_C)
```

### COOLANT_EXPECTED_C

```python
COOLANT_EXPECTED_C =
    np.maximum(85, AMBIENT_C + 55 * (0.3 + 0.7 * (OUTPUT_KW / 1650)))
```

### COOLANT_RESIDUAL_K

```python
COOLANT_RESIDUAL_K =
    COOLANT_TEMP_C
    - np.maximum(85, AMBIENT_C + 55 * (0.3 + 0.7 * (OUTPUT_KW / 1650)))
```

### ATS_TIME_S

```python
ATS_TIME_S =
    (LAST_OUTAGE_TO_LOAD_S - LAST_START_READY_S)
```

### TYPE10_MARGIN_S

```python
TYPE10_MARGIN_S =
    10 - LAST_OUTAGE_TO_LOAD_S
```

### FUEL_VOLUME_L

```python
FUEL_VOLUME_L =
    (BULK_TANK_PCT * 250 + DAY_TANK_PCT * 10)
```

### RUNTIME_FULL_LOAD_H

```python
RUNTIME_FULL_LOAD_H =
    (FUEL_VOLUME_L / 405.600662)
```

### RUNTIME_DESIGN_LOAD_H

```python
RUNTIME_DESIGN_LOAD_H =
    FUEL_VOLUME_L / 292.205309
```

### WET_STACK_INDEX

```python
WET_STACK_INDEX =
    LIGHT_LOAD_H / 8
```

### FUEL_TEST_DUE_D

```python
FUEL_TEST_DUE_D =
    365 - FUEL_TEST_AGE_D
```

### TRANSIENT_FREQ_MARGIN_PCT

```python
TRANSIENT_FREQ_MARGIN_PCT =
    7 - LAST_STEP_FREQ_DIP_PCT
```

## AlertExpression rules (15)

### GEN_TYPE10_FAIL

Critical · starting_battery_weak

```python
GEN_TYPE10_FAIL =
    LAST_OUTAGE_TO_LOAD_S > 10
```

### GEN_START_SLOW

High · starting_battery_weak

```python
GEN_START_SLOW =
    LAST_START_READY_S > 8.5
```

### GEN_RUNTIME_SHORT

High

```python
GEN_RUNTIME_SHORT =
    RUNTIME_FULL_LOAD_H < 48
```

### GEN_COOLANT_HOT

High · radiator_fouling

```python
GEN_COOLANT_HOT =
    (RUN_MODE > 2.5) & (COOLANT_RESIDUAL_K > 6)
```

### GEN_CRANK_DIP

Medium · starting_battery_weak

```python
GEN_CRANK_DIP =
    LAST_CRANK_MIN_V < 18
```

### GEN_ATS_SLOW

Medium · ats_slow

```python
GEN_ATS_SLOW =
    ATS_TIME_S > 1.5
```

### GEN_JW_HEATER_LOW

Medium · jacket_heater_failure

```python
GEN_JW_HEATER_LOW =
    LAST_PRESTART_COOLANT_C < 32
```

### GEN_EXH_TEMP_HIGH

Medium · air_restriction

```python
GEN_EXH_TEMP_HIGH =
    (RUN_MODE > 2.5) & ((OUTPUT_KW / 1650) >= 0.3) & (EXH_RESIDUAL_K > 40)
```

### GEN_EXH_SPREAD_HIGH

Medium · injector_fault

```python
GEN_EXH_SPREAD_HIGH =
    (RUN_MODE > 2.5) & ((OUTPUT_KW / 1650) >= 0.3) & (EXH_CYL_SPREAD_K > 60)
```

### GEN_FUEL_RATE_HIGH

Medium · air_restriction

```python
GEN_FUEL_RATE_HIGH =
    (RUN_MODE > 2.5) & ((OUTPUT_KW / 1650) >= 0.2) & (FUEL_RATIO > 1.08)
```

### GEN_TRANSIENT_G3

Medium · air_restriction

```python
GEN_TRANSIENT_G3 =
    (LAST_STEP_FREQ_DIP_PCT > 7) | (LAST_STEP_FREQ_RECOVERY_S > 3)
```

### GEN_TEST_LOAD_LOW

Medium · light_load_testing

```python
GEN_TEST_LOAD_LOW =
    (np.abs(RUN_MODE - 3) < 0.5)
    & ((OUTPUT_KW / 1650) < 0.3)
    & (EXH_MEAN_C < 230)
```

### GEN_WET_STACK_RISK

Medium · light_load_testing

```python
GEN_WET_STACK_RISK =
    LIGHT_LOAD_H > 8
```

### GEN_FUEL_WATER

Medium · fuel_water

```python
GEN_FUEL_WATER =
    FUEL_WATER_PPM > 200
```

### GEN_DAYTANK_LOW

Medium

```python
GEN_DAYTANK_LOW =
    DAY_TANK_PCT < 60
```
