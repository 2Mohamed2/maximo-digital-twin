# AC-4601: Maximo Monitor functions and alert rules

Device type `SCREW_AIR_COMPRESSOR`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### FLOW_FAD_M3MIN

```python
FLOW_FAD_M3MIN =
    (
      FLOW_NM3MIN
      * (1.01325 / INLET_PRESSURE_BARA)
      * (INLET_TEMP_C + 273.15)
      / 273.15
    )
```

### FAD_EXPECTED_M3MIN

```python
FAD_EXPECTED_M3MIN =
    (16.6588 * (1 - 0.02 * (DISCHARGE_PRESSURE_BARG - 8.6184)))
```

### FAD_RATIO

```python
FAD_RATIO =
    (FLOW_FAD_M3MIN / np.maximum((LOAD_PCT / 100), 0.01))
    / FAD_EXPECTED_M3MIN
```

### P_LOAD_EXPECTED_KW

```python
P_LOAD_EXPECTED_KW =
    (
      INLET_PRESSURE_BARA
      * 100000
      * FAD_EXPECTED_M3MIN
      / 60
      * 3.5
      * (
          (
            (DISCHARGE_PRESSURE_BARG + INLET_PRESSURE_BARA)
            / INLET_PRESSURE_BARA
          )
          ** 0.2857142857
          - 1
        )
      / 1000
      / 0.8144
    )
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    (
      (LOAD_PCT / 100) * P_LOAD_EXPECTED_KW
      + np.minimum(LOAD_CYCLES_PER_H * 40 / 3600, 1 - (LOAD_PCT / 100))
        * (P_LOAD_EXPECTED_KW + 20.7)
        / 2
      + (
          1
          - (LOAD_PCT / 100)
          - np.minimum(LOAD_CYCLES_PER_H * 40 / 3600, 1 - (LOAD_PCT / 100))
        )
        * 20.7
    )
```

### POWER_RATIO

```python
POWER_RATIO =
    PACKAGE_POWER_KW / POWER_EXPECTED_KW
```

### SPEC_POWER_KW_M3MIN

```python
SPEC_POWER_KW_M3MIN =
    (PACKAGE_POWER_KW / FLOW_FAD_M3MIN)
```

### SPEC_POWER_EXPECTED

```python
SPEC_POWER_EXPECTED =
    (
      POWER_EXPECTED_KW
      / (np.maximum((LOAD_PCT / 100), 0.01) * FAD_EXPECTED_M3MIN)
    )
```

### SPEC_POWER_RATIO

```python
SPEC_POWER_RATIO =
    SPEC_POWER_KW_M3MIN / SPEC_POWER_EXPECTED
```

### SPEC_POWER_VS_CAGI

```python
SPEC_POWER_VS_CAGI =
    SPEC_POWER_KW_M3MIN / 6.513074171
```

### SYSTEM_DP_BAR

```python
SYSTEM_DP_BAR =
    DISCHARGE_PRESSURE_BARG - HEADER_PRESSURE_BARG
```

### PRESSURE_EXCESS_BAR

```python
PRESSURE_EXCESS_BAR =
    (HEADER_PRESSURE_BARG - 7)
```

### PRESSURE_EXCESS_KW

```python
PRESSURE_EXCESS_KW =
    (LOAD_PCT / 100)
    * (
        P_LOAD_EXPECTED_KW
        - (
            INLET_PRESSURE_BARA
            * 100000
            * FAD_EXPECTED_M3MIN
            / 60
            * 3.5
            * (
                (
                  (
                    DISCHARGE_PRESSURE_BARG
                    - np.maximum((HEADER_PRESSURE_BARG - 7), 0)
                    + INLET_PRESSURE_BARA
                  )
                  / INLET_PRESSURE_BARA
                )
                ** 0.2857142857
                - 1
              )
            / 1000
            / 0.8144
          )
      )
```

### LEAK_FLOW_M3MIN

```python
LEAK_FLOW_M3MIN =
    LEAK_TEST_LOAD_PCT / 100 * FAD_EXPECTED_M3MIN
```

### LEAK_POWER_KW

```python
LEAK_POWER_KW =
    LEAK_TEST_LOAD_PCT / 100 * (P_LOAD_EXPECTED_KW - 20.7)
```

### DEW_POINT_ELEMENT_C

