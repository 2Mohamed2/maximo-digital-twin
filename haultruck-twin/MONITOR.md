# HT-4001: Maximo Monitor functions and alert rules

Device type `MINING_HAUL_TRUCK`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### PAYLOAD_PCT

```python
PAYLOAD_PCT =
    PAYLOAD_T / 226.8 * 100
```

### GVW_T

```python
GVW_T =
    (163.289 + PAYLOAD_T)
```

### WHEEL_POWER_KW

```python
WHEEL_POWER_KW =
    np.maximum(
      (163.289 + PAYLOAD_T) * 9.81 * SPEED_KMH / 3.6 * (GRADE_PCT + 3) / 100,
      0
    )
```

### ENGINE_POWER_EXP_KW

```python
ENGINE_POWER_EXP_KW =
    np.where(
      SPEED_KMH < 1,
      40,
      np.minimum(
        np.maximum(
          (163.289 + PAYLOAD_T)
          * 9.81
          * SPEED_KMH
          / 3.6
          * (GRADE_PCT + 3)
          / 100,
          0
        )
        / 0.82
        + 128,
        1976
      )
    )
```

### FUEL_EXP_LPH

```python
FUEL_EXP_LPH =
    (
      15
      + np.where(
          SPEED_KMH < 1,
          40,
          np.minimum(
            np.maximum(
              (163.289 + PAYLOAD_T)
              * 9.81
              * SPEED_KMH
              / 3.6
              * (GRADE_PCT + 3)
              / 100,
              0
            )
            / 0.82
            + 128,
            1976
          )
        )
        * 0.235571260306
    )
```

### FUEL_RATIO

```python
FUEL_RATIO =
    FUEL_LPH / FUEL_EXP_LPH
```

### BOOST_RATIO

```python
BOOST_RATIO =
    (
      BOOST_KPA
      / (
          30
          + 220
            * (
                np.where(
                  SPEED_KMH < 1,
                  40,
                  np.minimum(
                    np.maximum(
                      (163.289 + PAYLOAD_T)
                      * 9.81
                      * SPEED_KMH
                      / 3.6
                      * (GRADE_PCT + 3)
                      / 100,
                      0
                    )
                    / 0.82
                    + 128,
                    1976
                  )
                )
                / 1976
              )
        )
    )
```

### EXH_RESID_C

```python
EXH_RESID_C =
    (
      (EXH_LEFT_C + EXH_RIGHT_C) / 2
      - (
          300
          + 320
            * (
                np.where(
                  SPEED_KMH < 1,
                  40,
                  np.minimum(
                    np.maximum(
                      (163.289 + PAYLOAD_T)
                      * 9.81
                      * SPEED_KMH
                      / 3.6
                      * (GRADE_PCT + 3)
                      / 100,
                      0
                    )
                    / 0.82
                    + 128,
                    1976
                  )
                )
                / 1976
              )
        )
    )
```

### EXH_SPREAD_C

```python
EXH_SPREAD_C =
    np.abs(EXH_LEFT_C - EXH_RIGHT_C)
```

### COOLANT_EXP_C

```python
COOLANT_EXP_C =
    np.maximum(
      90,
      AMBIENT_C
      + 55
        * (
            np.where(
              SPEED_KMH < 1,
              40,
              np.minimum(
                np.maximum(
                  (163.289 + PAYLOAD_T)
                  * 9.81
                  * SPEED_KMH
                  / 3.6
                  * (GRADE_PCT + 3)
                  / 100,
                  0
                )
                / 0.82
                + 128,
                1976
              )
            )
            / 1976
          )
    )
```

### COOLANT_RESID_C

```python
COOLANT_RESID_C =
    COOLANT_C
    - np.maximum(
        90,
        AMBIENT_C
        + 55
          * (
              np.where(
                SPEED_KMH < 1,
                40,
                np.minimum(
                  np.maximum(
                    (163.289 + PAYLOAD_T)
                    * 9.81
                    * SPEED_KMH
                    / 3.6
                    * (GRADE_PCT + 3)
                    / 100,
                    0
                  )
                  / 0.82
                  + 128,
                  1976
                )
              )
              / 1976
            )
      )
```

### BLOWBY_RESID_KPA

