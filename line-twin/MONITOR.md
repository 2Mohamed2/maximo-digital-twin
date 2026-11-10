# OHL-901: Maximo Monitor functions and alert rules

Device type `OVERHEAD_LINE`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (17)

### WIND_ANGLE_DEG

```python
WIND_ANGLE_DEG =
    np.degrees(np.arcsin(np.abs(np.sin(np.radians(WIND_DIR_DEG - 75)))))
```

### R_AC_OHM_KM

```python
R_AC_OHM_KM =
    (7.2054e-05 + 2.8464e-07 * (CONDUCTOR_TEMP_C - 25)) * 1000
```

### JOULE_W_M

```python
JOULE_W_M =
    LINE_CURRENT_A ** 2
    * (7.2054e-05 + 2.8464e-07 * (CONDUCTOR_TEMP_C - 25))
```

### SOLAR_W_M

```python
SOLAR_W_M =
    0.022512 * SOLAR_WM2.clip(lower=0)
```

### TC_EXPECTED_C

```python
TC_EXPECTED_C =
    (
      AMBIENT_TEMP_C
      + (
          LINE_CURRENT_A ** 2 * (6.4938e-05 + 2.8464e-07 * AMBIENT_TEMP_C)
          + 0.022512 * SOLAR_WM2.clip(lower=0)
        )
        / (
            (
              np.maximum(
                (
                  (
                    1.194
                    - np.abs(np.cos(np.radians(WIND_DIR_DEG - 75)))
                    + 0.194 * np.cos(2 * np.radians(WIND_DIR_DEG - 75))
                    + 0.368
                      * np.abs(np.sin(2 * np.radians(WIND_DIR_DEG - 75)))
                  )
                  * np.maximum(
                      1.01
                      + 1.35
                        * (
                            0.02814
                            * (
                                (1.293 - 0.0183 + 9.18576e-05)
                                / (1 + 0.00367 * (AMBIENT_TEMP_C + 20))
                              )
                            * WIND_SPEED_MS.clip(lower=0)
                            / (
                                1.458e-06
                                * ((AMBIENT_TEMP_C + 20) + 273) ** 1.5
                                / ((AMBIENT_TEMP_C + 20) + 383.4)
                              )
                          )
                          ** 0.52,
                      0.754
                      * (
                          0.02814
                          * (
                              (1.293 - 0.0183 + 9.18576e-05)
                              / (1 + 0.00367 * (AMBIENT_TEMP_C + 20))
                            )
                          * WIND_SPEED_MS.clip(lower=0)
                          / (
                              1.458e-06
                              * ((AMBIENT_TEMP_C + 20) + 273) ** 1.5
                              / ((AMBIENT_TEMP_C + 20) + 383.4)
                            )
                        )
                        ** 0.6
                    )
                  * (
                      0.02424
                      + 7.477e-05 * (AMBIENT_TEMP_C + 20)
                      - 4.407e-09 * (AMBIENT_TEMP_C + 20) ** 2
                    )
                ),
                (
                  3.645
                  * (
                      (1.293 - 0.0183 + 9.18576e-05)
                      / (1 + 0.00367 * (AMBIENT_TEMP_C + 20))
                    )
                    ** 0.5
                  * 0.0687057476331
                  * (
                      (
                        (
                          (
                            (
                              AMBIENT_TEMP_C
                              + 5
                              + 60 * (LINE_CURRENT_A / 1000) ** 2
                            )
                            + (
                                AMBIENT_TEMP_C
                                + (
                                    LINE_CURRENT_A ** 2
                                    * (
                                        6.4938e-05
                                        + 2.8464e-07 * AMBIENT_TEMP_C
                                      )
                                    + 0.022512 * SOLAR_WM2.clip(lower=0)
                                  )
                                  / (
                                      (
                                        np.maximum(
                                          (
                                            (
                                              1.194
                                              - np.abs(
                                                  np.cos(
                                                    np.radians(
                                                      WIND_DIR_DEG - 75
                                                    )
                                                  )
                                                )
                                              + 0.194
                                                * np.cos(
                                                    2
                                                    * np.radians(
                                                        WIND_DIR_DEG - 75
                                                      )
                                                  )
                                              + 0.368
                                                * np.abs(
                                                    np.sin(
                                                      2
                                                      * np.radians(
                                                          WIND_DIR_DEG - 75
                                                        )
                                                    )
                                                  )
                                            )
                                            * np.maximum(
                                                1.01
                                                + 1.35
                                                  * (
                                                      0.02814
                                                      * (
                                                          (
                                                            1.293
                                                            - 0.0183
                                                            + 9.18576e-05
                                                          )
                                                          / (
                                                              1
                                                              + 0.00367
                                                                * (
                                                                    AMBIENT_TEMP_C
                                                                    + 20
                                                                  )
                                                            )
                                                        )
                                                      * WIND_SPEED_MS.clip(
                                                          lower=0
                                                        )
                                                      / (
                                                          1.458e-06
                                                          * (
                                                              (
                                                                AMBIENT_TEMP_C
                                                                + 20
                                                              )
                                                              + 273
                                                            )
                                                            ** 1.5
                                                          / (
                                                              (
                                                                AMBIENT_TEMP_C
                                                                + 20
                                                              )
                                                              + 383.4
                                                            )
                                                        )
                                                    )
                                                    ** 0.52,
                                                0.754
                                                * (
                                                    0.02814
                                                    * (
                                                        (
                                                          1.293
                                                          - 0.0183
                                                          + 9.18576e-05
                                                        )
                                                        / (
                                                            1
                                                            + 0.00367
                                                              * (
                                                                  AMBIENT_TEMP_C
                                                                  + 20
                                                                )
                                                          )
                                                      )
                                                    * WIND_SPEED_MS.clip(
                                                        lower=0
                                                      )
                                                    / (
                                                        1.458e-06
                                                        * (
                                                            (
                                                              AMBIENT_TEMP_C
                                                              + 20
                                                            )
                                                            + 273
                                                          )
                                                          ** 1.5
                                                        / (
                                                            (
                                                              AMBIENT_TEMP_C
                                                              + 20
                                                            )
                                                            + 383.4
                                                          )
                                                      )
                                                  )
                                                  ** 0.6
                                              )
                                            * (
                                                0.02424
                                                + 7.477e-05
                                                  * (AMBIENT_TEMP_C + 20)
                                                - 4.407e-09
                                                  * (AMBIENT_TEMP_C + 20)
                                                    ** 2
                                              )
                                          ),
                                          (
                                            3.645
                                            * (
                                                (
                                                  1.293
                                                  - 0.0183
                                                  + 9.18576e-05
                                                )
                                                / (
                                                    1
                                                    + 0.00367
                                                      * (
                                                          AMBIENT_TEMP_C
                                                          + 20
                                                        )
                                                  )
                                              )
                                              ** 0.5
                                            * 0.0687057476331
                                            * (
                                                (
                                                  (
                                                    AMBIENT_TEMP_C
                                                    + 5
                                                    + 60
                                                      * (
                                                          LINE_CURRENT_A
                                                          / 1000
                                                        )
                                                        ** 2
                                                  )
                                                )
                                                - AMBIENT_TEMP_C
                                              ).clip(lower=0.5)
                                              ** 0.25
                                          )
                                        )
                                        + (
                                            0.4007136
                                            * (
                                                (
                                                  (
                                                    (
                                                      AMBIENT_TEMP_C
                                                      + 5
                                                      + 60
                                                        * (
                                                            LINE_CURRENT_A
                                                            / 1000
                                                          )
                                                          ** 2
                                                    )
                                                  )
                                                  + 273
                                                )
                                                ** 4
                                                / 100000000
                                                - (AMBIENT_TEMP_C + 273)
                                                  ** 4
                                                  / 100000000
                                              )
                                            / (
                                                (
                                                  (
                                                    AMBIENT_TEMP_C
                                                    + 5
                                                    + 60
                                                      * (
                                                          LINE_CURRENT_A
                                                          / 1000
                                                        )
                                                        ** 2
                                                  )
                                                )
                                                - AMBIENT_TEMP_C
                                              ).clip(lower=0.5)
                                          )
                                      )
                                      - LINE_CURRENT_A ** 2 * 2.8464e-07
                                    )
                              )
                          )
                          / 2
                        )
                      )
                      - AMBIENT_TEMP_C
                    ).clip(lower=0.5)
                    ** 0.25
                )
              )
              + (
                  0.4007136
                  * (
                      (
                        (
                          (
                            (
                              (
                                AMBIENT_TEMP_C
                                + 5
                                + 60 * (LINE_CURRENT_A / 1000) ** 2
                              )
                              + (
                                  AMBIENT_TEMP_C
                                  + (
                                      LINE_CURRENT_A ** 2
                                      * (
                                          6.4938e-05
                                          + 2.8464e-07 * AMBIENT_TEMP_C
                                        )
                                      + 0.022512 * SOLAR_WM2.clip(lower=0)
                                    )
                                    / (
                                        (
                                          np.maximum(
                                            (
                                              (
                                                1.194
                                                - np.abs(
                                                    np.cos(
                                                      np.radians(
                                                        WIND_DIR_DEG - 75
                                                      )
                                                    )
                                                  )
                                                + 0.194
                                                  * np.cos(
                                                      2
                                                      * np.radians(
                                                          WIND_DIR_DEG - 75
                                                        )
                                                    )
                                                + 0.368
                                                  * np.abs(
                                                      np.sin(
                                                        2
                                                        * np.radians(
                                                            WIND_DIR_DEG
                                                            - 75
                                                          )
                                                      )
                                                    )
                                              )
                                              * np.maximum(
                                                  1.01
                                                  + 1.35
                                                    * (
                                                        0.02814
                                                        * (
                                                            (
                                                              1.293
                                                              - 0.0183
                                                              + 9.18576e-05
                                                            )
                                                            / (
                                                                1
                                                                + 0.00367
                                                                  * (
                                                                      AMBIENT_TEMP_C
                                                                      + 20
                                                                    )
                                                              )
                                                          )
                                                        * WIND_SPEED_MS.clip(
                                                            lower=0
                                                          )
                                                        / (
                                                            1.458e-06
                                                            * (
                                                                (
                                                                  AMBIENT_TEMP_C
                                                                  + 20
                                                                )
                                                                + 273
                                                              )
                                                              ** 1.5
                                                            / (
                                                                (
                                                                  AMBIENT_TEMP_C
                                                                  + 20
                                                                )
                                                                + 383.4
                                                              )
                                                          )
                                                      )
                                                      ** 0.52,
                                                  0.754
                                                  * (
                                                      0.02814
                                                      * (
                                                          (
                                                            1.293
                                                            - 0.0183
                                                            + 9.18576e-05
                                                          )
                                                          / (
                                                              1
                                                              + 0.00367
                                                                * (
                                                                    AMBIENT_TEMP_C
                                                                    + 20
                                                                  )
                                                            )
                                                        )
                                                      * WIND_SPEED_MS.clip(
                                                          lower=0
                                                        )
                                                      / (
                                                          1.458e-06
                                                          * (
                                                              (
                                                                AMBIENT_TEMP_C
                                                                + 20
                                                              )
                                                              + 273
                                                            )
                                                            ** 1.5
                                                          / (
                                                              (
                                                                AMBIENT_TEMP_C
                                                                + 20
                                                              )
                                                              + 383.4
                                                            )
                                                        )
                                                    )
                                                    ** 0.6
                                                )
                                              * (
                                                  0.02424
                                                  + 7.477e-05
                                                    * (AMBIENT_TEMP_C + 20)
                                                  - 4.407e-09
                                                    * (AMBIENT_TEMP_C + 20)
                                                      ** 2
                                                )
                                            ),
                                            (
                                              3.645
                                              * (
                                                  (
                                                    1.293
                                                    - 0.0183
                                                    + 9.18576e-05
                                                  )
                                                  / (
                                                      1
                                                      + 0.00367
                                                        * (
                                                            AMBIENT_TEMP_C
                                                            + 20
                                                          )
                                                    )
                                                )
                                                ** 0.5
                                              * 0.0687057476331
                                              * (
                                                  (
                                                    (
                                                      AMBIENT_TEMP_C
                                                      + 5
                                                      + 60
                                                        * (
                                                            LINE_CURRENT_A
                                                            / 1000
                                                          )
                                                          ** 2
                                                    )
                                                  )
                                                  - AMBIENT_TEMP_C
                                                ).clip(lower=0.5)
                                                ** 0.25
                                            )
                                          )
                                          + (
                                              0.4007136
                                              * (
                                                  (
                                                    (
                                                      (
                                                        AMBIENT_TEMP_C
                                                        + 5
                                                        + 60
                                                          * (
                                                              LINE_CURRENT_A
                                                              / 1000
                                                            )
                                                            ** 2
                                                      )
                                                    )
                                                    + 273
                                                  )
                                                  ** 4
                                                  / 100000000
                                                  - (AMBIENT_TEMP_C + 273)
                                                    ** 4
                                                    / 100000000
                                                )
                                              / (
                                                  (
                                                    (
                                                      AMBIENT_TEMP_C
                                                      + 5
                                                      + 60
                                                        * (
                                                            LINE_CURRENT_A
                                                            / 1000
                                                          )
                                                          ** 2
                                                    )
                                                  )
                                                  - AMBIENT_TEMP_C
                                                ).clip(lower=0.5)
                                            )
                                        )
                                        - LINE_CURRENT_A ** 2 * 2.8464e-07
                                      )
                                )
                            )
                            / 2
                          )
                        )
                        + 273
                      )
                      ** 4
                      / 100000000
                      - (AMBIENT_TEMP_C + 273) ** 4 / 100000000
                    )
                  / (
                      (
                        (
                          (
                            (
                              AMBIENT_TEMP_C
                              + 5
                              + 60 * (LINE_CURRENT_A / 1000) ** 2
                            )
                            + (
                                AMBIENT_TEMP_C
                                + (
                                    LINE_CURRENT_A ** 2
                                    * (
                                        6.4938e-05
                                        + 2.8464e-07 * AMBIENT_TEMP_C
                                      )
                                    + 0.022512 * SOLAR_WM2.clip(lower=0)
                                  )
                                  / (
                                      (
                                        np.maximum(
                                          (
                                            (
                                              1.194
                                              - np.abs(
                                                  np.cos(
                                                    np.radians(
                                                      WIND_DIR_DEG - 75
                                                    )
                                                  )
                                                )
                                              + 0.194
                                                * np.cos(
                                                    2
                                                    * np.radians(
                                                        WIND_DIR_DEG - 75
                                                      )
                                                  )
                                              + 0.368
                                                * np.abs(
                                                    np.sin(
                                                      2
                                                      * np.radians(
                                                          WIND_DIR_DEG - 75
                                                        )
                                                    )
                                                  )
                                            )
                                            * np.maximum(
                                                1.01
                                                + 1.35
                                                  * (
                                                      0.02814
                                                      * (
                                                          (
                                                            1.293
                                                            - 0.0183
                                                            + 9.18576e-05
                                                          )
                                                          / (
                                                              1
                                                              + 0.00367
                                                                * (
                                                                    AMBIENT_TEMP_C
                                                                    + 20
                                                                  )
                                                            )
                                                        )
                                                      * WIND_SPEED_MS.clip(
                                                          lower=0
                                                        )
                                                      / (
                                                          1.458e-06
                                                          * (
                                                              (
                                                                AMBIENT_TEMP_C
                                                                + 20
                                                              )
                                                              + 273
                                                            )
                                                            ** 1.5
                                                          / (
                                                              (
                                                                AMBIENT_TEMP_C
                                                                + 20
                                                              )
                                                              + 383.4
                                                            )
                                                        )
                                                    )
                                                    ** 0.52,
                                                0.754
                                                * (
                                                    0.02814
                                                    * (
                                                        (
                                                          1.293
                                                          - 0.0183
                                                          + 9.18576e-05
                                                        )
                                                        / (
                                                            1
                                                            + 0.00367
                                                              * (
                                                                  AMBIENT_TEMP_C
                                                                  + 20
                                                                )
                                                          )
                                                      )
                                                    * WIND_SPEED_MS.clip(
                                                        lower=0
                                                      )
                                                    / (
                                                        1.458e-06
                                                        * (
                                                            (
                                                              AMBIENT_TEMP_C
                                                              + 20
                                                            )
                                                            + 273
                                                          )
                                                          ** 1.5
                                                        / (
                                                            (
                                                              AMBIENT_TEMP_C
                                                              + 20
                                                            )
                                                            + 383.4
                                                          )
                                                      )
                                                  )
                                                  ** 0.6
                                              )
                                            * (
                                                0.02424
                                                + 7.477e-05
                                                  * (AMBIENT_TEMP_C + 20)
                                                - 4.407e-09
                                                  * (AMBIENT_TEMP_C + 20)
                                                    ** 2
                                              )
                                          ),
                                          (
                                            3.645
                                            * (
                                                (
                                                  1.293
                                                  - 0.0183
                                                  + 9.18576e-05
                                                )
                                                / (
                                                    1
                                                    + 0.00367
                                                      * (
                                                          AMBIENT_TEMP_C
                                                          + 20
                                                        )
                                                  )
                                              )
                                              ** 0.5
                                            * 0.0687057476331
                                            * (
                                                (
                                                  (
                                                    AMBIENT_TEMP_C
                                                    + 5
                                                    + 60
                                                      * (
                                                          LINE_CURRENT_A
                                                          / 1000
                                                        )
                                                        ** 2
                                                  )
                                                )
                                                - AMBIENT_TEMP_C
                                              ).clip(lower=0.5)
                                              ** 0.25
                                          )
                                        )
                                        + (
                                            0.4007136
                                            * (
                                                (
                                                  (
                                                    (
                                                      AMBIENT_TEMP_C
                                                      + 5
                                                      + 60
                                                        * (
                                                            LINE_CURRENT_A
                                                            / 1000
                                                          )
                                                          ** 2
                                                    )
                                                  )
                                                  + 273
                                                )
                                                ** 4
                                                / 100000000
                                                - (AMBIENT_TEMP_C + 273)
                                                  ** 4
                                                  / 100000000
                                              )
                                            / (
                                                (
                                                  (
                                                    AMBIENT_TEMP_C
                                                    + 5
                                                    + 60
                                                      * (
                                                          LINE_CURRENT_A
                                                          / 1000
                                                        )
                                                        ** 2
                                                  )
                                                )
                                                - AMBIENT_TEMP_C
                                              ).clip(lower=0.5)
                                          )
                                      )
                                      - LINE_CURRENT_A ** 2 * 2.8464e-07
                                    )
                              )
                          )
                          / 2
                        )
                      )
                      - AMBIENT_TEMP_C
                    ).clip(lower=0.5)
                )
            )
            - LINE_CURRENT_A ** 2 * 2.8464e-07
          )
    )
```

