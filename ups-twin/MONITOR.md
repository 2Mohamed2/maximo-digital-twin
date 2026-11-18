# UPS-6101: Maximo Monitor functions and alert rules

Device type `UPS_DOUBLE_CONVERSION`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### LOAD_PCT

```python
LOAD_PCT =
    OUTPUT_POWER_KW / 150 * 100
```

### EFF_MEASURED_PCT

```python
EFF_MEASURED_PCT =
    OUTPUT_POWER_KW / INPUT_POWER_KW * 100
```

### LOSS_MEASURED_KW

```python
LOSS_MEASURED_KW =
    (INPUT_POWER_KW - OUTPUT_POWER_KW)
```

### LOSS_EXPECTED_KW

```python
LOSS_EXPECTED_KW =
    (
      np.maximum(UPM_ONLINE, 1) * 0.196472499
      + 0.015974078 * OUTPUT_POWER_KW
      + 0.000400792 * OUTPUT_POWER_KW ** 2 / np.maximum(UPM_ONLINE, 1)
    )
```

### EFF_EXPECTED_PCT

```python
EFF_EXPECTED_PCT =
    OUTPUT_POWER_KW / (OUTPUT_POWER_KW + LOSS_EXPECTED_KW) * 100
```

### LOSS_RATIO

```python
LOSS_RATIO =
    LOSS_MEASURED_KW / LOSS_EXPECTED_KW
```

### LOSS_ESS_KW

```python
LOSS_ESS_KW =
    (0.25 + 0.005 * OUTPUT_POWER_KW)
```

### ESS_SAVING_MWH_Y

```python
ESS_SAVING_MWH_Y =
    (LOSS_EXPECTED_KW - (0.25 + 0.005 * OUTPUT_POWER_KW)) * 8.76
```

### PHASE_IMBALANCE_PCT

```python
PHASE_IMBALANCE_PCT =
    (
      3
      * np.maximum(
          np.maximum(OUTPUT_CURRENT_L1_A, OUTPUT_CURRENT_L2_A),
          OUTPUT_CURRENT_L3_A
        )
      / (OUTPUT_CURRENT_L1_A + OUTPUT_CURRENT_L2_A + OUTPUT_CURRENT_L3_A)
      - 1
    )
    * 100
```

### PHASE_MAX_KW

```python
PHASE_MAX_KW =
    (
      OUTPUT_POWER_KW
      * np.maximum(
          np.maximum(OUTPUT_CURRENT_L1_A, OUTPUT_CURRENT_L2_A),
          OUTPUT_CURRENT_L3_A
        )
      / (OUTPUT_CURRENT_L1_A + OUTPUT_CURRENT_L2_A + OUTPUT_CURRENT_L3_A)
    )
```

### REDUNDANCY_MARGIN_KW

```python
REDUNDANCY_MARGIN_KW =
    ((np.round(np.maximum(UPM_ONLINE, 1)) - 1) * 50 - 3 * PHASE_MAX_KW)
```

### HEATSINK_RISE_K

```python
HEATSINK_RISE_K =
    (HEATSINK_TEMP_MAX_C - INLET_AIR_C)
```

### HEATSINK_RISE_EXPECTED_K

```python
HEATSINK_RISE_EXPECTED_K =
    (15 * LOSS_MEASURED_KW / np.maximum(UPM_ONLINE, 1))
```

### FAN_SPEED_RATIO

```python
FAN_SPEED_RATIO =
    FAN_SPEED_PCT / np.maximum(FAN_CMD_PCT, 1)
```

### DC_RIPPLE_RATIO

```python
DC_RIPPLE_RATIO =
    (
      DC_RIPPLE_V
      / (1 + 3 * OUTPUT_POWER_KW / np.maximum(UPM_ONLINE, 1) / 50)
    )
```

### BATT_R_RATIO

```python
BATT_R_RATIO =
    BATTERY_R_MAX_MOHM / 3
```

### BATT_BLOCK_W

```python
BATT_BLOCK_W =
    (OUTPUT_POWER_KW * 1000 / 0.975 / 80)
```

### AUTONOMY_MIN

```python
AUTONOMY_MIN =
    np.exp(
      np.interp(
        np.log(
          np.maximum(
            BATT_BLOCK_W / (np.maximum(BATTERY_SOH_PCT, 1) / 100),
            1e-06
          )
        ),
        [6.48157712928, 6.78558764501, 7.00124562207, 7.30518821539, 7.57198844938, 7.76131918095, 7.95892649305, 8.06777619578, 8.17611034224, 8.22577079935, 8.28652137368, 8.43010908451],
        [4.49980967033, 4.09434456222, 3.80666248977, 3.40119738166, 2.99573227355, 2.7080502011, 2.30258509299, 2.07944154168, 1.79175946923, 1.60943791243, 1.38629436112, 0.69314718056]
      )
    )
```