```python
BLOWBY_RESID_KPA =
    (
      CRANKCASE_KPA
      - (
          0.3
          + 0.6
            * (
                np.where(
                  SPEED_KMH < 1,
                  40,
                  np.minimum(
                    np.maximum(
                      (163.289 + PAYLOAD_T)
                      * 9.81
                      * SPEED_KMH
                      / 3.6
                      * (GRADE_PCT + 3)
                      / 100,
                      0
                    )
                    / 0.82
                    + 128,
                    1976
                  )
                )
                / 1976
              )
        )
    )
```

### FE_PER_250H

```python
FE_PER_250H =
    OIL_FE_PPM * 250 / OIL_HOURS
```

### HYD_ISO_EXCESS

```python
HYD_ISO_EXCESS =
    np.maximum(np.maximum(HYD_ISO4 - 18, HYD_ISO6 - 16), HYD_ISO14 - 13)
```

### TYRE_COLD_MIN_PCT

```python
TYRE_COLD_MIN_PCT =
    (
      np.minimum(
        np.minimum(
          np.minimum(
            np.minimum(
              np.minimum(
                (
                  (TYRE1_KPA + 101.325)
                  * (AMBIENT_C + 273.15)
                  / (TYRE1_C + 273.15)
                  - 101.325
                ),
                (
                  (TYRE2_KPA + 101.325)
                  * (AMBIENT_C + 273.15)
                  / (TYRE2_C + 273.15)
                  - 101.325
                )
              ),
              (
                (TYRE3_KPA + 101.325)
                * (AMBIENT_C + 273.15)
                / (TYRE3_C + 273.15)
                - 101.325
              )
            ),
            (
              (TYRE4_KPA + 101.325)
              * (AMBIENT_C + 273.15)
              / (TYRE4_C + 273.15)
              - 101.325
            )
          ),
          (
            (TYRE5_KPA + 101.325)
            * (AMBIENT_C + 273.15)
            / (TYRE5_C + 273.15)
            - 101.325
          )
        ),
        (
          (TYRE6_KPA + 101.325) * (AMBIENT_C + 273.15) / (TYRE6_C + 273.15)
          - 101.325
        )
      )
      / 650
      * 100
    )
```

### TYRE_TEMP_MAX_C

```python
TYRE_TEMP_MAX_C =
    np.maximum(
      np.maximum(
        np.maximum(
          np.maximum(np.maximum(TYRE1_C, TYRE2_C), TYRE3_C),
          TYRE4_C
        ),
        TYRE5_C
      ),
      TYRE6_C
    )
```

### TYRE_LOAD_PCT

```python
TYRE_LOAD_PCT =
    (
      np.where(
        PAYLOAD_T > 1,
        np.maximum(
          (163.289 + PAYLOAD_T) * 0.165,
          (163.289 + PAYLOAD_T) * 0.1675
        ),
        np.maximum(
          (163.289 + PAYLOAD_T) * 0.245,
          (163.289 + PAYLOAD_T) * 0.1275
        )
      )
      / 67
      * 100
    )
```

### TKPH_SITE

```python
TKPH_SITE =
    (
      np.maximum(
        ((40.005805 + (163.289 + SHIFT_PAYLOAD_MEAN_T) * 0.165) / 2),
        ((20.8193475 + (163.289 + SHIFT_PAYLOAD_MEAN_T) * 0.1675) / 2)
      )
      * (CYCLE_KM / (CYCLE_MIN / 60))
      * np.interp(
          CYCLE_KM,
          [5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 40, 50],
          [1, 1.04, 1.06, 1.09, 1.1, 1.12, 1.14, 1.16, 1.17, 1.18, 1.19, 1.2, 1.21, 1.22, 1.23]
        )
      * (
          1
          / (
              1
              - np.where(AMBIENT_MAX_C > 38, 0.4, 0.25)
                * (AMBIENT_MAX_C - 38)
                / (CYCLE_KM / (CYCLE_MIN / 60))
            )
        )
    )
```

### TKPH_RATIO

```python
TKPH_RATIO =
    TKPH_SITE / 1286
```

### FUEL_LIFE_PCT

```python
FUEL_LIFE_PCT =
    FUEL_TOTAL_L / 3785411 * 100
```

## AlertExpression rules (15)

### HT_OVERLOAD_120

Critical

```python
HT_OVERLOAD_120 =
    (PAYLOAD_T / 226.8 * 100) > 120
```

### HT_PAYLOAD_POLICY

