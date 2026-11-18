# E-2501: Maximo Monitor functions and alert rules

Device type `SHELL_TUBE_HEX`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### Q_HOT_KW

```python
Q_HOT_KW =
    ((KERO_FLOW_T_H / 3.6 * 2.533) * (KERO_IN_C - KERO_OUT_C))
```

### Q_COLD_KW

```python
Q_COLD_KW =
    ((CRUDE_FLOW_T_H / 3.6 * 2.0515) * (CRUDE_OUT_C - CRUDE_IN_C))
```

### Q_KW

```python
Q_KW =
    ((Q_HOT_KW + Q_COLD_KW) / 2)
```

### BALANCE_PCT

```python
BALANCE_PCT =
    ((Q_HOT_KW - Q_COLD_KW) / Q_KW * 100)
```

### LMTD_K

```python
LMTD_K =
    np.where(
      np.abs(
        np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1)
        - np.maximum(KERO_OUT_C - CRUDE_IN_C, 0.1)
      )
      < 1e-09,
      np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1),
      (
        np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1)
        - np.maximum(KERO_OUT_C - CRUDE_IN_C, 0.1)
      )
      / np.log(
          np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1)
          / np.maximum(KERO_OUT_C - CRUDE_IN_C, 0.1)
        )
    )
```

### F_CORR

```python
F_CORR =
    np.clip(
      np.sqrt(
        ((KERO_IN_C - KERO_OUT_C) / (CRUDE_OUT_C - CRUDE_IN_C)) ** 2 + 1
      )
      * np.log(
          np.maximum(
            (1 - ((CRUDE_OUT_C - CRUDE_IN_C) / (KERO_IN_C - CRUDE_IN_C)))
            / np.maximum(
                1
                - ((KERO_IN_C - KERO_OUT_C) / (CRUDE_OUT_C - CRUDE_IN_C))
                  * ((CRUDE_OUT_C - CRUDE_IN_C) / (KERO_IN_C - CRUDE_IN_C)),
                1e-06
              ),
            1e-06
          )
        )
      / (
          (((KERO_IN_C - KERO_OUT_C) / (CRUDE_OUT_C - CRUDE_IN_C)) - 1)
          * np.log(
              np.maximum(
                (
                  2
                  - ((CRUDE_OUT_C - CRUDE_IN_C) / (KERO_IN_C - CRUDE_IN_C))
                    * (
                        (
                          (KERO_IN_C - KERO_OUT_C)
                          / (CRUDE_OUT_C - CRUDE_IN_C)
                        )
                        + 1
                        - np.sqrt(
                            (
                              (KERO_IN_C - KERO_OUT_C)
                              / (CRUDE_OUT_C - CRUDE_IN_C)
                            )
                            ** 2
                            + 1
                          )
                      )
                )
                / np.maximum(
                    2
                    - (
                        (CRUDE_OUT_C - CRUDE_IN_C)
                        / (KERO_IN_C - CRUDE_IN_C)
                      )
                      * (
                          (
                            (KERO_IN_C - KERO_OUT_C)
                            / (CRUDE_OUT_C - CRUDE_IN_C)
                          )
                          + 1
                          + np.sqrt(
                              (
                                (KERO_IN_C - KERO_OUT_C)
                                / (CRUDE_OUT_C - CRUDE_IN_C)
                              )
                              ** 2
                              + 1
                            )
                        ),
                    1e-06
                  ),
                1e-06
              )
            )
        ),
      0.3,
      1
    )
```

### U_ACTUAL_W_M2K

