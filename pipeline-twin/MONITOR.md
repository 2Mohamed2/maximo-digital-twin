# PIPE-1501: Maximo Monitor functions and alert rules

Device type `TRANSMISSION_MAIN`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (27)

### VELOCITY_MS

```python
VELOCITY_MS =
    ((FLOW_IN_M3H.clip(lower=1) / 3600) / 1.16095172045)
```

### REYNOLDS

```python
REYNOLDS =
    (
      VELOCITY_MS
      * 1.2158
      / (
          1.792e-06
          / (1 + 0.0337 * WATER_TEMP_C + 0.000221 * WATER_TEMP_C ** 2)
        )
    )
```

### FRICTION_FACTOR

```python
FRICTION_FACTOR =
    (0.25 / np.log10(2.2229829764e-05 + 5.74 / REYNOLDS ** 0.9) ** 2)
```

### HEADLOSS_EXPECTED_M

```python
HEADLOSS_EXPECTED_M =
    ((FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 14000)
```

### HEADLOSS_MEASURED_M

```python
HEADLOSS_MEASURED_M =
    ((32 + PRESSURE_PS_BAR / 0.09789) - (124 + PRESSURE_RES_BAR / 0.09789))
```

### HEADLOSS_RATIO

```python
HEADLOSS_RATIO =
    HEADLOSS_MEASURED_M / HEADLOSS_EXPECTED_M
```

### C_EFFECTIVE

```python
C_EFFECTIVE =
    (
      (
        149380
        * (FLOW_IN_M3H.clip(lower=1) / 3600) ** 1.852
        / (HEADLOSS_MEASURED_M.clip(lower=0.01) * 2.59007632414)
      )
      ** (1 / 1.852)
    )
```

### C_DESIGN

```python
C_DESIGN =
    (
      (
        149380
        * (FLOW_IN_M3H.clip(lower=1) / 3600) ** 1.852
        / (HEADLOSS_EXPECTED_M * 2.59007632414)
      )
      ** (1 / 1.852)
    )
```

### K_EFFECTIVE_MM

```python
K_EFFECTIVE_MM =
    (
      1000
      * 4.49846
      * (
          10
          ** (
               -0.5
               / np.sqrt(
                   (
                     HEADLOSS_MEASURED_M.clip(lower=0.01)
                     * 23.84585014
                     / (14000 * VELOCITY_MS ** 2)
                   )
                 )
             )
          - 5.74 / REYNOLDS ** 0.9
        )
    ).clip(lower=0)
```

### IMBALANCE_PCT

```python
IMBALANCE_PCT =
    ((FLOW_IN_M3H - FLOW_OUT_M3H) / FLOW_IN_M3H.clip(lower=1) * 100)
```

### IMBALANCE_M3H

```python
IMBALANCE_M3H =
    FLOW_IN_M3H - FLOW_OUT_M3H
```

### P_EXP_PT1_BAR

```python
P_EXP_PT1_BAR =
    (
      PRESSURE_PS_BAR
      + (
          32
          - 58
          - (FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 3500
        )
        * 0.09789
    )
```

### P_EXP_PT2_BAR

```python
P_EXP_PT2_BAR =
    (
      PRESSURE_PS_BAR
      + (
          32
          - 71
          - (FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 7000
        )
        * 0.09789
    )
```

### P_EXP_PT3_BAR

```python
P_EXP_PT3_BAR =
    (
      PRESSURE_PS_BAR
      + (
          32
          - 79
          - (FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 10500
        )
        * 0.09789
    )
```

### P_EXP_RES_BAR

```python
P_EXP_RES_BAR =
    (
      PRESSURE_PS_BAR
      + (
          32
          - 124
          - (FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 14000
        )
        * 0.09789
    )
```

### RES_PT1_BAR

```python
RES_PT1_BAR =
    PRESSURE_PT1_BAR - P_EXP_PT1_BAR
```

### RES_PT2_BAR

```python
RES_PT2_BAR =
    PRESSURE_PT2_BAR - P_EXP_PT2_BAR
```

