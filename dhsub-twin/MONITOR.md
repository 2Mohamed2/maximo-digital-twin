# DH-7101: Maximo Monitor functions and alert rules

Device type `DH_SUBSTATION`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### SH_POWER_KW

```python
SH_POWER_KW =
    (1.15 * SH_PUMP_FLOW_M3H * (SH_FLOW_C - SH_RETURN_C))
```

### HEAT_CURVE_C

```python
HEAT_CURVE_C =
    np.clip(20 + 1.25 * (20 - OUTDOOR_C), 25, 60)
```

### CURVE_OFFSET_K

```python
CURVE_OFFSET_K =
    SH_FLOW_SET_C - np.clip(20 + 1.25 * (20 - OUTDOOR_C), 25, 60)
```

### SUPPLY_SHORTFALL_K

```python
SUPPLY_SHORTFALL_K =
    SH_FLOW_SET_C - SH_FLOW_C
```

### SEC_FLOW_RATIO

```python
SEC_FLOW_RATIO =
    SH_PUMP_FLOW_M3H / 1.0783
```

### SH_APPROACH_K

```python
SH_APPROACH_K =
    SH_P_RETURN_C - SH_RETURN_C
```

### LMTD_K

```python
LMTD_K =
    np.where(
      np.abs(
        np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1)
        - np.maximum(SH_P_RETURN_C - SH_RETURN_C, 0.1)
      )
      < 1e-06,
      np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1),
      (
        np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1)
        - np.maximum(SH_P_RETURN_C - SH_RETURN_C, 0.1)
      )
      / np.log(
          np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1)
          / np.maximum(SH_P_RETURN_C - SH_RETURN_C, 0.1)
        )
    )
```

### UA_MEASURED_KW_K

```python
UA_MEASURED_KW_K =
    (
      SH_POWER_KW
      / np.where(
          np.abs(
            np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1)
            - np.maximum(SH_P_RETURN_C - SH_RETURN_C, 0.1)
          )
          < 1e-06,
          np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1),
          (
            np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1)
            - np.maximum(SH_P_RETURN_C - SH_RETURN_C, 0.1)
          )
          / np.log(
              np.maximum(P_SUPPLY_C - SH_FLOW_C, 0.1)
              / np.maximum(SH_P_RETURN_C - SH_RETURN_C, 0.1)
            )
        )
    )
```

### PRIMARY_FLOW_SH_M3H

```python
PRIMARY_FLOW_SH_M3H =
    (
      SH_PUMP_FLOW_M3H
      * (SH_FLOW_C - SH_RETURN_C)
      / np.maximum(P_SUPPLY_C - SH_P_RETURN_C, 0.5)
    )
```

### UA_EXPECTED_KW_K

```python
UA_EXPECTED_KW_K =
    (
      4.2975
      / (
          0.5 * (0.906 / np.maximum(PRIMARY_FLOW_SH_M3H, 0.01)) ** 0.65
          + 0.5 * (1.0783 / np.maximum(SH_PUMP_FLOW_M3H, 0.01)) ** 0.65
        )
    )
```

### UA_RATIO

```python
UA_RATIO =
    UA_MEASURED_KW_K / UA_EXPECTED_KW_K
```

### RETURN_REF_C

```python
RETURN_REF_C =
    (20 + (np.clip(20 + 1.25 * (20 - OUTDOOR_C), 25, 60) - 20) * 0.375 + 5)
```

### RETURN_EXCESS_K

```python
RETURN_EXCESS_K =
    (HM_T_RETURN_C - RETURN_REF_C)
```

### COOLING_K

```python
COOLING_K =
    HM_T_SUPPLY_C - HM_T_RETURN_C
```

### RETURN_COST_EUR_Y

```python
RETURN_COST_EUR_Y =
    np.maximum(RETURN_EXCESS_K, 0) * 12
```

### BYPASS_MIX_K

```python
BYPASS_MIX_K =
    HM_T_RETURN_C - SH_P_RETURN_C
```

### METER_ERROR_PCT

```python
METER_ERROR_PCT =
    (
      (
        HM_POWER_KW
        / (
            1.15
            * np.maximum(HM_FLOW_M3H, 0.001)
            * np.maximum(P_SUPPLY_C - P_RETURN_C, 0.1)
          )
        - 1
      )
      * 100
    )
```

### METER_MPE_PCT

```python
METER_MPE_PCT =
    (
      np.minimum(2 + 0.03 / np.maximum(HM_FLOW_M3H, 0.001), 5)
      + 0.5
      + 9 / np.maximum(P_SUPPLY_C - P_RETURN_C, 0.1)
      + 0.5
      + 3 / np.maximum(P_SUPPLY_C - P_RETURN_C, 0.1)
    )
```

### VALVE_AUTHORITY

```python
VALVE_AUTHORITY =
    32.0639 / np.maximum(DP_SECTION_KPA, 1)
```

## AlertExpression rules (13)

### DH_DHW_CIRC_LOW

High · dhw_circulation_fault

```python
DH_DHW_CIRC_LOW =
    DHW_CIRC_RETURN_C < 50
```

### DH_DHW_TEMP_LOW

High · dhw_setpoint_low

```python
DH_DHW_TEMP_LOW =
    DHW_C < 55
```

### DH_METER_ERROR

High · meter_sensor_fault

```python
DH_METER_ERROR =
    np.abs(METER_ERROR_PCT) > METER_MPE_PCT
```

### DH_PRIMARY_BYPASS

High · primary_bypass

```python
DH_PRIMARY_BYPASS =
    (DHW_FLOW_LPM < 1) & (BYPASS_MIX_K > 7.5)
```

### DH_SUPPLY_LOW

High

```python
DH_SUPPLY_LOW =
    (SH_FLOW_SET_C - SH_FLOW_C) > 5
```

### DH_RETURN_HIGH

Medium · secondary_overflow

```python
DH_RETURN_HIGH =
    RETURN_EXCESS_K > 3
```

### DH_UA_LOW

Medium · hex_fouling

```python
DH_UA_LOW =
    (SH_POWER_KW > 13.95) & (UA_RATIO < 0.7)
```

### DH_SEC_FLOW_HIGH

Medium · secondary_overflow

```python
DH_SEC_FLOW_HIGH =
    (SH_PUMP_FLOW_M3H / 1.0783) > 1.25
```

### DH_CURVE_HIGH

Medium · curve_too_high

```python
DH_CURVE_HIGH =
    CURVE_OFFSET_K > 5
```

### DH_METER_TEMP_MISMATCH

Medium · meter_sensor_fault

```python
DH_METER_TEMP_MISMATCH =
    (np.abs(HM_T_SUPPLY_C - P_SUPPLY_C) > 1)
    | (np.abs(HM_T_RETURN_C - P_RETURN_C) > 1)
```

### DH_AUTHORITY_LOW

Medium · dp_controller_fault

```python
DH_AUTHORITY_LOW =
    VALVE_AUTHORITY < 0.4
```

### DH_VALVE_HUNTING

Medium · dp_controller_fault

```python
DH_VALVE_HUNTING =
    (VALVE_REVERSALS_H > 20) & (SH_FLOW_RMS_K > 1.5)
```

### DH_METER_INFO

Low

```python
DH_METER_INFO =
    HM_INFO_CODE > 0.5
```
