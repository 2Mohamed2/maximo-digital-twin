# RF-6901: Maximo Monitor functions and alert rules

Device type `REFRIGERATION_RACK`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### TO_DEW_C

```python
TO_DEW_C =
    (
      2259.6065 / (10.420419 - np.log(SUCTION_PRESSURE_BARG + 1.01325))
      - 257.25
    )
```

### TC_DEW_C

```python
TC_DEW_C =
    (
      2259.6065 / (10.420419 - np.log(DISCHARGE_PRESSURE_BARG + 1.01325))
      - 257.25
    )
```

### TC_BUBBLE_C

```python
TC_BUBBLE_C =
    (
      2114.7218 / (10.062484 - np.log(DISCHARGE_PRESSURE_BARG + 1.01325))
      - 256.75
    )
```

### SUPERHEAT_K

```python
SUPERHEAT_K =
    SUCTION_TEMP_C - TO_DEW_C
```

### SUBCOOLING_K

```python
SUBCOOLING_K =
    TC_BUBBLE_C - LIQUID_TEMP_C
```

### Q_EXPECTED_KW

```python
Q_EXPECTED_KW =
    (
      (CAPACITY_PCT / 100 * 4)
      * (
          52.55784
          + 1.9463958 * TO_DEW_C
          - 0.41487961 * TC_DEW_C
          + 0.027210035 * TO_DEW_C ** 2
          - 0.011603987 * TO_DEW_C * TC_DEW_C
          - 0.0011819895 * TC_DEW_C ** 2
          + 0.00014118054 * TO_DEW_C ** 3
          - 0.00014912024 * TC_DEW_C * TO_DEW_C ** 2
          - 3.4307608e-05 * TO_DEW_C * TC_DEW_C ** 2
          + 3.1219596e-06 * TC_DEW_C ** 3
        )
    )
```

### P_EXPECTED_KW

```python
P_EXPECTED_KW =
    (
      (CAPACITY_PCT / 100 * 4)
      * (
          0.097746845
          - 0.31382544 * TO_DEW_C
          + 0.32571832 * TC_DEW_C
          - 0.0086358457 * TO_DEW_C ** 2
          + 0.0105305 * TO_DEW_C * TC_DEW_C
          - 0.0012372259 * TC_DEW_C ** 2
          - 6.1491949e-05 * TO_DEW_C ** 3
          + 8.526264e-05 * TC_DEW_C * TO_DEW_C ** 2
          - 9.5305173e-06 * TO_DEW_C * TC_DEW_C ** 2
          - 6.0642879e-06 * TC_DEW_C ** 3
        )
    )
```

### POWER_RATIO

```python
POWER_RATIO =
    RACK_POWER_KW / np.maximum(P_EXPECTED_KW, 1)
```

### COP_OPS

```python
COP_OPS =
    Q_EXPECTED_KW / np.maximum(RACK_POWER_KW, 1)
```

### T_DISCHARGE_EXPECTED_C

```python
T_DISCHARGE_EXPECTED_C =
    (
      (SUCTION_TEMP_C + 273.15)
      * (
          (DISCHARGE_PRESSURE_BARG + 1.01325)
          / (SUCTION_PRESSURE_BARG + 1.01325)
        )
        ** 0.17074
      - 273.15
    )
```

### T_DISCHARGE_RESIDUAL_K

```python
T_DISCHARGE_RESIDUAL_K =
    DISCHARGE_TEMP_C - T_DISCHARGE_EXPECTED_C
```

### COND_APPROACH_K

```python
COND_APPROACH_K =
    (TC_DEW_C - AMBIENT_TEMP_C)
```

### COND_APPROACH_EXPECTED_K

```python
COND_APPROACH_EXPECTED_K =
    (8 * (Q_EXPECTED_KW + RACK_POWER_KW) / 100)
```

### RECEIVER_LEVEL_EXPECTED_PCT

