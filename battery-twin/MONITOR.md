# BAT-1001: Maximo Monitor functions and alert rules

Device type `DC_BATTERY_SYSTEM`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### FLOAT_VPC

```python
FLOAT_VPC =
    (BATTERY_VOLTAGE_V / 54)
```

### FLOAT_VPC_EXPECTED

```python
FLOAT_VPC_EXPECTED =
    np.interp(
      BATTERY_TEMP_C,
      [-10, 0, 10, 20, 30, 40],
      [2.37, 2.33, 2.29, 2.25, 2.23, 2.21]
    )
```

### FLOAT_V_RESIDUAL_MV

```python
FLOAT_V_RESIDUAL_MV =
    (
      (BATTERY_VOLTAGE_V / 54)
      - np.interp(
          BATTERY_TEMP_C,
          [-10, 0, 10, 20, 30, 40],
          [2.37, 2.33, 2.29, 2.25, 2.23, 2.21]
        )
    )
    * 1000
```

### FLOAT_CURRENT_EXPECTED_A

```python
FLOAT_CURRENT_EXPECTED_A =
    (
      0.16275
      * np.power(2, (BATTERY_TEMP_C - 20) / 10)
      * np.power(2, ((BATTERY_VOLTAGE_V / 54) - 2.25) / 0.025)
    )
```

### FLOAT_CURRENT_RATIO

```python
FLOAT_CURRENT_RATIO =
    BATTERY_CURRENT_A / FLOAT_CURRENT_EXPECTED_A
```

### BATTERY_TEMP_RISE_K

```python
BATTERY_TEMP_RISE_K =
    BATTERY_TEMP_C - ROOM_TEMP_C
```

### CELL_DEV_MAX_PCT

```python
CELL_DEV_MAX_PCT =
    (
      np.maximum(CELL_V_MAX - CELL_V_MEAN, CELL_V_MEAN - CELL_V_MIN)
      / CELL_V_MEAN.clip(lower=0.1)
      * 100
    )
```

### RI_EXPECTED_MOHM

```python
RI_EXPECTED_MOHM =
    (0.51 * (1 - 0.006 * (BATTERY_TEMP_C - 20)))
```

### RI_RATIO_MAX

```python
RI_RATIO_MAX =
    RI_MAX_MOHM / RI_EXPECTED_MOHM
```

### RI_RATIO_MEAN

```python
RI_RATIO_MEAN =
    (RI_MEAN_MOHM / RI_EXPECTED_MOHM)
```

### RI_MAX_VS_MEAN

```python
RI_MAX_VS_MEAN =
    RI_MAX_MOHM / RI_MEAN_MOHM.clip(lower=0.001)
```

### CONN_R_RATIO

```python
CONN_R_RATIO =
    CONN_R_MAX_MOHM / 0.05
```

### CONN_TEMP_RISE_K

```python
CONN_TEMP_RISE_K =
    CONN_TEMP_MAX_C - BATTERY_TEMP_C
```

### RIPPLE_PER_100AH

```python
RIPPLE_PER_100AH =
    RIPPLE_CURRENT_A / 465 * 100
```

### POLE_IMBALANCE_PCT

```python
POLE_IMBALANCE_PCT =
    (
      (POS_EARTH_V + NEG_EARTH_V)
      / (POS_EARTH_V - NEG_EARTH_V).clip(lower=1)
      * 100
    )
```

### AGEING_RATE_V

```python
AGEING_RATE_V =
    np.power(2, (BATTERY_TEMP_C - 20) / 10)
```

### CAPACITY_FACTOR_T

```python
CAPACITY_FACTOR_T =
    np.interp(
      BATTERY_TEMP_C,
      [-10, 0, 10, 20, 30, 40],
      [0.6, 0.78, 0.9, 1, 1.05, 1.07]
    )
```

### CAPACITY_EST_PCT

```python
CAPACITY_EST_PCT =
    (1 - 0.65 * (RI_RATIO_MEAN - 1)).clip(lower=0.3, upper=1) * 100
```

### AUTONOMY_H

```python
AUTONOMY_H =
    (
      SOC_PCT
      / 100
      * 465
      * np.interp(
          BATTERY_TEMP_C,
          [-10, 0, 10, 20, 30, 40],
          [0.6, 0.78, 0.9, 1, 1.05, 1.07]
        )
      * (1 - 0.65 * (RI_RATIO_MEAN - 1)).clip(lower=0.3, upper=1)
      / LOAD_CURRENT_A.clip(lower=1)
    )
```

## AlertExpression rules (13)

### BAT_THERMAL_RUNAWAY

Critical · thermal_runaway

```python
BAT_THERMAL_RUNAWAY =
    ((CHARGER_AC_ON == 1) & (CHARGER_MODE == 0))
    & (SOC_PCT >= 98)
    & (FLOAT_CURRENT_RATIO > 3)
    & (BATTERY_TEMP_RISE_K > 5)
```

### BAT_FLOAT_VOLTAGE

Medium · float_setting

```python
BAT_FLOAT_VOLTAGE =
    ((CHARGER_AC_ON == 1) & (CHARGER_MODE == 0))
    & (FLOAT_V_RESIDUAL_MV.abs() > 30)
```

### BAT_CELL_IMBALANCE

Medium · weak_cell

```python
BAT_CELL_IMBALANCE =
    ((CHARGER_AC_ON == 1) & (CHARGER_MODE == 0)) & (CELL_DEV_MAX_PCT > 4.5)
```

### BAT_WEAK_CELL

High · weak_cell

```python
BAT_WEAK_CELL =
    RI_MAX_VS_MEAN > 1.5
```

### BAT_CELL_RI_HIGH

Low

```python
BAT_CELL_RI_HIGH =
    (RI_RATIO_MAX > 1.2) & (RI_MAX_VS_MEAN <= 1.5)
```

### BAT_LOOSE_CONNECTION

High · loose_connection

```python
BAT_LOOSE_CONNECTION =
    ((CONN_R_MAX_MOHM / 0.05) > 3) | (CONN_TEMP_RISE_K > 10)
```

### BAT_RIPPLE_HIGH

Medium · charger_ripple

```python
BAT_RIPPLE_HIGH =
    (RIPPLE_CURRENT_A / 465 * 100) > 5
```

### BAT_EARTH_FAULT

High · ground_fault

```python
BAT_EARTH_FAULT =
    (INSULATION_KOHM < 50) | (POLE_IMBALANCE_PCT.abs() > 30)
```

### BAT_ROOM_HOT

Medium · ventilation_failure

```python
BAT_ROOM_HOT =
    ROOM_TEMP_C > 30
```

### BAT_TEMP_HIGH

High · ventilation_failure

```python
BAT_TEMP_HIGH =
    BATTERY_TEMP_C > 35
```

### BAT_CAPACITY_LOW

High · capacity_fade

```python
BAT_CAPACITY_LOW =
    (RI_RATIO_MEAN > 1.3) | (AUTONOMY_H < 10)
```

### BAT_LOW_VOLTAGE

High

```python
BAT_LOW_VOLTAGE =
    ((BATTERY_VOLTAGE_V / 54) < 1.85)
```

### BAT_ON_BATTERY

Low

```python
BAT_ON_BATTERY =
    CHARGER_AC_ON == 0
```
