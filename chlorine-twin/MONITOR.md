# CL-5101: Maximo Monitor functions and alert rules

Device type `CHLORINE_CONTACT_TANK`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### VOLUME_M3

```python
VOLUME_M3 =
    (800 * LEVEL_M)
```

### TDT_MIN

```python
TDT_MIN =
    ((800 * LEVEL_M) / FLOW_OUT_M3H * 60)
```

### T10_MIN

```python
T10_MIN =
    (0.3 * TDT_MIN)
```

### CL_OUT_MIN_MGL

```python
CL_OUT_MIN_MGL =
    np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL)
```

### CT_ACHIEVED

```python
CT_ACHIEVED =
    (np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL) * T10_MIN)
```

### CT99_9_GIARDIA

```python
CT99_9_GIARDIA =
    np.where(
      TEMP_C < 12.5,
      1.059
      * (
          12.006
          + np.exp(
              2.46
              - 0.073 * TEMP_C
              + 0.125 * np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL)
              + 0.389 * PH
            )
        ),
      1.083
      * (
          -2.261
          + np.exp(
              2.69
              - 0.065 * TEMP_C
              + 0.111 * np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL)
              + 0.361 * PH
            )
        )
    )
```

### CT_REQUIRED

```python
CT_REQUIRED =
    np.where(
      TEMP_C < 12.5,
      1.059
      * (
          12.006
          + np.exp(
              2.46
              - 0.073 * TEMP_C
              + 0.125 * np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL)
              + 0.389 * PH
            )
        ),
      1.083
      * (
          -2.261
          + np.exp(
              2.69
              - 0.065 * TEMP_C
              + 0.111 * np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL)
              + 0.361 * PH
            )
        )
    )
    * 0.1666666667
```

### GIARDIA_LOG

```python
GIARDIA_LOG =
    (
      3
      * CT_ACHIEVED
      / np.where(
          TEMP_C < 12.5,
          1.059
          * (
              12.006
              + np.exp(
                  2.46
                  - 0.073 * TEMP_C
                  + 0.125 * np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL)
                  + 0.389 * PH
                )
            ),
          1.083
          * (
              -2.261
              + np.exp(
                  2.69
                  - 0.065 * TEMP_C
                  + 0.111 * np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL)
                  + 0.361 * PH
                )
            )
        )
    )
```

### CT_RATIO

```python
CT_RATIO =
    (GIARDIA_LOG / 0.5)
```

### VIRUS_LOG

```python
VIRUS_LOG =
    4
    * CT_ACHIEVED
    / np.interp(TEMP_C, [0.5, 5, 10, 15, 20, 25], [12, 8, 6, 4, 3, 2])
```

### HOCL_FRACTION

```python
HOCL_FRACTION =
    1
    / (
        1
        + 10
          ** (
               PH
               - (
                   3000 / (TEMP_C + 273.15)
                   - 10.0686
                   + 0.0253 * (TEMP_C + 273.15)
                 )
             )
      )
```

### HYPO_STRENGTH_GL

```python
HYPO_STRENGTH_GL =
    (
      HYPO_DELIVERED_GL
      * np.exp(
          -0.00385081767
          * np.exp(1.32175584 * (HYPO_TEMP_C - 25) / 10)
          * HYPO_AGE_D
        )
    )
```

### DOSE_APPLIED_MGL

```python
DOSE_APPLIED_MGL =
    (PUMP_FLOW_LH * HYPO_STRENGTH_GL / FLOW_IN_M3H)
```

### CL_DEMAND_MGL

```python
CL_DEMAND_MGL =
    DOSE_APPLIED_MGL - CL_IN_MGL
```

### CL_DECAY_PER_H

```python
CL_DECAY_PER_H =
    (
      np.log(
        np.maximum(CL_IN_MGL, 0.01)
        / np.maximum(np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL), 0.01)
      )
      / (TDT_MIN / 60)
    )
```

### PUMP_FLOW_RATIO

```python
PUMP_FLOW_RATIO =
    PUMP_FLOW_LH / PUMP_SP_LH
```

### TRIM_RATIO

```python
TRIM_RATIO =
    DOSE_SP_MGL / 1.6
```

### ANALYSER_DIFF_MGL

```python
ANALYSER_DIFF_MGL =
    np.abs(CL_OUT_A_MGL - CL_OUT_B_MGL)
```

### HYPO_DAYS_LEFT

```python
HYPO_DAYS_LEFT =
    HYPO_LEVEL_PCT / 100 * 15000 / np.maximum(PUMP_FLOW_LH * 24, 0.1)
```

## AlertExpression rules (14)

### CL_CT_FAIL

Critical · cold_peak_drawdown

```python
CL_CT_FAIL =
    CT_RATIO < 1
```

### CL_ENTRY_LOW

Critical · dose_pump_gas_lock

```python
CL_ENTRY_LOW =
    np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL) < 0.2
```

### CL_OUTLET_LOW

High · analyser_drift

```python
CL_OUTLET_LOW =
    (np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL) >= 0.2)
    & (np.minimum(CL_OUT_A_MGL, CL_OUT_B_MGL) < 0.7)
```

### CL_OUTLET_HIGH

High

```python
CL_OUTLET_HIGH =
    np.maximum(CL_OUT_A_MGL, CL_OUT_B_MGL) > 4
```

### DOSE_PUMP_DEVIATION

High · dose_pump_gas_lock

```python
DOSE_PUMP_DEVIATION =
    np.abs(PUMP_FLOW_LH / PUMP_SP_LH - 1) > 0.15
```

### CL_CT_MARGIN_LOW

Medium · cold_peak_drawdown

```python
CL_CT_MARGIN_LOW =
    (CT_RATIO >= 1) & (CT_RATIO < 1.5)
```

### CL_LEVEL_LOW

Medium · cold_peak_drawdown

```python
CL_LEVEL_LOW =
    LEVEL_M < 2.5
```

### CL_ANALYSER_MISMATCH

Medium · analyser_drift

```python
CL_ANALYSER_MISMATCH =
    np.abs(CL_OUT_A_MGL - CL_OUT_B_MGL) > 0.2
```

### HYPO_STRENGTH_LOW

Medium · hypo_strength_loss

```python
HYPO_STRENGTH_LOW =
    HYPO_STRENGTH_GL < 100
```

### CL_DEMAND_HIGH

Medium · demand_rise

```python
CL_DEMAND_HIGH =
    CL_DEMAND_MGL > 1
```

### CL_DECAY_HIGH

Medium · clearwell_decay

```python
CL_DECAY_HIGH =
    CL_DECAY_PER_H > 0.12
```

### CL_TRIM_HIGH

Medium · hypo_strength_loss

```python
CL_TRIM_HIGH =
    DOSE_SP_MGL / 1.6 > 1.5
```

### CL_PH_HIGH

Medium · ph_high

```python
CL_PH_HIGH =
    PH > 8
```

### HYPO_STOCK_LOW

Low

```python
HYPO_STOCK_LOW =
    HYPO_LEVEL_PCT / 100 * 15000 / np.maximum(PUMP_FLOW_LH * 24, 0.1) < 5
```