### RES_PT3_BAR

```python
RES_PT3_BAR =
    PRESSURE_PT3_BAR - P_EXP_PT3_BAR
```

### RES_OUT_BAR

```python
RES_OUT_BAR =
    PRESSURE_RES_BAR - P_EXP_RES_BAR
```

### SLOPE_RATIO_1

```python
SLOPE_RATIO_1 =
    (
      ((32 + PRESSURE_PS_BAR / 0.09789) - (58 + PRESSURE_PT1_BAR / 0.09789))
      / ((FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 3500)
    )
```

### SLOPE_RATIO_2

```python
SLOPE_RATIO_2 =
    (
      (
        (58 + PRESSURE_PT1_BAR / 0.09789)
        - (71 + PRESSURE_PT2_BAR / 0.09789)
      )
      / ((FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 3500)
    )
```

### SLOPE_RATIO_3

```python
SLOPE_RATIO_3 =
    (
      (
        (71 + PRESSURE_PT2_BAR / 0.09789)
        - (79 + PRESSURE_PT3_BAR / 0.09789)
      )
      / ((FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 3500)
    )
```

### SLOPE_RATIO_4

```python
SLOPE_RATIO_4 =
    (
      (
        (79 + PRESSURE_PT3_BAR / 0.09789)
        - (124 + PRESSURE_RES_BAR / 0.09789)
      )
      / ((FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133) * 3500)
    )
```

### LEAK_CH_KM

```python
LEAK_CH_KM =
    (
      (
        (
          HEADLOSS_MEASURED_M
          - (
              (
                0.25
                / np.log10(
                    2.2229829764e-05
                    + 5.74
                      / (
                          (
                            (FLOW_OUT_M3H.clip(lower=1) / 3600)
                            / 1.16095172045
                          )
                          * 1.2158
                          / (
                              1.792e-06
                              / (
                                  1
                                  + 0.0337 * WATER_TEMP_C
                                  + 0.000221 * WATER_TEMP_C ** 2
                                )
                            )
                        )
                        ** 0.9
                  )
                  ** 2
              )
              / 1.2158
              * ((FLOW_OUT_M3H.clip(lower=1) / 3600) / 1.16095172045) ** 2
              / 19.6133
            )
            * 14000
        )
        / (
            (FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133)
            - (
                (
                  0.25
                  / np.log10(
                      2.2229829764e-05
                      + 5.74
                        / (
                            (
                              (FLOW_OUT_M3H.clip(lower=1) / 3600)
                              / 1.16095172045
                            )
                            * 1.2158
                            / (
                                1.792e-06
                                / (
                                    1
                                    + 0.0337 * WATER_TEMP_C
                                    + 0.000221 * WATER_TEMP_C ** 2
                                  )
                              )
                          )
                          ** 0.9
                    )
                    ** 2
                )
                / 1.2158
                * ((FLOW_OUT_M3H.clip(lower=1) / 3600) / 1.16095172045) ** 2
                / 19.6133
              )
          ).clip(lower=1e-09)
      )
      / 1000
    ).clip(lower=0, upper=14)
```

### LEAK_SIGNAL_BAR

```python
LEAK_SIGNAL_BAR =
    (
      (
        (FRICTION_FACTOR / 1.2158 * VELOCITY_MS ** 2 / 19.6133)
        - (
            (
              0.25
              / np.log10(
                  2.2229829764e-05
                  + 5.74
                    / (
                        (
                          (FLOW_OUT_M3H.clip(lower=1) / 3600)
                          / 1.16095172045
                        )
                        * 1.2158
                        / (
                            1.792e-06
                            / (
                                1
                                + 0.0337 * WATER_TEMP_C
                                + 0.000221 * WATER_TEMP_C ** 2
                              )
                          )
                      )
                      ** 0.9
                )
                ** 2
            )
            / 1.2158
            * ((FLOW_OUT_M3H.clip(lower=1) / 3600) / 1.16095172045) ** 2
            / 19.6133
          )
      )
      * 685.23
    )
```

