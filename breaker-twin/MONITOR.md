# CB-701: Maximo Monitor functions and alert rules

Device type `CIRCUIT_BREAKER_SF6`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### SF6_P20_CALC_MPA

```python
SF6_P20_CALC_MPA =
    (SF6_PRESSURE_MPA * 293.15 / (SF6_GAS_TEMP_C + 273.15))
```

### SF6_DENSITY_KG_M3

```python
SF6_DENSITY_KG_M3 =
    SF6_P20_CALC_MPA * 1000000 / (56.92 * 293.15)
```

### SF6_MARGIN_ALARM_MPA

```python
SF6_MARGIN_ALARM_MPA =
    SF6_P20_CALC_MPA - 0.62
```

### SF6_MARGIN_LOCKOUT_MPA

```python
SF6_MARGIN_LOCKOUT_MPA =
    SF6_P20_CALC_MPA - 0.6
```

### DENSITY_MONITOR_DEV_MPA

```python
DENSITY_MONITOR_DEV_MPA =
    SF6_DENSITY_P20_MPA - SF6_P20_CALC_MPA
```

### OPEN_TIME_EXPECTED_MS

```python
OPEN_TIME_EXPECTED_MS =
    (23 + 0.08 * (110 - CONTROL_VOLTAGE_V))
```

### OPEN_TIME_DEV_MS

```python
OPEN_TIME_DEV_MS =
    LAST_OPEN_TIME_MS - OPEN_TIME_EXPECTED_MS
```

### CLOSE_TIME_EXPECTED_MS

```python
CLOSE_TIME_EXPECTED_MS =
    (54 + 0.15 * (110 - CONTROL_VOLTAGE_V))
```

### CLOSE_TIME_DEV_MS

```python
CLOSE_TIME_DEV_MS =
    LAST_CLOSE_TIME_MS - CLOSE_TIME_EXPECTED_MS
```

### TRIP_COIL_EXPECTED_A

```python
TRIP_COIL_EXPECTED_A =
    (CONTROL_VOLTAGE_V / 50)
```

### TRIP_COIL_RATIO

```python
TRIP_COIL_RATIO =
    TRIP_COIL_PEAK_A / (CONTROL_VOLTAGE_V / 50)
```

### CHARGE_TIME_EXPECTED_S

```python
CHARGE_TIME_EXPECTED_S =
    CONTROL_VOLTAGE_V * 0 + 12
```

### CHARGE_TIME_RATIO

```python
CHARGE_TIME_RATIO =
    SPRING_CHARGE_TIME_S / 12
```

### WEAR_L1_PCT

```python
WEAR_L1_PCT =
    (WEAR_SUM_L1 / 15301.6 * 100)
```

### WEAR_L2_PCT

```python
WEAR_L2_PCT =
    (WEAR_SUM_L2 / 15301.6 * 100)
```

### WEAR_L3_PCT

```python
WEAR_L3_PCT =
    (WEAR_SUM_L3 / 15301.6 * 100)
```

### WEAR_MAX_PCT

```python
WEAR_MAX_PCT =
    np.maximum(
      np.maximum(
        (WEAR_SUM_L1 / 15301.6 * 100),
        (WEAR_SUM_L2 / 15301.6 * 100)
      ),
      (WEAR_SUM_L3 / 15301.6 * 100)
    )
```

### POLE_RISE_L2_K

```python
POLE_RISE_L2_K =
    POLE_TEMP_L2_C - AMBIENT_TEMP_C
```

### POLE_RISE_EXPECTED_K

```python
POLE_RISE_EXPECTED_K =
    (35 * (LOAD_CURRENT_L2_A / 3150) ** 2)
```

### POLE_RESIDUAL_MAX_K

```python
POLE_RESIDUAL_MAX_K =
    np.maximum(
      np.maximum(
        (
          (POLE_TEMP_L1_C - AMBIENT_TEMP_C)
          - (35 * (LOAD_CURRENT_L1_A / 3150) ** 2)
        ),
        (POLE_RISE_L2_K - POLE_RISE_EXPECTED_K)
      ),
      (
        (POLE_TEMP_L3_C - AMBIENT_TEMP_C)
        - (35 * (LOAD_CURRENT_L3_A / 3150) ** 2)
      )
    )
```

