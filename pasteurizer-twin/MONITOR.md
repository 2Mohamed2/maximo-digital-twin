# PS-6801: Maximo Monitor functions and alert rules

Device type `HTST_PASTEURIZER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### HOLD_TIME_S

```python
HOLD_TIME_S =
    (150001.2 / FLOW_L_H)
```

### HOLD_TIME_MARGIN_S

```python
HOLD_TIME_MARGIN_S =
    (150001.2 / FLOW_L_H) - 15
```

### HOLD_TEMP_MARGIN_K

```python
HOLD_TEMP_MARGIN_K =
    np.minimum(HOLD_OUT_C, HOLD_REF_C) - 72
```

### HOLD_TUBE_LOSS_K

```python
HOLD_TUBE_LOSS_K =
    HEAT_OUT_C - HOLD_REF_C
```

### STLR_OFFSET_K

```python
STLR_OFFSET_K =
    HOLD_OUT_C - HOLD_REF_C
```

### REGEN_EFF_PCT

```python
REGEN_EFF_PCT =
    ((REGEN_RAW_OUT_C - RAW_IN_C) / (HOLD_REF_C - RAW_IN_C)) * 100
```

### REGEN_EFF_EXPECTED_PCT

```python
REGEN_EFF_EXPECTED_PCT =
    (
      4500
      * (FLOW_L_H / 10000) ** 0.6
      * 14.19
      / ((0.0011266 * FLOW_L_H) * 1000)
    )
    / (
        1
        + (
            4500
            * (FLOW_L_H / 10000) ** 0.6
            * 14.19
            / ((0.0011266 * FLOW_L_H) * 1000)
          )
      )
    * 100
```

### REGEN_APPROACH_K

```python
REGEN_APPROACH_K =
    HOLD_REF_C - REGEN_RAW_OUT_C
```

### U_REGEN_RATIO

```python
U_REGEN_RATIO =
    (
      np.minimum(
        ((REGEN_RAW_OUT_C - RAW_IN_C) / (HOLD_REF_C - RAW_IN_C)),
        0.999
      )
      / (
          1
          - np.minimum(
              ((REGEN_RAW_OUT_C - RAW_IN_C) / (HOLD_REF_C - RAW_IN_C)),
              0.999
            )
        )
    )
    / (
        4500
        * (FLOW_L_H / 10000) ** 0.6
        * 14.19
        / ((0.0011266 * FLOW_L_H) * 1000)
      )
```

### HEATER_DUTY_KW

```python
HEATER_DUTY_KW =
    ((0.0011266 * FLOW_L_H) * (HEAT_OUT_C - REGEN_RAW_OUT_C))
```

### HEATER_APPROACH_K

```python
HEATER_APPROACH_K =
    HW_IN_C - HEAT_OUT_C
```

### U_HEATER_RATIO

```python
U_HEATER_RATIO =
    (
      (
        HEATER_DUTY_KW
        * 1000
        / (
            5.26
            * np.where(
                np.abs(
                  np.maximum(HW_IN_C - HEAT_OUT_C, 0.05)
                  - np.maximum(HW_OUT_C - REGEN_RAW_OUT_C, 0.05)
                )
                < 1e-09,
                np.maximum(HW_IN_C - HEAT_OUT_C, 0.05),
                (
                  np.maximum(HW_IN_C - HEAT_OUT_C, 0.05)
                  - np.maximum(HW_OUT_C - REGEN_RAW_OUT_C, 0.05)
                )
                / np.log(
                    np.maximum(HW_IN_C - HEAT_OUT_C, 0.05)
                    / np.maximum(HW_OUT_C - REGEN_RAW_OUT_C, 0.05)
                  )
              )
          )
      )
      / (5000 * (FLOW_L_H / 10000) ** 0.35)
    )
```

### DP_HEATER_RATIO

```python
DP_HEATER_RATIO =
    (DP_HEATER_BAR / (0.6 * (FLOW_L_H / 10000) ** 1.8))
```

### DP_REGEN_RATIO

```python
DP_REGEN_RATIO =
    (DP_REGEN_BAR / (0.3 * (FLOW_L_H / 10000) ** 1.8))
```

### PRESSURE_DIFF_BAR

```python
PRESSURE_DIFF_BAR =
    (P_PAST_REGEN_OUT_BAR - P_RAW_REGEN_IN_BAR)
