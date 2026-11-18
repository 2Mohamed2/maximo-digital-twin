# BR-6001: Maximo Monitor functions and alert rules

Device type `BRIDGE_BEARINGS_JOINTS`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### TE_EFFECTIVE_C

```python
TE_EFFECTIVE_C =
    (0.5 * SLAB_TEMP_C + 0.5 * GIRDER_TEMP_C)
```

### SLAB_GIRDER_DIFF_K

```python
SLAB_GIRDER_DIFF_K =
    SLAB_TEMP_C - GIRDER_TEMP_C
```

### MOVE_EXP_P2_MM

```python
MOVE_EXP_P2_MM =
    (0.96 * (TE_EFFECTIVE_C - 10))
```

### RES_P2_MM

```python
RES_P2_MM =
    (BEARING_P2_DISP_MM - MOVE_EXP_P2_MM)
```

### MOVE_EXP_A2_MM

```python
MOVE_EXP_A2_MM =
    (1.68 * (TE_EFFECTIVE_C - 10))
```

### RES_A2_MM

```python
RES_A2_MM =
    BEARING_A2_DISP_MM - MOVE_EXP_A2_MM
```

### GAP_RES_A1_MM

```python
GAP_RES_A1_MM =
    (JOINT_A1_GAP_MM - (50 - 0.72 * (TE_EFFECTIVE_C - 10)))
```

### GAP_A2_TOTAL_MM

```python
GAP_A2_TOTAL_MM =
    (JOINT_A2_GAP1_MM + JOINT_A2_GAP2_MM + JOINT_A2_GAP3_MM)
```

### GAP_EXP_A2_MM

```python
GAP_EXP_A2_MM =
    (110 - MOVE_EXP_A2_MM)
```

### GAP_RES_A2_MM

```python
GAP_RES_A2_MM =
    (GAP_A2_TOTAL_MM - GAP_EXP_A2_MM)
```

### GAP_SPREAD_A2_MM

```python
GAP_SPREAD_A2_MM =
    np.maximum(
      np.maximum(JOINT_A2_GAP1_MM, JOINT_A2_GAP2_MM),
      JOINT_A2_GAP3_MM
    )
    - np.minimum(
        np.minimum(JOINT_A2_GAP1_MM, JOINT_A2_GAP2_MM),
        JOINT_A2_GAP3_MM
      )
```

### CLOSURE_A2_MM

```python
CLOSURE_A2_MM =
    (GAP_A2_TOTAL_MM + BEARING_A2_DISP_MM - 110)
```

### FRICTION_COEFF_EST

```python
FRICTION_COEFF_EST =
    (0.048 * np.abs(PIER_P2_TILT_MRAD))
```

### STRAIN_STATIC_RES_UE

```python
STRAIN_STATIC_RES_UE =
    (STRAIN_STATIC_UE - 1.5 * (SLAB_TEMP_C - GIRDER_TEMP_C))
```

### STRAIN_EXPECTED_UE

```python
STRAIN_EXPECTED_UE =
    (0.3 * WIM_LAST_HEAVY_KN)
```

### STRAIN_RATIO

```python
STRAIN_RATIO =
    (STRAIN_PEAK_UE / (0.3 * WIM_LAST_HEAVY_KN))
```

### SLIDING_GAP_EXPECTED_MM

```python
SLIDING_GAP_EXPECTED_MM =
    2 - 0.05 * BEARING_P2_PATH_M / 1000
```

### WEAR_LIFE_YEARS

```python
WEAR_LIFE_YEARS =
    ((10000 - BEARING_P2_PATH_M) / np.maximum(BEARING_P2_PATH_RATE_M_Y, 1))
```

### PATH_USED_PCT

```python
PATH_USED_PCT =
    BEARING_P2_PATH_M / 10000 * 100
```

## AlertExpression rules (15)

### BR_BEARING_SEIZED

High · bearing_seized

```python
BR_BEARING_SEIZED =
    (np.abs(RES_P2_MM) > 8) & (np.abs(PIER_P2_TILT_MRAD) > 1)
```

### BR_PIER_TILT

High · bearing_seized

```python
BR_PIER_TILT =
    np.abs(PIER_P2_TILT_MRAD) > 1
```

### BR_JOINT_BLOCKED

High · joint_blocked

```python
BR_JOINT_BLOCKED =
    (GAP_RES_A2_MM > 10) | (GAP_RES_A1_MM > 10)
```

### BR_DECK_RESTRAINT

High · joint_blocked

```python
BR_DECK_RESTRAINT =
    np.abs(STRAIN_STATIC_RES_UE) > 50
```

### BR_JOINT_GAP_LIMIT

High · joint_control_failure

```python
BR_JOINT_GAP_LIMIT =
    (
      np.maximum(
        np.maximum(JOINT_A2_GAP1_MM, JOINT_A2_GAP2_MM),
        JOINT_A2_GAP3_MM
      )
      > 80
    )
    | (
        np.minimum(
          np.minimum(JOINT_A2_GAP1_MM, JOINT_A2_GAP2_MM),
          JOINT_A2_GAP3_MM
        )
        < 5
      )
```

### BR_STRAIN_RATIO_HIGH

High · girder_stiffness_loss

```python
BR_STRAIN_RATIO_HIGH =
    STRAIN_RATIO > 1.2
```

### BR_BEARING_FRICTION_HIGH

Medium · ptfe_wear

```python
BR_BEARING_FRICTION_HIGH =
    FRICTION_COEFF_EST > 0.03
```

### BR_SLIDING_GAP_LOW

Medium · ptfe_wear

```python
BR_SLIDING_GAP_LOW =
    BEARING_P2_SLIDING_GAP_MM < 1
```

### BR_WEAR_RATE_HIGH

Medium · sliding_path_fast

```python
BR_WEAR_RATE_HIGH =
    BEARING_P2_PATH_RATE_M_Y > 600
```

### BR_WEAR_LIFE_LOW

Medium · sliding_path_fast

```python
BR_WEAR_LIFE_LOW =
    WEAR_LIFE_YEARS < 5
```

### BR_JOINT_GAP_UNEVEN

Medium · joint_control_failure

```python
BR_JOINT_GAP_UNEVEN =
    GAP_SPREAD_A2_MM > 15
```

### BR_JOINT_IMPACT

Medium · joint_control_failure

```python
BR_JOINT_IMPACT =
    JOINT_A2_IMPACT_G > 6
```

### BR_OVERWEIGHT_TRAFFIC

Medium · overweight_traffic

```python
BR_OVERWEIGHT_TRAFFIC =
    WIM_OVERWEIGHT_24H > 20
```

### BR_SENSOR_MISMATCH

Low · displacement_sensor

```python
BR_SENSOR_MISMATCH =
    np.abs(CLOSURE_A2_MM) > 6
```

### BR_TEMP_OUTSIDE_DESIGN

Low

```python
BR_TEMP_OUTSIDE_DESIGN =
    (TE_EFFECTIVE_C > 45) | (TE_EFFECTIVE_C < -20)
```
