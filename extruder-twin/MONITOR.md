# EX-4401: Maximo Monitor functions and alert rules

Device type `PIPE_EXTRUDER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### OUTPUT_EXPECTED_KG_H

```python
OUTPUT_EXPECTED_KG_H =
    5.5 * SCREW_SPEED_RPM
```

### SPECIFIC_RATE_RATIO

```python
SPECIFIC_RATE_RATIO =
    (OUTPUT_KG_H / (5.5 * np.maximum(SCREW_SPEED_RPM, 1)))
```

### CLEARANCE_RATIO

```python
CLEARANCE_RATIO =
    (
      (
        1
        + np.maximum(0, 1 - SPECIFIC_RATE_RATIO)
          * 300
          / (0.00238 * np.maximum(P_SCREEN_IN_BAR, 1))
      )
      ** (1 / 3)
    )
```

### DRIVE_POWER_EXPECTED_KW

```python
DRIVE_POWER_EXPECTED_KW =
    (8 + 0.2 * OUTPUT_KG_H * ((0.25 / LOT_MFR_G10MIN) ** 0.3))
```

### DRIVE_POWER_RATIO

```python
DRIVE_POWER_RATIO =
    MOTOR_POWER_KW / DRIVE_POWER_EXPECTED_KW
```

### TORQUE_PCT

```python
TORQUE_PCT =
    MOTOR_TORQUE_KNM / 15.2784 * 100
```

### SEC_KWH_KG

```python
SEC_KWH_KG =
    ((MOTOR_POWER_KW + HEATER_POWER_KW) / np.maximum(OUTPUT_KG_H, 1))
```

### SEC_EXPECTED_KWH_KG

```python
SEC_EXPECTED_KWH_KG =
    (
      (
        8
        + 0.2
          * np.maximum(OUTPUT_KG_H, 1)
          * ((0.25 / LOT_MFR_G10MIN) ** 0.3)
        + 15
      )
      / np.maximum(OUTPUT_KG_H, 1)
    )
```

### MELT_ENTHALPY_KWH_KG

```python
MELT_ENTHALPY_KWH_KG =
    ((2.2 * (MELT_TEMP_C - AMBIENT_TEMP_C) + 200) / 3600)
```

### PROCESS_EFFICIENCY

```python
PROCESS_EFFICIENCY =
    MELT_ENTHALPY_KWH_KG / SEC_KWH_KG
```

### DIE_PRESSURE_EXPECTED_BAR

```python
DIE_PRESSURE_EXPECTED_BAR =
    (
      250
      * (
          ((np.maximum(OUTPUT_KG_H, 1) / 600) ** 0.4)
          * ((0.25 / LOT_MFR_G10MIN) ** 0.7)
          * np.exp(-0.014 * (MELT_TEMP_C - 215))
        )
    )
```

### DIE_PRESSURE_RATIO

```python
DIE_PRESSURE_RATIO =
    P_DIE_BAR / DIE_PRESSURE_EXPECTED_BAR
```

### SCREEN_DP_BAR

```python
SCREEN_DP_BAR =
    (P_SCREEN_IN_BAR - P_DIE_BAR)
```

### SCREEN_DP_RATIO

```python
SCREEN_DP_RATIO =
    SCREEN_DP_BAR
    / (
        35
        * (
            ((np.maximum(OUTPUT_KG_H, 1) / 600) ** 0.4)
            * ((0.25 / LOT_MFR_G10MIN) ** 0.7)
            * np.exp(-0.014 * (MELT_TEMP_C - 215))
          )
      )
```

### MELT_TEMP_EXPECTED_C

```python
MELT_TEMP_EXPECTED_C =
    (
      213.2
      + 0.25 * (SCREW_SPEED_RPM - 109.1)
      + SCREEN_DP_BAR * 100000 / (760 * 2.6 * 1000)
    )
```

### MELT_TEMP_RESIDUAL_K

```python
MELT_TEMP_RESIDUAL_K =
    MELT_TEMP_C - MELT_TEMP_EXPECTED_C
```

### HEATER_CURRENT_RATIO_MIN

```python
HEATER_CURRENT_RATIO_MIN =
    np.minimum(
      np.minimum(
        np.minimum(
          np.minimum(
            (ZONE1_HEATER_A / 14.4337567297),
            (ZONE2_HEATER_A / 17.3205080757)
          ),
          (ZONE3_HEATER_A / 17.3205080757)
        ),
        (ZONE4_HEATER_A / 17.3205080757)
      ),
      (ZONE5_HEATER_A / 14.4337567297)
    )
