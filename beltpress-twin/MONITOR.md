# BP-5001: Maximo Monitor functions and alert rules

Device type `BELT_FILTER_PRESS`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### FEED_DS_KGH

```python
FEED_DS_KGH =
    (FEED_FLOW_M3H * FEED_DS_PCT * 10)
```

### HYDRAULIC_LOAD_M3MH

```python
HYDRAULIC_LOAD_M3MH =
    FEED_FLOW_M3H / 2
```

### SOLIDS_LOAD_KGMH

```python
SOLIDS_LOAD_KGMH =
    FEED_DS_KGH / 2
```

### HYDRAULIC_RATIO

```python
HYDRAULIC_RATIO =
    FEED_FLOW_M3H / 45
```

### SOLIDS_RATIO

```python
SOLIDS_RATIO =
    (FEED_DS_KGH / 900)
```

### POLYMER_ACTIVE_KGH

```python
POLYMER_ACTIVE_KGH =
    (POLYMER_SOLUTION_LPH * 0.0025)
```

### POLYMER_KG_PER_TDS

```python
POLYMER_KG_PER_TDS =
    (
      (POLYMER_SOLUTION_LPH * 0.0025)
      / np.maximum(FEED_DS_KGH / 1000, 0.001)
    )
```

### CAKE_DS_EXPECTED_PCT

```python
CAKE_DS_EXPECTED_PCT =
    (
      26 * (1 - np.exp(-POLYMER_KG_PER_TDS / 2))
      - 0.4 * np.maximum(POLYMER_KG_PER_TDS - 7, 0)
      + 1 * (np.minimum(TENSION_UPPER_BAR, TENSION_LOWER_BAR) - 5)
      - 4 * np.maximum(SOLIDS_RATIO - 1, 0)
    )
```

### CAKE_DS_RESIDUAL_PCT

```python
CAKE_DS_RESIDUAL_PCT =
    CAKE_DS_PCT - CAKE_DS_EXPECTED_PCT
```

### FILTRATE_SOLIDS_KGH

```python
FILTRATE_SOLIDS_KGH =
    (FILTRATE_FLOW_M3H * FILTRATE_TSS_MGL / 1000)
```

### CAPTURE_PCT

```python
CAPTURE_PCT =
    (100 * (1 - FILTRATE_SOLIDS_KGH / np.maximum(FEED_DS_KGH, 0.001)))
```

### CAKE_TPH

```python
CAKE_TPH =
    (
      FEED_DS_KGH
      * CAPTURE_PCT
      / 100
      / np.maximum(CAKE_DS_PCT / 100, 0.01)
      / 1000
    )
```

### FILTRATE_EXPECTED_M3H

```python
FILTRATE_EXPECTED_M3H =
    (
      FEED_FLOW_M3H
      + POLYMER_SOLUTION_LPH / 1000
      + WASH_FLOW_M3H
      - CAKE_TPH / 1
    )
```

### WATER_BALANCE_M3H

```python
WATER_BALANCE_M3H =
    FILTRATE_FLOW_M3H - FILTRATE_EXPECTED_M3H
```

### NOZZLE_OPEN_RATIO

```python
NOZZLE_OPEN_RATIO =
    (
      WASH_FLOW_M3H
      / (13.6 * np.sqrt(np.maximum(WASH_PRESSURE_BAR, 0.01) / 8))
    )
```

### WASH_M3_PER_TDS

```python
WASH_M3_PER_TDS =
    WASH_FLOW_M3H / np.maximum(FEED_DS_KGH / 1000, 0.001)
```

### TENSION_MIN_BAR

```python
TENSION_MIN_BAR =
    np.minimum(TENSION_UPPER_BAR, TENSION_LOWER_BAR)
```

### TRACKING_MAX_MM

```python
TRACKING_MAX_MM =
    np.maximum(np.abs(TRACKING_UPPER_MM), np.abs(TRACKING_LOWER_MM))
```

### BELT_LIFE_USED_PCT

```python
BELT_LIFE_USED_PCT =
    BELT_HOURS / 2700 * 100
```

## AlertExpression rules (13)

### BP_TRACKING_LIMIT

Critical · belt_mistracking

```python
BP_TRACKING_LIMIT =
    np.maximum(np.abs(TRACKING_UPPER_MM), np.abs(TRACKING_LOWER_MM)) > 35
```

### BP_CAPTURE_LOW

High · polymer_weak

```python
BP_CAPTURE_LOW =
    (RUNNING > 0.5) & (CAPTURE_PCT < 90)
```

### BP_CAKE_DRY_LOW

High · polymer_weak

```python
BP_CAKE_DRY_LOW =
    (RUNNING > 0.5) & (CAKE_DS_RESIDUAL_PCT < -2)
```

### BP_HYDRAULIC_HIGH

High · feed_overload

```python
BP_HYDRAULIC_HIGH =
    (RUNNING > 0.5) & ((FEED_FLOW_M3H / 45) > 1)
```

### BP_WASH_PRESSURE_LOW

High · wash_pressure_low

```python
BP_WASH_PRESSURE_LOW =
    (RUNNING > 0.5) & (WASH_PRESSURE_BAR < 6)
```

### BP_SOLIDS_LOAD_HIGH

Medium · feed_overload

```python
BP_SOLIDS_LOAD_HIGH =
    (RUNNING > 0.5) & (SOLIDS_RATIO > 1)
```

### BP_POLYMER_HIGH

Medium · polymer_overdose

```python
BP_POLYMER_HIGH =
    (RUNNING > 0.5) & (POLYMER_KG_PER_TDS > 8)
```

### BP_WASH_NOZZLES_BLOCKED

Medium · wash_nozzle_blinding

```python
BP_WASH_NOZZLES_BLOCKED =
    (RUNNING > 0.5) & (WASH_PRESSURE_BAR >= 6) & (NOZZLE_OPEN_RATIO < 0.8)
```

### BP_TRACKING_OFF

Medium · belt_mistracking

```python
BP_TRACKING_OFF =
    (np.maximum(np.abs(TRACKING_UPPER_MM), np.abs(TRACKING_LOWER_MM)) > 20)
    & (
        np.maximum(np.abs(TRACKING_UPPER_MM), np.abs(TRACKING_LOWER_MM))
        <= 35
      )
```

### BP_TENSION_LOW

Medium · tension_low

```python
BP_TENSION_LOW =
    (RUNNING > 0.5) & (np.minimum(TENSION_UPPER_BAR, TENSION_LOWER_BAR) < 4)
```

### BP_BELT_HOURS_HIGH

Medium · belt_wear

```python
BP_BELT_HOURS_HIGH =
    BELT_HOURS > 2700
```

### BP_FEED_SOLIDS_LOW

Low

```python
BP_FEED_SOLIDS_LOW =
    (RUNNING > 0.5) & (FEED_DS_PCT < 2)
```

### BP_WATER_BALANCE

Low

```python
BP_WATER_BALANCE =
    (RUNNING > 0.5) & (np.absWATER_BALANCE_M3H > 4)
```
