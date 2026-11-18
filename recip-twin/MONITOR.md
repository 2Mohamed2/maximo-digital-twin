# K-2201: Maximo Monitor functions and alert rules

Device type `RECIP_COMPRESSOR_API618`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### RINT_S1

```python
RINT_S1 =
    (((PD1_BARG + 1.01325) * 1.02) / ((PS1_BARG + 1.01325) * 0.98))
```

### RINT_S2

```python
RINT_S2 =
    (((PD2_BARG + 1.01325) * 1.01) / ((PS2_BARG + 1.01325) * 0.98))
```

### TD_EXPECTED_S1_C

```python
TD_EXPECTED_S1_C =
    (
      (TS1_C + 273.15)
      * 0.954
      / (1 - 0.046 * (RINT_S1 ** 0.2857142857))
      * (RINT_S1 ** 0.2857142857)
      - 273.15
    )
```

### TD_EXPECTED_S2_C

```python
TD_EXPECTED_S2_C =
    (
      (TS2_C + 273.15)
      * 0.962
      / (1 - 0.038 * (RINT_S2 ** 0.2857142857))
      * (RINT_S2 ** 0.2857142857)
      - 273.15
    )
```

### TD_RESIDUAL_S1_K

```python
TD_RESIDUAL_S1_K =
    (TD1_C - TD_EXPECTED_S1_C)
```

### TD_RESIDUAL_S2_K

```python
TD_RESIDUAL_S2_K =
    (TD2_C - TD_EXPECTED_S2_C)
```

### VE_S1

```python
VE_S1 =
    (
      1
      - ((PD1_BARG + 1.01325) / (PS1_BARG + 1.01325)) / 100
      - 0.18
        * (
            ((PD1_BARG + 1.01325) / (PS1_BARG + 1.01325)) ** 0.7142857143
            - 1
          )
    )
```

### VE_S2

```python
VE_S2 =
    (
      1
      - ((PD2_BARG + 1.01325) / (PS2_BARG + 1.01325)) / 100
      - 0.22
        * (
            ((PD2_BARG + 1.01325) / (PS2_BARG + 1.01325)) ** 0.7142857143
            - 1
          )
    )
```

### FLOW_EXPECTED_NM3H

```python
FLOW_EXPECTED_NM3H =
    (
      VE_S1
      * 0.02440186954
      * SPEED_RPM
      * 60
      * (PS1_BARG + 1.01325)
      / 1.01325
      * 273.15
      / (TS1_C + 273.15)
    )
```

### CAPACITY_RATIO

```python
CAPACITY_RATIO =
    (FLOW_NM3H / FLOW_EXPECTED_NM3H)
```

### ROD_LOAD_C_S1_PCT

```python
ROD_LOAD_C_S1_PCT =
    (
      (
        0.08563356397 * (((PD1_BARG + 1.01325) * 1.02) - 1.01325)
        - 0.08144530996 * (((PS1_BARG + 1.01325) * 0.98) - 1.01325)
      )
      * 100
      / 355.8577292
      * 100
    )
```

### ROD_LOAD_T_S1_PCT

```python
ROD_LOAD_T_S1_PCT =
    (
      (
        0.08144530996 * (((PD1_BARG + 1.01325) * 1.02) - 1.01325)
        - 0.08563356397 * (((PS1_BARG + 1.01325) * 0.98) - 1.01325)
      )
      * 100
      / 333.6166211
      * 100
    )
```

### ROD_LOAD_C_S2_PCT

```python
ROD_LOAD_C_S2_PCT =
    (
      (
        0.04104330581 * (((PD2_BARG + 1.01325) * 1.01) - 1.01325)
        - 0.0368550518 * (((PS2_BARG + 1.01325) * 0.98) - 1.01325)
      )
      * 100
      / 355.8577292
      * 100
    )
```

### ROD_LOAD_T_S2_PCT

```python
ROD_LOAD_T_S2_PCT =
    (
      (
        0.0368550518 * (((PD2_BARG + 1.01325) * 1.01) - 1.01325)
        - 0.04104330581 * (((PS2_BARG + 1.01325) * 0.98) - 1.01325)
      )
      * 100
      / 333.6166211
      * 100
    )
```

### ROD_LOAD_MAX_PCT

```python
ROD_LOAD_MAX_PCT =
    np.maximum(
      np.maximum(ROD_LOAD_C_S1_PCT, ROD_LOAD_T_S1_PCT),
      np.maximum(ROD_LOAD_C_S2_PCT, ROD_LOAD_T_S2_PCT)
    )
```

### SUCT_COVER_RISE_MAX_K

```python
SUCT_COVER_RISE_MAX_K =
    np.maximum(
      np.maximum((TV1_HE_S_C - TS1_C), (TV1_CE_S_C - TS1_C)),
      np.maximum((TV2_HE_S_C - TS2_C), (TV2_CE_S_C - TS2_C))
    )
```

### DISCH_COVER_DEV_MAX_K

```python
DISCH_COVER_DEV_MAX_K =
    np.maximum(
      np.maximum(
        (TV1_HE_D_C - TD_EXPECTED_S1_C),
        (TV1_CE_D_C - TD_EXPECTED_S1_C)
      ),
      np.maximum(
        (TV2_HE_D_C - TD_EXPECTED_S2_C),
        (TV2_CE_D_C - TD_EXPECTED_S2_C)
      )
    )
```