```python
U_ACTUAL_W_M2K =
    (
      Q_KW
      * 1000
      / (
          61.49
          * np.clip(
              np.sqrt(
                ((KERO_IN_C - KERO_OUT_C) / (CRUDE_OUT_C - CRUDE_IN_C)) ** 2
                + 1
              )
              * np.log(
                  np.maximum(
                    (
                      1
                      - (
                          (CRUDE_OUT_C - CRUDE_IN_C)
                          / (KERO_IN_C - CRUDE_IN_C)
                        )
                    )
                    / np.maximum(
                        1
                        - (
                            (KERO_IN_C - KERO_OUT_C)
                            / (CRUDE_OUT_C - CRUDE_IN_C)
                          )
                          * (
                              (CRUDE_OUT_C - CRUDE_IN_C)
                              / (KERO_IN_C - CRUDE_IN_C)
                            ),
                        1e-06
                      ),
                    1e-06
                  )
                )
              / (
                  (
                    ((KERO_IN_C - KERO_OUT_C) / (CRUDE_OUT_C - CRUDE_IN_C))
                    - 1
                  )
                  * np.log(
                      np.maximum(
                        (
                          2
                          - (
                              (CRUDE_OUT_C - CRUDE_IN_C)
                              / (KERO_IN_C - CRUDE_IN_C)
                            )
                            * (
                                (
                                  (KERO_IN_C - KERO_OUT_C)
                                  / (CRUDE_OUT_C - CRUDE_IN_C)
                                )
                                + 1
                                - np.sqrt(
                                    (
                                      (KERO_IN_C - KERO_OUT_C)
                                      / (CRUDE_OUT_C - CRUDE_IN_C)
                                    )
                                    ** 2
                                    + 1
                                  )
                              )
                        )
                        / np.maximum(
                            2
                            - (
                                (CRUDE_OUT_C - CRUDE_IN_C)
                                / (KERO_IN_C - CRUDE_IN_C)
                              )
                              * (
                                  (
                                    (KERO_IN_C - KERO_OUT_C)
                                    / (CRUDE_OUT_C - CRUDE_IN_C)
                                  )
                                  + 1
                                  + np.sqrt(
                                      (
                                        (KERO_IN_C - KERO_OUT_C)
                                        / (CRUDE_OUT_C - CRUDE_IN_C)
                                      )
                                      ** 2
                                      + 1
                                    )
                                ),
                            1e-06
                          ),
                        1e-06
                      )
                    )
                ),
              0.3,
              1
            )
          * np.where(
              np.abs(
                np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1)
                - np.maximum(KERO_OUT_C - CRUDE_IN_C, 0.1)
              )
              < 1e-09,
              np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1),
              (
                np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1)
                - np.maximum(KERO_OUT_C - CRUDE_IN_C, 0.1)
              )
              / np.log(
                  np.maximum(KERO_IN_C - CRUDE_OUT_C, 0.1)
                  / np.maximum(KERO_OUT_C - CRUDE_IN_C, 0.1)
                )
            )
        )
    )
```

### U_CLEAN_W_M2K

```python
U_CLEAN_W_M2K =
    (
      1
      / (
          1 / (640 * (CRUDE_FLOW_T_H / 67.585) ** 0.8)
          + 1 / (1100 * (KERO_FLOW_T_H / 19.867) ** 0.55)
          + 5e-05
        )
    )
```

### U_RATIO

```python
U_RATIO =
    U_ACTUAL_W_M2K / U_CLEAN_W_M2K
```

### RF_M2K_W

```python
RF_M2K_W =
    (1 / U_ACTUAL_W_M2K - 1 / U_CLEAN_W_M2K)
```

### RF_USED_PCT

```python
RF_USED_PCT =
    RF_M2K_W / 0.000528 * 100
```

### EFFECTIVENESS

```python
EFFECTIVENESS =
    Q_HOT_KW
    / (
        np.minimum(
          (KERO_FLOW_T_H / 3.6 * 2.533),
          (CRUDE_FLOW_T_H / 3.6 * 2.0515)
        )
        * (KERO_IN_C - CRUDE_IN_C)
      )
```

### Q_CLEAN_KW

```python
Q_CLEAN_KW =
    (
      2
      / (
          1
          + (
              np.minimum(
                (KERO_FLOW_T_H / 3.6 * 2.533),
                (CRUDE_FLOW_T_H / 3.6 * 2.0515)
              )
              / np.maximum(
                  (KERO_FLOW_T_H / 3.6 * 2.533),
                  (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                )
            )
          + np.sqrt(
              1
              + (
                  np.minimum(
                    (KERO_FLOW_T_H / 3.6 * 2.533),
                    (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                  )
                  / np.maximum(
                      (KERO_FLOW_T_H / 3.6 * 2.533),
                      (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                    )
                )
                ** 2
            )
            * (
                1
                + np.exp(
                    -(
                       U_CLEAN_W_M2K
                       * 61.49
                       / (
                           np.minimum(
                             (KERO_FLOW_T_H / 3.6 * 2.533),
                             (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                           )
                           * 1000
                         )
                     )
                    * np.sqrt(
                        1
                        + (
                            np.minimum(
                              (KERO_FLOW_T_H / 3.6 * 2.533),
                              (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                            )
                            / np.maximum(
                                (KERO_FLOW_T_H / 3.6 * 2.533),
                                (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                              )
                          )
                          ** 2
                      )
                  )
              )
            / (
                1
                - np.exp(
                    -(
                       U_CLEAN_W_M2K
                       * 61.49
                       / (
                           np.minimum(
                             (KERO_FLOW_T_H / 3.6 * 2.533),
                             (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                           )
                           * 1000
                         )
                     )
                    * np.sqrt(
                        1
                        + (
                            np.minimum(
                              (KERO_FLOW_T_H / 3.6 * 2.533),
                              (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                            )
                            / np.maximum(
                                (KERO_FLOW_T_H / 3.6 * 2.533),
                                (CRUDE_FLOW_T_H / 3.6 * 2.0515)
                              )
                          )
                          ** 2
                      )
                  )
              )
        )
      * np.minimum(
          (KERO_FLOW_T_H / 3.6 * 2.533),
          (CRUDE_FLOW_T_H / 3.6 * 2.0515)
        )
      * (KERO_IN_C - CRUDE_IN_C)
    )
```

