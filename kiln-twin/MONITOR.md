# KL-4201: Maximo Monitor functions and alert rules

Device type `CEMENT_ROTARY_KILN`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### SHC_FUEL_KJKG

```python
SHC_FUEL_KJKG =
    (
      (FUEL_KILN_TPH + FUEL_CALCINER_TPH)
      * FUEL_LHV_MJKG
      / CLINKER_TPH
      * 1000
    )
```

### SHELL_LOSS_KJKG

```python
SHELL_LOSS_KJKG =
    (
      1115.89371056
      * (
          5.103e-08
          * ((SHELL_MEAN_C + 273.15) ** 4 - (AMBIENT_C + 273.15) ** 4)
          + 12 * (SHELL_MEAN_C - AMBIENT_C)
        )
      / 1000
      * 3.6
      / CLINKER_TPH
    )
```

### PH_EXIT_LOSS_KJKG

```python
PH_EXIT_LOSS_KJKG =
    (PH_EXIT_FLOW_KNM3H * 1.45 * (PH_EXIT_TEMP_C - AMBIENT_C) / CLINKER_TPH)
```

### COOLER_EXH_LOSS_KJKG

```python
COOLER_EXH_LOSS_KJKG =
    (
      COOLER_EXH_FLOW_KNM3H
      * 1.31
      * (COOLER_EXH_TEMP_C - AMBIENT_C)
      / CLINKER_TPH
    )
```

### CLINKER_OUT_LOSS_KJKG

```python
CLINKER_OUT_LOSS_KJKG =
    (0.8 * (CLINKER_OUT_C - AMBIENT_C))
```

### SHC_BALANCE_KJKG

```python
SHC_BALANCE_KJKG =
    (
      1720
      + PH_EXIT_LOSS_KJKG
      + SHELL_LOSS_KJKG
      + COOLER_EXH_LOSS_KJKG
      + CLINKER_OUT_LOSS_KJKG
      + 255
    )
```

### SHC_MISMATCH_PCT

```python
SHC_MISMATCH_PCT =
    100 * (SHC_FUEL_KJKG / SHC_BALANCE_KJKG - 1)
```

### SHC_EXCESS_KJKG

```python
SHC_EXCESS_KJKG =
    SHC_FUEL_KJKG - 3005.9
```

### COOLER_EFF_PCT

```python
COOLER_EFF_PCT =
    (
      100
      * (
          1
          - (COOLER_EXH_LOSS_KJKG + CLINKER_OUT_LOSS_KJKG + 25)
            / (1 * (1400 - AMBIENT_C))
        )
    )
```

### FALSE_AIR_PCT

```python
FALSE_AIR_PCT =
    (100 * (O2_PH_EXIT_PCT - O2_CALCINER_PCT) / (21 - O2_PH_EXIT_PCT))
```

### LINING_EQ_MM

```python
LINING_EQ_MM =
    (
      2.8
      * (1400 - SHELL_MAX_C)
      / (
          5.103e-08
          * ((SHELL_MAX_C + 273.15) ** 4 - (AMBIENT_C + 273.15) ** 4)
          + 12 * (SHELL_MAX_C - AMBIENT_C)
        )
      * 1000
    )
```

### TORQUE_EXPECTED_PCT

```python
TORQUE_EXPECTED_PCT =
    (22 + 40 * (CLINKER_TPH / 208.333) * (4 / KILN_SPEED_RPM))
```

### TORQUE_RATIO

```python
TORQUE_RATIO =
    DRIVE_TORQUE_PCT / TORQUE_EXPECTED_PCT
```

### NOX_EXPECTED_PPM

```python
NOX_EXPECTED_PPM =
    (800 * np.exp(0.01 * (BZT_C - 1450)))
```

### NOX_RATIO

```python
NOX_RATIO =
    NOX_INLET_PPM / NOX_EXPECTED_PPM
```

### TYRE2_GAP_MM

```python
TYRE2_GAP_MM =
    TYRE2_MIGRATION_MM / 3.14159
```

### TYRE2_GAP_EXPECTED_MM

```python
TYRE2_GAP_EXPECTED_MM =
    (11 - 0.0576 * (SHELL_T2_C - TYRE2_TEMP_C))
```

### MIGRATION_MAX_MM

```python
MIGRATION_MAX_MM =
    np.maximum(
      np.maximum(TYRE1_MIGRATION_MM, TYRE2_MIGRATION_MM),
      TYRE3_MIGRATION_MM
    )
```

### MIGRATION_MIN_MM

```python
MIGRATION_MIN_MM =
    np.minimum(
      np.minimum(TYRE1_MIGRATION_MM, TYRE2_MIGRATION_MM),
      TYRE3_MIGRATION_MM
    )
```

### STACK_NOX_REF_MGNM3

```python
STACK_NOX_REF_MGNM3 =
    (STACK_NOX_MGNM3 * 11 / (21 - STACK_O2_PCT))
```

## AlertExpression rules (15)

### KLN_LINING_THIN

Critical · refractory_loss

```python
KLN_LINING_THIN =
    LINING_EQ_MM < 100
```

### KLN_SHELL_HOT

High · refractory_loss

```python
KLN_SHELL_HOT =
    SHELL_MAX_C > 400
```

### KLN_MIGRATION_LOW

High

```python
KLN_MIGRATION_LOW =
    np.minimum(
      np.minimum(TYRE1_MIGRATION_MM, TYRE2_MIGRATION_MM),
      TYRE3_MIGRATION_MM
    )
    < 3
```

### KLN_BZ_COLD

High · burning_zone_cold

```python
KLN_BZ_COLD =
    NOX_INLET_PPM < 450
```

### KLN_NOX_STACK_HIGH

High

```python
KLN_NOX_STACK_HIGH =
    STACK_NOX_REF_MGNM3 > 450
```

### KLN_TORQUE_HIGH

Medium · ring_formation

```python
KLN_TORQUE_HIGH =
    TORQUE_RATIO > 1.25
```

### KLN_INLET_O2_LOW

Medium · ring_formation

```python
KLN_INLET_O2_LOW =
    O2_INLET_PCT < 1
```

### KLN_FALSE_AIR_HIGH

Medium · false_air

```python
KLN_FALSE_AIR_HIGH =
    FALSE_AIR_PCT > 10
```

### KLN_COOLER_EFF_LOW

Medium · cooler_degradation

```python
KLN_COOLER_EFF_LOW =
    COOLER_EFF_PCT < 65
```

### KLN_SHC_HIGH

Medium · cooler_degradation

```python
KLN_SHC_HIGH =
    SHC_EXCESS_KJKG > 150
```

### KLN_SHC_MISMATCH

Medium · fuel_meter_drift

```python
KLN_SHC_MISMATCH =
    np.absSHC_MISMATCH_PCT > 5
```

### KLN_FREE_LIME_HIGH

Medium · burning_zone_cold

```python
KLN_FREE_LIME_HIGH =
    FREE_LIME_PCT > 2
```

### KLN_PYRO_MISMATCH

Medium · pyrometer_fouling

```python
KLN_PYRO_MISMATCH =
    (NOX_RATIO > 2) | (NOX_RATIO < 0.5)
```

### KLN_MIGRATION_HIGH

Medium · tyre_pad_wear

```python
KLN_MIGRATION_HIGH =
    np.maximum(
      np.maximum(TYRE1_MIGRATION_MM, TYRE2_MIGRATION_MM),
      TYRE3_MIGRATION_MM
    )
    > 12
```

### KLN_OVALITY_HIGH

Medium · tyre_pad_wear

```python
KLN_OVALITY_HIGH =
    OVALITY2_PCT > 0.48
```