### TC_RESIDUAL_K

```python
TC_RESIDUAL_K =
    CONDUCTOR_TEMP_C - TC_EXPECTED_C
```

### DLR_A

```python
DLR_A =
    np.sqrt(
      (
        np.maximum(
          (
            (
              1.194
              - np.abs(np.cos(np.radians(WIND_DIR_DEG - 75)))
              + 0.194 * np.cos(2 * np.radians(WIND_DIR_DEG - 75))
              + 0.368 * np.abs(np.sin(2 * np.radians(WIND_DIR_DEG - 75)))
            )
            * np.maximum(
                1.01
                + 1.35
                  * (
                      0.02814
                      * (
                          (1.293 - 0.0183 + 9.18576e-05)
                          / (1 + 0.00367 * ((75 + AMBIENT_TEMP_C) / 2))
                        )
                      * WIND_SPEED_MS.clip(lower=0)
                      / (
                          1.458e-06
                          * (((75 + AMBIENT_TEMP_C) / 2) + 273) ** 1.5
                          / (((75 + AMBIENT_TEMP_C) / 2) + 383.4)
                        )
                    )
                    ** 0.52,
                0.754
                * (
                    0.02814
                    * (
                        (1.293 - 0.0183 + 9.18576e-05)
                        / (1 + 0.00367 * ((75 + AMBIENT_TEMP_C) / 2))
                      )
                    * WIND_SPEED_MS.clip(lower=0)
                    / (
                        1.458e-06
                        * (((75 + AMBIENT_TEMP_C) / 2) + 273) ** 1.5
                        / (((75 + AMBIENT_TEMP_C) / 2) + 383.4)
                      )
                  )
                  ** 0.6
              )
            * (
                0.02424
                + 7.477e-05 * ((75 + AMBIENT_TEMP_C) / 2)
                - 4.407e-09 * ((75 + AMBIENT_TEMP_C) / 2) ** 2
              )
          )
          * (75 - AMBIENT_TEMP_C),
          3.645
          * (
              (1.293 - 0.0183 + 9.18576e-05)
              / (1 + 0.00367 * ((75 + AMBIENT_TEMP_C) / 2))
            )
            ** 0.5
          * 0.0687057476331
          * (75 - AMBIENT_TEMP_C).clip(lower=0) ** 1.25
        )
        + (
            0.4007136
            * (146.66178816 - (AMBIENT_TEMP_C + 273) ** 4 / 100000000)
          )
        - 0.022512 * SOLAR_WM2.clip(lower=0)
      ).clip(lower=0)
      / 8.6286e-05
    )
```

