# RP-2901: Maximo Monitor functions and alert rules

Device type `ROD_PUMP_SYSTEM`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### SUBMERGENCE_FT

```python
SUBMERGENCE_FT =
    ((PIP_PSI - CASING_PRESSURE_PSI) / 0.433)
```

### FO_EXPECTED_LB

```python
FO_EXPECTED_LB =
    (1.76715 * (TUBING_PRESSURE_PSI + 2598 - PIP_PSI))
```

### FLUID_LOAD_RATIO

```python
FLUID_LOAD_RATIO =
    (PUMP_FLUID_LOAD_LB / FO_EXPECTED_LB)
```

### ACCEL_FACTOR

```python
ACCEL_FACTOR =
    (SURFACE_STROKE_IN * SPM ** 2 / 70500)
```

### PPRL_EXPECTED_LB

```python
PPRL_EXPECTED_LB =
    (9475.15 + FO_EXPECTED_LB + 10866 * ACCEL_FACTOR)
```

### MPRL_EXPECTED_LB

```python
MPRL_EXPECTED_LB =
    (9475.15 - 10866 * ACCEL_FACTOR)
```

### PPRL_RATIO

```python
PPRL_RATIO =
    PPRL_LB / PPRL_EXPECTED_LB
```

### MPRL_RATIO

```python
MPRL_RATIO =
    MPRL_LB / MPRL_EXPECTED_LB
```

### STRUCTURE_LOAD_PCT

```python
STRUCTURE_LOAD_PCT =
    PPRL_LB / 25600 * 100
```

### ROD_LOADING_PCT

```python
ROD_LOADING_PCT =
    (PPRL_LB / 0.6013 / ((28750 + 0.5625 * MPRL_LB / 0.6013) * 0.9) * 100)
```

### TORQUE_UP_KINLB

```python
TORQUE_UP_KINLB =
    ((PPRL_LB - 11600) * SURFACE_STROKE_IN / 2000)
```

### TORQUE_DOWN_KINLB

```python
TORQUE_DOWN_KINLB =
    ((11600 - MPRL_LB) * SURFACE_STROKE_IN / 2000)
```

### GEARBOX_LOAD_PCT

```python
GEARBOX_LOAD_PCT =
    (np.maximum(TORQUE_UP_KINLB, TORQUE_DOWN_KINLB) / 320 * 100)
```

### CBE_IDEAL_LB

```python
CBE_IDEAL_LB =
    ((PPRL_LB + MPRL_LB) / 2)
```

### BALANCE_RATIO

```python
BALANCE_RATIO =
    (CURRENT_DOWN_A / np.maximum(CURRENT_UP_A, 0.1))
```

### GROSS_STROKE_EXPECTED_IN

```python
GROSS_STROKE_EXPECTED_IN =
    (SURFACE_STROKE_IN - FO_EXPECTED_LB * 0.00491806)
```

### PUMP_DISPLACEMENT_BPD

```python
PUMP_DISPLACEMENT_BPD =
    (0.26235 * PUMP_NET_STROKE_IN * SPM * RUNTIME_PCT / 100)
```

### VOL_EFF

```python
VOL_EFF =
    (FLOW_BPD / np.maximum(PUMP_DISPLACEMENT_BPD, 1))
```

### ENERGY_KWH_PER_BBL

```python
ENERGY_KWH_PER_BBL =
    (MOTOR_KW * 24 * RUNTIME_PCT / 100 / np.maximum(FLOW_BPD, 1))
```

## AlertExpression rules (14)

### RP_ROD_PART

Critical · rod_part

```python
RP_ROD_PART =
    FLUID_LOAD_RATIO < 0.3
```

### RP_GEARBOX_OVERLOAD

High · paraffin_drag

```python
RP_GEARBOX_OVERLOAD =
    GEARBOX_LOAD_PCT >= 100
```

### RP_STRUCTURE_OVERLOAD

High

```python
RP_STRUCTURE_OVERLOAD =
    PPRL_LB > 25600
```

### RP_ROD_OVERSTRESS

High · paraffin_drag

```python
RP_ROD_OVERSTRESS =
    ROD_LOADING_PCT > 100
```

### RP_FLUID_POUND

High · fluid_pound

```python
RP_FLUID_POUND =
    (PUMP_FILLAGE_PCT < 80)
    & (SUBMERGENCE_FT < 150)
    & (RUNTIME_PCT > 95)
    & (FLUID_LOAD_RATIO >= 0.3)
```

### RP_PUMP_LEAK

High · worn_pump

```python
RP_PUMP_LEAK =
    (TV_LOAD_LOSS_PCT > 10) & (FLUID_LOAD_RATIO >= 0.3)
```

### RP_TUBING_LEAK

High · tubing_leak

```python
RP_TUBING_LEAK =
    (VOL_EFF < 0.7)
    & (TV_LOAD_LOSS_PCT <= 10)
    & (PUMP_FILLAGE_PCT >= 80)
    & (FLUID_LOAD_RATIO >= 0.3)
```

### RP_GAS_INTERFERENCE

Medium · gas_interference

```python
RP_GAS_INTERFERENCE =
    (PUMP_FILLAGE_PCT < 80)
    & (SUBMERGENCE_FT >= 300)
    & (FLUID_LOAD_RATIO >= 0.3)
```

### RP_PRODUCTION_LOW

Medium · tubing_leak

```python
RP_PRODUCTION_LOW =
    (VOL_EFF < 0.7) & (FLUID_LOAD_RATIO >= 0.3)
```

### RP_PPRL_HIGH

Medium · paraffin_drag

```python
RP_PPRL_HIGH =
    PPRL_LB / PPRL_EXPECTED_LB > 1.15
```

### RP_MPRL_LOW

Medium · paraffin_drag

```python
RP_MPRL_LOW =
    (MPRL_LB / MPRL_EXPECTED_LB < 0.75) & (FLUID_LOAD_RATIO >= 0.3)
```

### RP_GEARBOX_HIGH

Medium

```python
RP_GEARBOX_HIGH =
    (GEARBOX_LOAD_PCT >= 90) & (GEARBOX_LOAD_PCT < 100)
```

### RP_OUT_OF_BALANCE

Medium · counterbalance_shift

```python
RP_OUT_OF_BALANCE =
    (BALANCE_RATIO < 0.75) | (BALANCE_RATIO > 1.33)
```

### RP_UNDERPUMPED

Low

```python
RP_UNDERPUMPED =
    (SUBMERGENCE_FT > 1000) & (PUMP_FILLAGE_PCT >= 95) & (RUNTIME_PCT >= 95)
```
