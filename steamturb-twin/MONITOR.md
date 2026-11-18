# ST-3201: Maximo Monitor functions and alert rules

Device type `STEAM_TURBINE_EXTRACTION`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### H_MAIN_KJKG

```python
H_MAIN_KJKG =
    (
      1996.72817
      + 1.70062946 * (MAIN_TEMP_C + 273.15)
      + 0.000295708033 * (MAIN_TEMP_C + 273.15) ** 2
      - 1.64999356 * ((MAIN_TEMP_C + 273.15) / 600) ** -2 * MAIN_PRESS_BARA
      - 0.0134772194
        * ((MAIN_TEMP_C + 273.15) / 600) ** -9
        * MAIN_PRESS_BARA ** 2
    )
```

### H_EXT_KJKG

```python
H_EXT_KJKG =
    (
      1996.72817
      + 1.70062946 * (EXT_TEMP_C + 273.15)
      + 0.000295708033 * (EXT_TEMP_C + 273.15) ** 2
      - 1.64999356 * ((EXT_TEMP_C + 273.15) / 600) ** -2 * EXT_PRESS_BARA
      - 0.0134772194
        * ((EXT_TEMP_C + 273.15) / 600) ** -9
        * EXT_PRESS_BARA ** 2
    )
```

### DH_HP_ACTUAL_KJKG

```python
DH_HP_ACTUAL_KJKG =
    (H_MAIN_KJKG - H_EXT_KJKG)
```

### DH_HP_ISEN_KJKG

```python
DH_HP_ISEN_KJKG =
    (
      4.4965034965
      * (
          0.46088254 * (MAIN_TEMP_C + 273.15)
          - 0.482389
            * ((MAIN_TEMP_C + 273.15) / 600) ** -2.5
            * MAIN_PRESS_BARA
          - 0.00270654
            * ((MAIN_TEMP_C + 273.15) / 600) ** -9
            * MAIN_PRESS_BARA ** 2
        )
      * (1 - (EXT_PRESS_BARA / MAIN_PRESS_BARA) ** 0.222395023328)
    )
```

### HP_EFF_PCT

```python
HP_EFF_PCT =
    (100 * DH_HP_ACTUAL_KJKG / DH_HP_ISEN_KJKG)
```

### HP_EFF_EXPECTED_PCT

```python
HP_EFF_EXPECTED_PCT =
    (80 - 25 * (1 - MAIN_FLOW_TH / 200) ** 2)
```

### HP_EFF_DEV_PTS

```python
HP_EFF_DEV_PTS =
    (HP_EFF_PCT - HP_EFF_EXPECTED_PCT)
```

### WHEEL_PRESS_EXPECTED_BARA

```python
WHEEL_PRESS_EXPECTED_BARA =
    (72 * (MAIN_FLOW_TH / 200) * np.sqrt((MAIN_TEMP_C + 273.15) / 773.15))
```

### WHEEL_PRESS_RATIO

```python
WHEEL_PRESS_RATIO =
    (WHEEL_PRESS_BARA / WHEEL_PRESS_EXPECTED_BARA)
```

### POWER_EXPECTED_MW

```python
POWER_EXPECTED_MW =
    (
      0.2987499435 * MAIN_FLOW_TH
      - 0.1759266667 * EXT_FLOW_TH
      - 0.6771689266
      - 0.0006 * (MAIN_PRESS_BARA - 100)
      + 0.0903 * (MAIN_TEMP_C - 500)
      - 21.8958046337 * ((COND_PRESS_MBAR / 86) ** 0.1597 - 1)
    )
```

### POWER_DEV_PCT

```python
POWER_DEV_PCT =
    (100 * (POWER_MW - POWER_EXPECTED_MW) / POWER_EXPECTED_MW)
```

### LOST_MW

```python
LOST_MW =
    (POWER_EXPECTED_MW - POWER_MW)
```

### LOST_EUR_H