### DLR_EMERGENCY_A

```python
DLR_EMERGENCY_A =
    np.sqrt(
      (
        np.maximum(
          (
            (
              1.194
              - np.abs(np.cos(np.radians(WIND_DIR_DEG - 75)))
              + 0.194 * np.cos(2 * np.radians(WIND_DIR_DEG - 75))
              + 0.368 * np.abs(np.sin(2 * np.radians(WIND_DIR_DEG - 75)))
            )
            * np.maximum(
                1.01
                + 1.35
                  * (
                      0.02814
                      * (
                          (1.293 - 0.0183 + 9.18576e-05)
                          / (1 + 0.00367 * ((100 + AMBIENT_TEMP_C) / 2))
                        )
                      * WIND_SPEED_MS.clip(lower=0)
                      / (
                          1.458e-06
                          * (((100 + AMBIENT_TEMP_C) / 2) + 273) ** 1.5
                          / (((100 + AMBIENT_TEMP_C) / 2) + 383.4)
                        )
                    )
                    ** 0.52,
                0.754
                * (
                    0.02814
                    * (
                        (1.293 - 0.0183 + 9.18576e-05)
                        / (1 + 0.00367 * ((100 + AMBIENT_TEMP_C) / 2))
                      )
                    * WIND_SPEED_MS.clip(lower=0)
                    / (
                        1.458e-06
                        * (((100 + AMBIENT_TEMP_C) / 2) + 273) ** 1.5
                        / (((100 + AMBIENT_TEMP_C) / 2) + 383.4)
                      )
                  )
                  ** 0.6
              )
            * (
                0.02424
                + 7.477e-05 * ((100 + AMBIENT_TEMP_C) / 2)
                - 4.407e-09 * ((100 + AMBIENT_TEMP_C) / 2) ** 2
              )
          )
          * (100 - AMBIENT_TEMP_C),
          3.645
          * (
              (1.293 - 0.0183 + 9.18576e-05)
              / (1 + 0.00367 * ((100 + AMBIENT_TEMP_C) / 2))
            )
            ** 0.5
          * 0.0687057476331
          * (100 - AMBIENT_TEMP_C).clip(lower=0) ** 1.25
        )
        + (
            0.4007136
            * (193.56878641 - (AMBIENT_TEMP_C + 273) ** 4 / 100000000)
          )
        - 0.022512 * SOLAR_WM2.clip(lower=0)
      ).clip(lower=0)
      / 9.3402e-05
    )
```

