# CR-6301: Maximo Monitor functions and alert rules

Device type `CRAH_CHILLED_WATER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### AIR_MASS_FLOW_KGS

```python
AIR_MASS_FLOW_KGS =
    ((353.05 / (SUPPLY_AIR_C + 273.15)) * AIRFLOW_M3H / 3600)
```

### Q_AIR_KW

```python
Q_AIR_KW =
    (AIR_MASS_FLOW_KGS * 1.006 * (RETURN_AIR_C - SUPPLY_AIR_C))
```

### Q_WATER_KW

```python
Q_WATER_KW =
    (1.163888889 * CHW_FLOW_M3H * (CHW_RETURN_C - CHW_SUPPLY_C))
```

### COIL_BALANCE

```python
COIL_BALANCE =
    Q_AIR_KW / Q_WATER_KW
```

### LOAD_PCT

```python
LOAD_PCT =
    Q_AIR_KW / 83.3 * 100
```

### CHW_DT_K

```python
CHW_DT_K =
    CHW_RETURN_C - CHW_SUPPLY_C
```

### LMTD_K

```python
LMTD_K =
    np.where(
      np.abs((RETURN_AIR_C - CHW_RETURN_C) - (SUPPLY_AIR_C - CHW_SUPPLY_C))
      < 1e-06,
      (RETURN_AIR_C - CHW_RETURN_C),
      ((RETURN_AIR_C - CHW_RETURN_C) - (SUPPLY_AIR_C - CHW_SUPPLY_C))
      / np.log(
          (RETURN_AIR_C - CHW_RETURN_C) / (SUPPLY_AIR_C - CHW_SUPPLY_C)
        )
    )
```

### UA_MEASURED_KW_K

```python
UA_MEASURED_KW_K =
    (
      Q_WATER_KW
      / np.where(
          np.abs(
            (RETURN_AIR_C - CHW_RETURN_C) - (SUPPLY_AIR_C - CHW_SUPPLY_C)
          )
          < 1e-06,
          (RETURN_AIR_C - CHW_RETURN_C),
          ((RETURN_AIR_C - CHW_RETURN_C) - (SUPPLY_AIR_C - CHW_SUPPLY_C))
          / np.log(
              (RETURN_AIR_C - CHW_RETURN_C) / (SUPPLY_AIR_C - CHW_SUPPLY_C)
            )
        )
    )
```

### UA_EXPECTED_KW_K

```python
UA_EXPECTED_KW_K =
    (
      8.46453728
      * (AIRFLOW_M3H / 20000) ** 0.6
      * (CHW_FLOW_M3H / 11.01083165) ** 0.25
    )
```

### UA_RATIO

```python
UA_RATIO =
    UA_MEASURED_KW_K / UA_EXPECTED_KW_K
```

### FILTER_DP_EXPECTED_PA

```python
FILTER_DP_EXPECTED_PA =
    (60 * (AIRFLOW_M3H / 20000) ** 1.6)
```

### FILTER_LOAD_RATIO

```python
FILTER_LOAD_RATIO =
    FILTER_DP_PA / FILTER_DP_EXPECTED_PA
```

### FAN_POWER_EXPECTED_KW

```python
FAN_POWER_EXPECTED_KW =
    (
      3.4 * (AIRFLOW_M3H / 20000) ** 3
      + AIRFLOW_M3H
        / 3600
        * (FILTER_DP_PA - FILTER_DP_EXPECTED_PA)
        / 490.1960784
    )
```

### FAN_POWER_RATIO

```python
FAN_POWER_RATIO =
    FAN_POWER_KW / FAN_POWER_EXPECTED_KW
```

### SFP_W_M3S

```python
SFP_W_M3S =
    (FAN_POWER_KW * 1000 / (AIRFLOW_M3H / 3600))
```

### BYPASS_FRACTION

```python
BYPASS_FRACTION =
    ((RACK_OUTLET_C - RETURN_AIR_C) / (RACK_OUTLET_C - SUPPLY_AIR_C))