### JOUKOWSKY_BAR

```python
JOUKOWSKY_BAR =
    (10.0528722 * VELOCITY_MS)
```

### SURGE_MARGIN_BAR

```python
SURGE_MARGIN_BAR =
    30 - SURGE_PMAX_BAR
```

## AlertExpression rules (9)

### PIPE_MASS_BALANCE

Medium

```python
PIPE_MASS_BALANCE =
    (FLOW_IN_M3H > 1500) & (IMBALANCE_PCT > 1.5)
```

### PIPE_LEAK

High · leak

```python
PIPE_LEAK =
    (FLOW_IN_M3H > 1500)
    & (IMBALANCE_PCT > 1.5)
    & (LEAK_SIGNAL_BAR > 0.035)
    & (RES_OUT_BAR > 0.42 * LEAK_SIGNAL_BAR)
```

### PIPE_FLOW_METER_DRIFT

Medium · meter_drift

```python
PIPE_FLOW_METER_DRIFT =
    (FLOW_IN_M3H > 1500)
    & (IMBALANCE_PCT > 2)
    & (LEAK_SIGNAL_BAR > 0.035)
    & (RES_OUT_BAR <= 0.42 * LEAK_SIGNAL_BAR)
```

### PIPE_ROUGHNESS

Medium · tuberculation

```python
PIPE_ROUGHNESS =
    (FLOW_IN_M3H > 1500)
    & (C_EFFECTIVE < 125)
    & (IMBALANCE_PCT.abs() < 1.5)
    & (SLOPE_RATIO_1 > 1.15)
    & (SLOPE_RATIO_2 > 1.15)
    & (SLOPE_RATIO_3 > 1.15)
    & (SLOPE_RATIO_4 > 1.15)
```

### PIPE_AIR_POCKET

Medium · air_pocket

```python
PIPE_AIR_POCKET =
    (FLOW_IN_M3H > 1500)
    & (
        (
          SLOPE_RATIO_2
          - (SLOPE_RATIO_1 + SLOPE_RATIO_3 + SLOPE_RATIO_4) / 3
        )
        > 0.6
      )
    & (SLOPE_RATIO_1 > 0.8)
    & (SLOPE_RATIO_3 > 0.8)
```

### PIPE_VALVE_THROTTLED

Medium · valve_throttled

```python
PIPE_VALVE_THROTTLED =
    (FLOW_IN_M3H > 1500)
    & (
        (
          SLOPE_RATIO_3
          - (SLOPE_RATIO_1 + SLOPE_RATIO_2 + SLOPE_RATIO_4) / 3
        )
        > 0.6
      )
    & (SLOPE_RATIO_2 > 0.8)
    & (SLOPE_RATIO_4 > 0.8)
```

### PIPE_TRANSMITTER_SUSPECT

Low · transmitter_fault

```python
PIPE_TRANSMITTER_SUSPECT =
    (FLOW_IN_M3H > 1500)
    & (
        ((SLOPE_RATIO_1 < 0.5) & (SLOPE_RATIO_2 > 1.5))
        | ((SLOPE_RATIO_1 > 1.5) & (SLOPE_RATIO_2 < 0.5))
        | ((SLOPE_RATIO_2 < 0.5) & (SLOPE_RATIO_3 > 1.5))
        | ((SLOPE_RATIO_2 > 1.5) & (SLOPE_RATIO_3 < 0.5))
        | ((SLOPE_RATIO_3 < 0.5) & (SLOPE_RATIO_4 > 1.5))
        | ((SLOPE_RATIO_3 > 1.5) & (SLOPE_RATIO_4 < 0.5))
      )
```

### PIPE_SURGE_ABOVE_PFA

High · surge_protection

```python
PIPE_SURGE_ABOVE_PFA =
    SURGE_PMAX_BAR > 25
```

### PIPE_COLUMN_SEPARATION

High · surge_protection

```python
PIPE_COLUMN_SEPARATION =
    SURGE_PMIN_HP_BAR < -0.5
```