### LOAD_PCT_DLR

```python
LOAD_PCT_DLR =
    LINE_CURRENT_A / DLR_A.clip(lower=1) * 100
```

### DLR_GAIN_PCT

```python
DLR_GAIN_PCT =
    (DLR_A / 725.3 - 1) * 100
```

### SAG_MEASURED_M

```python
SAG_MEASURED_M =
    (19.5 - CLEARANCE_M)
```

### SAG_EXPECTED_M

```python
SAG_EXPECTED_M =
    (
      7.907585022
      + 0.041849928 * CONDUCTOR_TEMP_C
      - 4.1911e-05 * CONDUCTOR_TEMP_C ** 2
      + 1.4e-08 * CONDUCTOR_TEMP_C ** 3
    )
```

### CLEARANCE_EXPECTED_M

```python
CLEARANCE_EXPECTED_M =
    19.5 - SAG_EXPECTED_M
```

### CLEARANCE_RESIDUAL_M

```python
CLEARANCE_RESIDUAL_M =
    CLEARANCE_M - CLEARANCE_EXPECTED_M
```

### TC_FROM_SAG_C

```python
TC_FROM_SAG_C =
    (
      -174.969382
      + 22.6864881 * (19.5 - CLEARANCE_M)
      - 0.3695129 * (19.5 - CLEARANCE_M) ** 2
      + 0.0377831 * (19.5 - CLEARANCE_M) ** 3
    )
```

