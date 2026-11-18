# ESDV-2101: Maximo Monitor functions and alert rules

Device type `ESD_VALVE_SIS`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (16)

### FRICTION_EXPECTED_BAR

```python
FRICTION_EXPECTED_BAR =
    (0.3 + 0.004 * PST_LINE_PRESSURE_BAR)
```

### FRICTION_MEASURED_BAR

```python
FRICTION_MEASURED_BAR =
    ((PST_P_OPEN_END_BAR - PST_P_CLOSE_START_BAR) / 2)
```

### FRICTION_RATIO

```python
FRICTION_RATIO =
    FRICTION_MEASURED_BAR / FRICTION_EXPECTED_BAR
```

### SPRING_MEASURED_BAR

```python
SPRING_MEASURED_BAR =
    ((PST_P_OPEN_END_BAR + PST_P_CLOSE_START_BAR) / 2)
```

### SPRING_DEV_BAR

```python
SPRING_DEV_BAR =
    SPRING_MEASURED_BAR - 3
```

### CLOSE_START_EXPECTED_BAR

```python
CLOSE_START_EXPECTED_BAR =
    3 - FRICTION_EXPECTED_BAR
```

### OPEN_END_EXPECTED_BAR

```python
OPEN_END_EXPECTED_BAR =
    3 + FRICTION_EXPECTED_BAR
```

### TORQUE_MARGIN

```python
TORQUE_MARGIN =
    (SPRING_MEASURED_BAR * 0.7 / (FRICTION_MEASURED_BAR * 1.4))
```

### AIR_MARGIN_BAR

```python
AIR_MARGIN_BAR =
    SUPPLY_PRESSURE_BAR - PST_P_OPEN_END_BAR
```

### STROKE_RATIO

```python
STROKE_RATIO =
    LAST_CLOSE_TIME_S / 8
```

### STROKE_MARGIN_S

```python
STROKE_MARGIN_S =
    15 - LAST_CLOSE_TIME_S
```

### PFD_FE_OPS

```python
PFD_FE_OPS =
    (
      3.25e-07 * PST_INTERVAL_ACHIEVED_H
      + 0.005256
      + 0.00219
      + BYPASS_HOURS_365D / 8760
    )
```

### PFD_SIF_OPS

```python
PFD_SIF_OPS =
    (PFD_FE_OPS + 0.0003)
```

### RRF_SIF_OPS

```python
RRF_SIF_OPS =
    1 / PFD_SIF_OPS
```

### SIL_ACHIEVED

```python
SIL_ACHIEVED =
    np.where(
      PFD_SIF_OPS < 0.001,
      3,
      np.where(PFD_SIF_OPS < 0.01, 2, np.where(PFD_SIF_OPS < 0.1, 1, 0))
    )
```

### PFD_NOW

```python
PFD_NOW =
    np.minimum(
      6.5e-07 * PST_HOURS_SINCE
      + 3e-07 * PROOF_HOURS_SINCE
      + 5e-08 * OVERHAUL_HOURS_SINCE
      + BYPASS_ACTIVE,
      1
    )
```

## AlertExpression rules (13)

### ESD_STROKE_TOO_SLOW

Critical · sov_exhaust_restriction

```python
ESD_STROKE_TOO_SLOW =
    LAST_CLOSE_TIME_S > 15
```

### ESD_PST_FAILED

High · stem_seat_sticking

```python
ESD_PST_FAILED =
    PST_RESULT < 0.5
```

### ESD_TORQUE_MARGIN_LIMIT

High · stem_seat_sticking

```python
ESD_TORQUE_MARGIN_LIMIT =
    TORQUE_MARGIN < 1.5
```

### ESD_SIL_DRIFT

High · pst_not_run

```python
ESD_SIL_DRIFT =
    PFD_SIF_OPS >= 0.01
```

### ESD_PROOF_OVERDUE

High

```python
ESD_PROOF_OVERDUE =
    PROOF_HOURS_SINCE > 35040
```

### ESD_BYPASS_LONG

High · bypass_left_on

```python
ESD_BYPASS_LONG =
    (BYPASS_ACTIVE > 0.5) & (BYPASS_ACTIVE_H > 8)
```

### ESD_TORQUE_MARGIN_LOW

Medium · stem_seat_sticking

```python
ESD_TORQUE_MARGIN_LOW =
    (TORQUE_MARGIN < 2) & (TORQUE_MARGIN >= 1.5)
```

### ESD_FRICTION_HIGH

Medium · stem_seat_sticking

```python
ESD_FRICTION_HIGH =
    FRICTION_RATIO > 1.5
```

### ESD_SPRING_WEAK

Medium · spring_relaxation

```python
ESD_SPRING_WEAK =
    SPRING_DEV_BAR < -0.35
```

### ESD_STROKE_SLOW

Medium · sov_exhaust_restriction

```python
ESD_STROKE_SLOW =
    ((LAST_CLOSE_TIME_S / 8) > 1.25) & (LAST_CLOSE_TIME_S <= 15)
```

### ESD_AIR_MARGIN

Medium · air_supply_low

```python
ESD_AIR_MARGIN =
    AIR_MARGIN_BAR < 0.5
```

### ESD_POSITION_MISMATCH

Medium · position_feedback

```python
ESD_POSITION_MISMATCH =
    ((LIMIT_OPEN > 0.5) & (TRAVEL_PCT < 95))
    | ((LIMIT_CLOSED > 0.5) & (TRAVEL_PCT > 5))
    | ((LIMIT_OPEN > 0.5) & (LIMIT_CLOSED > 0.5))
```

### ESD_PST_OVERDUE

Medium · pst_not_run

```python
ESD_PST_OVERDUE =
    PST_HOURS_SINCE > 1095
```
