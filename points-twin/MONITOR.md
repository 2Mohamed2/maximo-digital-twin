# PM-5501: Maximo Monitor functions and alert rules

Device type `POINT_MACHINE_CM`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (16)

### THROW_SPEED_MM_S

```python
THROW_SPEED_MM_S =
    220 / THROW_TIME_S
```

### THROW_TIME_RATIO

```python
THROW_TIME_RATIO =
    THROW_TIME_S / 6
```

### DRIVE_FORCE_N

```python
DRIVE_FORCE_N =
    (9.54545454545 * (DRIVE_POWER_MEAN_W - 280))
```

### DRIVE_FORCE_PEAK_N

```python
DRIVE_FORCE_PEAK_N =
    (9.54545454545 * (DRIVE_POWER_PEAK_W - 280))
```

### LOCK_FORCE_N

```python
LOCK_FORCE_N =
    (9.54545454545 * (LOCK_POWER_MEAN_W - 280))
```

### FORCE_EXPECTED_N

```python
FORCE_EXPECTED_N =
    (
      2000
      + 20 * np.maximum(0, 10 - RAIL_TEMP_C)
      + 25 * np.maximum(0, RAIL_TEMP_C - 40)
    )
```

### FORCE_RATIO

```python
FORCE_RATIO =
    DRIVE_FORCE_N / FORCE_EXPECTED_N
```

### LOCK_FORCE_RATIO

```python
LOCK_FORCE_RATIO =
    LOCK_FORCE_N / FORCE_EXPECTED_N
```

### CLUTCH_MARGIN_N

```python
CLUTCH_MARGIN_N =
    5500 - np.maximum(DRIVE_FORCE_PEAK_N, LOCK_FORCE_N)
```

### ENERGY_EXPECTED_KJ

```python
ENERGY_EXPECTED_KJ =
    ((1830 + 0.628571428571 * FORCE_EXPECTED_N) / 1000)
```

### ENERGY_RATIO

```python
ENERGY_RATIO =
    ENERGY_KJ / ENERGY_EXPECTED_KJ
```

### UNLOCK_PEAK_RATIO

```python
UNLOCK_PEAK_RATIO =
    UNLOCK_PEAK_W / 1500
```

### VOLTAGE_RATIO

```python
VOLTAGE_RATIO =
    MOTOR_VOLTAGE_V / 400
```

### POWER_FACTOR

```python
POWER_FACTOR =
    DRIVE_POWER_MEAN_W / (1.73205080757 * MOTOR_VOLTAGE_V * DRIVE_CURRENT_A)
```

### HEATER_DEFICIT_A

```python
HEATER_DEFICIT_A =
    HEATER_ON * 13 - HEATER_CURRENT_A
```

### OVERHAUL_USED_PCT

```python
OVERHAUL_USED_PCT =
    THROWS_SINCE_OVERHAUL / 1000000 * 100
```

## AlertExpression rules (13)

### PTS_DETECTION_LOST

Critical · obstruction

```python
PTS_DETECTION_LOST =
    DETECTION_OK < 0.5
```

### PTS_TRAILED

Critical · trailed

```python
PTS_TRAILED =
    TRAILED > 0.5
```

### PTS_CLUTCH_LIMIT

High · obstruction

```python
PTS_CLUTCH_LIMIT =
    np.maximum(DRIVE_FORCE_PEAK_N, LOCK_FORCE_N) > 4950
```

### PTS_FORCE_HIGH

High · lubrication_loss

```python
PTS_FORCE_HIGH =
    FORCE_RATIO > 1.6
```

### PTS_HEATER_FAIL

High · ice_heater

```python
PTS_HEATER_FAIL =
    (HEATER_ON > 0.5) & (HEATER_CURRENT_A < 6.5)
```

### PTS_FORCE_RISING

Medium · lubrication_loss

```python
PTS_FORCE_RISING =
    (FORCE_RATIO > 1.25) & (FORCE_RATIO <= 1.6)
```

### PTS_ENERGY_HIGH

Medium · lubrication_loss

```python
PTS_ENERGY_HIGH =
    ENERGY_KJ / ENERGY_EXPECTED_KJ > 1.2
```

### PTS_LOCK_FORCE_HIGH

Medium · ice_heater

```python
PTS_LOCK_FORCE_HIGH =
    (LOCK_FORCE_RATIO > 1.6) & (LOCK_FORCE_N <= 4950)
```

### PTS_THROW_SLOW

Medium · obstruction

```python
PTS_THROW_SLOW =
    THROW_TIME_S / 6 > 1.25
```

### PTS_UNLOCK_PEAK_HIGH

Medium · unlock_tight

```python
PTS_UNLOCK_PEAK_HIGH =
    UNLOCK_PEAK_W > 2500
```

### PTS_SUPPLY_LOW

Medium · supply_low

```python
PTS_SUPPLY_LOW =
    MOTOR_VOLTAGE_V / 400 < 0.9
```

### PTS_DETECTION_FLICKER

Medium · detector_adjust

```python
PTS_DETECTION_FLICKER =
    DETECTION_LOSSES_24H >= 2
```

### PTS_OVERHAUL_DUE

Low

```python
PTS_OVERHAUL_DUE =
    THROWS_SINCE_OVERHAUL > 900000
```
