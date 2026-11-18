# PV-3101: Maximo Monitor functions and alert rules

Device type `PV_BLOCK_STRING_INV`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### CELL_TEMP_C

```python
CELL_TEMP_C =
    (MODULE_TEMP_C + POA_WM2 / 1000 * 3)
```

### TEMP_FACTOR

```python
TEMP_FACTOR =
    (1 - 0.0029 * (CELL_TEMP_C - 25))
```

### DC_EXPECTED_KW

```python
DC_EXPECTED_KW =
    (
      375.84
      * POA_WM2
      / 1000
      * TEMP_FACTOR
      * 1.056
      * 0.98
      * (
          1
          - 0.01 * np.minimum(YEARS_IN_SERVICE, 1)
          - 0.004 * np.maximum(YEARS_IN_SERVICE - 1, 0)
        )
    )
```

### SOILING_RATIO

```python
SOILING_RATIO =
    (POA_SOILED_WM2 / np.maximum(POA_WM2, 1))
```

### SOILING_LOSS_PCT

```python
SOILING_LOSS_PCT =
    ((1 - SOILING_RATIO) * 100)
```

### SOILING_LOSS_KW

```python
SOILING_LOSS_KW =
    DC_EXPECTED_KW * (1 - SOILING_RATIO)
```

### PERF_INDEX

```python
PERF_INDEX =
    (P_DC_KW / np.maximum(DC_EXPECTED_KW, 0.1))
```

### PERF_INDEX_CORR

```python
PERF_INDEX_CORR =
    (PERF_INDEX / np.maximum(SOILING_RATIO, 0.01))
```

### INV_EFF_EXPECTED

```python
INV_EFF_EXPECTED =
    np.maximum(
      1.02521531597
      * (
          -0.0162 * (np.maximum(P_DC_KW, 1) / 334.008097166)
          - 0.0059 / (np.maximum(P_DC_KW, 1) / 334.008097166)
          + 0.9858
        ),
      0
    )
```

### INV_EFF_MEASURED

```python
INV_EFF_MEASURED =
    (P_AC_KW / np.maximum(P_DC_KW, 0.1))
```

### AC_LIMIT_KW

```python
AC_LIMIT_KW =
    np.minimum(
      np.interp(AMBIENT_TEMP_C, [40, 50, 60], [330, 300, 165]),
      330 * SETPOINT_PCT / 100
    )
```

### AC_EXPECTED_KW

```python
AC_EXPECTED_KW =
    np.minimum(
      np.maximum(
        1.02521531597
        * (
            -0.0162 * (np.maximum(P_DC_KW, 1) / 334.008097166)
            - 0.0059 / (np.maximum(P_DC_KW, 1) / 334.008097166)
            + 0.9858
          ),
        0
      )
      * P_DC_KW,
      np.minimum(
        np.interp(AMBIENT_TEMP_C, [40, 50, 60], [330, 300, 165]),
        330 * SETPOINT_PCT / 100
      )
    )
```

### CLIPPING_LOSS_KW

```python
CLIPPING_LOSS_KW =
    np.maximum(
      np.maximum(
        1.02521531597
        * (
            -0.0162
            * (
                np.maximum((DC_EXPECTED_KW * SOILING_RATIO), 1)
                / 334.008097166
              )
            - 0.0059
              / (
                  np.maximum((DC_EXPECTED_KW * SOILING_RATIO), 1)
                  / 334.008097166
                )
            + 0.9858
          ),
        0
      )
      * (DC_EXPECTED_KW * SOILING_RATIO)
      - np.minimum(
          np.interp(AMBIENT_TEMP_C, [40, 50, 60], [330, 300, 165]),
          330 * SETPOINT_PCT / 100
        ),
      0
    )
```

### PR_INST

```python
PR_INST =
    (P_AC_KW / np.maximum(375.84 * POA_WM2 / 1000, 0.1))
```

### PR_TEMP_CORR

```python
PR_TEMP_CORR =
    PR_INST / TEMP_FACTOR
```

### STRING_MEAN_A

```python
STRING_MEAN_A =
    (
      (
        I_S01_A
        + I_S02_A
        + I_S03_A
        + I_S04_A
        + I_S05_A
        + I_S06_A
        + I_S07_A
        + I_S08_A
        + I_S09_A
        + I_S10_A
        + I_S11_A
        + I_S12_A
        + I_S13_A
        + I_S14_A
        + I_S15_A
        + I_S16_A
        + I_S17_A
        + I_S18_A
        + I_S19_A
        + I_S20_A
        + I_S21_A
        + I_S22_A
        + I_S23_A
        + I_S24_A
      )
      / 24
    )
```

### STRING_EXPECTED_A

