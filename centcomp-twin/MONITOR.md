# K-2301: Maximo Monitor functions and alert rules

Device type `CENTRIFUGAL_COMPRESSOR`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### RHO1_KG_M3

```python
RHO1_KG_M3 =
    (
      SUCTION_PRESSURE_BARA
      * 100000
      / (370.3714 * (SUCTION_TEMP_C + 273.15))
    )
```

### Q_ACT_M3H

```python
Q_ACT_M3H =
    (3600 * 0.0458 * np.sqrt(FLOW_DP_MBAR * 100 / RHO1_KG_M3))
```

### MASS_FLOW_KG_S

```python
MASS_FLOW_KG_S =
    (Q_ACT_M3H / 3600 * RHO1_KG_M3)
```

### PRESSURE_RATIO

```python
PRESSURE_RATIO =
    (DISCHARGE_PRESSURE_BARA / SUCTION_PRESSURE_BARA)
```

### POLY_EXPONENT_M

```python
POLY_EXPONENT_M =
    (
      np.log((DISCHARGE_TEMP_C + 273.15) / (SUCTION_TEMP_C + 273.15))
      / np.log(PRESSURE_RATIO)
    )
```

### ETA_POLY

```python
ETA_POLY =
    (0.1666666667 / POLY_EXPONENT_M)
```

### HEAD_POLY_KJKG

```python
HEAD_POLY_KJKG =
    (
      370.3714
      * ((DISCHARGE_TEMP_C + 273.15) - (SUCTION_TEMP_C + 273.15))
      / POLY_EXPONENT_M
      / 1000
    )
```

### SPEED_RATIO

```python
SPEED_RATIO =
    (SPEED_RPM / 10500)
```

### FLOW_REDUCED

```python
FLOW_REDUCED =
    (Q_ACT_M3H / (15000 * (SPEED_RPM / 10500)))
```

### HEAD_EXPECTED_KJKG

```python
HEAD_EXPECTED_KJKG =
    (
      (SPEED_RPM / 10500) ** 2
      * 160
      * (0.76 + 1.04 * FLOW_REDUCED - 0.8 * FLOW_REDUCED ** 2)
    )
```

### HEAD_RATIO

```python
HEAD_RATIO =
    HEAD_POLY_KJKG / HEAD_EXPECTED_KJKG
```

### ETA_EXPECTED

```python
ETA_EXPECTED =
    (0.8 * (1 - 0.9 * (FLOW_REDUCED - 1) ** 2))
```

### ETA_DEV_PTS

```python
ETA_DEV_PTS =
    (ETA_POLY - ETA_EXPECTED) * 100
```

### Q_SURGE_M3H

```python
Q_SURGE_M3H =
    (10500 * np.sqrt(HEAD_POLY_KJKG / 175.36))
```

### SURGE_MARGIN_PCT

```python
SURGE_MARGIN_PCT =
    ((Q_ACT_M3H - Q_SURGE_M3H) / Q_ACT_M3H * 100)
```

### GAS_POWER_KW

```python
GAS_POWER_KW =
    (
      MASS_FLOW_KG_S
      * 2222.2284
      * ((DISCHARGE_TEMP_C + 273.15) - (SUCTION_TEMP_C + 273.15))
      / 1000
    )
```

### POWER_RATIO

```python
POWER_RATIO =
    (DRIVER_POWER_KW * 0.97 / GAS_POWER_KW)
```

### VENT_FLOW_MAX_NM3H

```python
VENT_FLOW_MAX_NM3H =
    np.maximum(VENT_FLOW_DE_NM3H, VENT_FLOW_NE_NM3H)
```

### VIB_MAX_UM

```python
VIB_MAX_UM =
    np.maximum(VIB_DE_UM, VIB_NE_UM)
```

### VIB_LIMIT_API617_UM

```python
VIB_LIMIT_API617_UM =
    np.minimum(25.4, 25.4 * np.sqrt(12000 / SPEED_RPM))
```

## AlertExpression rules (13)

### CC_SURGE_MARGIN_LOW

High · asv_stuck

```python
CC_SURGE_MARGIN_LOW =
    SURGE_MARGIN_PCT < 5
```

### CC_ASV_DEVIATION

High · asv_stuck

```python
CC_ASV_DEVIATION =
    np.abs(ASC_OUTPUT_PCT - RECYCLE_VALVE_PCT) > 10
```

### CC_SEAL_GAS_DP_LOW

High · seal_gas_supply

```python
CC_SEAL_GAS_DP_LOW =
    SEAL_GAS_DP_BAR < 0.5
```

### CC_SEAL_VENT_HIGH

High · seal_primary_wear

```python
CC_SEAL_VENT_HIGH =
    np.maximum(VENT_FLOW_DE_NM3H, VENT_FLOW_NE_NM3H) > 6
```

### CC_VIBRATION_HIGH

High · rotor_unbalance

```python
CC_VIBRATION_HIGH =
    np.maximum(VIB_DE_UM, VIB_NE_UM) > 50
```

### CC_THRUST_TEMP_HIGH

High · thrust_overload

```python
CC_THRUST_TEMP_HIGH =
    THRUST_TEMP_C > 110
```

### CC_SURGE_CONTROL_LINE

Medium · surge_approach

```python
CC_SURGE_CONTROL_LINE =
    (SURGE_MARGIN_PCT >= 5) & (SURGE_MARGIN_PCT < 15)
```

### CC_EFFICIENCY_LOW

Medium · impeller_fouling

```python
CC_EFFICIENCY_LOW =
    (ETA_POLY - ETA_EXPECTED) * 100 < -3
```

### CC_HEAD_LOW

Medium · impeller_fouling

```python
CC_HEAD_LOW =
    HEAD_POLY_KJKG / HEAD_EXPECTED_KJKG < 0.95
```

### CC_POWER_MISMATCH

Medium · discharge_tt_drift

```python
CC_POWER_MISMATCH =
    np.abs(POWER_RATIO - 1) > 0.06
```

### CC_AXIAL_POSITION

Medium · thrust_overload

```python
CC_AXIAL_POSITION =
    np.abs(AXIAL_POS_MM) > 0.3
```

### CC_BEARING_TEMP_HIGH

Medium

```python
CC_BEARING_TEMP_HIGH =
    np.maximum(BRG_TEMP_DE_C, BRG_TEMP_NE_C) > 105
```

### CC_RECYCLE_OPEN

Low · surge_approach

```python
CC_RECYCLE_OPEN =
    RECYCLE_VALVE_PCT > 10
```
