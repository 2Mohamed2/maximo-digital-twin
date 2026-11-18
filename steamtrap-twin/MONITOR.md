# ST-4701: Maximo Monitor functions and alert rules

Device type `STEAM_TRAP_TD`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### TSAT_C

```python
TSAT_C =
    (
      (
        650.175348448
        + (
            2
            * (
                -724213.167032
                * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25) ** 2
                - 3232555.03223
                  * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                + 405113.405421
              )
            / (
                -(
                   1167.05214528
                   * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25) ** 2
                   + 12020.8247025
                     * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                   - 4823.26573616
                 )
                - np.sqrt(
                    (
                      1167.05214528
                      * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25) ** 2
                      + 12020.8247025
                        * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                      - 4823.26573616
                    )
                    ** 2
                    - 4
                      * (
                          (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                          ** 2
                          - 17.0738469401
                            * (
                                ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                ** 0.25
                              )
                          + 14.9151086135
                        )
                      * (
                          -724213.167032
                          * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                            ** 2
                          - 3232555.03223
                            * (
                                ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                ** 0.25
                              )
                          + 405113.405421
                        )
                  )
              )
          )
        - np.sqrt(
            (
              650.175348448
              + (
                  2
                  * (
                      -724213.167032
                      * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25) ** 2
                      - 3232555.03223
                        * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                      + 405113.405421
                    )
                  / (
                      -(
                         1167.05214528
                         * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                           ** 2
                         + 12020.8247025
                           * (((LINE_PRESSURE_BARG + 1.01325) / 10) ** 0.25)
                         - 4823.26573616
                       )
                      - np.sqrt(
                          (
                            1167.05214528
                            * (
                                ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                ** 0.25
                              )
                              ** 2
                            + 12020.8247025
                              * (
                                  ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                  ** 0.25
                                )
                            - 4823.26573616
                          )
                          ** 2
                          - 4
                            * (
                                (
                                  ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                  ** 0.25
                                )
                                ** 2
                                - 17.0738469401
                                  * (
                                      ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                      ** 0.25
                                    )
                                + 14.9151086135
                              )
                            * (
                                -724213.167032
                                * (
                                    ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                    ** 0.25
                                  )
                                  ** 2
                                - 3232555.03223
                                  * (
                                      ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                      ** 0.25
                                    )
                                + 405113.405421
                              )
                        )
                    )
                )
            )
            ** 2
            - 4
              * (
                  -0.238555575678
                  + 650.175348448
                    * (
                        2
                        * (
                            -724213.167032
                            * (
                                ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                ** 0.25
                              )
                              ** 2
                            - 3232555.03223
                              * (
                                  ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                  ** 0.25
                                )
                            + 405113.405421
                          )
                        / (
                            -(
                               1167.05214528
                               * (
                                   ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                   ** 0.25
                                 )
                                 ** 2
                               + 12020.8247025
                                 * (
                                     ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                     ** 0.25
                                   )
                               - 4823.26573616
                             )
                            - np.sqrt(
                                (
                                  1167.05214528
                                  * (
                                      ((LINE_PRESSURE_BARG + 1.01325) / 10)
                                      ** 0.25
                                    )
                                    ** 2
                                  + 12020.8247025
                                    * (
                                        (
                                          (LINE_PRESSURE_BARG + 1.01325)
                                          / 10
                                        )
                                        ** 0.25
                                      )
                                  - 4823.26573616
                                )
                                ** 2
                                - 4
                                  * (
                                      (
                                        (
                                          (LINE_PRESSURE_BARG + 1.01325)
                                          / 10
                                        )
                                        ** 0.25
                                      )
                                      ** 2
                                      - 17.0738469401
                                        * (
                                            (
                                              (LINE_PRESSURE_BARG + 1.01325)
                                              / 10
                                            )
                                            ** 0.25
                                          )
                                      + 14.9151086135
                                    )
                                  * (
                                      -724213.167032
                                      * (
                                          (
                                            (LINE_PRESSURE_BARG + 1.01325)
                                            / 10
                                          )
                                          ** 0.25
                                        )
                                        ** 2
                                      - 3232555.03223
                                        * (
                                            (
                                              (LINE_PRESSURE_BARG + 1.01325)
                                              / 10
                                            )
                                            ** 0.25
                                          )
                                      + 405113.405421
                                    )
                              )
                          )
                      )
                )
          )
      )
      / 2
      - 273.15
    )
```

### SUBCOOL_C

```python
SUBCOOL_C =
    (TSAT_C - INLET_TEMP_C)
```

### SUBCOOL_EXCESS_C

```python
SUBCOOL_EXCESS_C =
    (SUBCOOL_C - 6)
```

### DP_BAR

```python
DP_BAR =
    (LINE_PRESSURE_BARG - OUTLET_PRESSURE_BARG)
```

### BACKPRESSURE_PCT

```python
BACKPRESSURE_PCT =
    OUTLET_PRESSURE_BARG / LINE_PRESSURE_BARG * 100
```

### ACOUSTIC_EXPECTED

```python
ACOUSTIC_EXPECTED =
    (25 + 2 * DP_BAR)
```

### ACOUSTIC_RATIO

```python
ACOUSTIC_RATIO =
    ACOUSTIC_LEVEL / ACOUSTIC_EXPECTED
```

### LEAK_FRACTION

```python
LEAK_FRACTION =
    np.clip(
      (ACOUSTIC_LEVEL - ACOUSTIC_EXPECTED)
      / ((60 + 9 * DP_BAR) - ACOUSTIC_EXPECTED),
      0,
      1
    )
```

### CYCLE_RATIO

```python
CYCLE_RATIO =
    CYCLE_RATE_PER_MIN / 2
```

### LOSS_FULL_OPEN_KGH

