# CH-201: Maximo Monitor functions and alert rules

Device type `CHILLER_SCREW`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (13)

### Q_EXPECTED_KW

```python
Q_EXPECTED_KW =
    (
      (SLIDE_PCT / 100)
      * (
          340.621030631
          + (12.8497068268)*EVAP_SAT_TEMP_C
          + (-1.11031598137)*COND_SAT_TEMP_C
          + (0.212575560301)*EVAP_SAT_TEMP_C**2
          + (-0.0329604008622)*EVAP_SAT_TEMP_C*COND_SAT_TEMP_C
          + (-0.039482147246)*COND_SAT_TEMP_C**2
          + (0.00173939747708)*EVAP_SAT_TEMP_C**3
          + (-0.00135718109792)*EVAP_SAT_TEMP_C**2*COND_SAT_TEMP_C
          + (-0.000758082269915)*EVAP_SAT_TEMP_C*COND_SAT_TEMP_C**2
          + (0.000223926705619)*COND_SAT_TEMP_C**3
        )
    )
```

### CAPACITY_DEVIATION_PCT

```python
CAPACITY_DEVIATION_PCT =
    (
      (1.1616 * CHW_FLOW_M3H * (CHW_IN_TEMP_C - CHW_OUT_TEMP_C))
      - Q_EXPECTED_KW
    )
    / Q_EXPECTED_KW.clip(lower=1)
    * 100
```

### P_EXPECTED_KW

```python
P_EXPECTED_KW =
    (
      (
        30.7853724101
        + (0.668184792836)*EVAP_SAT_TEMP_C
        + (0.716461719888)*COND_SAT_TEMP_C
        + (0.0172016708365)*EVAP_SAT_TEMP_C**2
        + (-0.00986932403655)*EVAP_SAT_TEMP_C*COND_SAT_TEMP_C
        + (-0.00600875087113)*COND_SAT_TEMP_C**2
        + (-5.21839531609e-05)*EVAP_SAT_TEMP_C**3
        + (-0.000226185634955)*EVAP_SAT_TEMP_C**2*COND_SAT_TEMP_C
        + (0.00010474433604)*EVAP_SAT_TEMP_C*COND_SAT_TEMP_C**2
        + (0.000197042230573)*COND_SAT_TEMP_C**3
      )
      * (0.3 + 0.7 * (SLIDE_PCT / 100))
    )
```

### POWER_DEVIATION_PCT

```python
POWER_DEVIATION_PCT =
    (POWER_KW - P_EXPECTED_KW) / P_EXPECTED_KW.clip(lower=1) * 100
```

### COP

```python
COP =
    (1.1616 * CHW_FLOW_M3H * (CHW_IN_TEMP_C - CHW_OUT_TEMP_C))
    / POWER_KW.clip(lower=0.5)
```

### COP_EXPECTED

```python
COP_EXPECTED =
    Q_EXPECTED_KW / P_EXPECTED_KW.clip(lower=0.5)
```

### KW_PER_TON

```python
KW_PER_TON =
    POWER_KW
    / ((1.1616 * CHW_FLOW_M3H * (CHW_IN_TEMP_C - CHW_OUT_TEMP_C)) / 3.517).clip(lower=0.5)
```

### COND_APPROACH_K

```python
COND_APPROACH_K =
    (COND_SAT_TEMP_C - CW_OUT_TEMP_C)
```

### COND_APPROACH_EXPECTED_K

```python
COND_APPROACH_EXPECTED_K =
    (
      0.0140104082499
      * (
          (1.1616 * CHW_FLOW_M3H * (CHW_IN_TEMP_C - CHW_OUT_TEMP_C))
          + POWER_KW
        )
    )
```

### COND_FOULING_K

```python
COND_FOULING_K =
    COND_APPROACH_K - COND_APPROACH_EXPECTED_K
```

### EVAP_APPROACH_K

```python
EVAP_APPROACH_K =
    (CHW_OUT_TEMP_C - EVAP_SAT_TEMP_C)
```

### EVAP_APPROACH_EXPECTED_K

```python
EVAP_APPROACH_EXPECTED_K =
    (
      0.0140528429395
      * (1.1616 * CHW_FLOW_M3H * (CHW_IN_TEMP_C - CHW_OUT_TEMP_C))
    )
```

### EVAP_FOULING_K

```python
EVAP_FOULING_K =
    EVAP_APPROACH_K - EVAP_APPROACH_EXPECTED_K
```

## AlertExpression rules (11)

### CHILLER_COND_FOULING

Medium · cond_fouling

```python
CHILLER_COND_FOULING =
    (RUNNING > 0) & (COND_FOULING_K > 1.5) & (SUBCOOLING_K <= 7.5)
```

### CHILLER_EVAP_FOULING

Medium · evap_fouling

```python
CHILLER_EVAP_FOULING =
    (RUNNING > 0) & (EVAP_FOULING_K > 1.2) & (SUPERHEAT_K <= 12)
```

### CHILLER_LOW_CHARGE

High · low_charge

```python
CHILLER_LOW_CHARGE =
    (RUNNING > 0) & (SUPERHEAT_K > 12) & (SUBCOOLING_K < 3)
```

### CHILLER_NONCONDENSABLES

Medium · noncondensables

```python
CHILLER_NONCONDENSABLES =
    (RUNNING > 0) & (SUBCOOLING_K > 7.5)
```

### CHILLER_CAPACITY_LOSS

Medium · compressor_wear

```python
CHILLER_CAPACITY_LOSS =
    (RUNNING > 0) & (CAPACITY_DEVIATION_PCT < -8)
```

### CHILLER_HIGH_DISCHARGE

High

```python
CHILLER_HIGH_DISCHARGE =
    DISCHARGE_TEMP_C > 95
```

### CHILLER_OIL_FILTER

Medium · oil_filter

```python
CHILLER_OIL_FILTER =
    (RUNNING > 0) & (OIL_FILTER_DP_BAR > 1.5)
```

### CHILLER_CURRENT_IMBALANCE

Medium · motor_winding

```python
CHILLER_CURRENT_IMBALANCE =
    (RUNNING > 0) & (CURRENT_IMBALANCE_PCT > 5)
```

### CHILLER_WINDING_TEMP_HIGH

High · motor_winding

```python
CHILLER_WINDING_TEMP_HIGH =
    WINDING_TEMP_C > 110
```

### CHILLER_LOW_EFFICIENCY

Low

```python
CHILLER_LOW_EFFICIENCY =
    (RUNNING > 0)
    & (
        POWER_KW
        / (
            (1.1616 * CHW_FLOW_M3H * (CHW_IN_TEMP_C - CHW_OUT_TEMP_C))
            / 3.517
          ).clip(lower=0.5)
        > 0.95
      )
```

### CHILLER_TRIPPED

Critical

```python
CHILLER_TRIPPED =
    TRIP_CODE > 0
```
