# LS-5201: Maximo Monitor functions and alert rules

Device type `SEWAGE_LIFT_STATION`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### INFLOW_LS

```python
INFLOW_LS =
    (0.1178097245 * LEVEL_RATE_MM_MIN + MAIN_FLOW_LS)
```

### INFLOW_RATIO

```python
INFLOW_RATIO =
    INFLOW_LS / 55
```

### FREEBOARD_M

```python
FREEBOARD_M =
    3.2 - LEVEL_M
```

### TIME_TO_SPILL_MIN

```python
TIME_TO_SPILL_MIN =
    np.where(
      (INFLOW_LS - 70.79707817) > 0.1,
      np.minimum(
        117.8097245
        * np.maximum(3.2 - LEVEL_M, 0)
        / np.maximum((INFLOW_LS - 70.79707817), 0.1),
        999
      ),
      999
    )
```

### CYCLE_INFLOW_LS

```python
CYCLE_INFLOW_LS =
    0.1178097245 * CYC_FILL_MM_MIN
```

### PUMP_FLOW_VOL_LS

```python
PUMP_FLOW_VOL_LS =
    (0.1178097245 * (CYC_DRAW_MM_MIN + CYC_FILL_MM_MIN))
```

### PUMP_HEAD_M

```python
PUMP_HEAD_M =
    (CYC_DISCHARGE_BAR * 10.19367992 + 2.8 - CYC_LEVEL_M)
```

### PUMP_FLOW_EXPECTED_LS

```python
PUMP_FLOW_EXPECTED_LS =
    (55 * np.sqrt(np.maximum(19 - PUMP_HEAD_M, 0) / 6))
```

### PUMP_FLOW_RATIO

```python
PUMP_FLOW_RATIO =
    (PUMP_FLOW_VOL_LS / np.maximum(PUMP_FLOW_EXPECTED_LS, 1))
```

### PUMP_POWER_EXPECTED_KW

```python
PUMP_POWER_EXPECTED_KW =
    (
      0.8660513644
      * PUMP_HEAD_M
      / (2 - np.sqrt(np.maximum(19 - PUMP_HEAD_M, 0) / 6))
    )
```

### PUMP_POWER_RATIO

```python
PUMP_POWER_RATIO =
    (CYC_POWER_KW / PUMP_POWER_EXPECTED_KW)
```

### SPECIFIC_ENERGY_KWH_M3

```python
SPECIFIC_ENERGY_KWH_M3 =
    CYC_POWER_KW / (np.maximum(PUMP_FLOW_VOL_LS, 1) * 3.6)
```

### MAIN_RESISTANCE_RATIO

```python
MAIN_RESISTANCE_RATIO =
    (
      (CYC_DISCHARGE_BAR * 10.19367992 - 6.2)
      / (0.001768595041 * np.maximum(PUMP_FLOW_VOL_LS, 1) ** 2)
    )
```

### MAIN_VELOCITY_MS

```python
MAIN_VELOCITY_MS =
    (PUMP_FLOW_VOL_LS / 45.23893421)
```

### BACKFLOW_LS

```python
BACKFLOW_LS =
    (0.1178097245 * (CYC_AFTER_STOP_MM_MIN - CYC_FILL_MM_MIN))
```

### REVERSE_VELOCITY_MS

```python
REVERSE_VELOCITY_MS =
    ((CYC_STOP_PEAK_BAR - 0.60822) / 10)
```

### STARTS_MAX_1H

```python
STARTS_MAX_1H =
    np.maximum(P1_STARTS_1H, P2_STARTS_1H)
```

### RUN_IMBALANCE

```python
RUN_IMBALANCE =
    (
      np.abs(P1_RUN_H_7D - P2_RUN_H_7D)
      / np.maximum(P1_RUN_H_7D + P2_RUN_H_7D, 1)
    )
```

### SUBMERGENCE_MARGIN

```python
SUBMERGENCE_MARGIN =
    ((LEVEL_M - 0.15) / 0.6613922703)
```

## AlertExpression rules (15)

### LS_SPILL_RISK

Critical · storm_inflow

```python
LS_SPILL_RISK =
    np.where(
      (INFLOW_LS - 70.79707817) > 0.1,
      np.minimum(
        117.8097245
        * np.maximum(3.2 - LEVEL_M, 0)
        / np.maximum((INFLOW_LS - 70.79707817), 0.1),
        999
      ),
      999
    )
    < 30
```

### LS_LEVEL_HIGH

High · storm_inflow

```python
LS_LEVEL_HIGH =
    LEVEL_M > 2.4
```

### LS_LEVEL_SENSOR_MISMATCH

High · level_sensor_fault

```python
LS_LEVEL_SENSOR_MISMATCH =
    ((FLOAT_HIGH > 0.5) & (LEVEL_M < 2.1))
    | ((FLOAT_HIGH < 0.5) & (LEVEL_M > 2.7))
```

### LS_RAGGING

High · impeller_ragging

```python
LS_RAGGING =
    (PUMP_FLOW_RATIO < 0.85) & (PUMP_POWER_RATIO > 1.1)
```

### LS_MAIN_RESISTANCE_HIGH

High · main_restriction

```python
LS_MAIN_RESISTANCE_HIGH =
    MAIN_RESISTANCE_RATIO > 1.8
```

### LS_SUBMERGENCE_LOW

High

```python
LS_SUBMERGENCE_LOW =
    ((LEVEL_M - 0.15) / 0.6613922703) < 1
```

### LS_INFLOW_ABOVE_CAPACITY

Medium · storm_inflow

```python
LS_INFLOW_ABOVE_CAPACITY =
    INFLOW_RATIO > 1
```

### LS_PUMP_FLOW_LOW

Medium · impeller_ragging

```python
LS_PUMP_FLOW_LOW =
    PUMP_FLOW_RATIO < 0.85
```

### LS_PUMP_WEAR

Medium · impeller_wear

```python
LS_PUMP_WEAR =
    (PUMP_FLOW_RATIO < 0.85) & (PUMP_POWER_RATIO <= 1.1)
```

### LS_CHECK_VALVE_PASSING

Medium · check_valve_passing

```python
LS_CHECK_VALVE_PASSING =
    BACKFLOW_LS > 3
```

### LS_CHECK_VALVE_SLAM

Medium · check_valve_slam

```python
LS_CHECK_VALVE_SLAM =
    REVERSE_VELOCITY_MS > 0.15
```

### LS_SEAL_LEAK

Medium · seal_leak

```python
LS_SEAL_LEAK =
    (P1_LEAK > 0.5) | (P2_LEAK > 0.5)
```

### LS_STARTS_HIGH

Medium

```python
LS_STARTS_HIGH =
    np.maximum(P1_STARTS_1H, P2_STARTS_1H) > 15
```

### LS_ALTERNATION_IMBALANCE

Low

```python
LS_ALTERNATION_IMBALANCE =
    RUN_IMBALANCE > 0.4
```

### LS_MAIN_VELOCITY_LOW

Low

```python
LS_MAIN_VELOCITY_LOW =
    MAIN_VELOCITY_MS < 0.6
```
