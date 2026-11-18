# WTG-3001: Maximo Monitor functions and alert rules

Device type `WIND_TURBINE_DFIG`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### AIR_DENSITY

```python
AIR_DENSITY =
    (AMBIENT_PRESSURE_HPA * 100 / (287.05 * (AMBIENT_TEMP_C + 273.15)))
```

### WIND_NORM_MS

```python
WIND_NORM_MS =
    (WIND_SPEED_MS * (AIR_DENSITY / 1.225) ** (1 / 3))
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    np.interp(
      WIND_NORM_MS,
      [3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5, 15, 15.5, 16, 16.5, 25],
      [0, 42.2, 93.3, 145.2, 211.3, 284.2, 390.9, 491.5, 601.1, 731.8, 884.5, 1087.6, 1247.1, 1429.6, 1594.3, 1742.9, 1861.2, 1948.1, 1993.3, 2003.5, 2007, 2007.7, 2007.3, 2007.4, 2007, 2006.8, 2006.7, 2006.5, 2006.5],
      left=0,
      right=0
    )
```

### POWER_RESIDUAL_KW

```python
POWER_RESIDUAL_KW =
    ACTIVE_POWER_KW
    - np.interp(
        WIND_NORM_MS,
        [3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5, 15, 15.5, 16, 16.5, 25],
        [0, 42.2, 93.3, 145.2, 211.3, 284.2, 390.9, 491.5, 601.1, 731.8, 884.5, 1087.6, 1247.1, 1429.6, 1594.3, 1742.9, 1861.2, 1948.1, 1993.3, 2003.5, 2007, 2007.7, 2007.3, 2007.4, 2007, 2006.8, 2006.7, 2006.5, 2006.5],
        left=0,
        right=0
      )
```

### POWER_RATIO

```python
POWER_RATIO =
    (
      ACTIVE_POWER_KW
      / np.maximum(
          np.interp(
            WIND_NORM_MS,
            [3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5, 15, 15.5, 16, 16.5, 25],
            [0, 42.2, 93.3, 145.2, 211.3, 284.2, 390.9, 491.5, 601.1, 731.8, 884.5, 1087.6, 1247.1, 1429.6, 1594.3, 1742.9, 1861.2, 1948.1, 1993.3, 2003.5, 2007, 2007.7, 2007.3, 2007.4, 2007, 2006.8, 2006.7, 2006.5, 2006.5],
            left=0,
            right=0
          ),
          50
        )
    )
```

### GBX_OIL_EXPECTED_C

```python
GBX_OIL_EXPECTED_C =
    (AMBIENT_TEMP_C + 32 + 18 * (ACTIVE_POWER_KW / 2000))
```

### GBX_OIL_RESIDUAL_C

```python
GBX_OIL_RESIDUAL_C =
    GBX_OIL_TEMP_C - GBX_OIL_EXPECTED_C
```

### HSS_BRG_EXPECTED_C

```python
HSS_BRG_EXPECTED_C =
    (GBX_OIL_TEMP_C + 4 + 10 * (ACTIVE_POWER_KW / 2000))
```

### HSS_BRG_RESIDUAL_C

```python
HSS_BRG_RESIDUAL_C =
    GBX_HSS_BRG_TEMP_C - HSS_BRG_EXPECTED_C
```

### MAIN_BRG_EXPECTED_C

```python
MAIN_BRG_EXPECTED_C =
    (AMBIENT_TEMP_C + 8 + 14 * (ACTIVE_POWER_KW / 2000))
```

### MAIN_BRG_RESIDUAL_C

```python
MAIN_BRG_RESIDUAL_C =
    MAIN_BRG_TEMP_C - MAIN_BRG_EXPECTED_C
```

### ISO4406_4UM

```python
ISO4406_4UM =
    np.ceil(np.log2(np.maximum(PC_4UM_PER_ML * 102.4, 1)))
```

### ISO4406_6UM

```python
ISO4406_6UM =
    np.ceil(np.log2(np.maximum(PC_6UM_PER_ML * 102.4, 1)))
```

### ISO4406_14UM

