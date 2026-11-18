# QC-5801: Maximo Monitor functions and alert rules

Device type `STS_CONTAINER_CRANE`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### LOAD_PCT

```python
LOAD_PCT =
    LAST_LOAD_T / 65 * 100
```

### HOIST_SPEED_EXP_MPM

```python
HOIST_SPEED_EXP_MPM =
    np.minimum(175, 5600 / (LAST_LOAD_T + 15))
```

### HOIST_POWER_EXP_KW

```python
HOIST_POWER_EXP_KW =
    ((LAST_LOAD_T + 15) * 0.192352941176 * LAST_LIFT_SPEED_MPM)
```

### HOIST_POWER_RATIO

```python
HOIST_POWER_RATIO =
    (LAST_LIFT_POWER_KW / HOIST_POWER_EXP_KW)
```

### MOVES_RATIO

```python
MOVES_RATIO =
    MOVES_PER_HOUR / 30
```

### CYCLES_USED_PCT

```python
CYCLES_USED_PCT =
    1 * MOVES_TOTAL / 2000000 * 100
```

### CYCLES_LEFT_Y

```python
CYCLES_LEFT_Y =
    (
      (2000000 - 1 * MOVES_TOTAL)
      / np.maximum(12.1666666667 * MOVES_30D, 1e-06)
    )
```

### STRUCT_USED_PCT

```python
STRUCT_USED_PCT =
    1 * STRUCT_EQUIV / 500000 * 100
```

### STRUCT_LEFT_Y

```python
STRUCT_LEFT_Y =
    (
      (500000 - 1 * STRUCT_EQUIV)
      / np.maximum(12.1666666667 * STRUCT_EQUIV_30D, 1e-06)
    )
```

### HOIST_DWP_USED_PCT

```python
HOIST_DWP_USED_PCT =
    1 * HOIST_EQUIV_H / 12500 * 100
```

### HOIST_DWP_LEFT_Y

```python
HOIST_DWP_LEFT_Y =
    (
      (12500 - 1 * HOIST_EQUIV_H)
      / np.maximum(12.1666666667 * HOIST_EQUIV_30D_H, 1e-06)
    )
```

### KM_LIFETIME

```python
KM_LIFETIME =
    HOIST_EQUIV_H / np.maximum(HOIST_HOURS, 1e-06)
```

### KM_30D

```python
KM_30D =
    HOIST_EQUIV_30D_H / np.maximum(HOIST_HOURS_30D, 1e-06)
```

### DWP_FIRST_LIMIT_Y

```python
DWP_FIRST_LIMIT_Y =
    np.minimum(np.minimum(CYCLES_LEFT_Y, STRUCT_LEFT_Y), HOIST_DWP_LEFT_Y)
```

### ROPE_DIA_DECREASE_PCT

```python
ROPE_DIA_DECREASE_PCT =
    ((36.6 - ROPE_DIA_MM) / 36 * 100)
```

### ROPE_LIFE_USED_PCT

```python
ROPE_LIFE_USED_PCT =
    ROPE_MOVES_SINCE_CHANGE / 120000 * 100
```

### TWL_FAULTS_PER_1000

```python
TWL_FAULTS_PER_1000 =
    (TWL_FAULTS_24H / np.maximum(TWL_CYCLES_24H, 1) * 1000)
```

### TROLLEY_WEAR_RATIO

```python
TROLLEY_WEAR_RATIO =
    (
      (630 - TROLLEY_WHEEL_MM)
      / np.maximum(TROLLEY_KM_SINCE_CHANGE, 1)
      * 1000
      / 0.5
    )
```

### TROLLEY_WHEEL_LEFT_MM

```python
TROLLEY_WHEEL_LEFT_MM =
    TROLLEY_WHEEL_MM - 620
```

### WIND_RATIO

```python
WIND_RATIO =
    (WIND_MS / 20)
```

## AlertExpression rules (15)

### STS_WIND_LIMIT

Critical · wind_operation

```python
STS_WIND_LIMIT =
    (CRANE_ACTIVE > 0.5) & ((WIND_MS / 20) >= 1)
```

### STS_ROPE_DISCARD

Critical · rope_wear

```python
STS_ROPE_DISCARD =
    ROPE_DIA_DECREASE_PCT >= 7.5
```

### STS_HOIST_POWER_HIGH

High · brake_drag

```python
STS_HOIST_POWER_HIGH =
    HOIST_POWER_RATIO > 1.15
```

### STS_BRAKE_PAD_LOW

High · brake_pad_wear

```python
STS_BRAKE_PAD_LOW =
    BRAKE_PAD_MM < 2
```

### STS_SNAG

High · snag_overload

```python
STS_SNAG =
    SNAG_EVENTS_24H >= 1
```

### STS_OVERLOAD

High · snag_overload

```python
STS_OVERLOAD =
    PEAK_LOAD_24H_T > 65
```

### STS_TROLLEY_WHEEL_MIN

High · trolley_wheel_wear

```python
STS_TROLLEY_WHEEL_MIN =
    (TROLLEY_WHEEL_MM - 620) < 2
```

### STS_DWP_SA_DUE

High

```python
STS_DWP_SA_DUE =
    np.minimum(np.minimum(CYCLES_LEFT_Y, STRUCT_LEFT_Y), HOIST_DWP_LEFT_Y)
    < 1
```

### STS_WIND_HIGH

Medium · wind_operation

```python
STS_WIND_HIGH =
    (CRANE_ACTIVE > 0.5) & ((WIND_MS / 20) >= 0.8) & ((WIND_MS / 20) < 1)
```

### STS_ROPE_DIAMETER

Medium · rope_wear

```python
STS_ROPE_DIAMETER =
    (ROPE_DIA_DECREASE_PCT >= 3.5) & (ROPE_DIA_DECREASE_PCT < 7.5)
```

### STS_ROPE_LIFE

Medium · rope_wear

```python
STS_ROPE_LIFE =
    ROPE_MOVES_SINCE_CHANGE > 120000
```

### STS_BRAKE_SLOW

Medium · brake_drag

```python
STS_BRAKE_SLOW =
    BRAKE_RELEASE_MS > 400
```

### STS_TWISTLOCK_FAULTS

Medium · twistlock_faults

```python
STS_TWISTLOCK_FAULTS =
    TWL_FAULTS_PER_1000 > 5
```

### STS_TROLLEY_WEAR_RATE

Medium · trolley_wheel_wear

```python
STS_TROLLEY_WEAR_RATE =
    TROLLEY_WEAR_RATIO > 1.5
```

### STS_MOVES_LOW

Low · twistlock_faults

```python
STS_MOVES_LOW =
    (CRANE_ACTIVE > 0.5) & ((MOVES_PER_HOUR / 30) < 0.8)
```
