# ESP-2801: Maximo Monitor functions and alert rules

Device type `ESP_WELL_VSD`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### FLOW_60HZ_BPD

```python
FLOW_60HZ_BPD =
    (FLOW_BPD / (np.maximum(VSD_FREQ_HZ, 1) / 60))
```

### SG_MIX

```python
SG_MIX =
    (WATER_CUT_PCT / 100 * 1.05 + (1 - WATER_CUT_PCT / 100) * 0.86)
```

### HEAD_MEASURED_FT

```python
HEAD_MEASURED_FT =
    ((PD_PSI - PIP_PSI) / (0.433 * SG_MIX))
```

### HEAD_EXPECTED_FT

```python
HEAD_EXPECTED_FT =
    np.maximum(
      266
      * (np.maximum(VSD_FREQ_HZ, 1) / 60) ** 2
      * (29 - 0.0015206 * FLOW_60HZ_BPD - 2.527e-06 * FLOW_60HZ_BPD ** 2),
      1
    )
```

### HEAD_RATIO

```python
HEAD_RATIO =
    (
      HEAD_MEASURED_FT
      / np.maximum(
          266
          * (np.maximum(VSD_FREQ_HZ, 1) / 60) ** 2
          * (
              29
              - 0.0015206 * FLOW_60HZ_BPD
              - 2.527e-06 * FLOW_60HZ_BPD ** 2
            ),
          1
        )
    )
```

### BEP_RATIO

```python
BEP_RATIO =
    (FLOW_60HZ_BPD / 1750)
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    (
      266
      * (0.305 + 2e-05 * FLOW_60HZ_BPD)
      * (np.maximum(VSD_FREQ_HZ, 1) / 60) ** 3
      * SG_MIX
      * 0.9032219
    )
```

### POWER_RATIO

```python
POWER_RATIO =
    VSD_KW / POWER_EXPECTED_KW
```

### LOAD_PCT

```python
LOAD_PCT =
    (VSD_KW * 1.1071476 / (100 * (np.maximum(VSD_FREQ_HZ, 1) / 60)) * 100)
```

### PUMP_EFF_PCT

```python
PUMP_EFF_PCT =
    FLOW_BPD
    * HEAD_MEASURED_FT
    * SG_MIX
    / 135770
    / (np.maximum(VSD_KW, 0.1) * 1.1071476)
    * 100
```

### FLUID_OVER_PUMP_FT

```python
FLUID_OVER_PUMP_FT =
    (PIP_PSI - CASING_PSI) / (0.433 * 0.86)
```

### PI_BPD_PSI

```python
PI_BPD_PSI =
    FLOW_BPD / np.maximum(2700 - (PIP_PSI + 0.433 * SG_MIX * 500), 1)
```

### INTAKE_GVF_PCT

```python
INTAKE_GVF_PCT =
    100
    * (
        0.0009072
        * (1 - WATER_CUT_PCT / 100)
        * np.maximum(GOR_SCF_STB - 200 * np.minimum(PIP_PSI / 800, 1), 0)
        * (INTAKE_TEMP_F + 460)
        / (PIP_PSI + 14.7)
      )
    / (
        (
          0.0009072
          * (1 - WATER_CUT_PCT / 100)
          * np.maximum(GOR_SCF_STB - 200 * np.minimum(PIP_PSI / 800, 1), 0)
          * (INTAKE_TEMP_F + 460)
          / (PIP_PSI + 14.7)
        )
        + 1
      )
```

### MOTOR_VELOCITY_FTS

```python
MOTOR_VELOCITY_FTS =
    (FLOW_BPD * 0.0012073363)
```

### MOTOR_RISE_F

```python
MOTOR_RISE_F =
    (MOTOR_TEMP_F - INTAKE_TEMP_F)
```

### MOTOR_RISE_EXPECTED_F

```python
MOTOR_RISE_EXPECTED_F =
    (
      40
      * LOAD_PCT
      / 100
      * np.sqrt(2 / np.maximum((FLOW_BPD * 0.0012073363), 0.2))
    )
```