## AlertExpression rules (13)

### CB_SF6_LOCKOUT

Critical · sf6_leak

```python
CB_SF6_LOCKOUT =
    SF6_P20_CALC_MPA < 0.6
```

### CB_SF6_ALARM

High · sf6_leak

```python
CB_SF6_ALARM =
    (SF6_P20_CALC_MPA < 0.62) & (SF6_P20_CALC_MPA >= 0.6)
```

### CB_SF6_LOW

Low · sf6_leak

```python
CB_SF6_LOW =
    (SF6_P20_CALC_MPA < 0.68) & (SF6_P20_CALC_MPA >= 0.62)
```

### CB_DENSITY_MONITOR

Medium · density_monitor_drift

```python
CB_DENSITY_MONITOR =
    np.absDENSITY_MONITOR_DEV_MPA > 0.015
```

### CB_OPEN_SLOW

Medium · mechanism_lubrication

```python
CB_OPEN_SLOW =
    OPEN_TIME_DEV_MS > 3
```

### CB_CLOSE_SLOW

Medium · mechanism_lubrication

```python
CB_CLOSE_SLOW =
    CLOSE_TIME_DEV_MS > 5
```

### CB_TRIP_COIL

High · trip_coil

```python
CB_TRIP_COIL =
    TRIP_COIL_RATIO < 0.8
```

### CB_SPRING_CHARGE

Medium · spring_motor

```python
CB_SPRING_CHARGE =
    (SPRING_CHARGE_TIME_S / 12) > 1.3
```

### CB_CONTACT_WEAR

Medium · contact_wear

```python
CB_CONTACT_WEAR =
    (
      np.maximum(
        np.maximum(
          (WEAR_SUM_L1 / 15301.6 * 100),
          (WEAR_SUM_L2 / 15301.6 * 100)
        ),
        (WEAR_SUM_L3 / 15301.6 * 100)
      )
      > 80
    )
    & (
        np.maximum(
          np.maximum(
            (WEAR_SUM_L1 / 15301.6 * 100),
            (WEAR_SUM_L2 / 15301.6 * 100)
          ),
          (WEAR_SUM_L3 / 15301.6 * 100)
        )
        < 100
      )
```

### CB_CONTACT_WEAR_LIMIT

High · contact_wear

```python
CB_CONTACT_WEAR_LIMIT =
    np.maximum(
      np.maximum(
        (WEAR_SUM_L1 / 15301.6 * 100),
        (WEAR_SUM_L2 / 15301.6 * 100)
      ),
      (WEAR_SUM_L3 / 15301.6 * 100)
    )
    >= 100
```

### CB_POLE_HOT

Medium · contact_wear

```python
CB_POLE_HOT =
    (
      np.maximum(
        np.maximum(
          (
            (POLE_TEMP_L1_C - AMBIENT_TEMP_C)
            - (35 * (LOAD_CURRENT_L1_A / 3150) ** 2)
          ),
          (POLE_RISE_L2_K - POLE_RISE_EXPECTED_K)
        ),
        (
          (POLE_TEMP_L3_C - AMBIENT_TEMP_C)
          - (35 * (LOAD_CURRENT_L3_A / 3150) ** 2)
        )
      )
      > 10
    )
    & (
        np.maximum(
          np.maximum(LOAD_CURRENT_L1_A, LOAD_CURRENT_L2_A),
          LOAD_CURRENT_L3_A
        )
        > 600
      )
```

### CB_HEATER

Medium · heater_fault

```python
CB_HEATER =
    (HEATER_CURRENT_A < 0.2) | (CABINET_HUMIDITY_PCT > 85)
```

### CB_INSPECTION_DUE

Low

```python
CB_INSPECTION_DUE =
    OPERATION_COUNT >= 3000
```