### LOST_DUTY_KW

```python
LOST_DUTY_KW =
    (Q_CLEAN_KW - Q_KW)
```

### FUEL_PENALTY_USD_DAY

```python
FUEL_PENALTY_USD_DAY =
    (np.maximum(LOST_DUTY_KW, 0) * 0.7 / 0.85 * 0.0864) * 6
```

### CO2_T_DAY

```python
CO2_T_DAY =
    (np.maximum(LOST_DUTY_KW, 0) * 0.7 / 0.85 * 0.0864) * 56.1 / 1000
```

### DP_TUBE_RATIO

```python
DP_TUBE_RATIO =
    (DP_TUBE_BAR / (0.45 * (CRUDE_FLOW_T_H / 67.585) ** 1.8))
```

### DP_SHELL_RATIO

```python
DP_SHELL_RATIO =
    (DP_SHELL_BAR / (0.24 * (KERO_FLOW_T_H / 19.867) ** 1.8))
```

### DP_TUBE_AT_DESIGN_BAR

```python
DP_TUBE_AT_DESIGN_BAR =
    DP_TUBE_BAR * (67.585 / CRUDE_FLOW_T_H) ** 1.8
```

### TUBE_VELOCITY_M_S

```python
TUBE_VELOCITY_M_S =
    (CRUDE_FLOW_T_H / 3.6 / 830 / 0.013132)
```

## AlertExpression rules (14)

### HEX_TUBE_LEAK

Critical · tube_leak

```python
HEX_TUBE_LEAK =
    (KERO_SAYBOLT < 18) & (CRUDE_PRESSURE_BARG - KERO_PRESSURE_BARG > 1)
```

### HEX_FOULING_LIMIT

High · tube_fouling

```python
HEX_FOULING_LIMIT =
    (RF_USED_PCT > 100) & (DP_TUBE_RATIO >= 0.8)
```

### HEX_DP_TUBE_LIMIT

High · tube_fouling

```python
HEX_DP_TUBE_LIMIT =
    DP_TUBE_AT_DESIGN_BAR > 0.689
```

### HEX_BYPASS_SUSPECT

High · partition_leak

```python
HEX_BYPASS_SUSPECT =
    (U_RATIO < 0.85) & (DP_TUBE_RATIO < 0.8)
```

### HEX_FOULING_WARN

Medium · tube_fouling

```python
HEX_FOULING_WARN =
    (RF_USED_PCT > 60) & (RF_USED_PCT <= 100) & (DP_TUBE_RATIO >= 0.8)
```

### HEX_PRODUCT_COLOUR

Medium · tube_leak

```python
HEX_PRODUCT_COLOUR =
    KERO_SAYBOLT < 22
```

### HEX_DP_TUBE_HIGH

Medium · tube_fouling

```python
HEX_DP_TUBE_HIGH =
    DP_TUBE_RATIO > 1.3
```

### HEX_DP_SHELL_HIGH

Medium · shell_fouling

```python
HEX_DP_SHELL_HIGH =
    DP_SHELL_RATIO > 1.3
```

### HEX_DP_TUBE_LOW

Medium · partition_leak

```python
HEX_DP_TUBE_LOW =
    DP_TUBE_RATIO < 0.8
```

### HEX_HOT_DUTY_EXCESS

Medium

```python
HEX_HOT_DUTY_EXCESS =
    BALANCE_PCT > 5
```

### HEX_COLD_DUTY_EXCESS

Medium · ti_drift

```python
HEX_COLD_DUTY_EXCESS =
    BALANCE_PCT < -5
```

### HEX_VELOCITY_LOW

Medium · low_throughput

```python
HEX_VELOCITY_LOW =
    TUBE_VELOCITY_M_S < 1
```

### HEX_FUEL_PENALTY

Medium · tube_fouling

```python
HEX_FUEL_PENALTY =
    (np.maximum(LOST_DUTY_KW, 0) * 0.7 / 0.85 * 0.0864) * 6 > 50
```

### HEX_RF_NEGATIVE

Low · ti_drift

```python
HEX_RF_NEGATIVE =
    RF_M2K_W < -5e-05
```
