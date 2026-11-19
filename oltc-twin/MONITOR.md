# PT-7501: Maximo Monitor functions and alert rules

Device type `TRANSFORMER_OLTC_BUSHING`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### LOAD_DROP_PCT

```python
LOAD_DROP_PCT =
    (
      LV_CURRENT_A
      / 1049.7
      * (
          0.004333 * POWER_FACTOR
          + 0.124925 * np.sqrt(1 - POWER_FACTOR ** 2)
        )
    )
    * 100
```

### LV_VOLTAGE_EXPECTED_KV

```python
LV_VOLTAGE_EXPECTED_KV =
    (
      (HV_VOLTAGE_KV / 132) / (1 - (TAP_POSITION - 9) * 0.0125)
      - (
          LV_CURRENT_A
          / 1049.7
          * (
              0.004333 * POWER_FACTOR
              + 0.124925 * np.sqrt(1 - POWER_FACTOR ** 2)
            )
        )
    )
    * 33
```

### LV_VOLTAGE_RESIDUAL_PCT

```python
LV_VOLTAGE_RESIDUAL_PCT =
    (
      (
        LV_VOLTAGE_KV / 33
        - (
            (HV_VOLTAGE_KV / 132) / (1 - (TAP_POSITION - 9) * 0.0125)
            - (
                LV_CURRENT_A
                / 1049.7
                * (
                    0.004333 * POWER_FACTOR
                    + 0.124925 * np.sqrt(1 - POWER_FACTOR ** 2)
                  )
              )
          )
      )
      * 100
    )
```

### TAP_EXPECTED

```python
TAP_EXPECTED =
    (
      9
      + (
          1
          - (HV_VOLTAGE_KV / 132)
            / (
                (AVR_SETPOINT_KV / 33)
                + (
                    LV_CURRENT_A
                    / 1049.7
                    * (
                        0.004333 * POWER_FACTOR
                        + 0.124925 * np.sqrt(1 - POWER_FACTOR ** 2)
                      )
                  )
              )
        )
        / 0.0125
    )
```

### TAP_DEVIATION

```python
TAP_DEVIATION =
    TAP_POSITION - TAP_EXPECTED
```

### VOLTAGE_DEVIATION_PCT

```python
VOLTAGE_DEVIATION_PCT =
    (LV_VOLTAGE_KV / AVR_SETPOINT_KV - 1) * 100
```

### BAND_MARGIN_PCT

```python
BAND_MARGIN_PCT =
    AVR_BAND_PCT - 0.75
```

### OPS_RATIO

```python
OPS_RATIO =
    OPS_24H / 30
```

### MOTOR_CURRENT_EXPECTED_A

```python
MOTOR_CURRENT_EXPECTED_A =
    (1.6 * (1 + 0.006 * (20 - CABINET_TEMP_C)))
```

### MOTOR_CURRENT_RATIO

```python
MOTOR_CURRENT_RATIO =
    MOTOR_CURRENT_A / MOTOR_CURRENT_EXPECTED_A
```

### OP_TIME_RATIO

```python
OP_TIME_RATIO =
    OP_TIME_S / 5.5
```

### CONTACT_WEAR_PCT

```python
CONTACT_WEAR_PCT =
    (WEAR_SUM_PU / 600000 * 100)
```

### MAINT_DUE_PCT

```python
MAINT_DUE_PCT =
    (np.maximum(OPS_SINCE_MAINT / 300000, YEARS_SINCE_MAINT / 10) * 100)
```

### MAINT_REMAINING_YEARS

```python
MAINT_REMAINING_YEARS =
    np.minimum(
      (300000 - OPS_SINCE_MAINT) / np.maximum(OPS_365D, 1),
      10 - YEARS_SINCE_MAINT
    )
```

### OLTC_TEMP_DIFF_K

```python
OLTC_TEMP_DIFF_K =
    OLTC_OIL_TEMP_C - TOP_OIL_TEMP_C
```

### OLTC_C2H2_EXCESS_PPM

```python
OLTC_C2H2_EXCESS_PPM =
    OLTC_C2H2_PPM - MAIN_C2H2_PPM
```

### OLTC_C2H4_EXCESS_PPM

```python
OLTC_C2H4_EXCESS_PPM =
    OLTC_C2H4_PPM - MAIN_C2H4_PPM
```

### BSH_C1_CHANGE_MAX_PCT

