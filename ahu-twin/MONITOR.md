# AHU-6401: Maximo Monitor functions and alert rules

Device type `AIR_HANDLING_UNIT`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### SFP_KW_M3S

```python
SFP_KW_M3S =
    ((SUPPLY_FAN_KW + EXTRACT_FAN_KW) / SUPPLY_FLOW_M3S)
```

### SFP_EXPECTED_KW_M3S

```python
SFP_EXPECTED_KW_M3S =
    (
      (
        SUPPLY_FLOW_M3S
        * (450 * SUPPLY_FLOW_M3S ** 2 + 70 * SUPPLY_FLOW_M3S ** 1.5)
        + EXTRACT_FLOW_M3S
          * (410 * EXTRACT_FLOW_M3S ** 2 + 50 * EXTRACT_FLOW_M3S ** 1.5)
      )
      / 0.62
      / 1000
      / SUPPLY_FLOW_M3S
    )
```

### SFP_RATIO

```python
SFP_RATIO =
    SFP_KW_M3S / SFP_EXPECTED_KW_M3S
```

### SFP_SUPPLY_W_M3S

```python
SFP_SUPPLY_W_M3S =
    (SUPPLY_FAN_KW / SUPPLY_FLOW_M3S * 1000)
```

### SFP_SUPPLY_CATEGORY

```python
SFP_SUPPLY_CATEGORY =
    np.where(
      SFP_SUPPLY_W_M3S >= 4500,
      7,
      np.where(
        SFP_SUPPLY_W_M3S >= 3000,
        6,
        np.where(
          SFP_SUPPLY_W_M3S >= 2000,
          5,
          np.where(
            SFP_SUPPLY_W_M3S >= 1250,
            4,
            np.where(
              SFP_SUPPLY_W_M3S >= 750,
              3,
              np.where(
                SFP_SUPPLY_W_M3S >= 500,
                2,
                np.where(SFP_SUPPLY_W_M3S >= 300, 1, 0)
              )
            )
          )
        )
      )
    )
```

### FILTER_SUP_RATIO

```python
FILTER_SUP_RATIO =
    (SUPPLY_FILTER_PA / (70 * SUPPLY_FLOW_M3S ** 1.5))
```

### FILTER_EXT_RATIO

```python
FILTER_EXT_RATIO =
    (EXTRACT_FILTER_PA / (50 * EXTRACT_FLOW_M3S ** 1.5))
```

### FILTER_EXTRA_COST_EUR_Y

```python
FILTER_EXTRA_COST_EUR_Y =
    (
      SUPPLY_FLOW_M3S
      * (SUPPLY_FILTER_PA - (70 * SUPPLY_FLOW_M3S ** 1.5))
      / 0.62
      / 1000
      * 1000
    )
```

### FAN_SUP_EXPECTED_KW

```python
FAN_SUP_EXPECTED_KW =
    (
      SUPPLY_FLOW_M3S
      * (450 * SUPPLY_FLOW_M3S ** 2 + SUPPLY_FILTER_PA)
      / 0.62
      / 1000
    )
```

### FAN_SUP_EFF_RATIO

```python
FAN_SUP_EFF_RATIO =
    (FAN_SUP_EXPECTED_KW / SUPPLY_FAN_KW)
```

### HR_EFF

```python
HR_EFF =
    ((T_AFTER_HR_C - T_OUTDOOR_C) / (T_EXTRACT_C - T_OUTDOOR_C))
```

### HR_EFF_EXPECTED

```python
HR_EFF_EXPECTED =
    (
      np.minimum(0.9, 0.83 - 0.08 * (SUPPLY_FLOW_M3S / 1 - 1))
      * np.minimum(1, EXTRACT_FLOW_M3S / SUPPLY_FLOW_M3S)
    )
```

### HR_EFF_DEV

```python
HR_EFF_DEV =
    (HR_EFF - HR_EFF_EXPECTED)
```

### HR_RECOVERED_KW

```python
HR_RECOVERED_KW =
    (1.2072 * SUPPLY_FLOW_M3S * (T_AFTER_HR_C - T_OUTDOOR_C))
```

### HR_LOST_KW

