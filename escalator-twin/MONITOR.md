# ES-5601: Maximo Monitor functions and alert rules

Device type `ESCALATOR_HEAVY_DUTY`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### LOAD_POWER_KW

```python
LOAD_POWER_KW =
    np.where(
      DIRECTION > 0,
      (PASSENGERS_PER_MIN / 60 * 7.3575) / 0.85,
      -(PASSENGERS_PER_MIN / 60 * 7.3575) * 0.85
    )
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    6.44 * STEP_SPEED_MS / 0.5
    + np.where(
        DIRECTION > 0,
        (PASSENGERS_PER_MIN / 60 * 7.3575) / 0.85,
        -(PASSENGERS_PER_MIN / 60 * 7.3575) * 0.85
      )
```

### POWER_RESIDUAL_KW

```python
POWER_RESIDUAL_KW =
    MOTOR_POWER_KW - POWER_EXPECTED_KW
```

### NOLOAD_POWER_EST_KW

```python
NOLOAD_POWER_EST_KW =
    (
      (
        MOTOR_POWER_KW
        - np.where(
            DIRECTION > 0,
            (PASSENGERS_PER_MIN / 60 * 7.3575) / 0.85,
            -(PASSENGERS_PER_MIN / 60 * 7.3575) * 0.85
          )
      )
      * 0.5
      / np.maximum(STEP_SPEED_MS, 0.05)
    )
```

### DRAG_RATIO

```python
DRAG_RATIO =
    (NOLOAD_POWER_EST_KW / 6.44)
```

### ENERGY_PER_PAX_WH

```python
ENERGY_PER_PAX_WH =
    MOTOR_POWER_KW * 1000 / 60 / np.maximum(PASSENGERS_PER_MIN, 1)
```

### HANDRAIL_L_DEV_PCT

```python
HANDRAIL_L_DEV_PCT =
    ((HANDRAIL_LEFT_MS / np.maximum(STEP_SPEED_MS, 0.05) - 1) * 100)
```

### HANDRAIL_R_DEV_PCT

```python
HANDRAIL_R_DEV_PCT =
    ((HANDRAIL_RIGHT_MS / np.maximum(STEP_SPEED_MS, 0.05) - 1) * 100)
```

### CHAIN_ELONG_EXPECTED_PCT

```python
CHAIN_ELONG_EXPECTED_PCT =
    (0.1 + 0.007 * RUN_HOURS / 1000)
```

### CHAIN_WEAR_RESIDUAL_PCT

```python
CHAIN_WEAR_RESIDUAL_PCT =
    CHAIN_ELONGATION_PCT - (0.1 + 0.007 * RUN_HOURS / 1000)
```

### CHAIN_HOURS_TO_LIMIT

```python
CHAIN_HOURS_TO_LIMIT =
    (1.5 - CHAIN_ELONGATION_PCT) / 0.007 * 1000
```

### BRAKE_FORCE_KN

```python
BRAKE_FORCE_KN =
    (
      (
        (
          (16000 + LAST_STOP_LOAD_KG) * LAST_STOP_DECEL_MS2
          - 5152
          - LAST_STOP_DIR * LAST_STOP_LOAD_KG * 4.905
        )
      )
      / 1000
    )
```

### STOP_DIST_FULL_DOWN_M

```python
STOP_DIST_FULL_DOWN_M =
    np.where(
      ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242) > 0.02,
      0.5 * LAST_STOP_DELAY_S
      + 0.125
        / np.maximum(
            ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242),
            0.02
          ),
      9.99
    )
```

### STOP_DIST_EMPTY_M

```python
STOP_DIST_EMPTY_M =
    (
      0.5 * LAST_STOP_DELAY_S
      + 0.125 / np.maximum(((BRAKE_FORCE_KN * 1000 + 5152) / 16000), 0.02)
    )
```

### STOP_DIST_MODEL_ERR_M

```python
STOP_DIST_MODEL_ERR_M =
    LAST_STOP_DISTANCE_M
    - (
        LAST_STOP_SPEED_MS * LAST_STOP_DELAY_S
        + LAST_STOP_SPEED_MS ** 2
          / 2
          / np.maximum(LAST_STOP_DECEL_MS2, 0.02)
      )
```

### OIL_TEMP_EXPECTED_C

```python
OIL_TEMP_EXPECTED_C =
    (AMBIENT_TEMP_C + 18 + 1.2 * np.maximum(MOTOR_POWER_AVG_KW, 0))
```

### OIL_TEMP_RESIDUAL_C