High · payload_overload

```python
HT_PAYLOAD_POLICY =
    (SHIFT_OVER110_PCT > 10) | (SHIFT_PAYLOAD_MEAN_T > 226.8)
```

### HT_EXH_HIGH

High · air_intake_restriction

```python
HT_EXH_HIGH =
    (
      (
        np.where(
          SPEED_KMH < 1,
          40,
          np.minimum(
            np.maximum(
              (163.289 + PAYLOAD_T)
              * 9.81
              * SPEED_KMH
              / 3.6
              * (GRADE_PCT + 3)
              / 100,
              0
            )
            / 0.82
            + 128,
            1976
          )
        )
        / 1976
      )
      > 0.5
    )
    & (EXH_RESID_C > 70)
```

### HT_EXH_SPREAD

High · injector_fault

```python
HT_EXH_SPREAD =
    (
      (
        np.where(
          SPEED_KMH < 1,
          40,
          np.minimum(
            np.maximum(
              (163.289 + PAYLOAD_T)
              * 9.81
              * SPEED_KMH
              / 3.6
              * (GRADE_PCT + 3)
              / 100,
              0
            )
            / 0.82
            + 128,
            1976
          )
        )
        / 1976
      )
      > 0.5
    )
    & (np.abs(EXH_LEFT_C - EXH_RIGHT_C) > 50)
```

### HT_COOLANT_HIGH

High · cooling_degraded

```python
HT_COOLANT_HIGH =
    COOLANT_RESID_C > 8
```

### HT_TYRE_PRESSURE_LOW

High · tyre_underinflation

```python
HT_TYRE_PRESSURE_LOW =
    TYRE_COLD_MIN_PCT < 90
```

### HT_TYRE_TEMP_HIGH

High · tyre_underinflation

```python
HT_TYRE_TEMP_HIGH =
    np.maximum(
      np.maximum(
        np.maximum(
          np.maximum(np.maximum(TYRE1_C, TYRE2_C), TYRE3_C),
          TYRE4_C
        ),
        TYRE5_C
      ),
      TYRE6_C
    )
    > 85
```

### HT_TKPH_LIMIT

High · tkph_exceeded

```python
HT_TKPH_LIMIT =
    TKPH_RATIO > 1
```

### HT_OVERLOAD_110

Medium · payload_overload

```python
HT_OVERLOAD_110 =
    ((PAYLOAD_T / 226.8 * 100) > 110) & ((PAYLOAD_T / 226.8 * 100) <= 120)
```

### HT_FUEL_HIGH

Medium · air_intake_restriction

```python
HT_FUEL_HIGH =
    (
      (
        np.where(
          SPEED_KMH < 1,
          40,
          np.minimum(
            np.maximum(
              (163.289 + PAYLOAD_T)
              * 9.81
              * SPEED_KMH
              / 3.6
              * (GRADE_PCT + 3)
              / 100,
              0
            )
            / 0.82
            + 128,
            1976
          )
        )
        / 1976
      )
      > 0.5
    )
    & (FUEL_RATIO > 1.12)
```

### HT_BOOST_LOW

Medium · air_intake_restriction

```python
HT_BOOST_LOW =
    (
      (
        np.where(
          SPEED_KMH < 1,
          40,
          np.minimum(
            np.maximum(
              (163.289 + PAYLOAD_T)
              * 9.81
              * SPEED_KMH
              / 3.6
              * (GRADE_PCT + 3)
              / 100,
              0
            )
            / 0.82
            + 128,
            1976
          )
        )
        / 1976
      )
      > 0.5
    )
    & (BOOST_RATIO < 0.85)
```

### HT_BLOWBY_HIGH

Medium · dust_ingestion

```python
HT_BLOWBY_HIGH =
    BLOWBY_RESID_KPA > 0.8
```

### HT_OIL_WEAR

Medium · dust_ingestion

```python
HT_OIL_WEAR =
    FE_PER_250H > 40
```

### HT_OIL_DIRT

Medium · dust_ingestion

```python
HT_OIL_DIRT =
    OIL_SI_PPM > 15
```

### HT_HYD_CLEANLINESS

Medium · hydraulic_contamination

```python
HT_HYD_CLEANLINESS =
    np.maximum(np.maximum(HYD_ISO4 - 18, HYD_ISO6 - 16), HYD_ISO14 - 13) > 0
```
