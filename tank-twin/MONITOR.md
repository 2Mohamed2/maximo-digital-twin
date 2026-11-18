# TK-2701: Maximo Monitor functions and alert rules

Device type `STORAGE_TANK_EFR`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### TOV_M3

```python
TOV_M3 =
    1256.637 * LEVEL_MM / 1000
```

### CTSH

```python
CTSH =
    (
      1
      + 2 * 1.12e-05 * (PRODUCT_TEMP_C - 15)
      + 1.12e-05 ** 2 * (PRODUCT_TEMP_C - 15) ** 2
    )
```

### VCF

```python
VCF =
    np.exp(
      -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
      * (PRODUCT_TEMP_C - 15)
      * (
          1
          + 0.8
            * (613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
            * (PRODUCT_TEMP_C - 15)
        )
    )
```

### FRA_M3

```python
FRA_M3 =
    np.where(
      LEVEL_MM >= 1085.96928699,
      90000
      / (
          DENSITY15_KGM3
          * np.exp(
              -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
              * (PRODUCT_TEMP_C - 15)
              * (
                  1
                  + 0.8
                    * (613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                    * (PRODUCT_TEMP_C - 15)
                )
            )
        ),
      0
    )
```

### GSV_M3

```python
GSV_M3 =
    (
      (
        (1256.637 * LEVEL_MM / 1000 - 1256.637 * WATER_LEVEL_MM / 1000)
        * CTSH
        - np.where(
            LEVEL_MM >= 1085.96928699,
            90000
            / (
                DENSITY15_KGM3
                * np.exp(
                    -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                    * (PRODUCT_TEMP_C - 15)
                    * (
                        1
                        + 0.8
                          * (
                              613.9723 / DENSITY15_KGM3 ** 2
                              + 0 / DENSITY15_KGM3
                            )
                          * (PRODUCT_TEMP_C - 15)
                      )
                  )
              ),
            0
          )
      )
      * np.exp(
          -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
          * (PRODUCT_TEMP_C - 15)
          * (
              1
              + 0.8
                * (613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                * (PRODUCT_TEMP_C - 15)
            )
        )
    )
```

### MASS_T

```python
MASS_T =
    GSV_M3 * DENSITY15_KGM3 / 1000
```

### ROOM_TO_HH_M3

```python
ROOM_TO_HH_M3 =
    (16005 - LEVEL_MM) * 1256.637 / 1000
```

### TIME_TO_HH_MIN

```python
TIME_TO_HH_MIN =
    np.where(
      (INFLOW_M3H - OUTFLOW_M3H) > 1,
      np.maximum(16005 - LEVEL_MM, 0)
      * 1256.637
      / 1000
      / np.maximum((INFLOW_M3H - OUTFLOW_M3H), 1)
      * 60,
      9999
    )
```

### GAUGE_DIFF_MM

```python
GAUGE_DIFF_MM =
    LEVEL_MM - LEVEL2_MM
```

### MV_IMBALANCE_M3

```python
MV_IMBALANCE_M3 =
    (
      (
        (
          (
            1256.637 * MV_CLOSE_LEVEL_MM / 1000
            - 1256.637 * WATER_LEVEL_MM / 1000
          )
          * (
              1
              + 2 * 1.12e-05 * (MV_CLOSE_TEMP_C - 15)
              + 1.12e-05 ** 2 * (MV_CLOSE_TEMP_C - 15) ** 2
            )
          - np.where(
              MV_CLOSE_LEVEL_MM >= 1085.96928699,
              90000
              / (
                  DENSITY15_KGM3
                  * np.exp(
                      -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                      * (MV_CLOSE_TEMP_C - 15)
                      * (
                          1
                          + 0.8
                            * (
                                613.9723 / DENSITY15_KGM3 ** 2
                                + 0 / DENSITY15_KGM3
                              )
                            * (MV_CLOSE_TEMP_C - 15)
                        )
                    )
                ),
              0
            )
        )
        * np.exp(
            -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
            * (MV_CLOSE_TEMP_C - 15)
            * (
                1
                + 0.8
                  * (613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                  * (MV_CLOSE_TEMP_C - 15)
              )
          )
      )
      - (
          (
            (
              1256.637 * MV_OPEN_LEVEL_MM / 1000
              - 1256.637 * WATER_LEVEL_MM / 1000
            )
            * (
                1
                + 2 * 1.12e-05 * (MV_OPEN_TEMP_C - 15)
                + 1.12e-05 ** 2 * (MV_OPEN_TEMP_C - 15) ** 2
              )
            - np.where(
                MV_OPEN_LEVEL_MM >= 1085.96928699,
                90000
                / (
                    DENSITY15_KGM3
                    * np.exp(
                        -(
                           613.9723 / DENSITY15_KGM3 ** 2
                           + 0 / DENSITY15_KGM3
                         )
                        * (MV_OPEN_TEMP_C - 15)
                        * (
                            1
                            + 0.8
                              * (
                                  613.9723 / DENSITY15_KGM3 ** 2
                                  + 0 / DENSITY15_KGM3
                                )
                              * (MV_OPEN_TEMP_C - 15)
                          )
                      )
                  ),
                0
              )
          )
          * np.exp(
              -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
              * (MV_OPEN_TEMP_C - 15)
              * (
                  1
                  + 0.8
                    * (613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                    * (MV_OPEN_TEMP_C - 15)
                )
            )
        )
      - MV_METER_M3
    )
```

