# PUMP-101: Maximo Monitor functions and alert rules

Device type `PUMP_CENTRIFUGAL`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (10)

### SPEED_RATIO

```python
SPEED_RATIO =
    (SPEED_RPM.clip(lower=1) / 1450)
```

### BEP_RATIO

```python
BEP_RATIO =
    ((FLOW_M3H / SPEED_RATIO) / 486)
```

### HEAD_EXPECTED_M

```python
HEAD_EXPECTED_M =
    (
      SPEED_RATIO**2
      * (
          69.4477201136
          + (FLOW_M3H / SPEED_RATIO)
            * (
                -0.012451785361
                + (FLOW_M3H / SPEED_RATIO)
                  * (
                      5.83106513097e-05
                      + (FLOW_M3H / SPEED_RATIO) * (-1.50973057711e-07)
                    )
              )
        )
    )
```

### HEAD_DEVIATION_PCT

```python
HEAD_DEVIATION_PCT =
    (HEAD_M - HEAD_EXPECTED_M) / HEAD_EXPECTED_M.clip(lower=1) * 100
```

### EFF_EXPECTED_PCT

```python
EFF_EXPECTED_PCT =
    (
      100
      * 9792.342
      * (FLOW_M3H / SPEED_RATIO)
      / 3600
      * (
          69.4477201136
          + (FLOW_M3H / SPEED_RATIO)
            * (
                -0.012451785361
                + (FLOW_M3H / SPEED_RATIO)
                  * (
                      5.83106513097e-05
                      + (FLOW_M3H / SPEED_RATIO) * (-1.50973057711e-07)
                    )
              )
        )
      / (
          1000
          * (
              34.2602680006
              + (FLOW_M3H / SPEED_RATIO)
                * (
                    0.18977819823
                    + (FLOW_M3H / SPEED_RATIO)
                      * (
                          -0.000128008700931
                          + (FLOW_M3H / SPEED_RATIO) * (5.40530698495e-08)
                        )
                  )
            )
        )
    )
```

### EFF_DEVIATION_PTS

```python
EFF_DEVIATION_PTS =
    PUMP_EFFICIENCY_PCT - EFF_EXPECTED_PCT
```

### NPSHR_M

```python
NPSHR_M =
    (
      SPEED_RATIO**2
      * (
          -0.974303889413
          + (FLOW_M3H / SPEED_RATIO).clip(lower=300)
            * (
                0.0189244268458
                + (FLOW_M3H / SPEED_RATIO).clip(lower=300)
                  * (
                      -4.36870791769e-05
                      + (FLOW_M3H / SPEED_RATIO).clip(lower=300)
                        * (4.09013238085e-08)
                    )
              )
        )
    )
```

### NPSH_MARGIN_M

```python
NPSH_MARGIN_M =
    NPSHA_M - NPSHR_M
```

### SPECIFIC_ENERGY_KWH_M3

```python
SPECIFIC_ENERGY_KWH_M3 =
    MOTOR_POWER_KW / FLOW_M3H.clip(lower=1)
```

### WIRE_TO_WATER_PCT

```python
WIRE_TO_WATER_PCT =
    HYDRAULIC_POWER_KW / MOTOR_POWER_KW.clip(lower=0.1) * 100
```

## AlertExpression rules (11)

### PUMP_BEARING_DEFECT_EARLY

Medium · bearing_de

```python
PUMP_BEARING_DEFECT_EARLY =
    (RUNNING > 0) & (VIB_DE_ENVELOPE > 2)
```

### PUMP_VIBRATION_HIGH

High

```python
PUMP_VIBRATION_HIGH =
    (RUNNING > 0) & (VIB_DE_VEL_RMS > 4.5)
```

### PUMP_BEARING_TEMP_HIGH

High · bearing_de

```python
PUMP_BEARING_TEMP_HIGH =
    BEARING_DE_TEMP_C > 85
```

### PUMP_CAVITATION_RISK

High · cavitation

```python
PUMP_CAVITATION_RISK =
    (RUNNING > 0) & (NPSH_MARGIN_M < 1)
```

### PUMP_OFF_BEP

Low

```python
PUMP_OFF_BEP =
    (RUNNING > 0) & ((BEP_RATIO < 0.7) | (BEP_RATIO > 1.2))
```

### PUMP_HEAD_DEGRADED

Medium · impeller_wear

```python
PUMP_HEAD_DEGRADED =
    (RUNNING > 0) & (HEAD_DEVIATION_PCT < -5)
```

### PUMP_EFFICIENCY_LOSS

Medium · impeller_wear

```python
PUMP_EFFICIENCY_LOSS =
    (RUNNING > 0) & (EFF_DEVIATION_PTS < -4)
```

### PUMP_SEAL_LEAK

Medium · seal_leak

```python
PUMP_SEAL_LEAK =
    SEAL_LEAK_MLMIN > 30
```

### PUMP_CURRENT_IMBALANCE

Medium · motor_winding

```python
PUMP_CURRENT_IMBALANCE =
    (RUNNING > 0) & (CURRENT_IMBALANCE_PCT > 5)
```

### PUMP_WINDING_TEMP_HIGH

High · motor_winding

```python
PUMP_WINDING_TEMP_HIGH =
    WINDING_TEMP_C > 140
```

### PUMP_TRIPPED

Critical

```python
PUMP_TRIPPED =
    TRIP_CODE > 0
```
