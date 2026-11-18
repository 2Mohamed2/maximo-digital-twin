# CV-3801: Maximo Monitor functions and alert rules

Device type `BELT_CONVEYOR_OVERLAND`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### LOAD_KG_M

```python
LOAD_KG_M =
    (TONNAGE_TPH / (3.6 * np.maximum(BELT_SPEED_MS, 0.1)))
```

### RESIST_MAIN_KN

```python
RESIST_MAIN_KN =
    (507.177 * (97.33 + LOAD_KG_M)) / 1000
```

### RESIST_SLOPE_KN

```python
RESIST_SLOPE_KN =
    (LOAD_KG_M * 392.4) / 1000
```

### FU_EXPECTED_KN

```python
FU_EXPECTED_KN =
    (((507.177 * (97.33 + LOAD_KG_M)) + (LOAD_KG_M * 392.4)) / 1000)
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    (FU_EXPECTED_KN * np.maximum(BELT_SPEED_MS, 0.1) / 0.92)
```

### POWER_MEASURED_KW

```python
POWER_MEASURED_KW =
    (MOTOR1_POWER_KW + MOTOR2_POWER_KW)
```

### POWER_RESIDUAL_KW

```python
POWER_RESIDUAL_KW =
    POWER_MEASURED_KW - POWER_EXPECTED_KW
```

### POWER_RATIO

```python
POWER_RATIO =
    POWER_MEASURED_KW / POWER_EXPECTED_KW
```

### FU_MEASURED_KN

```python
FU_MEASURED_KN =
    (POWER_MEASURED_KW * 0.92 / np.maximum(BELT_SPEED_MS, 0.1))
```

### FRICTION_APPARENT

```python
FRICTION_APPARENT =
    (FU_MEASURED_KN * 1000 - (LOAD_KG_M * 392.4))
    / (25358.85 * (97.33 + LOAD_KG_M))
```

### LOAD_IMBALANCE_PCT

```python
LOAD_IMBALANCE_PCT =
    np.abs(MOTOR1_POWER_KW - MOTOR2_POWER_KW)
    / np.maximum(POWER_MEASURED_KW, 1)
    * 100
```

### SLIP_PCT

```python
SLIP_PCT =
    (
      (DRIVE_PULLEY_SPEED_MS - BELT_SPEED_MS)
      / np.maximum(DRIVE_PULLEY_SPEED_MS, 0.1)
      * 100
    )
```

### CREEP_EXPECTED_PCT

```python
CREEP_EXPECTED_PCT =
    (FU_MEASURED_KN * 0.00104166666667)
```

### SLIP_EXCESS_PCT

```python
SLIP_EXCESS_PCT =
    SLIP_PCT - CREEP_EXPECTED_PCT
```

### T2_MIN_KN

```python
T2_MIN_KN =
    (FU_MEASURED_KN / 2.60678574441)
```

### SLIP_MARGIN

```python
SLIP_MARGIN =
    (TAKEUP_FORCE_KN / 2) / np.maximum(T2_MIN_KN, 1)
```

### TAKEUP_ELASTIC_M

```python
TAKEUP_ELASTIC_M =
    (FU_MEASURED_KN * 0.00651041666667)
```

### BELT_ELONGATION_PCT

```python
BELT_ELONGATION_PCT =
    ((TAKEUP_POSITION_M - 1.5 - TAKEUP_ELASTIC_M) / 25)
```

### BELT_SAFETY_FACTOR

```python
BELT_SAFETY_FACTOR =
    2400 / ((TAKEUP_FORCE_KN / 2) + FU_MEASURED_KN)
```

### IDLER_DT_K

```python
IDLER_DT_K =
    IDLER_MAX_TEMP_C - AMBIENT_TEMP_C
```

## AlertExpression rules (15)

### CV_SPLICE_CRITICAL

Critical · splice_failure

```python
CV_SPLICE_CRITICAL =
    SPLICE_MAX_GROWTH_MM > 20
```

### CV_MOTOR_OVERLOAD

High · load_share_imbalance

```python
CV_MOTOR_OVERLOAD =
    np.maximum(MOTOR1_POWER_KW, MOTOR2_POWER_KW) > 560
```

### CV_SLIP

High · lagging_wear

```python
CV_SLIP =
    SLIP_EXCESS_PCT > 0.5
```

### CV_SLIP_MARGIN_LOW

High · takeup_jammed

```python
CV_SLIP_MARGIN_LOW =
    SLIP_MARGIN < 1.1
```

### CV_IDLER_CRITICAL

High · idler_bearing_failure

```python
CV_IDLER_CRITICAL =
    IDLER_DT_K > 50
```

### CV_MISTRACKING_SEVERE

High · mistracking

```python
CV_MISTRACKING_SEVERE =
    np.maximum(np.abs(TRACKING_HEAD_MM), np.abs(TRACKING_TAIL_MM)) > 100
```

### CV_POWER_HIGH

Medium · high_resistance

```python
CV_POWER_HIGH =
    POWER_RATIO > 1.15
```

### CV_LOAD_SHARE

Medium · load_share_imbalance

```python
CV_LOAD_SHARE =
    LOAD_IMBALANCE_PCT > 10
```

### CV_TAKEUP_TENSION_LOW

Medium · takeup_jammed

```python
CV_TAKEUP_TENSION_LOW =
    TAKEUP_FORCE_KN < 183.447
```

### CV_TAKEUP_TRAVEL_END

Medium · belt_stretch

```python
CV_TAKEUP_TRAVEL_END =
    TAKEUP_POSITION_M > 5.1
```

### CV_BELT_STRETCH

Medium · belt_stretch

```python
CV_BELT_STRETCH =
    BELT_ELONGATION_PCT > 0.12
```

### CV_IDLER_HOT

Medium · idler_bearing_failure

```python
CV_IDLER_HOT =
    (IDLER_DT_K > 20) & (IDLER_DT_K <= 50)
```

### CV_SPLICE_GROWTH

Medium · splice_failure

```python
CV_SPLICE_GROWTH =
    (SPLICE_MAX_GROWTH_MM > 10) & (SPLICE_MAX_GROWTH_MM <= 20)
```

### CV_MISTRACKING

Medium · mistracking

```python
CV_MISTRACKING =
    (np.maximum(np.abs(TRACKING_HEAD_MM), np.abs(TRACKING_TAIL_MM)) > 50)
    & (
        np.maximum(np.abs(TRACKING_HEAD_MM), np.abs(TRACKING_TAIL_MM))
        <= 100
      )
```

### CV_COVER_WORN

Medium

```python
CV_COVER_WORN =
    TOP_COVER_MIN_MM < 3
```
