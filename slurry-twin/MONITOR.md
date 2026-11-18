# SP-4101: Maximo Monitor functions and alert rules

Device type `SLURRY_PUMP_VSD`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### CW_SOLIDS_PCT

```python
CW_SOLIDS_PCT =
    (100 * (DENSITY_SG - 1) / 1.7 * 2.7 / DENSITY_SG)
```

### SLURRY_HR

```python
SLURRY_HR =
    (
      1
      - 0.0016241296 * CW_SOLIDS_PCT * np.log(np.maximum(D50_UM / 22.7, 1))
    )
```

### FLOW_REF_M3H

```python
FLOW_REF_M3H =
    (FLOW_M3H / (np.maximum(SPEED_RPM, 1) / 1000))
```

### BEP_RATIO

```python
BEP_RATIO =
    (FLOW_REF_M3H / 900)
```

### HEAD_WATER_EXPECTED_M

```python
HEAD_WATER_EXPECTED_M =
    (
      (np.maximum(SPEED_RPM, 1) / 1000) ** 2
      * (50 + 0 * FLOW_REF_M3H - 9.8765432e-06 * FLOW_REF_M3H ** 2)
    )
```

### HEAD_EXPECTED_M

```python
HEAD_EXPECTED_M =
    (SLURRY_HR * HEAD_WATER_EXPECTED_M)
```

### HEAD_MEASURED_M

```python
HEAD_MEASURED_M =
    ((DISCHARGE_KPA - SUCTION_KPA) / (9.80665 * DENSITY_SG))
```

### HEAD_RATIO

```python
HEAD_RATIO =
    (HEAD_MEASURED_M / HEAD_EXPECTED_M)
```

### EFF_EXPECTED_PCT

```python
EFF_EXPECTED_PCT =
    (100 * SLURRY_HR * 0.75 * (2 * BEP_RATIO - BEP_RATIO ** 2))
```

### PUMP_EFF_PCT

```python
PUMP_EFF_PCT =
    (DISCHARGE_KPA - SUCTION_KPA)
    * FLOW_M3H
    / 3600
    / (np.maximum(MOTOR_KW, 0.1) * 0.94)
    * 100
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    (
      DENSITY_SG
      * 9.80665
      * FLOW_M3H
      / 3600
      * HEAD_EXPECTED_M
      / (EFF_EXPECTED_PCT / 100)
      / 0.94
    )
```

### MOTOR_LOAD_PCT

```python
MOTOR_LOAD_PCT =
    MOTOR_KW / 200 * 100
```

### LINE_VELOCITY_MS

```python
LINE_VELOCITY_MS =
    (FLOW_M3H / 3600 / 0.050670748)
```

### DEPOSITION_MARGIN

```python
DEPOSITION_MARGIN =
    ((FLOW_M3H / 3600 / 0.050670748) / 3.0556665)
```

### NPSH_AVAILABLE_M

```python
NPSH_AVAILABLE_M =
    ((SUCTION_KPA + 98.13) / (9.80665 * DENSITY_SG))
```

### NPSH_REQUIRED_M

```python
NPSH_REQUIRED_M =
    ((np.maximum(SPEED_RPM, 1) / 1000) ** 2 * (2 + 2.5 * BEP_RATIO ** 2))
```

### NPSH_MARGIN

```python
NPSH_MARGIN =
    NPSH_AVAILABLE_M / NPSH_REQUIRED_M
```

### GLAND_DP_KPA

```python
GLAND_DP_KPA =
    GLAND_KPA - DISCHARGE_KPA
```

### BEARING_RISE_K

```python
BEARING_RISE_K =
    np.maximum(BEARING_DE_C, BEARING_NDE_C) - AMBIENT_C
```

### WEAR_RATE_PCT_KH

```python
WEAR_RATE_PCT_KH =
    ((1 - HEAD_RATIO) * 100 / np.maximum(HOURS_SINCE_ADJUST / 1000, 0.1))
```

## AlertExpression rules (15)

### SLY_DEPOSITION_RISK

High · line_sanding

```python
SLY_DEPOSITION_RISK =
    (RUNNING > 0.5) & (DEPOSITION_MARGIN < 1)
```

### SLY_HEAD_LOSS_HIGH

High · impeller_wear

```python
SLY_HEAD_LOSS_HIGH =
    (RUNNING > 0.5) & (HEAD_RATIO < 0.85)
```

### SLY_NPSH_LOW

High · suction_blockage

```python
SLY_NPSH_LOW =
    (RUNNING > 0.5) & (NPSH_MARGIN < 1.3)
```

### SLY_GLAND_PRESSURE_LOW

High · gland_water_loss

```python
SLY_GLAND_PRESSURE_LOW =
    (RUNNING > 0.5) & ((GLAND_KPA - DISCHARGE_KPA) < 20)
```

### SLY_BEARING_TEMP_HIGH

High · bearing_failure

```python
SLY_BEARING_TEMP_HIGH =
    BEARING_RISE_K > 45
```

### SLY_MOTOR_OVERLOAD

High

```python
SLY_MOTOR_OVERLOAD =
    MOTOR_KW > 200
```

### SLY_DEPOSITION_MARGIN

Medium · line_sanding

```python
SLY_DEPOSITION_MARGIN =
    (RUNNING > 0.5) & (DEPOSITION_MARGIN >= 1) & (DEPOSITION_MARGIN < 1.1)
```

### SLY_HEAD_LOW

Medium · impeller_wear

```python
SLY_HEAD_LOW =
    (RUNNING > 0.5) & (HEAD_RATIO >= 0.85) & (HEAD_RATIO < 0.93)
```

### SLY_WEAR_RATE_HIGH

Medium · impeller_wear

```python
SLY_WEAR_RATE_HIGH =
    (RUNNING > 0.5) & (HOURS_SINCE_ADJUST > 200) & (WEAR_RATE_PCT_KH > 5)
```

### SLY_BEP_LOW

Medium · line_sanding

```python
SLY_BEP_LOW =
    (RUNNING > 0.5) & (BEP_RATIO < 0.7)
```

### SLY_BEP_HIGH

Medium

```python
SLY_BEP_HIGH =
    (RUNNING > 0.5) & (BEP_RATIO > 1.15)
```

### SLY_GLAND_FLOW_LOW

Medium · gland_water_loss

```python
SLY_GLAND_FLOW_LOW =
    (RUNNING > 0.5) & (GLAND_FLOW_LPM < 4)
```

### SLY_GLAND_FLOW_HIGH

Medium · packing_wear

```python
SLY_GLAND_FLOW_HIGH =
    GLAND_FLOW_LPM > 25
```

### SLY_VIBRATION_HIGH

Medium · bearing_failure

```python
SLY_VIBRATION_HIGH =
    VIBRATION_MMS > 7.1
```

### SLY_DENSITY_HIGH

Medium · density_high

```python
SLY_DENSITY_HIGH =
    DENSITY_SG > 1.5
```
