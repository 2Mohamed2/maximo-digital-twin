# BFP-3301: Maximo Monitor functions and alert rules

Device type `BOILER_FEED_PUMP`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### BEP_RATIO

```python
BEP_RATIO =
    (SUCTION_FLOW_M3H / ((np.maximum(SPEED_RPM, 1) / 5300) * 520))
```

### HEAD_MEASURED_M

```python
HEAD_MEASURED_M =
    (
      (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR)
      * 100000
      / (
          (913 - 0.98 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160))
          * 9.81
        )
    )
```

### HEAD_EXPECTED_M

```python
HEAD_EXPECTED_M =
    (
      2520 * (np.maximum(SPEED_RPM, 1) / 5300) ** 2
      - 0.0017381657 * SUCTION_FLOW_M3H ** 2
    )
```

### HEAD_RATIO

```python
HEAD_RATIO =
    HEAD_MEASURED_M / HEAD_EXPECTED_M
```

### TEMP_RISE_K

```python
TEMP_RISE_K =
    (DISCHARGE_TEMP_C - SUCTION_TEMP_C)
```

### EFF_THERMO_PCT

```python
EFF_THERMO_PCT =
    100
    * (
        (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR)
        * 100000
        / (913 - 0.98 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160))
        / (
            (
              0.0005973
              - 3.28e-06 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160)
            )
            * (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR)
            * 100000
            + (
                4303.7
                + 2.74 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160)
              )
              * TEMP_RISE_K
          )
      )
```

### EFF_EXPECTED_PCT

```python
EFF_EXPECTED_PCT =
    100 * (0.81 * (2 * BEP_RATIO - BEP_RATIO ** 2))
```

### EFF_RATIO

```python
EFF_RATIO =
    (
      (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR)
      * 100000
      / (913 - 0.98 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160))
      / (
          (
            0.0005973
            - 3.28e-06 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160)
          )
          * (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR)
          * 100000
          + (
              4303.7
              + 2.74 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160)
            )
            * TEMP_RISE_K
        )
    )
    / np.maximum((0.81 * (2 * BEP_RATIO - BEP_RATIO ** 2)), 0.01)
```

### SHAFT_POWER_KW

```python
SHAFT_POWER_KW =
    (MOTOR_KW * 0.955)
```

### FLOW_THERMO_M3H

```python
FLOW_THERMO_M3H =
    (
      (MOTOR_KW * 0.955)
      * 1000
      * (
          (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR)
          * 100000
          / (913 - 0.98 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160))
          / (
              (
                0.0005973
                - 3.28e-06
                  * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160)
              )
              * (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR)
              * 100000
              + (
                  4303.7
                  + 2.74 * (((SUCTION_TEMP_C + DISCHARGE_TEMP_C) / 2) - 160)
                )
                * TEMP_RISE_K
            )
        )
      / np.maximum(
          (DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR) * 100000,
          1
        )
      * 3600
    )
```

### FLOW_METER_RATIO

```python
FLOW_METER_RATIO =
    SUCTION_FLOW_M3H / np.maximum(FLOW_THERMO_M3H, 1)
```

### LEAKOFF_EXPECTED_M3H

```python
LEAKOFF_EXPECTED_M3H =
    np.maximum(
      15
      * np.sqrt(
          np.maximum((DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR), 0)
          / 183
        ),
      0.1
    )
```

### LEAKOFF_RATIO

```python
LEAKOFF_RATIO =
    LEAKOFF_FLOW_M3H
    / np.maximum(
        15
        * np.sqrt(
            np.maximum((DISCHARGE_PRESSURE_BAR - SUCTION_PRESSURE_BAR), 0)
            / 183
          ),
        0.1
      )
```

### MIN_FLOW_M3H

```python
MIN_FLOW_M3H =
    (182 * (np.maximum(SPEED_RPM, 1) / 5300))
```

### NPSH_AVAILABLE_M

```python
NPSH_AVAILABLE_M =
    (
      (
        SUCTION_PRESSURE_BAR
        + 1.01325
        - (
            np.power(10, 8.14019 - 1810.94 / (244.485 + SUCTION_TEMP_C))
            * 0.00133322
          )
      )
      * 100000
      / ((913 - 0.98 * (SUCTION_TEMP_C - 160)) * 9.81)
    )
```

### NPSHA_DEAERATOR_M

```python
NPSHA_DEAERATOR_M =
    (
      (
        DA_PRESSURE_BAR
        + 1.01325
        - (
            np.power(10, 8.14019 - 1810.94 / (244.485 + SUCTION_TEMP_C))
            * 0.00133322
          )
      )
      * 100000
      / ((913 - 0.98 * (SUCTION_TEMP_C - 160)) * 9.81)
      + 25
      + DA_LEVEL_M
      - 4.4378698e-06 * SUCTION_FLOW_M3H ** 2
    )
```