```python
BSH_C1_CHANGE_MAX_PCT =
    np.maximum(
      np.maximum(
        (BSH_C1_L1_PF / 418 - 1) * 100,
        (BSH_C1_L2_PF / 422 - 1) * 100
      ),
      (BSH_C1_L3_PF / 415 - 1) * 100
    )
```

### BSH_TAND_RATIO_MAX

```python
BSH_TAND_RATIO_MAX =
    np.maximum(
      np.maximum(BSH_TAND_L1_PCT / 0.32, BSH_TAND_L2_PCT / 0.35),
      BSH_TAND_L3_PCT / 0.33
    )
```

### BSH_TAND_MAX_PCT

```python
BSH_TAND_MAX_PCT =
    np.maximum(
      np.maximum(BSH_TAND_L1_PCT, BSH_TAND_L2_PCT),
      BSH_TAND_L3_PCT
    )
```

## AlertExpression rules (14)

### BSH_C1_CRITICAL

Critical · bushing_layer_short

```python
BSH_C1_CRITICAL =
    np.maximum(
      np.maximum(
        (BSH_C1_L1_PF / 418 - 1) * 100,
        (BSH_C1_L2_PF / 422 - 1) * 100
      ),
      (BSH_C1_L3_PF / 415 - 1) * 100
    )
    >= 10
```

### BSH_C1_HIGH

High · bushing_layer_short

```python
BSH_C1_HIGH =
    (
      np.maximum(
        np.maximum(
          (BSH_C1_L1_PF / 418 - 1) * 100,
          (BSH_C1_L2_PF / 422 - 1) * 100
        ),
        (BSH_C1_L3_PF / 415 - 1) * 100
      )
      >= 5
    )
    & (
        np.maximum(
          np.maximum(
            (BSH_C1_L1_PF / 418 - 1) * 100,
            (BSH_C1_L2_PF / 422 - 1) * 100
          ),
          (BSH_C1_L3_PF / 415 - 1) * 100
        )
        < 10
      )
```

### BSH_TAND_LIMIT

High · bushing_moisture

```python
BSH_TAND_LIMIT =
    np.maximum(
      np.maximum(BSH_TAND_L1_PCT, BSH_TAND_L2_PCT),
      BSH_TAND_L3_PCT
    )
    >= 0.7
```

### OLTC_DGA_ARCING

High · vacuum_loss

```python
OLTC_DGA_ARCING =
    OLTC_C2H2_EXCESS_PPM > 10
```

### OLTC_TEMP_DIFF

High · compartment_heating

```python
OLTC_TEMP_DIFF =
    OLTC_TEMP_DIFF_K > 2
```

### BSH_TAND_RISE

Medium · bushing_moisture

```python
BSH_TAND_RISE =
    np.maximum(
      np.maximum(BSH_TAND_L1_PCT / 0.32, BSH_TAND_L2_PCT / 0.35),
      BSH_TAND_L3_PCT / 0.33
    )
    >= 2
```

### OLTC_DGA_HEATING

Medium · compartment_heating

```python
OLTC_DGA_HEATING =
    OLTC_C2H4_EXCESS_PPM > 50
```

### OLTC_MOTOR_CURRENT_HIGH

Medium · drive_stiff

```python
OLTC_MOTOR_CURRENT_HIGH =
    MOTOR_CURRENT_A / MOTOR_CURRENT_EXPECTED_A > 1.3
```

### OLTC_OP_SLOW

Medium · drive_stiff

```python
OLTC_OP_SLOW =
    OP_TIME_S / 5.5 > 1.2
```

### OLTC_TAP_MISMATCH

Medium · tap_sensor_fault

```python
OLTC_TAP_MISMATCH =
    np.abs(LV_VOLTAGE_RESIDUAL_PCT) > 1.25
```

### OLTC_HUNTING

Medium · band_too_narrow

```python
OLTC_HUNTING =
    OPS_24H / 30 > 2.5
```

### OLTC_CONTACT_WEAR

Medium · contact_wear

```python
OLTC_CONTACT_WEAR =
    (WEAR_SUM_PU / 600000 * 100) > 80
```

### OLTC_MAINT_DUE

Medium

```python
OLTC_MAINT_DUE =
    MAINT_DUE_PCT >= 100
```

### OLTC_BAND_NARROW

Low · band_too_narrow

```python
OLTC_BAND_NARROW =
    AVR_BAND_PCT < 0.75
```
