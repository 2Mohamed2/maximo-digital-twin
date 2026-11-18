# ML-3901: Maximo Monitor functions and alert rules

Device type `SAG_MILL`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (17)

### LINER_EXPECTED_MM

```python
LINER_EXPECTED_MM =
    (150 - 0.01666666667 * LINER_KT)
```

### D_EFF_M

```python
D_EFF_M =
    (9 - 2 * LINER_EXPECTED_MM / 1000)
```

### CRIT_SPEED_PCT

```python
CRIT_SPEED_PCT =
    100 * (MILL_SPEED_RPM * np.sqrt(D_EFF_M) / 42.3)
```

### CHARGE_MASS_T

```python
CHARGE_MASS_T =
    (
      (BRG_FE_PRESSURE_BAR + BRG_DE_PRESSURE_BAR) * 5.096839959
      - (420 + 0.9333333333 * LINER_EXPECTED_MM)
    )
```

### FILLING_PCT

```python
FILLING_PCT =
    100
    * (
        (
          CHARGE_MASS_T / (3.534291735 * D_EFF_M ** 2)
          - 0.7 * (BALL_CHARGE_PCT / 100) * (7.8 - ORE_SG)
        )
        / (0.7 * ORE_SG + 0.3 * (1 / (0.8 / ORE_SG + 0.2)))
      )
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    (
      (
        50.085
        * D_EFF_M ** 2.5
        * (
            1
            - 1.03
              * (
                  (
                    CHARGE_MASS_T / (3.534291735 * D_EFF_M ** 2)
                    - 0.7 * (BALL_CHARGE_PCT / 100) * (7.8 - ORE_SG)
                  )
                  / (0.7 * ORE_SG + 0.3 * (1 / (0.8 / ORE_SG + 0.2)))
                )
          )
        * (
            0.7
            * (ORE_SG / 0.8)
            * (
                (
                  CHARGE_MASS_T / (3.534291735 * D_EFF_M ** 2)
                  - 0.7 * (BALL_CHARGE_PCT / 100) * (7.8 - ORE_SG)
                )
                / (0.7 * ORE_SG + 0.3 * (1 / (0.8 / ORE_SG + 0.2)))
              )
            + 0.6 * (BALL_CHARGE_PCT / 100) * (7.8 - ORE_SG / 0.8)
          )
        * (MILL_SPEED_RPM * np.sqrt(D_EFF_M) / 42.3)
        * (
            1
            - 0.1
              / np.power(
                  2,
                  9 - 10 * (MILL_SPEED_RPM * np.sqrt(D_EFF_M) / 42.3)
                )
          )
      )
      / 0.931
    )
```

### POWER_RATIO

```python
POWER_RATIO =
    MOTOR_POWER_KW / POWER_EXPECTED_KW
```

### SE_KWH_T

```python
SE_KWH_T =
    (MOTOR_POWER_KW / FEED_TPH)
```

### WA_KWH_T

```python
WA_KWH_T =
    (
      3.8
      * ORE_MIA
      * (
          0.1411564187
          - np.power(
              (FEED_F80_MM * 1000),
              -(0.295 + (FEED_F80_MM * 1000) / 1000000)
            )
        )
    )
```

### SE_RATIO

```python
SE_RATIO =
    (MOTOR_POWER_KW / FEED_TPH) / (1 * WA_KWH_T)
```

### THROUGHPUT_EXPECTED_TPH

```python
THROUGHPUT_EXPECTED_TPH =
    MOTOR_POWER_KW / (1 * WA_KWH_T)
```

### LINER_WEAR_RATIO

```python
LINER_WEAR_RATIO =
    ((150 - LINER_SCAN_MM) / LINER_SCAN_KT) / 0.01666666667
```

### LINER_REMAINING_KT

```python
LINER_REMAINING_KT =
    (
      (LINER_SCAN_MM - 50) / ((150 - LINER_SCAN_MM) / LINER_SCAN_KT)
      - (LINER_KT - LINER_SCAN_KT)
    )
```

### RELINE_DAYS

```python
RELINE_DAYS =
    LINER_REMAINING_KT * 1000 / (FEED_TPH * 24)
```

### BRG_SPLIT

```python
BRG_SPLIT =
    (
      (BRG_FE_PRESSURE_BAR - BRG_DE_PRESSURE_BAR)
      / (BRG_FE_PRESSURE_BAR + BRG_DE_PRESSURE_BAR)
    )
```

### BRG_RISE_MAX_K

```python
BRG_RISE_MAX_K =
    (np.maximum(BRG_FE_TEMP_C, BRG_DE_TEMP_C) - LUBE_OIL_TEMP_C)
```

### GEAR_LOAD_RATIO

```python
GEAR_LOAD_RATIO =
    MOTOR_POWER_KW / 7800
```

## AlertExpression rules (13)

### SAG_POWER_DROP_LOADED

Critical · charge_overload

```python
SAG_POWER_DROP_LOADED =
    (FILLING_PCT > 33) & (POWER_RATIO < 0.92)
```

### SAG_OVERLOAD_RISK

High · charge_overload

```python
SAG_OVERLOAD_RISK =
    FILLING_PCT > 35
```

### SAG_RELINE_DUE

High · liner_wear_fast

```python
SAG_RELINE_DUE =
    RELINE_DAYS < 30
```

### SAG_BRG_TEMP_HIGH

High · bearing_lube

```python
SAG_BRG_TEMP_HIGH =
    np.maximum(BRG_FE_TEMP_C, BRG_DE_TEMP_C) > 65
```

### SAG_PINION_VIB_HIGH

High · gear_misalignment

```python
SAG_PINION_VIB_HIGH =
    PINION_VIB_MM_S > 7.1
```

### SAG_GEAR_OVERPOWER

High · ball_overcharge

```python
SAG_GEAR_OVERPOWER =
    MOTOR_POWER_KW > 7800
```

### SAG_LINER_WEAR_FAST

Medium · liner_wear_fast

```python
SAG_LINER_WEAR_FAST =
    LINER_WEAR_RATIO > 1.25
```

### SAG_SE_HIGH

Medium · lifter_profile_loss

```python
SAG_SE_HIGH =
    SE_RATIO > 1.2
```

### SAG_BRG_RISE_HIGH

Medium · bearing_lube

```python
SAG_BRG_RISE_HIGH =
    (BRG_RISE_MAX_K > 10) & (np.maximum(BRG_FE_TEMP_C, BRG_DE_TEMP_C) <= 65)
```

### SAG_BRG_SPLIT

Medium · pocket_leak

```python
SAG_BRG_SPLIT =
    np.abs(BRG_SPLIT) > 0.1
```

### SAG_GEAR_DT_HIGH

Medium · gear_misalignment

```python
SAG_GEAR_DT_HIGH =
    GEAR_DT_K > 8
```

### SAG_PINION_VIB_ALERT

Medium · gear_misalignment

```python
SAG_PINION_VIB_ALERT =
    (PINION_VIB_MM_S > 4.5) & (PINION_VIB_MM_S <= 7.1)
```

### SAG_BALL_CHARGE_HIGH

Medium · ball_overcharge

```python
SAG_BALL_CHARGE_HIGH =
    BALL_CHARGE_PCT > 15
```
