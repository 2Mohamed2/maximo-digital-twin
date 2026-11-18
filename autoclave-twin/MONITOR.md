# ST-6601: Maximo Monitor functions and alert rules

Device type `STEAM_STERILIZER_LARGE`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### TSAT_HOLD_C

```python
TSAT_HOLD_C =
    (
      (
        650.175348448
        + (
            2
            * (
                -724213.167032
                * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                - 3232555.03223 * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                + 405113.405421
              )
            / (
                -(
                   1167.05214528
                   * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                   + 12020.8247025
                     * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                   - 4823.26573616
                 )
                - np.sqrt(
                    (
                      1167.05214528
                      * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                      + 12020.8247025
                        * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                      - 4823.26573616
                    )
                    ** 2
                    - 4
                      * (
                          ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                          - 17.0738469401
                            * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                          + 14.9151086135
                        )
                      * (
                          -724213.167032
                          * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                          - 3232555.03223
                            * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
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
                      * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                      - 3232555.03223
                        * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                      + 405113.405421
                    )
                  / (
                      -(
                         1167.05214528
                         * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                         + 12020.8247025
                           * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                         - 4823.26573616
                       )
                      - np.sqrt(
                          (
                            1167.05214528
                            * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                            + 12020.8247025
                              * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                            - 4823.26573616
                          )
                          ** 2
                          - 4
                            * (
                                ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                                ** 2
                                - 17.0738469401
                                  * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                                + 14.9151086135
                              )
                            * (
                                -724213.167032
                                * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                                  ** 2
                                - 3232555.03223
                                  * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
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
                            * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                            - 3232555.03223
                              * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                            + 405113.405421
                          )
                        / (
                            -(
                               1167.05214528
                               * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                                 ** 2
                               + 12020.8247025
                                 * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                               - 4823.26573616
                             )
                            - np.sqrt(
                                (
                                  1167.05214528
                                  * ((CYC_HOLD_PRESSURE_BAR_A / 10) ** 0.25)
                                    ** 2
                                  + 12020.8247025
                                    * (
                                        (CYC_HOLD_PRESSURE_BAR_A / 10)
                                        ** 0.25
                                      )
                                  - 4823.26573616
                                )
                                ** 2
                                - 4
                                  * (
                                      (
                                        (CYC_HOLD_PRESSURE_BAR_A / 10)
                                        ** 0.25
                                      )
                                      ** 2
                                      - 17.0738469401
                                        * (
                                            (CYC_HOLD_PRESSURE_BAR_A / 10)
                                            ** 0.25
                                          )
                                      + 14.9151086135
                                    )
                                  * (
                                      -724213.167032
                                      * (
                                          (CYC_HOLD_PRESSURE_BAR_A / 10)
                                          ** 0.25
                                        )
                                        ** 2
                                      - 3232555.03223
                                        * (
                                            (CYC_HOLD_PRESSURE_BAR_A / 10)
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

### SAT_DEV_K

```python
SAT_DEV_K =
    (CYC_HOLD_TEMP_MEAN_C - TSAT_HOLD_C)