### MV_IMBALANCE_PCT

```python
MV_IMBALANCE_PCT =
    (MV_IMBALANCE_M3 / np.maximum(np.abs(MV_METER_M3), 1) * 100)
```

### STATIC_LOSS_M3H

```python
STATIC_LOSS_M3H =
    (
      (
        (
          (
            (
              1256.637 * ST_OPEN_LEVEL_MM / 1000
              - 1256.637 * WATER_LEVEL_MM / 1000
            )
            * (
                1
                + 2 * 1.12e-05 * (ST_OPEN_TEMP_C - 15)
                + 1.12e-05 ** 2 * (ST_OPEN_TEMP_C - 15) ** 2
              )
            - np.where(
                ST_OPEN_LEVEL_MM >= 1085.96928699,
                90000
                / (
                    DENSITY15_KGM3
                    * np.exp(
                        -(
                           613.9723 / DENSITY15_KGM3 ** 2
                           + 0 / DENSITY15_KGM3
                         )
                        * (ST_OPEN_TEMP_C - 15)
                        * (
                            1
                            + 0.8
                              * (
                                  613.9723 / DENSITY15_KGM3 ** 2
                                  + 0 / DENSITY15_KGM3
                                )
                              * (ST_OPEN_TEMP_C - 15)
                          )
                      )
                  ),
                0
              )
          )
          * np.exp(
              -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
              * (ST_OPEN_TEMP_C - 15)
              * (
                  1
                  + 0.8
                    * (613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                    * (ST_OPEN_TEMP_C - 15)
                )
            )
        )
        - (
            (
              (
                1256.637 * ST_CLOSE_LEVEL_MM / 1000
                - 1256.637 * WATER_LEVEL_MM / 1000
              )
              * (
                  1
                  + 2 * 1.12e-05 * (ST_CLOSE_TEMP_C - 15)
                  + 1.12e-05 ** 2 * (ST_CLOSE_TEMP_C - 15) ** 2
                )
              - np.where(
                  ST_CLOSE_LEVEL_MM >= 1085.96928699,
                  90000
                  / (
                      DENSITY15_KGM3
                      * np.exp(
                          -(
                             613.9723 / DENSITY15_KGM3 ** 2
                             + 0 / DENSITY15_KGM3
                           )
                          * (ST_CLOSE_TEMP_C - 15)
                          * (
                              1
                              + 0.8
                                * (
                                    613.9723 / DENSITY15_KGM3 ** 2
                                    + 0 / DENSITY15_KGM3
                                  )
                                * (ST_CLOSE_TEMP_C - 15)
                            )
                        )
                    ),
                  0
                )
            )
            * np.exp(
                -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                * (ST_CLOSE_TEMP_C - 15)
                * (
                    1
                    + 0.8
                      * (
                          613.9723 / DENSITY15_KGM3 ** 2
                          + 0 / DENSITY15_KGM3
                        )
                      * (ST_CLOSE_TEMP_C - 15)
                  )
              )
          )
      )
      / np.maximum(ST_HOURS, 0.1)
    )
```

### ROOF_TILT_MM

```python
ROOF_TILT_MM =
    np.maximum(np.maximum(ROOF_H1_MM, ROOF_H2_MM), ROOF_H3_MM)
    - np.minimum(np.minimum(ROOF_H1_MM, ROOF_H2_MM), ROOF_H3_MM)
```

### ROOF_DRAFT_RATIO

```python
ROOF_DRAFT_RATIO =
    (
      (LEVEL_MM + 900 - ((ROOF_H1_MM + ROOF_H2_MM + ROOF_H3_MM) / 3))
      / (
          90000
          / (
              DENSITY15_KGM3
              * np.exp(
                  -(613.9723 / DENSITY15_KGM3 ** 2 + 0 / DENSITY15_KGM3)
                  * (PRODUCT_TEMP_C - 15)
                  * (
                      1
                      + 0.8
                        * (
                            613.9723 / DENSITY15_KGM3 ** 2
                            + 0 / DENSITY15_KGM3
                          )
                        * (PRODUCT_TEMP_C - 15)
                    )
                )
              * 1231.63
            )
          * 1000
        )
    )
```