```

### RECIRC_K

```python
RECIRC_K =
    RACK_INLET_C - SUPPLY_AIR_C
```

### INLET_MARGIN_K

```python
INLET_MARGIN_K =
    27 - RACK_INLET_C
```

### DEWPOINT_RETURN_C

```python
DEWPOINT_RETURN_C =
    (
      243.04
      * (
          np.log(RETURN_RH_PCT / 100)
          + 17.625 * RETURN_AIR_C / (243.04 + RETURN_AIR_C)
        )
      / (
          17.625
          - (
              np.log(RETURN_RH_PCT / 100)
              + 17.625 * RETURN_AIR_C / (243.04 + RETURN_AIR_C)
            )
        )
    )
```

### DEWPOINT_INLET_C

```python
DEWPOINT_INLET_C =
    (
      243.04
      * (
          np.log(RACK_INLET_RH_PCT / 100)
          + 17.625 * RACK_INLET_C / (243.04 + RACK_INLET_C)
        )
      / (
          17.625
          - (
              np.log(RACK_INLET_RH_PCT / 100)
              + 17.625 * RACK_INLET_C / (243.04 + RACK_INLET_C)
            )
        )
    )
```

## AlertExpression rules (14)

### CRAH_INLET_ALLOWABLE

Critical

```python
CRAH_INLET_ALLOWABLE =
    RACK_INLET_C > 32
```

### CRAH_INLET_HIGH

High · recirculation

```python
CRAH_INLET_HIGH =
    (RACK_INLET_C > 27) & (RACK_INLET_C <= 32)
```

### CRAH_VALVE_SATURATED

High · coil_fouling

```python
CRAH_VALVE_SATURATED =
    (VALVE_POS_PCT >= 95) & (SUPPLY_AIR_C - SUPPLY_SETPOINT_C > 1.5)
```

### CRAH_DEWPOINT_HIGH

High · humidity_sensor_drift

```python
CRAH_DEWPOINT_HIGH =
    DEWPOINT_INLET_C > 15
```

### CRAH_UA_LOW

Medium · coil_fouling

```python
CRAH_UA_LOW =
    UA_RATIO < 0.75
```

### CRAH_CHW_DT_LOW

Medium · coil_fouling

```python
CRAH_CHW_DT_LOW =
    ((CHW_RETURN_C - CHW_SUPPLY_C) < 4.5) & (VALVE_POS_PCT > 50)
```

### CRAH_COIL_BALANCE

Medium · supply_sensor_drift

```python
CRAH_COIL_BALANCE =
    np.abs(COIL_BALANCE - 1) > 0.15
```

### CRAH_FILTER_DIRTY

Medium · filter_loading

```python
CRAH_FILTER_DIRTY =
    FILTER_DP_PA / FILTER_DP_EXPECTED_PA > 2
```

### CRAH_FAN_POWER_HIGH

Medium · fan_degradation

```python
CRAH_FAN_POWER_HIGH =
    FAN_POWER_KW / FAN_POWER_EXPECTED_KW > 1.2
```

### CRAH_BYPASS_HIGH

Medium · bypass_air

```python
CRAH_BYPASS_HIGH =
    BYPASS_FRACTION > 0.25
```

### CRAH_RECIRC_HIGH

Medium · recirculation

```python
CRAH_RECIRC_HIGH =
    (RACK_INLET_C - SUPPLY_AIR_C) > 5
```

### CRAH_VALVE_HUNTING

Medium · valve_hunting

```python
CRAH_VALVE_HUNTING =
    VALVE_REVERSALS_H > 30
```

### CRAH_RH_SENSOR_MISMATCH

Medium · humidity_sensor_drift

```python
CRAH_RH_SENSOR_MISMATCH =
    np.abs(DEWPOINT_RETURN_C - DEWPOINT_INLET_C) > 2.5
```

### CRAH_SFP_HIGH

Low · bypass_air

```python
CRAH_SFP_HIGH =
    SFP_W_M3S > 550
```