### BATT_AGEING_FACTOR

```python
BATT_AGEING_FACTOR =
    2 ** ((BATTERY_TEMP_C - 25) / 8)
```

### BATT_LIFE_REMAINING_Y

```python
BATT_LIFE_REMAINING_Y =
    10 * 2 ** (-np.maximum(BATTERY_TEMP_LIFE_C - 25, 0) / 8)
    - BATTERY_AGE_DAYS / 365
```

## AlertExpression rules (15)

### UPS_ON_BATTERY

High

```python
UPS_ON_BATTERY =
    np.abs(UPS_MODE - 4) < 0.5
```

### UPS_ON_BYPASS

High

```python
UPS_ON_BYPASS =
    np.abs(UPS_MODE - 3) < 0.5
```

### UPS_AUTONOMY_SHORT

High · battery_ageing

```python
UPS_AUTONOMY_SHORT =
    np.exp(
      np.interp(
        np.log(
          np.maximum(
            BATT_BLOCK_W / (np.maximum(BATTERY_SOH_PCT, 1) / 100),
            1e-06
          )
        ),
        [6.48157712928, 6.78558764501, 7.00124562207, 7.30518821539, 7.57198844938, 7.76131918095, 7.95892649305, 8.06777619578, 8.17611034224, 8.22577079935, 8.28652137368, 8.43010908451],
        [4.49980967033, 4.09434456222, 3.80666248977, 3.40119738166, 2.99573227355, 2.7080502011, 2.30258509299, 2.07944154168, 1.79175946923, 1.60943791243, 1.38629436112, 0.69314718056]
      )
    )
    < 10
```

### UPS_REDUNDANCY_LOST

High · upm_failure

```python
UPS_REDUNDANCY_LOST =
    REDUNDANCY_MARGIN_KW < 0
```

### UPS_DC_RIPPLE_LIMIT

High · dc_capacitor_ageing

```python
UPS_DC_RIPPLE_LIMIT =
    DC_RIPPLE_RATIO > 2.4
```

### UPS_MODULE_OFFLINE

Medium · upm_failure

```python
UPS_MODULE_OFFLINE =
    UPM_ONLINE < 3.5
```

### UPS_PHASE_IMBALANCE

Medium · phase_load_growth

```python
UPS_PHASE_IMBALANCE =
    (
      3
      * np.maximum(
          np.maximum(OUTPUT_CURRENT_L1_A, OUTPUT_CURRENT_L2_A),
          OUTPUT_CURRENT_L3_A
        )
      / (OUTPUT_CURRENT_L1_A + OUTPUT_CURRENT_L2_A + OUTPUT_CURRENT_L3_A)
      - 1
    )
    * 100
    > 10
```

### UPS_DC_RIPPLE_HIGH

Medium · dc_capacitor_ageing

```python
UPS_DC_RIPPLE_HIGH =
    (DC_RIPPLE_RATIO > 1.6) & (DC_RIPPLE_RATIO <= 2.4)
```

### UPS_FAN_SLOW

Medium · fan_wear

```python
UPS_FAN_SLOW =
    FAN_SPEED_PCT / np.maximum(FAN_CMD_PCT, 1) < 0.85
```

### UPS_HEATSINK_RISE_HIGH

Medium · fan_wear

```python
UPS_HEATSINK_RISE_HIGH =
    (HEATSINK_RISE_K - HEATSINK_RISE_EXPECTED_K) > 6
```

### UPS_EFFICIENCY_LOW

Medium · converter_losses

```python
UPS_EFFICIENCY_LOW =
    (np.abs(UPS_MODE - 1) < 0.5)
    & (LOSS_MEASURED_KW / LOSS_EXPECTED_KW > 1.3)
```

### UPS_BATT_R_HIGH

Medium · battery_ageing

```python
UPS_BATT_R_HIGH =
    BATTERY_R_MAX_MOHM / 3 > 1.3
```

### UPS_BATT_SOH_LOW

Medium · battery_ageing

```python
UPS_BATT_SOH_LOW =
    BATTERY_SOH_PCT < 80
```

### UPS_BATT_TEMP_HIGH

Medium · battery_room_hot

```python
UPS_BATT_TEMP_HIGH =
    BATTERY_TEMP_C > 30
```

### UPS_BYPASS_EVENTS

Medium · bypass_transfers

```python
UPS_BYPASS_EVENTS =
    BYPASS_EVENTS_30D > 2
```