### NPSH3_M

```python
NPSH3_M =
    (
      (np.maximum(SPEED_RPM, 1) / 5300) ** 2
      * 14
      * (0.5 + 0.5 * BEP_RATIO ** 2)
    )
```

### NPSH_RATIO

```python
NPSH_RATIO =
    NPSH_AVAILABLE_M / NPSH3_M
```

### THRUST_EXCESS_K

```python
THRUST_EXCESS_K =
    (
      THRUST_BEARING_C
      - LUBE_OIL_C
      - 30 * (np.maximum(SPEED_RPM, 1) / 5300) ** 2
    )
```

### JOURNAL_EXCESS_K

```python
JOURNAL_EXCESS_K =
    (
      np.maximum(BEARING_DE_C, BEARING_NDE_C)
      - LUBE_OIL_C
      - 22 * (np.maximum(SPEED_RPM, 1) / 5300) ** 2
    )
```

## AlertExpression rules (15)

### BFP_MIN_FLOW_LOW

High · minflow_valve_stuck

```python
BFP_MIN_FLOW_LOW =
    (RUNNING > 0.5) & (SUCTION_FLOW_M3H < MIN_FLOW_M3H)
```

### BFP_NPSH_MARGIN_LIMIT

High · npsh_loss

```python
BFP_NPSH_MARGIN_LIMIT =
    (RUNNING > 0.5) & (NPSH_RATIO < 1.2)
```

### BFP_LEAKOFF_LIMIT

High · balance_drum_wear

```python
BFP_LEAKOFF_LIMIT =
    (RUNNING > 0.5) & (LEAKOFF_RATIO >= 2)
```

### BFP_EFF_LOSS_HIGH

High · impeller_wear

```python
BFP_EFF_LOSS_HIGH =
    (RUNNING > 0.5) & (SUCTION_FLOW_M3H >= MIN_FLOW_M3H) & (EFF_RATIO < 0.9)
```

### BFP_VIBRATION_LIMIT

High · bearing_degradation

```python
BFP_VIBRATION_LIMIT =
    VIBRATION_MM_S >= 7.1
```

### BFP_HEAD_LOW

Medium · impeller_wear

```python
BFP_HEAD_LOW =
    (RUNNING > 0.5)
    & (SUCTION_FLOW_M3H >= MIN_FLOW_M3H)
    & (HEAD_RATIO < 0.95)
```

### BFP_EFF_LOW

Medium · impeller_wear

```python
BFP_EFF_LOW =
    (RUNNING > 0.5)
    & (SUCTION_FLOW_M3H >= MIN_FLOW_M3H)
    & (EFF_RATIO >= 0.9)
    & (EFF_RATIO < 0.95)
```

### BFP_LEAKOFF_HIGH

Medium · balance_drum_wear

```python
BFP_LEAKOFF_HIGH =
    (RUNNING > 0.5) & (LEAKOFF_RATIO >= 1.5) & (LEAKOFF_RATIO < 2)
```

### BFP_NPSH_MARGIN_LOW

Medium · strainer_clogging

```python
BFP_NPSH_MARGIN_LOW =
    (RUNNING > 0.5) & (NPSH_RATIO >= 1.2) & (NPSH_RATIO < 1.5)
```

### BFP_STRAINER_DP_HIGH

Medium · strainer_clogging

```python
BFP_STRAINER_DP_HIGH =
    STRAINER_DP_BAR > 0.5
```

### BFP_RECIRC_PASSING

Medium · recirc_valve_passing

```python
BFP_RECIRC_PASSING =
    (RECIRC_VALVE_PCT < 2) & (RECIRC_FLOW_M3H > 20)
```

### BFP_FLOW_MISMATCH

Medium · flow_meter_drift

```python
BFP_FLOW_MISMATCH =
    (RUNNING > 0.5)
    & (SUCTION_FLOW_M3H >= MIN_FLOW_M3H)
    & (np.abs(FLOW_METER_RATIO - 1) > 0.08)
```

### BFP_THRUST_TEMP_HIGH

Medium · balance_drum_wear

```python
BFP_THRUST_TEMP_HIGH =
    THRUST_EXCESS_K > 10
```

### BFP_JOURNAL_TEMP_HIGH

Medium · bearing_degradation

```python
BFP_JOURNAL_TEMP_HIGH =
    JOURNAL_EXCESS_K > 10
```

### BFP_VIBRATION_HIGH

Medium · npsh_loss

```python
BFP_VIBRATION_HIGH =
    (VIBRATION_MM_S >= 4.5) & (VIBRATION_MM_S < 7.1)
```