```python
HR_LOST_KW =
    (
      np.where(
        WHEEL_SPEED_PCT >= 95,
        np.maximum(0, HR_EFF_EXPECTED - HR_EFF),
        0
      )
      * 1.2072
      * SUPPLY_FLOW_M3S
      * (T_EXTRACT_C - T_OUTDOOR_C)
    )
```

### COIL_AIR_KW

```python
COIL_AIR_KW =
    (1.2072 * SUPPLY_FLOW_M3S * (T_SUPPLY_C - T_AFTER_HR_C) - SUPPLY_FAN_KW)
```

### COIL_BALANCE_K

```python
COIL_BALANCE_K =
    ((COIL_AIR_KW - (HEATING_KW - COOLING_KW)) / (1.2072 * SUPPLY_FLOW_M3S))
```

### FLOW_BALANCE

```python
FLOW_BALANCE =
    (EXTRACT_FLOW_M3S / SUPPLY_FLOW_M3S)
```

### OCC_FROM_CO2

```python
OCC_FROM_CO2 =
    (SUPPLY_FLOW_M3S * (CO2_PPM - 420) * 1e-06 / 5.2e-06)
```

### VENT_PER_PERSON_LS

```python
VENT_PER_PERSON_LS =
    (SUPPLY_FLOW_M3S * 1000 / np.maximum(OCCUPANCY, 1))
```

## AlertExpression rules (13)

### AHU_FILTER_SUP_LIMIT

High · filter_loading

```python
AHU_FILTER_SUP_LIMIT =
    FILTER_SUP_RATIO > 3
```

### AHU_FILTER_SUP_LOW

High · filter_bypass

```python
AHU_FILTER_SUP_LOW =
    FILTER_SUP_RATIO < 0.5
```

### AHU_UNDERVENTILATION

High · co2_sensor_drift

```python
AHU_UNDERVENTILATION =
    (OCCUPANCY >= 20) & (VENT_PER_PERSON_LS < 7)
```

### AHU_FILTER_SUP_DIRTY

Medium · filter_loading

```python
AHU_FILTER_SUP_DIRTY =
    (FILTER_SUP_RATIO > 2) & (FILTER_SUP_RATIO <= 3)
```

### AHU_SFP_HIGH

Medium · filter_loading

```python
AHU_SFP_HIGH =
    SFP_KW_M3S / SFP_EXPECTED_KW_M3S > 1.15
```

### AHU_FAN_EFF_LOW

Medium · fan_degradation

```python
AHU_FAN_EFF_LOW =
    FAN_SUP_EFF_RATIO < 0.85
```

### AHU_HR_EFF_LOW

Medium · wheel_slip

```python
AHU_HR_EFF_LOW =
    (WHEEL_SPEED_PCT >= 95)
    & ((T_EXTRACT_C - T_OUTDOOR_C) >= 8)
    & (HR_EFF_DEV < -0.1)
```

### AHU_HEAT_VALVE_PASSING

Medium · heating_valve_passing

```python
AHU_HEAT_VALVE_PASSING =
    (HEATING_KW > 1) & (HEATING_VALVE_PCT < 2)
```

### AHU_SIMULT_HEAT_COOL

Medium · heating_valve_passing

```python
AHU_SIMULT_HEAT_COOL =
    (HEATING_KW > 1) & (COOLING_KW > 1)
```

### AHU_COIL_BALANCE

Medium · supply_temp_drift

```python
AHU_COIL_BALANCE =
    np.abs(COIL_BALANCE_K) > 1.5
```

### AHU_CO2_OCC_MISMATCH

Medium · co2_sensor_drift

```python
AHU_CO2_OCC_MISMATCH =
    np.abs(OCC_FROM_CO2 - OCCUPANCY) > np.maximum(15, 0.25 * OCCUPANCY)
```

### AHU_FLOW_IMBALANCE

Medium · extract_blockage

```python
AHU_FLOW_IMBALANCE =
    np.abs(FLOW_BALANCE - 1) > 0.1
```

### AHU_FILTER_EXT_DIRTY

Medium

```python
AHU_FILTER_EXT_DIRTY =
    FILTER_EXT_RATIO > 2.5
```