```python
ISO4406_14UM =
    np.ceil(np.log2(np.maximum(PC_14UM_PER_ML * 102.4, 1)))
```

### PLANET_MESH_HZ

```python
PLANET_MESH_HZ =
    99 * ROTOR_RPM / 60
```

### HSS_BPFO_HZ

```python
HSS_BPFO_HZ =
    5.50667 * GEN_RPM / 60
```

### VIB_PLANET_RATIO

```python
VIB_PLANET_RATIO =
    (VIB_PLANET_MESH / (0.6 + 1.2 * (ACTIVE_POWER_KW / 2000)))
```

### VIB_HSS_BRG_RATIO

```python
VIB_HSS_BRG_RATIO =
    (VIB_HSS_BRG_ENV / (0.8 + 0.6 * (ACTIVE_POWER_KW / 2000)))
```

### VIB_MB_RATIO

```python
VIB_MB_RATIO =
    (VIB_MB_ENV / (0.15 + 0.15 * (ACTIVE_POWER_KW / 2000)))
```

### YAW_LOSS_PCT

```python
YAW_LOSS_PCT =
    (1 - np.cos(np.radians(YAW_ERROR_DEG)) ** 3) * 100
```

## AlertExpression rules (12)

### GBX_OIL_TEMP_HIGH

High · oil_cooler_fouling

```python
GBX_OIL_TEMP_HIGH =
    (TURBINE_STATE > 0.5) & (GBX_OIL_TEMP_C > 80)
```

### GBX_HSS_BRG_VIB

High · hss_bearing_damage

```python
GBX_HSS_BRG_VIB =
    (TURBINE_STATE > 0.5) & (VIB_HSS_BRG_RATIO > 2.5)
```

### GBX_FERROUS_PARTICLES

High · hss_bearing_damage

```python
GBX_FERROUS_PARTICLES =
    FE_PARTICLES_24H > 15
```

### GBX_VIB_OVERALL

High · planet_gear_pitting

```python
GBX_VIB_OVERALL =
    (TURBINE_STATE > 0.5) & (VIB_GBX_RMS_MMS > 4.5)
```

### MB_VIB_ENV

High · main_bearing_wear

```python
MB_VIB_ENV =
    (TURBINE_STATE > 0.5) & (VIB_MB_RATIO > 2.5)
```

### GBX_HSS_BRG_TEMP

Medium · hss_bearing_damage

```python
GBX_HSS_BRG_TEMP =
    (TURBINE_STATE > 0.5) & (HSS_BRG_RESIDUAL_C > 5)
```

### GBX_OIL_TEMP_RESIDUAL

Medium · oil_cooler_fouling

```python
GBX_OIL_TEMP_RESIDUAL =
    (TURBINE_STATE > 0.5) & (GBX_OIL_RESIDUAL_C > 6)
```

### GBX_PLANET_MESH_VIB

Medium · planet_gear_pitting

```python
GBX_PLANET_MESH_VIB =
    (TURBINE_STATE > 0.5) & (VIB_PLANET_RATIO > 2)
```

### OIL_CLEANLINESS

Medium · oil_contamination

```python
OIL_CLEANLINESS =
    (np.ceil(np.log2(np.maximum(PC_6UM_PER_ML * 102.4, 1))) > 15)
    | (np.ceil(np.log2(np.maximum(PC_14UM_PER_ML * 102.4, 1))) > 12)
```

### MB_TEMP_RESIDUAL

Medium · main_bearing_wear

```python
MB_TEMP_RESIDUAL =
    (TURBINE_STATE > 0.5) & (MAIN_BRG_RESIDUAL_C > 6)
```

### WTG_YAW_MISALIGNMENT

Medium · yaw_misalignment

```python
WTG_YAW_MISALIGNMENT =
    (TURBINE_STATE > 0.5) & (np.abs(YAW_ERROR_DEG) > 8)
```

### WTG_UNDERPERFORMANCE

Medium · rotor_performance_loss

```python
WTG_UNDERPERFORMANCE =
    (TURBINE_STATE > 0.5)
    & (WIND_NORM_MS >= 5)
    & (WIND_NORM_MS <= 11)
    & (POWER_RATIO < 0.88)
```