### MOTOR_RISE_RATIO

```python
MOTOR_RISE_RATIO =
    MOTOR_RISE_F / np.maximum(MOTOR_RISE_EXPECTED_F, 1)
```

### LEAKAGE_CORR_UA

```python
LEAKAGE_CORR_UA =
    (LEAKAGE_UA / np.power(2, (MOTOR_TEMP_F - 220) / 18))
```

### RUN_LIFE_YEARS

```python
RUN_LIFE_YEARS =
    RUN_DAYS / 365.25
```

## AlertExpression rules (15)

### ESP_SHAFT_BROKEN

Critical · broken_shaft

```python
ESP_SHAFT_BROKEN =
    (RUNNING > 0.5)
    & (HEAD_RATIO < 0.3)
    & (LOAD_PCT < 40)
    & (CURRENT_CV_PCT <= 5)
```

### ESP_GAS_LOCK

High · gas_interference

```python
ESP_GAS_LOCK =
    (RUNNING > 0.5) & (BEP_RATIO < 0.28571429) & (CURRENT_CV_PCT > 5)
```

### ESP_HEAD_LOSS_HIGH

High · stage_wear

```python
ESP_HEAD_LOSS_HIGH =
    (RUNNING > 0.5)
    & (HEAD_RATIO >= 0.3)
    & (HEAD_RATIO < 0.8)
    & (CURRENT_CV_PCT <= 5)
```

### ESP_INSULATION_LOW

High · motor_insulation

```python
ESP_INSULATION_LOW =
    LEAKAGE_CORR_UA > 20
```

### ESP_MOTOR_TEMP_LIMIT

High · motor_cooling

```python
ESP_MOTOR_TEMP_LIMIT =
    MOTOR_TEMP_F > 300
```

### ESP_HEAD_LOW

Medium · scale_deposits

```python
ESP_HEAD_LOW =
    (RUNNING > 0.5)
    & (HEAD_RATIO >= 0.8)
    & (HEAD_RATIO < 0.92)
    & (CURRENT_CV_PCT <= 5)
```

### ESP_POWER_HIGH

Medium · scale_deposits

```python
ESP_POWER_HIGH =
    (RUNNING > 0.5) & (POWER_RATIO > 1.15)
```

### ESP_VIBRATION_HIGH

Medium · stage_wear

```python
ESP_VIBRATION_HIGH =
    VIBRATION_G > 1
```

### ESP_CURRENT_UNSTABLE

Medium · gas_interference

```python
ESP_CURRENT_UNSTABLE =
    (RUNNING > 0.5) & (CURRENT_CV_PCT > 5)
```

### ESP_GAS_HIGH

Medium · gas_interference

```python
ESP_GAS_HIGH =
    INTAKE_GVF_PCT > 15
```

### ESP_DOWNTHRUST

Medium · inflow_decline

```python
ESP_DOWNTHRUST =
    (RUNNING > 0.5)
    & (BEP_RATIO < 0.28571429)
    & (CURRENT_CV_PCT <= 5)
    & (HEAD_RATIO >= 0.3)
```

### ESP_LOW_SUBMERGENCE

Medium · inflow_decline

```python
ESP_LOW_SUBMERGENCE =
    FLUID_OVER_PUMP_FT < 1000
```

### ESP_MOTOR_COOLING

Medium · motor_cooling

```python
ESP_MOTOR_COOLING =
    (RUNNING > 0.5) & (MOTOR_RISE_RATIO > 1.5)
```

### ESP_LEAKAGE_RISING

Medium · motor_insulation

```python
ESP_LEAKAGE_RISING =
    (LEAKAGE_CORR_UA > 4.5) & (LEAKAGE_CORR_UA <= 20)
```

### ESP_RESTARTS_HIGH

Medium · gas_interference

```python
ESP_RESTARTS_HIGH =
    STARTS_30D > 3
```