```python
RECEIVER_LEVEL_EXPECTED_PCT =
    (36 - 0.15 * (AMBIENT_TEMP_C - 20) - 4 * (CAPACITY_PCT / 100 - 0.6))
```

### CHARGE_DEFICIT_KG

```python
CHARGE_DEFICIT_KG =
    (
      (RECEIVER_LEVEL_EXPECTED_PCT - RECEIVER_LEVEL_PCT)
      / 100
      * 0.15
      * (
          -0.011526884 * LIQUID_TEMP_C ** 2
          - 3.8993434 * LIQUID_TEMP_C
          + 1197.0186
        )
    )
```

### LEAK_RATE_KG_YR

```python
LEAK_RATE_KG_YR =
    (
      np.maximum(CHARGE_DEFICIT_KG, 0)
      * 365
      / np.maximum(DAYS_SINCE_TOPUP, 1)
    )
```

### LEAK_CO2E_T_YR

```python
LEAK_CO2E_T_YR =
    LEAK_RATE_KG_YR * 1387 / 1000
```

### COIL_TD_K

```python
COIL_TD_K =
    ROOM_AIR_C - TO_DEW_C
```

### PRODUCT_MARGIN_K

```python
PRODUCT_MARGIN_K =
    5 - PRODUCT_TEMP_C
```

## AlertExpression rules (14)

### RF_PRODUCT_TEMP_HIGH

High · door_left_open

```python
RF_PRODUCT_TEMP_HIGH =
    PRODUCT_TEMP_C > 5
```

### RF_RECEIVER_LOW

High · refrigerant_leak

```python
RF_RECEIVER_LOW =
    RECEIVER_LEVEL_PCT < 10
```

### RF_LEAK_RATE_HIGH

High · refrigerant_leak

```python
RF_LEAK_RATE_HIGH =
    LEAK_RATE_KG_YR > 16
```

### RF_SUPERHEAT_LOW

High · superheat_drift

```python
RF_SUPERHEAT_LOW =
    SUPERHEAT_K < 5
```

### RF_DISCHARGE_TEMP_LIMIT

High

```python
RF_DISCHARGE_TEMP_LIMIT =
    DISCHARGE_TEMP_C > 135
```

### RF_CHARGE_LOSS

Medium · refrigerant_leak

```python
RF_CHARGE_LOSS =
    CHARGE_DEFICIT_KG > 8
```

### RF_SUBCOOLING_LOW

Medium · refrigerant_leak

```python
RF_SUBCOOLING_LOW =
    SUBCOOLING_K < 1
```

### RF_DISCHARGE_TEMP_HIGH

Medium · compressor_valve_wear

```python
RF_DISCHARGE_TEMP_HIGH =
    T_DISCHARGE_RESIDUAL_K > 15
```

### RF_POWER_HIGH

Medium · compressor_mechanical

```python
RF_POWER_HIGH =
    RACK_POWER_KW / np.maximum(P_EXPECTED_KW, 1) > 1.1
```

### RF_COND_APPROACH_HIGH

Medium · condenser_fouled

```python
RF_COND_APPROACH_HIGH =
    (TC_DEW_C > 20.5) & (COND_APPROACH_K > 1.6 * COND_APPROACH_EXPECTED_K)
```

### RF_COIL_TD_HIGH

Medium · evaporator_icing

```python
RF_COIL_TD_HIGH =
    COIL_TD_K > 14.5
```

### RF_DEFROST_ON_TIME

Medium · evaporator_icing

```python
RF_DEFROST_ON_TIME =
    DEFROST_END_ON_TEMP < 0.5
```

### RF_DOOR_OPEN_LONG

Medium · door_left_open

```python
RF_DOOR_OPEN_LONG =
    DOOR_OPEN_MIN_H > 10
```

### RF_LEAK_CHECK_OVERDUE

Low

```python
RF_LEAK_CHECK_OVERDUE =
    DAYS_SINCE_LEAK_CHECK > 182.5
```