```python
LOST_EUR_H =
    LOST_MW * 80
```

### COND_TSAT_C

```python
COND_TSAT_C =
    (1737.94135822 / (8.21118462 - np.log10(COND_PRESS_MBAR)) - 234)
```

### COND_TTD_K

```python
COND_TTD_K =
    (COND_TSAT_C - CW_OUT_C)
```

### COND_PRESS_EXPECTED_MBAR

```python
COND_PRESS_EXPECTED_MBAR =
    (10 ** (8.21118462 - 1737.94135822 / (CW_OUT_C + 5 + 234)))
```

### COND_PRESS_DEV_MBAR

```python
COND_PRESS_DEV_MBAR =
    (COND_PRESS_MBAR - COND_PRESS_EXPECTED_MBAR)
```

### BACKPRESSURE_LOSS_MW

```python
BACKPRESSURE_LOSS_MW =
    21.8958046337
    * (
        (COND_PRESS_MBAR / 86) ** 0.1597
        - (COND_PRESS_EXPECTED_MBAR / 86) ** 0.1597
      )
```

### VALVE_FLOW_RATIO

```python
VALVE_FLOW_RATIO =
    (
      MAIN_FLOW_TH
      / (
          200
          * (GV_LIFT_PCT / 80)
          * (MAIN_PRESS_BARA / 100)
          * np.sqrt(773.15 / (MAIN_TEMP_C + 273.15))
        )
    )
```

### VIB_MAX_MMS

```python
VIB_MAX_MMS =
    np.maximum(VIB_BRG1_MMS, VIB_BRG2_MMS)
```

## AlertExpression rules (12)

### ST_VIB_ZONE_D

High

```python
ST_VIB_ZONE_D =
    np.maximum(VIB_BRG1_MMS, VIB_BRG2_MMS) >= 11.8
```

### ST_HP_EFF_VERY_LOW

High · solid_particle_erosion

```python
ST_HP_EFF_VERY_LOW =
    HP_EFF_DEV_PTS <= -7
```

### ST_THRUST_POS

High · thrust_bearing_wear

```python
ST_THRUST_POS =
    np.abs(THRUST_POS_MM) > 0.25
```

### ST_POWER_LOW

Medium · lp_blade_damage

```python
ST_POWER_LOW =
    POWER_DEV_PCT < -1.5
```

### ST_HP_EFF_LOW

Medium · hp_deposits

```python
ST_HP_EFF_LOW =
    (HP_EFF_DEV_PTS <= -3) & (HP_EFF_DEV_PTS > -7)
```

### ST_WHEEL_PRESS_HIGH

Medium · hp_deposits

```python
ST_WHEEL_PRESS_HIGH =
    WHEEL_PRESS_RATIO > 1.04
```

### ST_WHEEL_PRESS_LOW

Medium · solid_particle_erosion

```python
ST_WHEEL_PRESS_LOW =
    WHEEL_PRESS_RATIO < 0.97
```

### ST_COND_PRESS_HIGH

Medium · condenser_fouling

```python
ST_COND_PRESS_HIGH =
    COND_PRESS_DEV_MBAR > 15
```

### ST_TTD_HIGH

Medium · condenser_fouling

```python
ST_TTD_HIGH =
    COND_TTD_K > 9
```

### ST_VALVE_CAPACITY_LOW

Medium · governor_valve

```python
ST_VALVE_CAPACITY_LOW =
    VALVE_FLOW_RATIO < 0.92
```

### ST_VIB_ZONE_C

Medium · rotor_unbalance

```python
ST_VIB_ZONE_C =
    (np.maximum(VIB_BRG1_MMS, VIB_BRG2_MMS) >= 7.5)
    & (np.maximum(VIB_BRG1_MMS, VIB_BRG2_MMS) < 11.8)
```

### ST_THRUST_TEMP

Medium · thrust_bearing_wear

```python
ST_THRUST_TEMP =
    THRUST_PAD_C > 95
```