### TC_SAG_DIFF_K

```python
TC_SAG_DIFF_K =
    CONDUCTOR_TEMP_C - TC_FROM_SAG_C
```

### JOINT_DELTA_K

```python
JOINT_DELTA_K =
    JOINT_TEMP_C - CONDUCTOR_TEMP_C
```

## AlertExpression rules (12)

### OHL_OVER_DLR

High · overload_beyond_dlr

```python
OHL_OVER_DLR =
    (LINE_CURRENT_A > DLR_A) & (CONDUCTOR_TEMP_C > 70)
```

### OHL_CONDUCTOR_HOT

High · overload_beyond_dlr

```python
OHL_CONDUCTOR_HOT =
    CONDUCTOR_TEMP_C > 75
```

### OHL_CONDUCTOR_EMERGENCY

Critical

```python
OHL_CONDUCTOR_EMERGENCY =
    CONDUCTOR_TEMP_C > 100
```

### OHL_JOINT_HOT

Medium · joint_hotspot

```python
OHL_JOINT_HOT =
    (JOINT_DELTA_K > 10) & (TC_SAG_DIFF_K > -6)
```

### OHL_JOINT_CRITICAL

High · joint_hotspot

```python
OHL_JOINT_CRITICAL =
    (JOINT_DELTA_K > 25) & (TC_SAG_DIFF_K > -6)
```

