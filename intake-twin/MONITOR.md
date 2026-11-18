# INT-3701: Maximo Monitor functions and alert rules

Device type `CW_INTAKE_SCREEN`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### DH_M

```python
DH_M =
    (LEVEL_UP_M - LEVEL_DOWN_M)
```

### DH_CLEAN_M

```python
DH_CLEAN_M =
    (0.05 * (CW_FLOW_M3S / 5) ** 2 * (6.5 / LEVEL_UP_M) ** 2)
```

### DH_RATIO

```python
DH_RATIO =
    (LEVEL_UP_M - LEVEL_DOWN_M) / DH_CLEAN_M
```

### BLINDING

```python
BLINDING =
    np.clip(
      1
      - np.sqrt(DH_CLEAN_M / np.maximum((LEVEL_UP_M - LEVEL_DOWN_M), 0.001)),
      0,
      1
    )
```

### V_THROUGH_SCREEN

```python
V_THROUGH_SCREEN =
    CW_FLOW_M3S / (1.44 * LEVEL_UP_M)
```

### V_APPROACH

```python
V_APPROACH =
    CW_FLOW_M3S / (3.5 * LEVEL_UP_M)
```

### CULVERT_LOSS_M

```python
CULVERT_LOSS_M =
    (SEA_LEVEL_M - LEVEL_UP_M)
```

### CULVERT_LOSS_RATIO

```python
CULVERT_LOSS_RATIO =
    (SEA_LEVEL_M - LEVEL_UP_M)
    / (0.1 * (np.maximum(CW_FLOW_M3S, 0.1) / 5) ** 2)
```

### SUBMERGENCE_M

```python
SUBMERGENCE_M =
    (LEVEL_DOWN_M - 0.6)
```

### SUBMERGENCE_REQ_M

```python
SUBMERGENCE_REQ_M =
    (1.9 + 0.3570039732 * CW_FLOW_M3S)
```

### SUBMERGENCE_MARGIN

```python
SUBMERGENCE_MARGIN =
    (LEVEL_DOWN_M - 0.6) / SUBMERGENCE_REQ_M
```

### PUMP_HEAD_M

```python
PUMP_HEAD_M =
    (PUMP_DISCHARGE_BAR * 9.945053579 + 9.5 - LEVEL_DOWN_M)
```

### PUMP_HEAD_EXPECTED_M

```python
PUMP_HEAD_EXPECTED_M =
    (27 - 9 * (CW_FLOW_M3S / 5) ** 2)
```

### PUMP_HEAD_RATIO

```python
PUMP_HEAD_RATIO =
    PUMP_HEAD_M / PUMP_HEAD_EXPECTED_M
```

### PUMP_EFF

```python
PUMP_EFF =
    (10.05525 * CW_FLOW_M3S * PUMP_HEAD_M / np.maximum(PUMP_POWER_KW, 1))
```

### PUMP_EFF_RATIO

```python
PUMP_EFF_RATIO =
    PUMP_EFF / (0.88 * (2 * CW_FLOW_M3S / 5 - (CW_FLOW_M3S / 5) ** 2))
```

### TORQUE_EXPECTED_PCT

```python
TORQUE_EXPECTED_PCT =
    (25 + 40 * (LEVEL_UP_M - LEVEL_DOWN_M))
```

### TORQUE_RESIDUAL_PCT

```python
TORQUE_RESIDUAL_PCT =
    SCREEN_TORQUE_PCT - TORQUE_EXPECTED_PCT
```

### WASH_NOZZLE_RATIO

```python
WASH_NOZZLE_RATIO =
    ((WASH_FLOW_M3H / 60) / np.sqrt(np.maximum(WASH_PRESSURE_BAR, 0.1) / 4))
```

### COND_DP_RATIO

```python
COND_DP_RATIO =
    (COND_DP_BAR / (0.6 * (np.maximum(CW_FLOW_M3S, 0.1) / 5) ** 2))
```

## AlertExpression rules (15)

### INT_DP_HIGH_HIGH

Critical · debris_surge

```python
INT_DP_HIGH_HIGH =
    (LEVEL_UP_M - LEVEL_DOWN_M) > 0.8
```

### INT_SUBMERGENCE_LOW

High · culvert_fouling

```python
INT_SUBMERGENCE_LOW =
    SUBMERGENCE_MARGIN < 1
```

### INT_DP_HIGH

High · debris_surge

```python
INT_DP_HIGH =
    ((LEVEL_UP_M - LEVEL_DOWN_M) > 0.4)
    & ((LEVEL_UP_M - LEVEL_DOWN_M) <= 0.8)
```

### INT_SCREEN_BYPASS

High · seal_carryover

```python
INT_SCREEN_BYPASS =
    DH_RATIO < 0.4
```

### INT_DRIVE_TORQUE_HIGH

High · drive_chain_wear

```python
INT_DRIVE_TORQUE_HIGH =
    (SCREEN_SPEED_M_MIN > 0.5) & (TORQUE_RESIDUAL_PCT > 20)
```

### INT_PUMP_VIBRATION

High · culvert_fouling

```python
INT_PUMP_VIBRATION =
    PUMP_VIB_MM_S > 7.1
```

### INT_SCREEN_BLINDING

Medium · debris_surge

```python
INT_SCREEN_BLINDING =
    np.clip(
      1
      - np.sqrt(DH_CLEAN_M / np.maximum((LEVEL_UP_M - LEVEL_DOWN_M), 0.001)),
      0,
      1
    )
    > 0.35
```

### INT_WASH_DUTY_HIGH

Medium · mesh_biofouling

```python
INT_WASH_DUTY_HIGH =
    HIGH_SPEED_H_24H > 12
```

### INT_WASH_NOZZLES_BLOCKED

Medium · spray_nozzle_blockage

```python
INT_WASH_NOZZLES_BLOCKED =
    WASH_NOZZLE_RATIO < 0.8
```

### INT_WASH_PRESSURE_LOW

Medium · wash_pump_wear

```python
INT_WASH_PRESSURE_LOW =
    WASH_PRESSURE_BAR < 3
```

### INT_PUMP_HEAD_LOW

Medium · cw_pump_wear

```python
INT_PUMP_HEAD_LOW =
    PUMP_HEAD_RATIO < 0.92
```

### INT_PUMP_EFF_LOW

Medium · cw_pump_wear

```python
INT_PUMP_EFF_LOW =
    PUMP_EFF_RATIO < 0.92
```

### INT_CULVERT_LOSS_HIGH

Medium · culvert_fouling

```python
INT_CULVERT_LOSS_HIGH =
    CULVERT_LOSS_RATIO > 2.5
```

### INT_COND_DP_HIGH

Medium · seal_carryover

```python
INT_COND_DP_HIGH =
    COND_DP_RATIO > 1.3
```

### INT_CW_INLET_HIGH

Medium

```python
INT_CW_INLET_HIGH =
    CW_IN_C > 33
```
