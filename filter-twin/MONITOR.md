# FLT-1401: Maximo Monitor functions and alert rules

Device type `GRAVITY_FILTER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (14)

### RATE_M_H

```python
RATE_M_H =
    (FLOW_M3H / 60)
```

### VISCOSITY_RATIO

```python
VISCOSITY_RATIO =
    np.power(10, 247.8 / (WATER_TEMP_C + 133.15) - 1.6180215475)
```

### CLEAN_BED_EXPECTED_M

```python
CLEAN_BED_EXPECTED_M =
    (
      0.3882
      * ((FLOW_M3H / 60) / 8)
      * np.power(10, 247.8 / (WATER_TEMP_C + 133.15) - 1.6180215475)
    )
```

### UNDERDRAIN_EXPECTED_M

```python
UNDERDRAIN_EXPECTED_M =
    (0.12 * ((FLOW_M3H / 60) / 8) ** 2)
```

### UFRV_M3_M2

```python
UFRV_M3_M2 =
    (RUN_VOLUME_M3 / 60)
```

### SOLIDS_LOAD_KG_M2

```python
SOLIDS_LOAD_KG_M2 =
    ((RUN_VOLUME_M3 / 60) * SETTLED_TURBIDITY_AVG_NTU * 1.5 / 1000)
```

### DEPOSIT_EXPECTED_M

```python
DEPOSIT_EXPECTED_M =
    (
      2.58
      * SOLIDS_LOAD_KG_M2
      * ((FLOW_M3H / 60) / 8)
      * np.power(10, 247.8 / (WATER_TEMP_C + 133.15) - 1.6180215475)
    )
```

### HEADLOSS_MEDIA_EXPECTED_M

```python
HEADLOSS_MEDIA_EXPECTED_M =
    (CLEAN_BED_EXPECTED_M + DEPOSIT_EXPECTED_M)
```

### HEADLOSS_RESIDUAL_M

```python
HEADLOSS_RESIDUAL_M =
    (HEADLOSS_MEDIA_M - HEADLOSS_MEDIA_EXPECTED_M)
```

### DEPOSIT_RATIO

```python
DEPOSIT_RATIO =
    (
      (HEADLOSS_MEDIA_M - CLEAN_BED_EXPECTED_M)
      / DEPOSIT_EXPECTED_M.clip(lower=0.05)
    )
```

### UNDERDRAIN_RATIO

```python
UNDERDRAIN_RATIO =
    (UNDERDRAIN_DP_M / UNDERDRAIN_EXPECTED_M.clip(lower=0.01))
```

### EXPANSION_EXPECTED_PCT

```python
EXPANSION_EXPECTED_PCT =
    np.where(
      (BACKWASH_FLOW_M3H / 60) > 0.1,
      (
        (1 - 0.5)
        / (
            1
            - np.clip(
                np.power(
                  ((BACKWASH_FLOW_M3H / 60) / 3600)
                  / (
                      5.886e-06
                      / (
                          18
                          * (
                              2.414e-05
                              * np.power(
                                  10,
                                  247.8 / (WATER_TEMP_C + 133.15)
                                )
                              / 998
                            )
                          + 6.64417037711e-05
                        )
                    ),
                  1
                  / (
                      4.45
                      * np.power(
                          (
                            5.886e-06
                            / (
                                18
                                * (
                                    2.414e-05
                                    * np.power(
                                        10,
                                        247.8 / (WATER_TEMP_C + 133.15)
                                      )
                                    / 998
                                  )
                                + 6.64417037711e-05
                              )
                          )
                          * 0.001
                          / (
                              2.414e-05
                              * np.power(
                                  10,
                                  247.8 / (WATER_TEMP_C + 133.15)
                                )
                              / 998
                            ),
                          -0.1
                        )
                    )
                ),
                0.5,
                0.95
              )
          )
        - 1
      )
      * 100,
      0
    )
```

### EXPANSION_RATIO

```python
EXPANSION_RATIO =
    np.where(
      (FILTER_STATE == 1) & ((BACKWASH_FLOW_M3H / 60) > 10),
      BED_EXPANSION_PCT
      / np.maximum(
          np.where(
            (BACKWASH_FLOW_M3H / 60) > 0.1,
            (
              (1 - 0.5)
              / (
                  1
                  - np.clip(
                      np.power(
                        ((BACKWASH_FLOW_M3H / 60) / 3600)
                        / (
                            5.886e-06
                            / (
                                18
                                * (
                                    2.414e-05
                                    * np.power(
                                        10,
                                        247.8 / (WATER_TEMP_C + 133.15)
                                      )
                                    / 998
                                  )
                                + 6.64417037711e-05
                              )
                          ),
                        1
                        / (
                            4.45
                            * np.power(
                                (
                                  5.886e-06
                                  / (
                                      18
                                      * (
                                          2.414e-05
                                          * np.power(
                                              10,
                                              247.8
                                              / (WATER_TEMP_C + 133.15)
                                            )
                                          / 998
                                        )
                                      + 6.64417037711e-05
                                    )
                                )
                                * 0.001
                                / (
                                    2.414e-05
                                    * np.power(
                                        10,
                                        247.8 / (WATER_TEMP_C + 133.15)
                                      )
                                    / 998
                                  ),
                                -0.1
                              )
                          )
                      ),
                      0.5,
                      0.95
                    )
                )
              - 1
            )
            * 100,
            0
          ),
          1
        ),
      1
    )