```

### CIP_DP_RECOVERY

```python
CIP_DP_RECOVERY =
    (RUN_START_DP_HEATER_BAR / (0.6 * (RUN_START_FLOW_L_H / 10000) ** 1.8))
```

### STEAM_EXPECTED_KG_H

```python
STEAM_EXPECTED_KG_H =
    (HEATER_DUTY_KW * 3600 / (2133 * 0.95))
```

### STEAM_PER_M3_KG

```python
STEAM_PER_M3_KG =
    (STEAM_KG_H / (FLOW_L_H / 1000))
```

### ENERGY_KJ_PER_L

```python
ENERGY_KJ_PER_L =
    (
      HEATER_DUTY_KW
      + ((0.0011266 * FLOW_L_H) * (REGEN_PAST_OUT_C - PRODUCT_OUT_C))
    )
    * 3600
    / FLOW_L_H
```

## AlertExpression rules (15)

### PAST_UNDERTEMP_FORWARD

Critical

```python
PAST_UNDERTEMP_FORWARD =
    (np.minimum(HOLD_OUT_C, HOLD_REF_C) < 72) & (FDD_FORWARD > 0.5)
```

### PAST_HOLD_TIME_SHORT

Critical · flow_timing_drift

```python
PAST_HOLD_TIME_SHORT =
    ((150001.2 / FLOW_L_H) < 15) & (FDD_FORWARD > 0.5)
```

### PAST_PRESSURE_DIFF_LOW

Critical · pressure_diff_loss

```python
PAST_PRESSURE_DIFF_LOW =
    PRESSURE_DIFF_BAR < 0.069
```

### PAST_DIVERT_FREQUENT

High · heating_unstable

```python
PAST_DIVERT_FREQUENT =
    FDD_DIVERTS_1H >= 3
```

### PAST_STLR_MISMATCH

High · stlr_drift

```python
PAST_STLR_MISMATCH =
    (HOLD_OUT_C - HOLD_REF_C) > 0.3
```

### PAST_RUN_OVERDUE

High · cip_skipped

```python
PAST_RUN_OVERDUE =
    HOURS_SINCE_CIP > 10
```

### PAST_HOLD_MARGIN_LOW

Medium · flow_timing_drift

```python
PAST_HOLD_MARGIN_LOW =
    ((150001.2 / FLOW_L_H) >= 15) & ((150001.2 / FLOW_L_H) < 15.5)
```

### PAST_TEMP_MARGIN_LOW

Medium · heating_unstable

```python
PAST_TEMP_MARGIN_LOW =
    (HOLD_TEMP_MARGIN_K >= 0) & (HOLD_TEMP_MARGIN_K < 1)
```

### PAST_PRESSURE_MARGIN_LOW

Medium · pressure_diff_loss

```python
PAST_PRESSURE_MARGIN_LOW =
    (PRESSURE_DIFF_BAR >= 0.069) & (PRESSURE_DIFF_BAR < 0.3)
```

### PAST_HEATER_FOULING

Medium · heater_fouling

```python
PAST_HEATER_FOULING =
    U_HEATER_RATIO < 0.7
```

### PAST_HEATER_DP_HIGH

Medium · heater_fouling

```python
PAST_HEATER_DP_HIGH =
    DP_HEATER_RATIO > 1.5
```

### PAST_REGEN_EFF_LOW

Medium · regen_fouling

```python
PAST_REGEN_EFF_LOW =
    REGEN_EFF_PCT
    < (
        (
          4500
          * (FLOW_L_H / 10000) ** 0.6
          * 14.19
          / ((0.0011266 * FLOW_L_H) * 1000)
        )
        / (
            1
            + (
                4500
                * (FLOW_L_H / 10000) ** 0.6
                * 14.19
                / ((0.0011266 * FLOW_L_H) * 1000)
              )
          )
        * 100
        - 4
      )
```

### PAST_REGEN_DP_HIGH

Medium · regen_fouling

```python
PAST_REGEN_DP_HIGH =
    DP_REGEN_RATIO > 1.5
```

### PAST_CIP_INEFFECTIVE

Medium · cip_incomplete

```python
PAST_CIP_INEFFECTIVE =
    CIP_DP_RECOVERY > 1.15
```

### PAST_ENERGY_HIGH

Low · regen_fouling

```python
PAST_ENERGY_HIGH =
    STEAM_PER_M3_KG > 27.75773
```
