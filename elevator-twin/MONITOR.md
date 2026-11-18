# EL-5701: Maximo Monitor functions and alert rules

Device type `ELEVATOR_TRACTION_MRL`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### UP_FORCE_KN

```python
UP_FORCE_KN =
    (UP_TORQUE_NM * 0.01)
```

### DOWN_FORCE_KN

```python
DOWN_FORCE_KN =
    (DOWN_TORQUE_NM * 0.01)
```

### FRICTION_APPARENT_KN

```python
FRICTION_APPARENT_KN =
    (
      (
        (UP_TORQUE_NM * 0.01)
        - (DOWN_TORQUE_NM * 0.01)
        - (UP_LOAD_KG - DOWN_LOAD_KG) * 0.00981
      )
      / 2
    )
```

### BALANCE_APPARENT_PCT

```python
BALANCE_APPARENT_PCT =
    (
      (
        UP_LOAD_KG
        + DOWN_LOAD_KG
        - ((UP_TORQUE_NM * 0.01) + (DOWN_TORQUE_NM * 0.01)) * 101.936799185
      )
      / 20
    )
```

### BALANCE_DEV_PCT

```python
BALANCE_DEV_PCT =
    BALANCE_APPARENT_PCT - 45
```

### UP_TORQUE_EXPECTED_NM

```python
UP_TORQUE_EXPECTED_NM =
    (((UP_LOAD_KG - 450) * 9.81 + 600) * 0.1)
```

### DOWN_TORQUE_EXPECTED_NM

```python
DOWN_TORQUE_EXPECTED_NM =
    (((DOWN_LOAD_KG - 450) * 9.81 - 600) * 0.1)
```

### UP_TORQUE_RESIDUAL_NM

```python
UP_TORQUE_RESIDUAL_NM =
    UP_TORQUE_NM - UP_TORQUE_EXPECTED_NM
```

### DOWN_TORQUE_RESIDUAL_NM

```python
DOWN_TORQUE_RESIDUAL_NM =
    DOWN_TORQUE_NM - DOWN_TORQUE_EXPECTED_NM
```

### DOOR_CLOSE_RATIO

```python
DOOR_CLOSE_RATIO =
    DOOR_CLOSE_TIME_S / 2.8
```

### DOOR_CURRENT_RATIO

```python
DOOR_CURRENT_RATIO =
    DOOR_CLOSE_CURRENT_A / 1.5
```

### REOPEN_RATE_PCT

```python
REOPEN_RATE_PCT =
    DOOR_REOPENS_1H / np.maximum(STARTS_1H, 20) * 100
```

### RELEVEL_RATE_PCT

```python
RELEVEL_RATE_PCT =
    RELEVELS_1H / np.maximum(STARTS_1H, 20) * 100
```

### BRAKE_TEST_RATIO

```python
BRAKE_TEST_RATIO =
    (BRAKE_TEST_TORQUE_NM / 784.8)
```

### ENERGY_PER_TRIP_WH

```python
ENERGY_PER_TRIP_WH =
    ((ENERGY_KWH_24H - 2.88) * 1000 / np.maximum(TRIPS_24H, 1))
```

### ENERGY_EXPECTED_WH

```python
ENERGY_EXPECTED_WH =
    (8 + 0.9 * DISTANCE_M_24H / np.maximum(TRIPS_24H, 1))
```

### ENERGY_RATIO

```python
ENERGY_RATIO =
    ENERGY_PER_TRIP_WH / ENERGY_EXPECTED_WH
```

### ROPE_LIFE_USED_PCT

```python
ROPE_LIFE_USED_PCT =
    TRIPS_SINCE_ROPE_CHANGE / 15000
```

### STARTS_RATIO

```python
STARTS_RATIO =
    STARTS_1H / 180
```

## AlertExpression rules (15)

### EL_BRAKE_TEST_FAIL

Critical · brake_wear

```python
EL_BRAKE_TEST_FAIL =
    BRAKE_TEST_RATIO < 1
```

### EL_DOOR_LOCK_FAIL

High · door_lock_fault

```python
EL_DOOR_LOCK_FAIL =
    DOOR_LOCK_FAILS_24H > 4
```

### EL_LEVELLING

High · levelling_drift

```python
EL_LEVELLING =
    LEVEL_ERROR_MAX_MM > 10
```

### EL_BRAKE_MARGIN_LOW

Medium · brake_wear

```python
EL_BRAKE_MARGIN_LOW =
    (BRAKE_TEST_RATIO < 1.3) & (BRAKE_TEST_RATIO >= 1)
```

### EL_BRAKE_TEST_OVERDUE

Medium

```python
EL_BRAKE_TEST_OVERDUE =
    BRAKE_TEST_HOURS_SINCE > 30
```

### EL_DOOR_SLOW

Medium · door_obstruction

```python
EL_DOOR_SLOW =
    (DOOR_CLOSE_TIME_S / 2.8) > 1.25
```

### EL_DOOR_CURRENT_HIGH

Medium · door_obstruction

```python
EL_DOOR_CURRENT_HIGH =
    (DOOR_CLOSE_CURRENT_A / 1.5) > 1.4
```

### EL_DOOR_REOPENS

Medium · light_curtain_fault

```python
EL_DOOR_REOPENS =
    REOPEN_RATE_PCT > 15
```

### EL_BALANCE_OFF

Medium · counterweight_imbalance

```python
EL_BALANCE_OFF =
    np.absBALANCE_DEV_PCT > 5
```

### EL_FRICTION_HIGH

Medium · guide_friction_high

```python
EL_FRICTION_HIGH =
    FRICTION_APPARENT_KN > 1
```

### EL_RIDE_LATERAL

Medium · guide_friction_high

```python
EL_RIDE_LATERAL =
    VIB_LATERAL_MG > 20
```

### EL_RELEVEL_HIGH

Medium · levelling_drift

```python
EL_RELEVEL_HIGH =
    RELEVEL_RATE_PCT > 10
```

### EL_ENERGY_HIGH

Medium · regen_lost

```python
EL_ENERGY_HIGH =
    ENERGY_RATIO > 1.3
```

### EL_ROPE_LIFE

Medium

```python
EL_ROPE_LIFE =
    (TRIPS_SINCE_ROPE_CHANGE / 15000) > 85
```

### EL_STARTS_HIGH

Low

```python
EL_STARTS_HIGH =
    STARTS_1H > 180
```