```

### FLOW_ERROR_PCT

```python
FLOW_ERROR_PCT =
    ((FLOW_M3H - FLOW_SETPOINT_M3H) / FLOW_SETPOINT_M3H.clip(lower=1) * 100)
```

## AlertExpression rules (10)

### FLT_MUDBALLS

Medium · mudballs

```python
FLT_MUDBALLS =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
    & (HEADLOSS_RESIDUAL_M > 0.15)
    & (DEPOSIT_RATIO < 1.6)
    & (BED_PRESSURE_HEAD_M > 0)
```

### FLT_MEDIA_LOSS

Medium · media_loss

```python
FLT_MEDIA_LOSS =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4)) & (BED_DEPTH_M < 0.85)
```

### FLT_AIR_BINDING

High · air_binding

```python
FLT_AIR_BINDING =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
    & (BED_PRESSURE_HEAD_M < 0)
```

### FLT_SHORT_CIRCUIT

High · short_circuiting

```python
FLT_SHORT_CIRCUIT =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
    & (HEADLOSS_RESIDUAL_M < -0.15)
    & (EFFLUENT_TURBIDITY_NTU > 0.15)
    & (PARTICLE_COUNT_ML > 50)
```

### FLT_UNDERDRAIN

High · underdrain_failure

```python
FLT_UNDERDRAIN =
    (
      ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
      & (UNDERDRAIN_RATIO < 0.7)
    )
    | (
        (FILTER_STATE == 1)
        & (
            np.where(
              (FILTER_STATE == 1) & ((BACKWASH_FLOW_M3H / 60) > 10),
              BED_EXPANSION_PCT
              / np.maximum(
                  np.where(
                    (BACKWASH_FLOW_M3H / 60) > 0.1,
                    (
                      (1 - 0.5)
                      / (
                          1
                          - np.clip(
                              np.power(
                                ((BACKWASH_FLOW_M3H / 60) / 3600)
                                / (
                                    5.886e-06
                                    / (
                                        18
                                        * (
                                            2.414e-05
                                            * np.power(
                                                10,
                                                247.8
                                                / (WATER_TEMP_C + 133.15)
                                              )
                                            / 998
                                          )
                                        + 6.64417037711e-05
                                      )
                                  ),
                                1
                                / (
                                    4.45
                                    * np.power(
                                        (
                                          5.886e-06
                                          / (
                                              18
                                              * (
                                                  2.414e-05
                                                  * np.power(
                                                      10,
                                                      247.8
                                                      / (
                                                          WATER_TEMP_C
                                                          + 133.15
                                                        )
                                                    )
                                                  / 998
                                                )
                                              + 6.64417037711e-05
                                            )
                                        )
                                        * 0.001
                                        / (
                                            2.414e-05
                                            * np.power(
                                                10,
                                                247.8
                                                / (WATER_TEMP_C + 133.15)
                                              )
                                            / 998
                                          ),
                                        -0.1
                                      )
                                  )
                              ),
                              0.5,
                              0.95
                            )
                        )
                      - 1
                    )
                    * 100,
                    0
                  ),
                  1
                ),
              1
            )
            < 0.7
          )
      )
```

### FLT_RATE_CONTROL

Medium · valve_sticking

```python
FLT_RATE_CONTROL =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
    & (np.abs(FLOW_ERROR_PCT) > 8)
```

### FLT_COAGULATION

Medium · coagulation_upset

```python
FLT_COAGULATION =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
    & (DEPOSIT_RATIO >= 1.6)
    & ((RUN_VOLUME_M3 / 60) > 30)
    & (HEADLOSS_RESIDUAL_M > 0.15)
    & (BED_PRESSURE_HEAD_M > 0)
```

### FLT_BREAKTHROUGH

High · coagulation_upset

```python
FLT_BREAKTHROUGH =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
    & (EFFLUENT_TURBIDITY_NTU > 0.3)
    & (PARTICLE_COUNT_ML > 100)
```

### FLT_TURBIDIMETER

Medium · turbidimeter_drift

```python
FLT_TURBIDIMETER =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4))
    & (EFFLUENT_TURBIDITY_NTU > 0.15)
    & (PARTICLE_COUNT_ML < 50)
```

### FLT_TERMINAL_HEADLOSS

Low

```python
FLT_TERMINAL_HEADLOSS =
    ((FILTER_STATE == 0) & ((FLOW_M3H / 60) > 4)) & (HEADLOSS_TOTAL_M > 2.4)
```
