# EV-7001: Maximo Monitor functions and alert rules

Device type `EV_CHARGER_DC`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### DC_POWER_KW

```python
DC_POWER_KW =
    (
      (
        DC_VOLTAGE_C1_V * DC_CURRENT_C1_A
        + DC_VOLTAGE_C2_V * DC_CURRENT_C2_A
      )
      / 1000
    )
```

### LOSS_KW

```python
LOSS_KW =
    (AC_INPUT_KW - DC_POWER_KW)
```

### LOSS_EXPECTED_KW

```python
LOSS_EXPECTED_KW =
    (
      0.43847 * np.maximum(STACKS_ACTIVE, 1)
      + 0.000191568 * DC_POWER_KW ** 2 / np.maximum(STACKS_ACTIVE, 1)
    )
```

### EFFICIENCY_PCT

```python
EFFICIENCY_PCT =
    100 * DC_POWER_KW / np.maximum(AC_INPUT_KW, 0.001)
```

### EFFICIENCY_EXPECTED_PCT

```python
EFFICIENCY_EXPECTED_PCT =
    100 * DC_POWER_KW / (DC_POWER_KW + LOSS_EXPECTED_KW)
```

### LOSS_RATIO

```python
LOSS_RATIO =
    (LOSS_KW / LOSS_EXPECTED_KW)
```

### STACK_RISE_EXPECTED_K

```python
STACK_RISE_EXPECTED_K =
    (12 * np.maximum(LOSS_KW, 0) / np.maximum(STACKS_ACTIVE, 1))
```

### STACK_RISE_RATIO

```python
STACK_RISE_RATIO =
    (
      (STACK_TEMP_MAX_C - AMBIENT_C)
      / np.maximum(STACK_RISE_EXPECTED_K, 0.5)
    )
```

### POWER_AVAILABLE_KW

```python
POWER_AVAILABLE_KW =
    STACKS_AVAILABLE * 100
```

### CABLE_HEAT_W

```python
CABLE_HEAT_W =
    ((DC_CURRENT_C1_A ** 2 + DC_CURRENT_C2_A ** 2) * 0.0039)
```

### COOLANT_RISE_EXPECTED_K

```python
COOLANT_RISE_EXPECTED_K =
    (
      CABLE_HEAT_W
      / (2 * np.maximum(COOLANT_FLOW_LPM, 0.1) * 0.0178333333 * 3350)
    )
```

### COOLANT_RISE_RATIO

```python
COOLANT_RISE_RATIO =
    (COOLANT_RETURN_C - COOLANT_SUPPLY_C)
    / np.maximum(COOLANT_RISE_EXPECTED_K, 0.5)
```

### CONTACT_RATIO_C1

```python
CONTACT_RATIO_C1 =
    (
      (CONTACT_TEMP_C1_C - COOLANT_RETURN_C)
      / (120 * (np.maximum(DC_CURRENT_C1_A, 150) / 1000) ** 2)
    )
```

### CONTACT_RATIO_C2

```python
CONTACT_RATIO_C2 =
    (
      (CONTACT_TEMP_C2_C - COOLANT_RETURN_C)
      / (120 * (np.maximum(DC_CURRENT_C2_A, 150) / 1000) ** 2)
    )
```

### INSULATION_OHM_PER_V

```python
INSULATION_OHM_PER_V =
    (INSULATION_KOHM * 1000 / 1000)
```

### START_SUCCESS_PCT

```python
START_SUCCESS_PCT =
    (
      100
      * (
          STARTS_ATTEMPTED_24H
          - STARTS_FAILED_COMM_24H
          - STARTS_FAILED_AUTH_24H
          - STARTS_FAILED_SAFETY_24H
          - STARTS_FAILED_OTHER_24H
          - SESSIONS_ABORTED_24H
        )
      / np.maximum(STARTS_ATTEMPTED_24H, 1)
    )
```

### FAIL_COMM_PCT