```python
OIL_TEMP_RESIDUAL_C =
    GEAR_OIL_TEMP_C - OIL_TEMP_EXPECTED_C
```

### VIB_RATIO

```python
VIB_RATIO =
    GEARBOX_VIB_MMS / 1.2
```

### SAFETY_TRIPS_24H

```python
SAFETY_TRIPS_24H =
    TRIPS_COMB_24H
    + TRIPS_HANDRAIL_INLET_24H
    + TRIPS_STEP_SAG_24H
    + TRIPS_ESTOP_24H
```

### STANDBY_LOST_KWH_DAY

```python
STANDBY_LOST_KWH_DAY =
    np.maximum(0.25 - STANDBY_SHARE_24H, 0) * 77.28
```

## AlertExpression rules (14)

### ESC_STOP_TOO_LONG

Critical · brake_weak

```python
ESC_STOP_TOO_LONG =
    np.where(
      ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242) > 0.02,
      0.5 * LAST_STOP_DELAY_S
      + 0.125
        / np.maximum(
            ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242),
            0.02
          ),
      9.99
    )
    > 1
```

### ESC_STOP_HARSH

High · brake_harsh

```python
ESC_STOP_HARSH =
    STOP_DIST_EMPTY_M < 0.2
```

### ESC_HANDRAIL_SLIP

High · handrail_slip

```python
ESC_HANDRAIL_SLIP =
    np.minimum(HANDRAIL_L_DEV_PCT, HANDRAIL_R_DEV_PCT) < -10
```

### ESC_CHAIN_ELONG_LIMIT

High · chain_wear

```python
ESC_CHAIN_ELONG_LIMIT =
    CHAIN_ELONGATION_PCT > 1.5
```

### ESC_STOP_MARGIN_LOW

Medium · brake_weak

```python
ESC_STOP_MARGIN_LOW =
    (
      np.where(
        ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242) > 0.02,
        0.5 * LAST_STOP_DELAY_S
        + 0.125
          / np.maximum(
              ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242),
              0.02
            ),
        9.99
      )
      > 0.85
    )
    & (
        np.where(
          ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242) > 0.02,
          0.5 * LAST_STOP_DELAY_S
          + 0.125
            / np.maximum(
                ((BRAKE_FORCE_KN * 1000 - 20335.12763) / 21196.15242),
                0.02
              ),
          9.99
        )
        <= 1
      )
```

### ESC_HANDRAIL_OUT_OF_TOL

Medium · handrail_slip

```python
ESC_HANDRAIL_OUT_OF_TOL =
    (
      (np.minimum(HANDRAIL_L_DEV_PCT, HANDRAIL_R_DEV_PCT) < 0)
      | (np.maximum(HANDRAIL_L_DEV_PCT, HANDRAIL_R_DEV_PCT) > 2)
    )
    & (np.minimum(HANDRAIL_L_DEV_PCT, HANDRAIL_R_DEV_PCT) >= -10)
```

### ESC_CHAIN_ELONG_ALERT

Medium · chain_wear

```python
ESC_CHAIN_ELONG_ALERT =
    (CHAIN_ELONGATION_PCT > 1) & (CHAIN_ELONGATION_PCT <= 1.5)
```

### ESC_CHAIN_WEAR_FAST

Medium · chain_wear

```python
ESC_CHAIN_WEAR_FAST =
    CHAIN_WEAR_RESIDUAL_PCT > 0.3
```

### ESC_DRAG_HIGH

Medium · step_band_drag

```python
ESC_DRAG_HIGH =
    DRAG_RATIO > 1.3
```

### ESC_STEP_SAG_TRIPS

Medium · step_band_drag

```python
ESC_STEP_SAG_TRIPS =
    TRIPS_STEP_SAG_24H >= 2
```

### ESC_GEAR_OIL_HOT

Medium · gearbox_wear

```python
ESC_GEAR_OIL_HOT =
    OIL_TEMP_RESIDUAL_C > 10
```

### ESC_GEAR_VIB_HIGH

Medium · gearbox_wear

```python
ESC_GEAR_VIB_HIGH =
    GEARBOX_VIB_MMS / 1.2 > 2.5
```

### ESC_COMB_TRIPS

Medium · comb_damage

```python
ESC_COMB_TRIPS =
    TRIPS_COMB_24H >= 3
```

### ESC_STANDBY_UNUSED

Low · standby_disabled

```python
ESC_STANDBY_UNUSED =
    STANDBY_SHARE_24H < 0.1
```
