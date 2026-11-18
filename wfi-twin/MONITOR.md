# WFI-6701: Maximo Monitor functions and alert rules

Device type `WFI_LOOP`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### POU_DRAW_M3H

```python
POU_DRAW_M3H =
    SUPPLY_FLOW_M3H - RETURN_FLOW_M3H
```

### SUPPLY_VELOCITY_MS

```python
SUPPLY_VELOCITY_MS =
    SUPPLY_FLOW_M3H / 3600 / 0.00177205460617
```

### RETURN_VELOCITY_MS

```python
RETURN_VELOCITY_MS =
    (RETURN_FLOW_M3H / 3600 / 0.000951148591801)
```

### RETURN_DENSITY_KGM3

```python
RETURN_DENSITY_KGM3 =
    (
      1000
      * (
          1
          - (RETURN_TEMP_C + 288.9414)
            / (508929.2 * (RETURN_TEMP_C + 68.12963))
            * (RETURN_TEMP_C - 3.9863) ** 2
        )
    )
```

### RETURN_VISCOSITY_MPAS

```python
RETURN_VISCOSITY_MPAS =
    (2.414e-05 * np.power(10, 247.8 / (RETURN_TEMP_C + 133.15))) * 1000
```

### RETURN_REYNOLDS

```python
RETURN_REYNOLDS =
    RETURN_DENSITY_KGM3
    * RETURN_VELOCITY_MS
    * 0.0348
    / (2.414e-05 * np.power(10, 247.8 / (RETURN_TEMP_C + 133.15)))
```

### LOOP_MIN_TEMP_C

```python
LOOP_MIN_TEMP_C =
    np.minimum(np.minimum(SUPPLY_TEMP_C, RETURN_TEMP_C), TANK_TEMP_C)
```

### LOOP_HEAT_LOSS_KW

```python
LOOP_HEAT_LOSS_KW =
    RETURN_DENSITY_KGM3
    * 4.19
    * RETURN_FLOW_M3H
    / 3600
    * (SUPPLY_TEMP_C - RETURN_TEMP_C)
```

### COND_STAGE1_LIMIT

```python
COND_STAGE1_LIMIT =
    np.array([0.6, 0.8, 0.9, 1, 1.1, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9, 2.1, 2.2, 2.4, 2.5, 2.7, 2.7, 2.7, 2.7, 2.9, 3.1])[np.clip(np.floor(RETURN_TEMP_C / 5), 0, 20).astype(int)]
```

### COND_RATIO

```python
COND_RATIO =
    COND_US_CM
    / np.array([0.6, 0.8, 0.9, 1, 1.1, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9, 2.1, 2.2, 2.4, 2.5, 2.7, 2.7, 2.7, 2.7, 2.9, 3.1])[np.clip(np.floor(RETURN_TEMP_C / 5), 0, 20).astype(int)]
```

### TOC_RATIO

```python
TOC_RATIO =
    TOC_PPB / 500
```

### PUMP_DP_EXPECTED_BAR

```python
PUMP_DP_EXPECTED_BAR =
    (3.4 * (PUMP_SPEED_RPM / 2900) ** 2 - 0.012 * SUPPLY_FLOW_M3H ** 2)
```

### PUMP_DP_RATIO

```python
PUMP_DP_RATIO =
    PUMP_DP_BAR / PUMP_DP_EXPECTED_BAR
```

### PUMP_EFFICIENCY

```python
PUMP_EFFICIENCY =
    SUPPLY_FLOW_M3H * PUMP_DP_BAR / 36 / PUMP_POWER_KW
```

### SEAL_QUENCH_RISE_C

```python
SEAL_QUENCH_RISE_C =
    SEAL_QUENCH_TEMP_C - 25
```

### COOLER_DP_BAR

```python
COOLER_DP_BAR =
    COOLER_WFI_BAR - COOLER_CW_BAR
```

### DEADLEG_DELTA_C

```python
DEADLEG_DELTA_C =
    np.minimum(np.minimum(SUPPLY_TEMP_C, RETURN_TEMP_C), TANK_TEMP_C)
    - DEADLEG_TEMP_C
```

### VENT_FILTER_MARGIN_C

```python
VENT_FILTER_MARGIN_C =
    VENT_FILTER_TEMP_C - TANK_TEMP_C
```

### MICRO_RATIO

```python
MICRO_RATIO =
    MICRO_CFU_100ML / 10
```

### ENDOTOXIN_RATIO

```python
ENDOTOXIN_RATIO =
    ENDOTOXIN_EU_ML / 0.25
```

## AlertExpression rules (15)

### WFI_COOLER_LEAK

Critical · cooler_leak

```python
WFI_COOLER_LEAK =
    COOLER_TELLTALE > 0.5
```

### WFI_TEMP_LOW

High · heating_loss

```python
WFI_TEMP_LOW =
    np.minimum(np.minimum(SUPPLY_TEMP_C, RETURN_TEMP_C), TANK_TEMP_C) < 70
```

### WFI_VELOCITY_LOW

High · over_draw

```python
WFI_VELOCITY_LOW =
    RETURN_VELOCITY_MS < 0.9
```

### WFI_COND_STAGE1_FAIL

High · generator_upset

```python
WFI_COND_STAGE1_FAIL =
    COND_RATIO > 1
```

### WFI_TOC_LIMIT

High · generator_upset

```python
WFI_TOC_LIMIT =
    TOC_PPB > 500
```

### WFI_MICRO_ACTION

High · biofilm_deadleg

```python
WFI_MICRO_ACTION =
    (MICRO_CFU_100ML >= 10) | (ENDOTOXIN_EU_ML >= 0.25)
```

### WFI_COOLER_DP_LOW

High · cooler_leak

```python
WFI_COOLER_DP_LOW =
    COOLER_DP_BAR < 0.5
```

### WFI_TEMP_MARGIN_LOW

Medium · heating_loss

```python
WFI_TEMP_MARGIN_LOW =
    (np.minimum(np.minimum(SUPPLY_TEMP_C, RETURN_TEMP_C), TANK_TEMP_C) < 75)
    & (
        np.minimum(np.minimum(SUPPLY_TEMP_C, RETURN_TEMP_C), TANK_TEMP_C)
        >= 70
      )
```

### WFI_COND_ALERT

Medium · generator_upset

```python
WFI_COND_ALERT =
    (COND_RATIO > 0.6) & (COND_RATIO <= 1)
```

### WFI_TOC_ALERT

Medium · generator_upset

```python
WFI_TOC_ALERT =
    (TOC_PPB > 250) & (TOC_PPB <= 500)
```

### WFI_PUMP_HEAD_LOW

Medium · pump_wear

```python
WFI_PUMP_HEAD_LOW =
    PUMP_DP_RATIO < 0.9
```

### WFI_SEAL_LEAK

Medium · seal_wear

```python
WFI_SEAL_LEAK =
    (SEAL_QUENCH_TEMP_C - 25) > 20
```

### WFI_DEADLEG_COLD

Medium · biofilm_deadleg

```python
WFI_DEADLEG_COLD =
    DEADLEG_DELTA_C > 10
```

### WFI_SUBLOOP_SANITISE_DUE

Medium · biofilm_deadleg

```python
WFI_SUBLOOP_SANITISE_DUE =
    SUBLOOP_COLD_H > 8
```

### WFI_VENT_FILTER_COLD

Medium · vent_heater_fail

```python
WFI_VENT_FILTER_COLD =
    VENT_FILTER_MARGIN_C < 3
```
