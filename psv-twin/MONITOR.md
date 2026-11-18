# PSV-2601: Maximo Monitor functions and alert rules

Device type `PSV_SPRING_API526`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (17)

### OP_RATIO_PCT

```python
OP_RATIO_PCT =
    (VESSEL_PRESSURE_BARG / 15 * 100)
```

### RELIEF_LOAD_KGH

```python
RELIEF_LOAD_KGH =
    (1 * VAPOUR_FEED_KGH)
```

### REQUIRED_AREA_MM2

```python
REQUIRED_AREA_MM2 =
    (
      (1 * VAPOUR_FEED_KGH)
      * np.sqrt((VESSEL_TEMP_C + 273.15) * 0.85 / 44.1)
      / 42.7790687752
    )
```

### RATED_CAPACITY_KGH

```python
RATED_CAPACITY_KGH =
    35506.6270834 / np.sqrt((VESSEL_TEMP_C + 273.15) * 0.85 / 44.1)
```

### CAPACITY_UTIL_PCT

```python
CAPACITY_UTIL_PCT =
    (REQUIRED_AREA_MM2 / 830 * 100)
```

### ACOUSTIC_EXCESS

```python
ACOUSTIC_EXCESS =
    (ACOUSTIC_LEVEL - 22)
```

### OUTLET_DT_K

```python
OUTLET_DT_K =
    (OUTLET_TEMP_C - AMBIENT_TEMP_C)
```

### INLET_LOSS_PCT

```python
INLET_LOSS_PCT =
    ((LIFT_VESSEL_BARG - LIFT_INLET_BARG) / 15 * 100)
```

### BUILTUP_BP_PCT

```python
BUILTUP_BP_PCT =
    (LIFT_OUTLET_BARG / 15 * 100)
```

### SUPERIMPOSED_BP_PCT

```python
SUPERIMPOSED_BP_PCT =
    HEADER_PRESSURE_BARG / 15 * 100
```

### OPEN_PCT_OF_SET

```python
OPEN_PCT_OF_SET =
    (LIFT_OPEN_BARG / 15 * 100)
```

### ACCUMULATION_PCT

```python
ACCUMULATION_PCT =
    ((LIFT_PEAK_BARG - 15) / 15 * 100)
```

### POP_DEV_PCT

```python
POP_DEV_PCT =
    ((TEST_ASFOUND_BARG - 15) / 15 * 100)
```

### DRIFT_RATE_PCT_Y

```python
DRIFT_RATE_PCT_Y =
    (
      (TEST_ASFOUND_BARG - TEST_PREV_ASLEFT_BARG)
      / 15
      * 100
      / (TEST_INTERVAL_H / 8760)
    )
```

### SEAT_LEAK_RATIO

```python
SEAT_LEAK_RATIO =
    TEST_SEAT_BPM / 20
```

### RBI_INTERVAL_Y

```python
RBI_INTERVAL_Y =
    np.minimum(5, 3 / np.maximum(np.abs(DRIFT_RATE_PCT_Y), 0.05))
```

### TEST_DUE_RATIO

```python
TEST_DUE_RATIO =
    TEST_HOURS_SINCE / 35040
```

## AlertExpression rules (14)

### PSV_CAPACITY_SHORT

Critical · relief_load_increase

```python
PSV_CAPACITY_SHORT =
    CAPACITY_UTIL_PCT > 100
```

### PSV_ACCUMULATION

Critical · valve_sticking

```python
PSV_ACCUMULATION =
    ACCUMULATION_PCT > 10
```

### PSV_LATE_OPENING

High · valve_sticking

```python
PSV_LATE_OPENING =
    (LIFT_OPEN_BARG / 15 * 100) > 103
```

### PSV_INLET_LOSS

High · inlet_restriction

```python
PSV_INLET_LOSS =
    INLET_LOSS_PCT > 3
```

### PSV_BACKPRESSURE_HIGH

High · high_backpressure

```python
PSV_BACKPRESSURE_HIGH =
    (LIFT_OUTLET_BARG / 15 * 100) > 10
```

### PSV_PASSING

High · seat_passing

```python
PSV_PASSING =
    ((ACOUSTIC_LEVEL - 22) > 15)
    & (np.abs(OUTLET_DT_K) > 5)
    & (LIFT_ACTIVE < 0.5)
    & (OP_RATIO_PCT < 90)
```

### PSV_NEAR_SET

High · operating_near_set

```python
PSV_NEAR_SET =
    (OP_RATIO_PCT >= 95) & (LIFT_ACTIVE < 0.5)
```

### PSV_TEST_OVERDUE

High · test_overdue

```python
PSV_TEST_OVERDUE =
    TEST_HOURS_SINCE > 35040
```

### PSV_SIMMER_ZONE

Medium · operating_near_set

```python
PSV_SIMMER_ZONE =
    (OP_RATIO_PCT >= 90) & (OP_RATIO_PCT < 95) & (LIFT_ACTIVE < 0.5)
```

### PSV_CAPACITY_MARGIN

Medium · relief_load_increase

```python
PSV_CAPACITY_MARGIN =
    (CAPACITY_UTIL_PCT > 90) & (CAPACITY_UTIL_PCT <= 100)
```

### PSV_CHATTER

Medium · inlet_restriction

```python
PSV_CHATTER =
    (LIFT_COUNT_30D >= 6) & (LIFT_DURATION_S < 10)
```

### PSV_POP_DRIFT

Medium · set_pressure_drift

```python
PSV_POP_DRIFT =
    np.abs(POP_DEV_PCT) > 3
```

### PSV_SEAT_TIGHTNESS

Medium · set_pressure_drift

```python
PSV_SEAT_TIGHTNESS =
    TEST_SEAT_BPM > 20
```

### PSV_RBI_INTERVAL_SHORT

Medium · set_pressure_drift

```python
PSV_RBI_INTERVAL_SHORT =
    np.minimum(5, 3 / np.maximum(np.abs(DRIFT_RATE_PCT_Y), 0.05)) < 4
```