```python
LOSS_FULL_OPEN_KGH =
    (2.989549067 * (LINE_PRESSURE_BARG + 1.01325))
```

### STEAM_LOSS_KGH

```python
STEAM_LOSS_KGH =
    (
      np.clip(
        (ACOUSTIC_LEVEL - ACOUSTIC_EXPECTED)
        / ((60 + 9 * DP_BAR) - ACOUSTIC_EXPECTED),
        0,
        1
      )
      * LOSS_FULL_OPEN_KGH
      * (SUBCOOL_EXCESS_C < 12)
    )
```

### STEAM_LOSS_COST_Y

```python
STEAM_LOSS_COST_Y =
    STEAM_LOSS_KGH * 200
```

### STEAM_LOSS_CO2_T_Y

```python
STEAM_LOSS_CO2_T_Y =
    STEAM_LOSS_KGH * 1.23620112
```

### POP_FAILED_OPEN_PCT

```python
POP_FAILED_OPEN_PCT =
    POP_FAILED_OPEN / POP_TRAPS_TOTAL * 100
```

### POP_FAILED_COLD_PCT

```python
POP_FAILED_COLD_PCT =
    POP_FAILED_COLD / POP_TRAPS_TOTAL * 100
```

### POP_LOSS_KGH

```python
POP_LOSS_KGH =
    (POP_FAILED_OPEN * LOSS_FULL_OPEN_KGH)
```

### POP_LOSS_COST_Y

```python
POP_LOSS_COST_Y =
    POP_LOSS_KGH * 200
```

### POP_CO2_T_Y

```python
POP_CO2_T_Y =
    POP_LOSS_KGH * 1.23620112
```

### POP_FAIL_RATE_PCT_Y

```python
POP_FAIL_RATE_PCT_Y =
    POP_NEW_FAILED_OPEN_365D / POP_TRAPS_TOTAL * 100
```

### SURVEY_INTERVAL_OPT_D

```python
SURVEY_INTERVAL_OPT_D =
    (
      365
      * np.sqrt(
          2
          * 12
          * POP_TRAPS_TOTAL
          / (
              np.maximum(POP_NEW_FAILED_OPEN_365D, 1)
              * (LOSS_FULL_OPEN_KGH * 200)
            )
        )
    )
```

## AlertExpression rules (12)

### TRAP_BLOW_THROUGH

High · failed_open

```python
TRAP_BLOW_THROUGH =
    (
      np.clip(
        (ACOUSTIC_LEVEL - ACOUSTIC_EXPECTED)
        / ((60 + 9 * DP_BAR) - ACOUSTIC_EXPECTED),
        0,
        1
      )
      >= 0.5
    )
    & (SUBCOOL_EXCESS_C < 12)
    & (INLET_TEMP_C > AMBIENT_TEMP_C + 15)
```

### TRAP_COLD

High · blocked_cold

```python
TRAP_COLD =
    (SUBCOOL_EXCESS_C > 30)
    & (ACOUSTIC_RATIO < 0.5)
    & (INLET_TEMP_C > AMBIENT_TEMP_C + 15)
```

### POP_FAILED_OPEN_HIGH

High · survey_lapsed

```python
POP_FAILED_OPEN_HIGH =
    POP_FAILED_OPEN / POP_TRAPS_TOTAL * 100 > 5
```

### TRAP_LEAKING

Medium · disc_wear

```python
TRAP_LEAKING =
    (
      np.clip(
        (ACOUSTIC_LEVEL - ACOUSTIC_EXPECTED)
        / ((60 + 9 * DP_BAR) - ACOUSTIC_EXPECTED),
        0,
        1
      )
      >= 0.15
    )
    & (
        np.clip(
          (ACOUSTIC_LEVEL - ACOUSTIC_EXPECTED)
          / ((60 + 9 * DP_BAR) - ACOUSTIC_EXPECTED),
          0,
          1
        )
        < 0.5
      )
    & (SUBCOOL_EXCESS_C < 12)
    & (INLET_TEMP_C > AMBIENT_TEMP_C + 15)
```

### TRAP_RAPID_CYCLING

Medium · disc_wear

```python
TRAP_RAPID_CYCLING =
    CYCLE_RATE_PER_MIN / 2 > 3
```

### TRAP_BACKING_UP

Medium · condensate_overload

```python
TRAP_BACKING_UP =
    (SUBCOOL_EXCESS_C > 12)
    & (ACOUSTIC_RATIO >= 0.5)
    & (INLET_TEMP_C > AMBIENT_TEMP_C + 15)
```

### TRAP_BACKPRESSURE_HIGH

Medium · backpressure_high

```python
TRAP_BACKPRESSURE_HIGH =
    OUTLET_PRESSURE_BARG / LINE_PRESSURE_BARG * 100 > 80
```

### POP_FAILED_COLD_HIGH

Medium · survey_lapsed

```python
POP_FAILED_COLD_HIGH =
    POP_FAILED_COLD / POP_TRAPS_TOTAL * 100 > 3
```

### POP_SURVEY_OVERDUE

Medium · survey_lapsed

```python
POP_SURVEY_OVERDUE =
    SURVEY_DAYS_SINCE > 1.5 * SURVEY_INTERVAL_OPT_D
```

### POP_FAIL_RATE_HIGH

Medium · population_ageing

```python
POP_FAIL_RATE_HIGH =
    POP_NEW_FAILED_OPEN_365D / POP_TRAPS_TOTAL * 100 > 9
```

### TRAP_DP_LOW

Low

```python
TRAP_DP_LOW =
    DP_BAR < 0.25
```

### TRAP_SENSOR_SUSPECT

Low · sensor_fault

```python
TRAP_SENSOR_SUSPECT =
    INLET_TEMP_C <= AMBIENT_TEMP_C + 15
```
