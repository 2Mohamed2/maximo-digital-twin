# GPU-5901: Maximo Monitor functions and alert rules

Device type `GROUND_POWER_400HZ`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### LOAD_KVA

```python
LOAD_KVA =
    ((U_OUT_A * I_A + U_OUT_B * I_B + U_OUT_C * I_C) / 1000)
```

### LOAD_PCT

```python
LOAD_PCT =
    (LOAD_KVA / 90 * 100)
```

### LOAD_PF

```python
LOAD_PF =
    np.clip(P_OUT_KW / np.maximum(LOAD_KVA, 0.1), 0, 1)
```

### V_CONN_AVG

```python
V_CONN_AVG =
    ((CONN_V_A + CONN_V_B + CONN_V_C) / 3)
```

### V_CONN_MIN

```python
V_CONN_MIN =
    np.minimum(np.minimum(CONN_V_A, CONN_V_B), CONN_V_C)
```

### V_UNBALANCE_V

```python
V_UNBALANCE_V =
    np.maximum(np.maximum(CONN_V_A, CONN_V_B), CONN_V_C)
    - np.minimum(np.minimum(CONN_V_A, CONN_V_B), CONN_V_C)
```

### CABLE_DROP_EXPECTED_V

```python
CABLE_DROP_EXPECTED_V =
    (
      ((I_A + I_B + I_C) / 3)
      * (
          0.0084 * np.clip(P_OUT_KW / np.maximum(LOAD_KVA, 0.1), 0, 1)
          + 0.01792
            * np.sqrt(
                1 - np.clip(P_OUT_KW / np.maximum(LOAD_KVA, 0.1), 0, 1) ** 2
              )
        )
    )
```

### CABLE_DROP_MEASURED_V

```python
CABLE_DROP_MEASURED_V =
    (((U_OUT_A + U_OUT_B + U_OUT_C) / 3) - V_CONN_AVG)
```

### CABLE_DROP_RATIO

```python
CABLE_DROP_RATIO =
    CABLE_DROP_MEASURED_V / np.maximum(CABLE_DROP_EXPECTED_V, 0.2)
```

### V_OUT_SETPOINT_V

```python
V_OUT_SETPOINT_V =
    115 + CABLE_DROP_EXPECTED_V
```

### REGULATION_ERROR_V

```python
REGULATION_ERROR_V =
    ((U_OUT_A + U_OUT_B + U_OUT_C) / 3) - V_OUT_SETPOINT_V
```

### FREQ_DEV_HZ

```python
FREQ_DEV_HZ =
    FREQ_HZ - 400
```

### LOSS_MEASURED_KW

```python
LOSS_MEASURED_KW =
    (P_IN_KW - P_OUT_KW)
```

### LOSS_EXPECTED_KW

```python
LOSS_EXPECTED_KW =
    (2.2 + 0.000295771 * LOAD_KVA ** 2)
```

### LOSS_EXCESS_KW

```python
LOSS_EXCESS_KW =
    (P_IN_KW - P_OUT_KW) - LOSS_EXPECTED_KW
```

### EFFICIENCY

```python
EFFICIENCY =
    P_OUT_KW / np.maximum(P_IN_KW, 0.1)
```

### EFFICIENCY_EXPECTED

```python
EFFICIENCY_EXPECTED =
    P_OUT_KW / np.maximum(P_OUT_KW + LOSS_EXPECTED_KW, 0.1)
```

### HEATSINK_RESIDUAL_K

```python
HEATSINK_RESIDUAL_K =
    HEATSINK_C - (AMBIENT_C + 6.5 * (P_IN_KW - P_OUT_KW))
```

### APU_FUEL_AVOIDED_KG_H

```python
APU_FUEL_AVOIDED_KG_H =
    (CONTACTOR > 0.5) * (1 - APU_RUNNING) * 110
```

### CO2_AVOIDED_KG_H

```python
CO2_AVOIDED_KG_H =
    (CONTACTOR > 0.5) * (1 - APU_RUNNING) * 347.6 - P_IN_KW * 0.4
```

## AlertExpression rules (15)

### GPU_CONN_VOLTAGE_LOW

High · cable_compensation_mismatch

```python
GPU_CONN_VOLTAGE_LOW =
    (CONTACTOR > 0.5)
    & (np.minimum(np.minimum(CONN_V_A, CONN_V_B), CONN_V_C) < 113)
```

### GPU_CONN_VOLTAGE_HIGH

High

```python
GPU_CONN_VOLTAGE_HIGH =
    (CONTACTOR > 0.5)
    & (np.maximum(np.maximum(CONN_V_A, CONN_V_B), CONN_V_C) > 118)
```

### GPU_THD_LIMIT

High · output_filter_aging

```python
GPU_THD_LIMIT =
    THD_V_PCT > 5
```

### GPU_OVERLOAD

High

```python
GPU_OVERLOAD =
    LOAD_PCT > 125
```

### GPU_HEATSINK_HOT

High · cooling_degraded

```python
GPU_HEATSINK_HOT =
    HEATSINK_C > 85
```

### GPU_REGULATION_ERROR

Medium · voltage_regulation_fault

```python
GPU_REGULATION_ERROR =
    (CONTACTOR > 0.5) & (LOAD_PCT > 20) & (np.absREGULATION_ERROR_V > 1.5)
```

### GPU_CABLE_DROP_HIGH

Medium · cable_compensation_mismatch

```python
GPU_CABLE_DROP_HIGH =
    (CONTACTOR > 0.5)
    & (LOAD_PCT > 20)
    & (CABLE_DROP_MEASURED_V / np.maximum(CABLE_DROP_EXPECTED_V, 0.2) > 1.6)
```

### GPU_PHASE_UNBALANCE

Medium · connector_pin_wear

```python
GPU_PHASE_UNBALANCE =
    (CONTACTOR > 0.5)
    & (
        np.maximum(np.maximum(CONN_V_A, CONN_V_B), CONN_V_C)
        - np.minimum(np.minimum(CONN_V_A, CONN_V_B), CONN_V_C)
        > 1.5
      )
```

### GPU_FREQ_OUT_OF_SPEC

Medium

```python
GPU_FREQ_OUT_OF_SPEC =
    np.abs(FREQ_HZ - 400) > 0.4
```

### GPU_THD_HIGH

Medium · output_filter_aging

```python
GPU_THD_HIGH =
    (THD_V_PCT > 2) & (THD_V_PCT <= 5)
```

### GPU_EFFICIENCY_LOW

Medium · power_stage_losses

```python
GPU_EFFICIENCY_LOW =
    (CONTACTOR > 0.5)
    & (LOAD_PCT > 20)
    & ((P_IN_KW - P_OUT_KW) - LOSS_EXPECTED_KW > 1.5)
```

### GPU_HEATSINK_FOULED

Medium · cooling_degraded

```python
GPU_HEATSINK_FOULED =
    HEATSINK_C - (AMBIENT_C + 6.5 * (P_IN_KW - P_OUT_KW)) > 12
```

### GPU_CONTACTOR_LIFE

Medium · contactor_wear

```python
GPU_CONTACTOR_LIFE =
    CONTACTOR_OPS > 90000
```

### GPU_CONNECTOR_CYCLES

Medium · connector_pin_wear

```python
GPU_CONNECTOR_CYCLES =
    PLUG_CYCLES > 5000
```

### GPU_APU_RUNNING

Medium · apu_left_running

```python
GPU_APU_RUNNING =
    (CONTACTOR > 0.5) & (APU_RUNNING > 0.5)
```