### VALVE_PEER_SPREAD_K

```python
VALVE_PEER_SPREAD_K =
    np.maximum(
      np.maximum(
        np.abs(TV1_HE_S_C - TV1_CE_S_C),
        np.abs(TV1_HE_D_C - TV1_CE_D_C)
      ),
      np.maximum(
        np.abs(TV2_HE_S_C - TV2_CE_S_C),
        np.abs(TV2_HE_D_C - TV2_CE_D_C)
      )
    )
```

### LUBE_RATE_RATIO

```python
LUBE_RATE_RATIO =
    (15 / LUBE_CYCLE_S)
```

### XHEAD_VIB_RATIO

```python
XHEAD_VIB_RATIO =
    np.maximum((XHEAD_ACC1_G / 2.5), (XHEAD_ACC2_G / 2.5))
```

## AlertExpression rules (13)

### RECIP_ROD_LOAD_LIMIT

Critical · discharge_pressure_high

```python
RECIP_ROD_LOAD_LIMIT =
    np.maximum(
      np.maximum(ROD_LOAD_C_S1_PCT, ROD_LOAD_T_S1_PCT),
      np.maximum(ROD_LOAD_C_S2_PCT, ROD_LOAD_T_S2_PCT)
    )
    > 100
```

### RECIP_ROD_LOAD_HIGH

High · discharge_pressure_high

```python
RECIP_ROD_LOAD_HIGH =
    (
      np.maximum(
        np.maximum(ROD_LOAD_C_S1_PCT, ROD_LOAD_T_S1_PCT),
        np.maximum(ROD_LOAD_C_S2_PCT, ROD_LOAD_T_S2_PCT)
      )
      > 85
    )
    & (
        np.maximum(
          np.maximum(ROD_LOAD_C_S1_PCT, ROD_LOAD_T_S1_PCT),
          np.maximum(ROD_LOAD_C_S2_PCT, ROD_LOAD_T_S2_PCT)
        )
        <= 100
      )
```

### RECIP_TD_HIGH

High

```python
RECIP_TD_HIGH =
    np.maximum(TD1_C, TD2_C) > 145
```

### RECIP_PACKING_LEAK

High · packing_leak

```python
RECIP_PACKING_LEAK =
    np.maximum(PACKING_VENT1_NM3H, PACKING_VENT2_NM3H) > 1.5
```

### RECIP_LUBE_LOW

High · lube_starvation

```python
RECIP_LUBE_LOW =
    (15 / LUBE_CYCLE_S) < 0.75
```

### RECIP_XHEAD_VIB

High · crosshead_wear

```python
RECIP_XHEAD_VIB =
    np.maximum((XHEAD_ACC1_G / 2.5), (XHEAD_ACC2_G / 2.5)) > 2
```

### RECIP_SUCTION_VALVE_LEAK

Medium · suction_valve_leak

```python
RECIP_SUCTION_VALVE_LEAK =
    np.maximum(
      np.maximum((TV1_HE_S_C - TS1_C), (TV1_CE_S_C - TS1_C)),
      np.maximum((TV2_HE_S_C - TS2_C), (TV2_CE_S_C - TS2_C))
    )
    > 20
```

### RECIP_DISCHARGE_VALVE_LEAK

Medium · discharge_valve_leak

```python
RECIP_DISCHARGE_VALVE_LEAK =
    np.maximum(
      np.maximum(
        (TV1_HE_D_C - TD_EXPECTED_S1_C),
        (TV1_CE_D_C - TD_EXPECTED_S1_C)
      ),
      np.maximum(
        (TV2_HE_D_C - TD_EXPECTED_S2_C),
        (TV2_CE_D_C - TD_EXPECTED_S2_C)
      )
    )
    > 15
```

### RECIP_VALVE_PEER_SPREAD

Medium · discharge_valve_leak

```python
RECIP_VALVE_PEER_SPREAD =
    np.maximum(
      np.maximum(
        np.abs(TV1_HE_S_C - TV1_CE_S_C),
        np.abs(TV1_HE_D_C - TV1_CE_D_C)
      ),
      np.maximum(
        np.abs(TV2_HE_S_C - TV2_CE_S_C),
        np.abs(TV2_HE_D_C - TV2_CE_D_C)
      )
    )
    > 10
```

### RECIP_TD_DEVIATION_S1

Medium · discharge_valve_leak

```python
RECIP_TD_DEVIATION_S1 =
    TD_RESIDUAL_S1_K > 8
```

### RECIP_TD_DEVIATION_S2

Medium · ring_wear

```python
RECIP_TD_DEVIATION_S2 =
    TD_RESIDUAL_S2_K > 8
```

### RECIP_CAPACITY_LOW

Medium · discharge_valve_leak

```python
RECIP_CAPACITY_LOW =
    CAPACITY_RATIO < 0.92
```

### RECIP_ROD_DROP

Medium · rider_band_wear

```python
RECIP_ROD_DROP =
    np.maximum(ROD_DROP1_MM, ROD_DROP2_MM) > 1
```