```python
FAIL_COMM_PCT =
    (100 * STARTS_FAILED_COMM_24H / np.maximum(STARTS_ATTEMPTED_24H, 1))
```

### FAIL_AUTH_PCT

```python
FAIL_AUTH_PCT =
    (100 * STARTS_FAILED_AUTH_24H / np.maximum(STARTS_ATTEMPTED_24H, 1))
```

### UPTIME_PCT

```python
UPTIME_PCT =
    ((525600 - (OUTAGE_MIN_365D - OUTAGE_EXCLUDED_MIN_365D)) / 525600 * 100)
```

### METER_DEV_PCT

```python
METER_DEV_PCT =
    (
      100
      * (LAST_SESSION_METER_KWH - LAST_SESSION_INTERNAL_KWH)
      / np.maximum(LAST_SESSION_INTERNAL_KWH, 0.1)
    )
```

## AlertExpression rules (15)

### CHG_INSULATION_FAULT

Critical · insulation_degradation

```python
CHG_INSULATION_FAULT =
    (INSULATION_KOHM * 1000 / 1000) < 100
```

### CHG_CONTACTOR_WELDED

Critical · contactor_welded

```python
CHG_CONTACTOR_WELDED =
    CONTACTOR_WELD > 0.5
```

### CHG_STACK_DERATED

High · power_stack_failure

```python
CHG_STACK_DERATED =
    STACKS_AVAILABLE < 3.5
```

### CHG_COOLANT_FLOW_LOW

High · coolant_flow_low

```python
CHG_COOLANT_FLOW_LOW =
    COOLANT_FLOW_LPM < 1.4
```

### CHG_CONTACT_TEMP_HIGH

High · contact_wear

```python
CHG_CONTACT_TEMP_HIGH =
    np.maximum(CONTACT_TEMP_C1_C, CONTACT_TEMP_C2_C) > 80
```

### CHG_UPTIME_LOW

High · contactor_welded

```python
CHG_UPTIME_LOW =
    UPTIME_PCT < 97
```

### CHG_SUCCESS_LOW

High

```python
CHG_SUCCESS_LOW =
    (STARTS_ATTEMPTED_24H >= 10) & (START_SUCCESS_PCT < 90)
```

### CHG_PAYMENT_OFFLINE

High · payment_backend_fault

```python
CHG_PAYMENT_OFFLINE =
    (PAYMENT_TERMINAL_OK < 0.5) | (OCPP_HEARTBEAT_AGE_S > 300)
```

### CHG_EFFICIENCY_LOW

Medium · stack_cooling_ageing

```python
CHG_EFFICIENCY_LOW =
    (DC_POWER_KW >= 50) & (LOSS_RATIO > 1.35)
```

### CHG_STACK_HOT

Medium · stack_cooling_ageing

```python
CHG_STACK_HOT =
    (DC_POWER_KW >= 50) & (STACK_RISE_RATIO > 1.4)
```

### CHG_CONTACT_WEAR

Medium · contact_wear

```python
CHG_CONTACT_WEAR =
    np.maximum(CONTACT_RATIO_C1, CONTACT_RATIO_C2) > 1.6
```

### CHG_INSULATION_WARN

Medium · insulation_degradation

```python
CHG_INSULATION_WARN =
    ((INSULATION_KOHM * 1000 / 1000) >= 100)
    & ((INSULATION_KOHM * 1000 / 1000) < 500)
```

### CHG_FAIL_COMM

Medium · vehicle_comm_failures

```python
CHG_FAIL_COMM =
    (STARTS_ATTEMPTED_24H >= 10) & (FAIL_COMM_PCT > 8)
```

### CHG_FAIL_AUTH

Medium · payment_backend_fault

```python
CHG_FAIL_AUTH =
    (STARTS_ATTEMPTED_24H >= 10) & (FAIL_AUTH_PCT > 8)
```

### CHG_METER_DEVIATION

Medium

```python
CHG_METER_DEVIATION =
    np.abs(METER_DEV_PCT) > 1
```