```

### AIR_FRACTION_PCT

```python
AIR_FRACTION_PCT =
    (
      np.maximum(
        1
        - (
            (
              2
              * (
                  14.9151086135
                  * (
                      (CYC_HOLD_TEMP_MEAN_C + 273.15)
                      - 0.238555575678
                        / ((CYC_HOLD_TEMP_MEAN_C + 273.15) - 650.175348448)
                    )
                    ** 2
                  - 4823.26573616
                    * (
                        (CYC_HOLD_TEMP_MEAN_C + 273.15)
                        - 0.238555575678
                          / (
                              (CYC_HOLD_TEMP_MEAN_C + 273.15)
                              - 650.175348448
                            )
                      )
                  + 405113.405421
                )
              / (
                  -(
                     -17.0738469401
                     * (
                         (CYC_HOLD_TEMP_MEAN_C + 273.15)
                         - 0.238555575678
                           / (
                               (CYC_HOLD_TEMP_MEAN_C + 273.15)
                               - 650.175348448
                             )
                       )
                       ** 2
                     + 12020.8247025
                       * (
                           (CYC_HOLD_TEMP_MEAN_C + 273.15)
                           - 0.238555575678
                             / (
                                 (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                 - 650.175348448
                               )
                         )
                     - 3232555.03223
                   )
                  + np.sqrt(
                      (
                        -17.0738469401
                        * (
                            (CYC_HOLD_TEMP_MEAN_C + 273.15)
                            - 0.238555575678
                              / (
                                  (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                  - 650.175348448
                                )
                          )
                          ** 2
                        + 12020.8247025
                          * (
                              (CYC_HOLD_TEMP_MEAN_C + 273.15)
                              - 0.238555575678
                                / (
                                    (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                    - 650.175348448
                                  )
                            )
                        - 3232555.03223
                      )
                      ** 2
                      - 4
                        * (
                            (
                              (CYC_HOLD_TEMP_MEAN_C + 273.15)
                              - 0.238555575678
                                / (
                                    (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                    - 650.175348448
                                  )
                            )
                            ** 2
                            + 1167.05214528
                              * (
                                  (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                  - 0.238555575678
                                    / (
                                        (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                        - 650.175348448
                                      )
                                )
                            - 724213.167032
                          )
                        * (
                            14.9151086135
                            * (
                                (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                - 0.238555575678
                                  / (
                                      (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                      - 650.175348448
                                    )
                              )
                              ** 2
                            - 4823.26573616
                              * (
                                  (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                  - 0.238555575678
                                    / (
                                        (CYC_HOLD_TEMP_MEAN_C + 273.15)
                                        - 650.175348448
                                      )
                                )
                            + 405113.405421
                          )
                    )
                )
            )
            ** 4
            * 10
          )
          / CYC_HOLD_PRESSURE_BAR_A,
        0
      )
      * 100
    )
```

### BAND_MARGIN_LOW_K

```python
BAND_MARGIN_LOW_K =
    CYC_HOLD_TEMP_MIN_C - 134
```

### BAND_MARGIN_HIGH_K

```python
BAND_MARGIN_HIGH_K =
    137 - CYC_HOLD_TEMP_MAX_C
```

### HOLD_TIME_RATIO

```python
HOLD_TIME_RATIO =
    CYC_HOLD_TIME_S / 420
```

### F0_HOLD_MIN

```python
F0_HOLD_MIN =
    (CYC_HOLD_TIME_S / 60 * 10 ** ((CYC_HOLD_TEMP_MIN_C - 121.1) / 10))
```

### F0_MARGIN

```python
F0_MARGIN =
    F0_HOLD_MIN / 136.489122
```

### SENSOR_DIFF_K

```python
SENSOR_DIFF_K =
    np.abs(CYC_HOLD_TEMP2_MEAN_C - CYC_HOLD_TEMP_MEAN_C)
```

### TSAT_JACKET_C

```python
TSAT_JACKET_C =
    (
      (
        650.175348448
        + (
            2
            * (
                -724213.167032
                * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                - 3232555.03223 * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                + 405113.405421
              )
            / (
                -(
                   1167.05214528
                   * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                   + 12020.8247025
                     * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                   - 4823.26573616
                 )
                - np.sqrt(
                    (
                      1167.05214528
                      * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                      + 12020.8247025
                        * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                      - 4823.26573616
                    )
                    ** 2
                    - 4
                      * (
                          ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                          - 17.0738469401
                            * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                          + 14.9151086135
                        )
                      * (
                          -724213.167032
                          * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                          - 3232555.03223
                            * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
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
                      * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                      - 3232555.03223
                        * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                      + 405113.405421
                    )
                  / (
                      -(
                         1167.05214528
                         * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25) ** 2
                         + 12020.8247025
                           * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                         - 4823.26573616
                       )
                      - np.sqrt(
                          (
                            1167.05214528
                            * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                              ** 2
                            + 12020.8247025
                              * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                            - 4823.26573616
                          )
                          ** 2
                          - 4
                            * (
                                ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                                ** 2
                                - 17.0738469401
                                  * (
                                      (CYC_JACKET_PRESSURE_BAR_A / 10)
                                      ** 0.25
                                    )
                                + 14.9151086135
                              )
                            * (
                                -724213.167032
                                * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                                  ** 2
                                - 3232555.03223
                                  * (
                                      (CYC_JACKET_PRESSURE_BAR_A / 10)
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
                            * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                              ** 2
                            - 3232555.03223
                              * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                            + 405113.405421
                          )
                        / (
                            -(
                               1167.05214528
                               * ((CYC_JACKET_PRESSURE_BAR_A / 10) ** 0.25)
                                 ** 2
                               + 12020.8247025
                                 * (
                                     (CYC_JACKET_PRESSURE_BAR_A / 10)
                                     ** 0.25
                                   )
                               - 4823.26573616
                             )
                            - np.sqrt(
                                (
                                  1167.05214528
                                  * (
                                      (CYC_JACKET_PRESSURE_BAR_A / 10)
                                      ** 0.25
                                    )
                                    ** 2
                                  + 12020.8247025
                                    * (
                                        (CYC_JACKET_PRESSURE_BAR_A / 10)
                                        ** 0.25
                                      )
                                  - 4823.26573616
                                )
                                ** 2
                                - 4
                                  * (
                                      (
                                        (CYC_JACKET_PRESSURE_BAR_A / 10)
                                        ** 0.25
                                      )
                                      ** 2
                                      - 17.0738469401
                                        * (
                                            (CYC_JACKET_PRESSURE_BAR_A / 10)
                                            ** 0.25
                                          )
                                      + 14.9151086135
                                    )
                                  * (
                                      -724213.167032
                                      * (
                                          (CYC_JACKET_PRESSURE_BAR_A / 10)
                                          ** 0.25
                                        )
                                        ** 2
                                      - 3232555.03223
                                        * (
                                            (CYC_JACKET_PRESSURE_BAR_A / 10)
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

### JACKET_ABOVE_CHAMBER_K

```python
JACKET_ABOVE_CHAMBER_K =
    TSAT_JACKET_C - CYC_HOLD_TEMP_MEAN_C
```

### LEAK_RATE_MBAR_MIN

```python
LEAK_RATE_MBAR_MIN =
    LT_RISE_MBAR / 10
```

### LEAK_RATIO

```python
LEAK_RATIO =
    LT_RISE_MBAR / 13
```

### EQUIL_RATIO

```python
EQUIL_RATIO =
    BD_EQUIL_TIME_S / 15
```

### VACUUM_RATIO

```python
VACUUM_RATIO =
    CYC_VAC_MIN_MBAR / 60
```

### STEAM_RATIO

```python
STEAM_RATIO =
    CYC_STEAM_KG / 9
```

### WATER_RATIO

```python
WATER_RATIO =
    CYC_WATER_L / 80
```

### ENERGY_EXPECTED_KWH

```python
ENERGY_EXPECTED_KWH =
    (0.4 + CYC_STEAM_KG * 0.7790087719)
```

### ENERGY_RATIO

```python
ENERGY_RATIO =
    CYC_ENERGY_KWH / ENERGY_EXPECTED_KWH
```

### SEAL_LIFE_USED_PCT

```python
SEAL_LIFE_USED_PCT =
    CYCLES_SINCE_SEAL / 6000 * 100
```

## AlertExpression rules (15)

### AC_HOLD_NOT_MET

Critical · steam_supply_low

```python
AC_HOLD_NOT_MET =
    (CYC_HOLD_TIME_S < 420)
    | (CYC_HOLD_TEMP_MIN_C < 134)
    | (CYC_HOLD_TEMP_MAX_C > 137)
```

### AC_AIR_IN_CHAMBER

High · door_seal_wear

```python
AC_AIR_IN_CHAMBER =
    SAT_DEV_K < -2
```

### AC_SUPERHEAT

High · jacket_overheat

```python
AC_SUPERHEAT =
    SAT_DEV_K > 2
```

### AC_BD_FAIL

High · door_seal_wear

```python
AC_BD_FAIL =
    (BD_RESULT < 0.5) | (BD_DELTA_T_C >= 2)
```

### AC_LEAK_FAIL

High · door_seal_wear

```python
AC_LEAK_FAIL =
    LT_RISE_MBAR > 13
```

### AC_LEAK_RISING

Medium · door_seal_wear

```python
AC_LEAK_RISING =
    (LT_RISE_MBAR > 7.8) & (LT_RISE_MBAR <= 13)
```

### AC_EQUILIBRATION_SLOW

Medium · door_seal_wear

```python
AC_EQUILIBRATION_SLOW =
    BD_EQUIL_TIME_S > 15
```

### AC_VACUUM_WEAK

Medium · vacuum_pump_wear

```python
AC_VACUUM_WEAK =
    CYC_VAC_MIN_MBAR > 100
```

### AC_JACKET_HOT

Medium · jacket_overheat

```python
AC_JACKET_HOT =
    JACKET_ABOVE_CHAMBER_K > 4
```

### AC_SUPPLY_LOW

Medium · steam_supply_low

```python
AC_SUPPLY_LOW =
    STEAM_SUPPLY_BAR_G < 3
```

### AC_SENSOR_DISAGREE

Medium · sensor_drift

```python
AC_SENSOR_DISAGREE =
    np.abs(CYC_HOLD_TEMP2_MEAN_C - CYC_HOLD_TEMP_MEAN_C) > 1
```

### AC_STEAM_HIGH

Medium · drain_trap_passing

```python
AC_STEAM_HIGH =
    CYC_STEAM_KG / 9 > 1.1
```

### AC_ENERGY_HIGH

Medium · generator_scaling

```python
AC_ENERGY_HIGH =
    CYC_ENERGY_KWH / ENERGY_EXPECTED_KWH > 1.15
```

### AC_TESTS_OVERDUE

Medium

```python
AC_TESTS_OVERDUE =
    (BD_HOURS_SINCE > 26) | (LT_HOURS_SINCE > 192)
```

### AC_SEAL_LIFE

Low · door_seal_wear

```python
AC_SEAL_LIFE =
    CYCLES_SINCE_SEAL > 6000
```
