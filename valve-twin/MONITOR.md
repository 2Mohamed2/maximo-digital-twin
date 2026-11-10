# FCV-401: Maximo Monitor functions and alert rules

Device type `CONTROL_VALVE`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (10)

### KV_MEASURED

```python
KV_MEASURED =
    (
      FLOW_M3H
      / np.sqrt(
          (VALVE_INLET_PRESSURE_BAR - VALVE_OUTLET_PRESSURE_BAR).clip(lower=0.005)
          / 1
        )
    )
```

### KV_EXPECTED

```python
KV_EXPECTED =
    (200 * np.maximum((POSITION_PCT.clip(lower=0) / 100), 0.0005))
```

### KV_RATIO

```python
KV_RATIO =
    KV_MEASURED / KV_EXPECTED
```

### SIGMA

```python
SIGMA =
    (
      (
        VALVE_INLET_PRESSURE_BAR
        - (
            0.61094
            * np.exp(17.625 * FLUID_TEMP_C / (FLUID_TEMP_C + 243.04))
            / 100
          )
      )
      / (VALVE_INLET_PRESSURE_BAR - VALVE_OUTLET_PRESSURE_BAR).clip(lower=0.005)
    )
```

### POSITION_ERROR_PCT

```python
POSITION_ERROR_PCT =
    POSITION_CMD_PCT - POSITION_PCT
```

### FLOW_ERROR_PCT

```python
FLOW_ERROR_PCT =
    (FLOW_M3H - FLOW_SETPOINT_M3H) / FLOW_SETPOINT_M3H.clip(lower=1) * 100
```

### FORCE_EXPECTED_PCT

```python
FORCE_EXPECTED_PCT =
    (
      (
        600
        + (VALVE_INLET_PRESSURE_BAR - VALVE_OUTLET_PRESSURE_BAR).clip(lower=0.005)
          * 100000
          * 0.00785
      )
      / 4500
      * 100
    )
```

### FORCE_DEVIATION_PCT

```python
FORCE_DEVIATION_PCT =
    ACTUATOR_FORCE_PCT - FORCE_EXPECTED_PCT
```

### STRAINER_KV_RATIO

```python
STRAINER_KV_RATIO =
    (FLOW_M3H / np.sqrt(STRAINER_DP_BAR.clip(lower=0.0002) / 1)) / 600
```

### VALVE_AUTHORITY

```python
VALVE_AUTHORITY =
    (VALVE_INLET_PRESSURE_BAR - VALVE_OUTLET_PRESSURE_BAR)
    / (INLET_PRESSURE_BAR - RETURN_PRESSURE_BAR).clip(lower=0.01)
```

## AlertExpression rules (10)

### FCV_SEAT_PLUG_WEAR

Medium · seat_plug_wear

```python
FCV_SEAT_PLUG_WEAR =
    ((POSITION_PCT.clip(lower=0) / 100) > 0.005)
    & ((POSITION_PCT.clip(lower=0) / 100) < 0.5)
    & (KV_RATIO > 1.15)
```

### FCV_KV_LOW

Medium · position_sensor_drift

```python
FCV_KV_LOW =
    ((POSITION_PCT.clip(lower=0) / 100) > 0.08)
    & (KV_RATIO < 0.85)
    & (POSITION_CMD_PCT < 99)
```

### FCV_CAVITATION

High · seat_plug_wear

```python
FCV_CAVITATION =
    ((POSITION_PCT.clip(lower=0) / 100) > 0.02) & (SIGMA < 1.3)
```

### FCV_CAVITATION_INCIPIENT

Low

```python
FCV_CAVITATION_INCIPIENT =
    ((POSITION_PCT.clip(lower=0) / 100) > 0.02)
    & (SIGMA < 2)
    & (SIGMA >= 1.3)
```

### FCV_STICTION

Medium · stiction

```python
FCV_STICTION =
    (ACTUATOR_FORCE_PCT - FORCE_EXPECTED_PCT > 15)
    & (ACTUATOR_FORCE_PCT <= 95)
```

### FCV_ACTUATOR_OVERLOAD

High · actuator_fault

```python
FCV_ACTUATOR_OVERLOAD =
    (ACTUATOR_TEMP_C > 75) | (ACTUATOR_FORCE_PCT > 95)
```

### FCV_GLAND_LEAK

Medium · gland_leak

```python
FCV_GLAND_LEAK =
    GLAND_LEAK_ML_MIN > 2
```

### FCV_STRAINER_BLOCKED

Medium · strainer_blockage

```python
FCV_STRAINER_BLOCKED =
    STRAINER_KV_RATIO < 0.6
```

### FCV_SATURATED

Medium

```python
FCV_SATURATED =
    (POSITION_CMD_PCT > 98)
    & (
        (FLOW_M3H - FLOW_SETPOINT_M3H)
        / FLOW_SETPOINT_M3H.clip(lower=1)
        * 100
        < -5
      )
```

### FCV_FAULT

Critical

```python
FCV_FAULT =
    FAULT_CODE > 0
```