```python
DEW_POINT_ELEMENT_C =
    (
      243.12
      * np.log(
          INLET_RH_PCT
          / 100
          * np.exp(17.62 * INLET_TEMP_C / (243.12 + INLET_TEMP_C))
          * (
              (
                DISCHARGE_PRESSURE_BARG
                + SEPARATOR_DP_BAR
                + INLET_PRESSURE_BARA
              )
              / INLET_PRESSURE_BARA
            )
        )
      / (
          17.62
          - np.log(
              INLET_RH_PCT
              / 100
              * np.exp(17.62 * INLET_TEMP_C / (243.12 + INLET_TEMP_C))
              * (
                  (
                    DISCHARGE_PRESSURE_BARG
                    + SEPARATOR_DP_BAR
                    + INLET_PRESSURE_BARA
                  )
                  / INLET_PRESSURE_BARA
                )
            )
        )
    )
```

### OIL_DEW_MARGIN_K

```python
OIL_DEW_MARGIN_K =
    ELEMENT_OUTLET_TEMP_C - DEW_POINT_ELEMENT_C
```

### CYCLES_EXPECTED_PER_H

```python
CYCLES_EXPECTED_PER_H =
    (
      60
      * INLET_PRESSURE_BARA
      * (FLOW_FAD_M3MIN / np.maximum((LOAD_PCT / 100), 0.01))
      * (LOAD_PCT / 100)
      * (1 - (LOAD_PCT / 100))
    )
    / (12 * 1)
```

### STORAGE_EFFECTIVE_M3

```python
STORAGE_EFFECTIVE_M3 =
    (
      60
      * INLET_PRESSURE_BARA
      * (FLOW_FAD_M3MIN / np.maximum((LOAD_PCT / 100), 0.01))
      * (LOAD_PCT / 100)
      * (1 - (LOAD_PCT / 100))
    )
    / (1 * np.maximum(LOAD_CYCLES_PER_H, 0.1))
```

### MOTOR_LOAD_PCT

```python
MOTOR_LOAD_PCT =
    MOTOR_CURRENT_A / 140 * 100
```

## AlertExpression rules (13)

### AC_ELEMENT_TEMP_HIGH

High · oil_cooler_fouled

```python
AC_ELEMENT_TEMP_HIGH =
    ELEMENT_OUTLET_TEMP_C > 100
```

### AC_OIL_DEW_MARGIN_LOW

High · thermostat_stuck_open

```python
AC_OIL_DEW_MARGIN_LOW =
    OIL_DEW_MARGIN_K < 10
```

### AC_PDP_HIGH

High · dryer_fault

```python
AC_PDP_HIGH =
    DRYER_PDP_C > 7
```

### AC_MOTOR_OVERLOAD

High

```python
AC_MOTOR_OVERLOAD =
    MOTOR_CURRENT_A / 140 * 100 > 115
```

### AC_SEPARATOR_DP_HIGH

Medium · separator_clogged

```python
AC_SEPARATOR_DP_HIGH =
    SEPARATOR_DP_BAR > 0.7
```

### AC_POWER_HIGH

Medium · separator_clogged

```python
AC_POWER_HIGH =
    PACKAGE_POWER_KW / POWER_EXPECTED_KW > 1.04
```

### AC_FAD_LOW

Medium · element_wear

```python
AC_FAD_LOW =
    (FLOW_FAD_M3MIN / np.maximum((LOAD_PCT / 100), 0.01))
    / FAD_EXPECTED_M3MIN
    < 0.9
```

### AC_SPEC_POWER_HIGH

Medium · element_wear

```python
AC_SPEC_POWER_HIGH =
    SPEC_POWER_KW_M3MIN / SPEC_POWER_EXPECTED > 1.25
```

### AC_LEAK_HIGH

Medium · leaks_growing

```python
AC_LEAK_HIGH =
    LEAK_TEST_LOAD_PCT > 10
```

### AC_PRESSURE_EXCESS

Medium · pressure_setpoint_high

```python
AC_PRESSURE_EXCESS =
    (HEADER_PRESSURE_BARG - 7) > 1
```

### AC_CYCLING_HIGH

Medium · receiver_isolated

```python
AC_CYCLING_HIGH =
    LOAD_CYCLES_PER_H > 60
```

### AC_SYSTEM_DP_HIGH

Medium

```python
AC_SYSTEM_DP_HIGH =
    SYSTEM_DP_BAR > 0.7
```

### AC_STORAGE_LOW

Low · receiver_isolated

```python
AC_STORAGE_LOW =
    (
      60
      * INLET_PRESSURE_BARA
      * (FLOW_FAD_M3MIN / np.maximum((LOAD_PCT / 100), 0.01))
      * (LOAD_PCT / 100)
      * (1 - (LOAD_PCT / 100))
    )
    / (1 * np.maximum(LOAD_CYCLES_PER_H, 0.1))
    < 6
```