### BOTTOM_RATE_MM_Y

```python
BOTTOM_RATE_MM_Y =
    (
      (BOTTOM_T_PREV_MM - BOTTOM_T_MM)
      / np.maximum(BOTTOM_YEARS_BETWEEN, 0.1)
    )
```

### BOTTOM_MRT_MM

```python
BOTTOM_MRT_MM =
    (
      BOTTOM_T_MM
      - BOTTOM_RATE_MM_Y * np.maximum(10 - YEARS_SINCE_INTERNAL, 0)
    )
```

### BOTTOM_LIFE_Y

```python
BOTTOM_LIFE_Y =
    (BOTTOM_T_MM - 2.54) / np.maximum(BOTTOM_RATE_MM_Y, 0.001)
```

### SHELL_RATE_MM_Y

```python
SHELL_RATE_MM_Y =
    ((SHELL_T_PREV_MM - SHELL_T_MM) / np.maximum(SHELL_YEARS_BETWEEN, 0.1))
```

### SHELL_UT_INTERVAL_Y

```python
SHELL_UT_INTERVAL_Y =
    np.minimum(
      (SHELL_T_MM - 14.23) / (2 * np.maximum(SHELL_RATE_MM_Y, 0.001)),
      15
    )
```

## AlertExpression rules (15)

### TANK_LEVEL_CH

Critical · overfill

```python
TANK_LEVEL_CH =
    (LEVEL_MM >= 17000) | (LEVEL2_MM >= 17000)
```

### TANK_STATIC_LOSS

Critical · bottom_leak

```python
TANK_STATIC_LOSS =
    (ST_HOURS >= 4) & (STATIC_LOSS_M3H > 0.4)
```

### TANK_LEVEL_HH

High · overfill

```python
TANK_LEVEL_HH =
    ((LEVEL_MM >= 16005) | (HH_SWITCH > 0.5))
    & (LEVEL_MM < 17000)
    & (LEVEL2_MM < 17000)
```

### TANK_ROOF_TILT

High · roof_tilt

```python
TANK_ROOF_TILT =
    ROOF_TILT_MM > 100
```

### TANK_RIM_GAS

High · rim_seal_damage

```python
TANK_RIM_GAS =
    RIM_GAS_LEL_PCT > 10
```

### TANK_BOTTOM_MRT

High · bottom_corrosion

```python
TANK_BOTTOM_MRT =
    BOTTOM_MRT_MM < 2.54
```

### TANK_SHELL_TMIN

High

```python
TANK_SHELL_TMIN =
    SHELL_T_MM < 14.23
```

### TANK_OVERFILL_TIME

Medium · overfill

```python
TANK_OVERFILL_TIME =
    (
      np.where(
        (INFLOW_M3H - OUTFLOW_M3H) > 1,
        np.maximum(16005 - LEVEL_MM, 0)
        * 1256.637
        / 1000
        / np.maximum((INFLOW_M3H - OUTFLOW_M3H), 1)
        * 60,
        9999
      )
      < 30
    )
    & (LEVEL_MM < 16005)
    & (HH_SWITCH < 0.5)
```

### TANK_GAUGE_MISMATCH

Medium · gauge_drift

```python
TANK_GAUGE_MISMATCH =
    np.abs(LEVEL_MM - LEVEL2_MM) > 10
```

### TANK_METER_IMBALANCE

Medium · meter_error

```python
TANK_METER_IMBALANCE =
    (np.abs(MV_METER_M3) >= 500) & (np.abs(MV_IMBALANCE_PCT) > 0.3)
```

### TANK_ROOF_LOW

Medium · roof_drain_blocked

```python
TANK_ROOF_LOW =
    (LEVEL_MM >= 1385.96928699) & (ROOF_DRAFT_RATIO > 1.3)
```

### TANK_ROOF_LANDING

Medium

```python
TANK_ROOF_LANDING =
    LEVEL_MM < 1385.96928699
```

### TANK_BOTTOM_RATE

Medium · bottom_corrosion

```python
TANK_BOTTOM_RATE =
    BOTTOM_RATE_MM_Y > 0.2
```

### TANK_UT_OVERDUE

Medium

```python
TANK_UT_OVERDUE =
    YEARS_SINCE_UT
    > np.minimum(
        (SHELL_T_MM - 14.23) / (2 * np.maximum(SHELL_RATE_MM_Y, 0.001)),
        15
      )
```

### TANK_INTERNAL_OVERDUE

Medium

```python
TANK_INTERNAL_OVERDUE =
    YEARS_SINCE_INTERNAL > 10
```