### OHL_SAG_EXCESS

Medium · conductor_creep

```python
OHL_SAG_EXCESS =
    (CLEARANCE_RESIDUAL_M < -0.6)
    & (TC_SAG_DIFF_K < -12)
    & (TC_RESIDUAL_K > -10)
```

### OHL_CLEARANCE_LOW

Critical

```python
OHL_CLEARANCE_LOW =
    CLEARANCE_M < 7
```

### OHL_VEGETATION

High · vegetation_encroachment

```python
OHL_VEGETATION =
    VEGETATION_DISTANCE_M < 3
```

### OHL_SENSOR_SUSPECT

Medium · sensor_fault

```python
OHL_SENSOR_SUSPECT =
    (TC_RESIDUAL_K < -10) & (TC_SAG_DIFF_K < -12)
```

### OHL_INSULATOR_LEAKAGE

Medium · insulator_pollution

```python
OHL_INSULATOR_LEAKAGE =
    LEAKAGE_CURRENT_MA > 5
```

### OHL_INSULATOR_FLASHOVER_RISK

High · insulator_pollution

```python
OHL_INSULATOR_FLASHOVER_RISK =
    LEAKAGE_CURRENT_MA > 15
```

### OHL_VIBRATION

Medium · damper_loss

```python
OHL_VIBRATION =
    VIBRATION_UM > 150
```
