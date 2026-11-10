# UGC-801: Maximo Monitor functions and alert rules

Device type `HV_CABLE_XLPE`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (13)

### LOAD_A

```python
LOAD_A =
    ((CURRENT_L1_A + CURRENT_L2_A + CURRENT_L3_A) / 3)
```

### CROSSING_EXPECTED_C

```python
CROSSING_EXPECTED_C =
    (
      SOIL_AMBIENT_C
      + (
          LOAD_EQ_A.clip(lower=0) ** 2
          * (
              2.47e-05
              * (
                  1
                  + 0.00403
                    * (
                        (
                          (
                            SOIL_AMBIENT_C
                            + LOAD_EQ_A.clip(lower=0) ** 2
                              * (
                                  2.47e-05
                                  * (
                                      1
                                      + 0.00403
                                        * ((SOIL_AMBIENT_C + 40) - 20)
                                    )
                                  * 1.12509
                                )
                              * 2.6759184
                            + 1.071783756
                          )
                        )
                        - 20
                      )
                )
              * 1.12509
            )
          * 1.02
          + 0.4383
        )
        * 2.25992
    )
```

### CROSSING_RESIDUAL_K

```python
CROSSING_RESIDUAL_K =
    DTS_SEG07_C - CROSSING_EXPECTED_C
```

### NORMAL_EXPECTED_C

```python
NORMAL_EXPECTED_C =
    (
      SOIL_AMBIENT_C
      + (
          LOAD_EQ_A.clip(lower=0) ** 2
          * (
              2.47e-05
              * (
                  1
                  + 0.00403
                    * (
                        (
                          (
                            SOIL_AMBIENT_C
                            + LOAD_EQ_A.clip(lower=0) ** 2
                              * (
                                  2.47e-05
                                  * (
                                      1
                                      + 0.00403
                                        * ((SOIL_AMBIENT_C + 40) - 20)
                                    )
                                  * 1.12509
                                )
                              * 2.3378904
                            + 0.926531136
                          )
                        )
                        - 20
                      )
                )
              * 1.12509
            )
          * 1.02
          + 0.4383
        )
        * 1.92852
    )
```

### CONDUCTOR_TEMP_C

```python
CONDUCTOR_TEMP_C =
    (
      DTS_MAX_C
      + LOAD_A ** 2
        * (
            2.47e-05
            * (
                1
                + 0.00403
                  * (
                      (
                        (
                          DTS_MAX_C
                          + LOAD_A ** 2
                            * (
                                2.47e-05
                                * (1 + 0.00403 * ((DTS_MAX_C + 10) - 20))
                                * 1.12509
                              )
                            * 0.3708
                          + 0.08126082
                        )
                      )
                      - 20
                    )
              )
            * 1.12509
          )
        * 0.3708
      + 0.08126082
    )
```

### RATING_A

```python
RATING_A =
    np.sqrt(
      (90 - SOIL_AMBIENT_C - 1.071783756).clip(lower=0) / 9.53410994491e-05
    )
```

### RATING_UTILISATION

```python
RATING_UTILISATION =
    LOAD_EQ_A.clip(lower=0)
    / np.sqrt(
        (90 - SOIL_AMBIENT_C - 1.071783756).clip(lower=0)
        / 9.53410994491e-05
      ).clip(lower=1)
```

### SHEATH_EXPECTED_A

```python
SHEATH_EXPECTED_A =
    0.03 * LOAD_A
```

### SHEATH_RATIO

```python
SHEATH_RATIO =
    SHEATH_CURRENT_A / LOAD_A.clip(lower=1)
```

### TERM_EXPECTED_C

```python
TERM_EXPECTED_C =
    (AIR_TEMP_C + 12 * (LOAD_A / 1000) ** 2)
```

### TERM_RESIDUAL_K

```python
TERM_RESIDUAL_K =
    TERM_A_TEMP_C - TERM_EXPECTED_C
```

### LOSSES_KW_KM

```python
LOSSES_KW_KM =
    3
    * (
        LOAD_A ** 2
        * (2.47e-05 * (1 + 0.00403 * ((CONDUCTOR_TEMP_C) - 20)) * 1.12509)
        * 1.02
        + 0.4383
      )
```

### FIBRE_SHORTFALL_KM

```python
FIBRE_SHORTFALL_KM =
    3.6 - DTS_FIBRE_KM
```

## AlertExpression rules (12)

### UGC_CONDUCTOR_LIMIT

Critical · overload

```python
UGC_CONDUCTOR_LIMIT =
    (DTS_FIBRE_KM >= 3.6 - 0.05) & (CONDUCTOR_TEMP_C > 90)
```

### UGC_CONDUCTOR_HOT

High · overload

```python
UGC_CONDUCTOR_HOT =
    (DTS_FIBRE_KM >= 3.6 - 0.05)
    & (CONDUCTOR_TEMP_C > 85)
    & (CONDUCTOR_TEMP_C <= 90)
```

### UGC_CROSSING_HOT

Medium · soil_drying

```python
UGC_CROSSING_HOT =
    (DTS_FIBRE_KM >= 3.6 - 0.05)
    & (CROSSING_RESIDUAL_K > 6)
    & (LOAD_EQ_A.clip(lower=0) > 150)
```

### UGC_OVERLOAD

High · overload

```python
UGC_OVERLOAD =
    RATING_UTILISATION > 1
```

### UGC_RATING_HIGH

Low

```python
UGC_RATING_HIGH =
    (RATING_UTILISATION > 0.9) & (RATING_UTILISATION <= 1)
```

### UGC_BONDING_FAULT

High · cross_bonding_fault

```python
UGC_BONDING_FAULT =
    (SHEATH_RATIO > 0.12) & (LOAD_A > 100)
```

### UGC_JACKET_LEAKAGE

Medium · jacket_damage

```python
UGC_JACKET_LEAKAGE =
    SHEATH_LEAKAGE_MA > 1
```

### UGC_PD_JOINT

Medium · joint_pd

```python
UGC_PD_JOINT =
    (PD_JOINT_PC > 100) & (PD_JOINT_PC <= 500)
```

### UGC_PD_JOINT_HIGH

High · joint_pd

```python
UGC_PD_JOINT_HIGH =
    PD_JOINT_PC > 500
```

### UGC_PD_TERMINATION

Medium

```python
UGC_PD_TERMINATION =
    PD_TERM_PC > 100
```

### UGC_TERMINATION_HOT

Medium · termination_overheating

```python
UGC_TERMINATION_HOT =
    TERM_RESIDUAL_K > 15
```

### UGC_DTS_FIBRE

Medium · dts_fibre_break

```python
UGC_DTS_FIBRE =
    ~(DTS_FIBRE_KM >= 3.6 - 0.05)
```