```

### ZONE_TEMP_DEV_MAX_K

```python
ZONE_TEMP_DEV_MAX_K =
    np.maximum(
      np.maximum(
        np.maximum(
          np.maximum(np.abs(ZONE1_TEMP_C - 190), np.abs(ZONE2_TEMP_C - 200)),
          np.abs(ZONE3_TEMP_C - 205)
        ),
        np.abs(ZONE4_TEMP_C - 210)
      ),
      np.abs(ZONE5_TEMP_C - 210)
    )
```

### THRUST_LIFE_RATE

```python
THRUST_LIFE_RATE =
    (
      (np.maximum(SCREW_SPEED_RPM, 1) / 110)
      * (np.maximum(P_SCREEN_IN_BAR, 0) / 300) ** 3.33333333333
    )
```

### GEARBOX_OIL_RESIDUAL_K

```python
GEARBOX_OIL_RESIDUAL_K =
    (
      GEARBOX_OIL_TEMP_C
      - (AMBIENT_TEMP_C + 0.25 * MOTOR_TORQUE_KNM * SCREW_SPEED_RPM / 9.549)
    )
```

## AlertExpression rules (15)

### EXT_HEAD_PRESSURE_HIGH

Critical · screen_pack_clogging

```python
EXT_HEAD_PRESSURE_HIGH =
    P_SCREEN_IN_BAR > 380
```

### EXT_SCREW_WORN

High · screw_barrel_wear

```python
EXT_SCREW_WORN =
    (CLEARANCE_RATIO > 3.5) & (FEED_BUSH_TEMP_C <= 60)
```

### EXT_FEED_BUSH_HOT

High · feed_bush_cooling_loss

```python
EXT_FEED_BUSH_HOT =
    FEED_BUSH_TEMP_C > 60
```

### EXT_GEARBOX_VIB_HIGH

High · gearbox_bearing_damage

```python
EXT_GEARBOX_VIB_HIGH =
    GEARBOX_VIB_MM_S > 4.5
```

### EXT_TORQUE_HIGH

High

```python
EXT_TORQUE_HIGH =
    MOTOR_TORQUE_KNM / 15.2784 * 100 > 90
```

### EXT_SPECIFIC_RATE_LOW

Medium · screw_barrel_wear

```python
EXT_SPECIFIC_RATE_LOW =
    SPECIFIC_RATE_RATIO < 0.95
```

### EXT_MELT_TEMP_HIGH

Medium · screw_barrel_wear

```python
EXT_MELT_TEMP_HIGH =
    MELT_TEMP_RESIDUAL_K > 8
```

### EXT_SCREEN_CHANGE_DUE

Medium · screen_pack_clogging

```python
EXT_SCREEN_CHANGE_DUE =
    SCREEN_DP_RATIO > 2.5
```

### EXT_THRUST_LIFE_FAST

Medium · screen_pack_clogging

```python
EXT_THRUST_LIFE_FAST =
    THRUST_LIFE_RATE > 2.2
```

### EXT_DIE_PRESSURE_DEV

Medium · die_restriction

```python
EXT_DIE_PRESSURE_DEV =
    np.abs(DIE_PRESSURE_RATIO - 1) > 0.2
```

### EXT_HEATER_BAND_FAILED

Medium · heater_band_failure

```python
EXT_HEATER_BAND_FAILED =
    np.minimum(
      np.minimum(
        np.minimum(
          np.minimum(
            (ZONE1_HEATER_A / 14.4337567297),
            (ZONE2_HEATER_A / 17.3205080757)
          ),
          (ZONE3_HEATER_A / 17.3205080757)
        ),
        (ZONE4_HEATER_A / 17.3205080757)
      ),
      (ZONE5_HEATER_A / 14.4337567297)
    )
    < 0.8
```

### EXT_ZONE_TEMP_DEV

Medium

```python
EXT_ZONE_TEMP_DEV =
    np.maximum(
      np.maximum(
        np.maximum(
          np.maximum(np.abs(ZONE1_TEMP_C - 190), np.abs(ZONE2_TEMP_C - 200)),
          np.abs(ZONE3_TEMP_C - 205)
        ),
        np.abs(ZONE4_TEMP_C - 210)
      ),
      np.abs(ZONE5_TEMP_C - 210)
    )
    > 10
```

### EXT_GEARBOX_VIB_ALERT

Medium · gearbox_bearing_damage

```python
EXT_GEARBOX_VIB_ALERT =
    (GEARBOX_VIB_MM_S > 2.8) & (GEARBOX_VIB_MM_S <= 4.5)
```

### EXT_GEARBOX_OIL_HOT

Medium · gearbox_bearing_damage

```python
EXT_GEARBOX_OIL_HOT =
    GEARBOX_OIL_RESIDUAL_K > 8
```

### EXT_SEC_HIGH

Medium · barrel_cooling_stuck

```python
EXT_SEC_HIGH =
    (SEC_KWH_KG / SEC_EXPECTED_KWH_KG) > 1.15
```