```python
STRING_EXPECTED_A =
    (
      13.62
      * POA_WM2
      / 1000
      * (1 + 0.00045 * (CELL_TEMP_C - 25))
      * 1.056
      * 0.98
      * (
          1
          - 0.01 * np.minimum(YEARS_IN_SERVICE, 1)
          - 0.004 * np.maximum(YEARS_IN_SERVICE - 1, 0)
        )
      * SOILING_RATIO
    )
```

### STRING_MIN_RATIO

```python
STRING_MIN_RATIO =
    (
      np.minimum.reduce(
        [I_S01_A, I_S02_A, I_S03_A, I_S04_A, I_S05_A, I_S06_A, I_S07_A, I_S08_A, I_S09_A, I_S10_A, I_S11_A, I_S12_A, I_S13_A, I_S14_A, I_S15_A, I_S16_A, I_S17_A, I_S18_A, I_S19_A, I_S20_A, I_S21_A, I_S22_A, I_S23_A, I_S24_A]
      )
      / np.maximum(STRING_MEAN_A, 0.01)
    )
```

### INV_TEMP_EXPECTED_C

```python
INV_TEMP_EXPECTED_C =
    (AMBIENT_TEMP_C + 15 * P_AC_KW / 330)
```

### INV_TEMP_EXCESS_K

```python
INV_TEMP_EXCESS_K =
    INV_TEMP_C - INV_TEMP_EXPECTED_C
```

## AlertExpression rules (12)

### PV_RISO_TRIP

Critical · ground_fault

```python
PV_RISO_TRIP =
    RISO_KOHM < 50
```

### PV_INVERTER_DOWN

High · ground_fault

```python
PV_INVERTER_DOWN =
    (POA_WM2 >= 300) & (INV_RUNNING < 0.5)
```

### PV_STRING_OPEN

High · string_open

```python
PV_STRING_OPEN =
    (POA_WM2 >= 300) & (INV_RUNNING > 0.5) & (STRING_MIN_RATIO < 0.1)
```

### PV_DC_UNDERPERFORM

High · module_degradation

```python
PV_DC_UNDERPERFORM =
    (POA_WM2 >= 300)
    & (INV_RUNNING > 0.5)
    & (P_AC_KW < 0.98 * P_MAX_KW)
    & (PERF_INDEX_CORR < 0.92)
```

### PV_CLEANING_DUE

Medium · soiling

```python
PV_CLEANING_DUE =
    (POA_WM2 >= 300) & (SOILING_LOSS_PCT >= 8.04084401128)
```

### PV_STRING_LOW

Medium · string_bypass

```python
PV_STRING_LOW =
    (POA_WM2 >= 300)
    & (INV_RUNNING > 0.5)
    & (STRING_MIN_RATIO >= 0.1)
    & (STRING_MIN_RATIO < 0.9)
```

### PV_RISO_LOW

Medium · ground_fault

```python
PV_RISO_LOW =
    (RISO_KOHM >= 50) & (RISO_KOHM < 500)
```

### PV_INV_EFF_LOW

Medium · inverter_efficiency

```python
PV_INV_EFF_LOW =
    (INV_RUNNING > 0.5)
    & (P_DC_KW > 33)
    & (
        INV_EFF_MEASURED
        < np.maximum(
            1.02521531597
            * (
                -0.0162 * (np.maximum(P_DC_KW, 1) / 334.008097166)
                - 0.0059 / (np.maximum(P_DC_KW, 1) / 334.008097166)
                + 0.9858
              ),
            0
          )
          - 0.015
      )
```

### PV_INV_HOT

Medium · inverter_cooling

```python
PV_INV_HOT =
    (INV_RUNNING > 0.5) & (INV_TEMP_EXCESS_K > 10)
```

### PV_DERATE_EARLY

Medium · inverter_cooling

```python
PV_DERATE_EARLY =
    (INV_RUNNING > 0.5)
    & (
        P_MAX_KW
        < np.minimum(
            np.interp(AMBIENT_TEMP_C, [40, 50, 60], [330, 300, 165]),
            330 * SETPOINT_PCT / 100
          )
          - 16.5
      )
```

### PV_IRRADIANCE_SENSOR

Medium · irradiance_sensor

```python
PV_IRRADIANCE_SENSOR =
    (POA_WM2 >= 300)
    & (
        (
          (INV_RUNNING > 0.5)
          & (P_AC_KW < 0.98 * P_MAX_KW)
          & (PERF_INDEX > 1.06)
        )
        | (SOILING_RATIO > 1.03)
      )
```

### PV_SOILING_HIGH

Low · soiling

```python
PV_SOILING_HIGH =
    (POA_WM2 >= 300)
    & (SOILING_LOSS_PCT >= 3)
    & (SOILING_LOSS_PCT < 8.04084401128)
```
