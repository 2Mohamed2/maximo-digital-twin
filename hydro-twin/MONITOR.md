# HYD-3601: Maximo Monitor functions and alert rules

Device type `HYDRO_FRANCIS_UNIT`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### FLOW_M3S

```python
FLOW_M3S =
    (3.8 * np.sqrt(WK_DP_KPA))
```

### NET_HEAD_M

```python
NET_HEAD_M =
    (
      (
        191
        + SPIRAL_PRESSURE_BAR * 100000 / (9810)
        + ((3.8 * np.sqrt(WK_DP_KPA)) / 5.30929) ** 2 / 19.62
      )
      - (TAILWATER_LEVEL_M + ((3.8 * np.sqrt(WK_DP_KPA)) / 30) ** 2 / 19.62)
    )
```

### HEAD_LOSS_M

```python
HEAD_LOSS_M =
    (
      HEADWATER_LEVEL_M
      - (
          191
          + SPIRAL_PRESSURE_BAR * 100000 / (9810)
          + ((3.8 * np.sqrt(WK_DP_KPA)) / 5.30929) ** 2 / 19.62
        )
    )
```

### HEAD_LOSS_RATIO

```python
HEAD_LOSS_RATIO =
    (HEAD_LOSS_M / (0.00313226 * (3.8 * np.sqrt(WK_DP_KPA)) ** 2))
```

### N_ED

```python
N_ED =
    (SPEED_RPM / 60 * 1.8 / np.sqrt(9.81 * NET_HEAD_M))
```

### Q_ED

```python
Q_ED =
    ((3.8 * np.sqrt(WK_DP_KPA)) / (3.24 * np.sqrt(9.81 * NET_HEAD_M)))
```

### Q_RATIO

```python
Q_RATIO =
    (Q_ED / 0.2)
```

### EFF_EXPECTED_PCT

```python
EFF_EXPECTED_PCT =
    (
      100
      * (
          0.95
          - 0.45
            * np.minimum((Q_RATIO - 1 - 0.5 * (N_ED / 0.18 - 1)), 0) ** 2
          - 0.6
            * np.maximum((Q_RATIO - 1 - 0.5 * (N_ED / 0.18 - 1)), 0) ** 2
          - 1.2 * (N_ED / 0.18 - 1) ** 2
        )
    )
```

### EFF_MEASURED_PCT

```python
EFF_MEASURED_PCT =
    (
      100
      * ACTIVE_POWER_MW
      * 1000000
      / (9633.42 * (3.8 * np.sqrt(WK_DP_KPA)) * NET_HEAD_M)
    )
```

### EFF_DEFICIT_PTS

```python
EFF_DEFICIT_PTS =
    (EFF_EXPECTED_PCT - EFF_MEASURED_PCT)
```

### POWER_EXPECTED_MW

```python
POWER_EXPECTED_MW =
    (
      EFF_EXPECTED_PCT
      / 100
      * 9633.42
      * (3.8 * np.sqrt(WK_DP_KPA))
      * NET_HEAD_M
      / 1000000
    )
```

### LOST_MW

```python
LOST_MW =
    POWER_EXPECTED_MW - ACTIVE_POWER_MW
```

### GATE_FLOW_RATIO

```python
GATE_FLOW_RATIO =
    (Q_RATIO / (GATE_POSITION_PCT / 72))
```

### SIGMA_PLANT

```python
SIGMA_PLANT =
    (
      (
        (
          AMBIENT_PRESSURE_KPA
          - (
              0.61078
              * np.exp(17.27 * WATER_TEMP_C / (WATER_TEMP_C + 237.3))
            )
        )
        * 1000
        / 9810
        - (191 - TAILWATER_LEVEL_M)
      )
      / NET_HEAD_M
    )
```

### SIGMA_REQUIRED

```python
SIGMA_REQUIRED =
    (
      0.06
      * (
          1
          + 1.5 * np.maximum(Q_RATIO - 1, 0)
          + 0.3 * np.maximum(1 - Q_RATIO, 0)
        )
    )
```

### SIGMA_MARGIN

```python
SIGMA_MARGIN =
    SIGMA_PLANT / SIGMA_REQUIRED
```

### DT_PULSATION_EXPECTED_PCT

```python
DT_PULSATION_EXPECTED_PCT =
    (0.5 + 4 * np.exp(-((Q_RATIO - 0.6) / 0.12) ** 2))
```

### ROPE_FREQ_HZ

```python
ROPE_FREQ_HZ =
    0.3 * SPEED_RPM / 60
```

### TGB_OIL_RESIDUAL_C

```python
TGB_OIL_RESIDUAL_C =
    (
      TGB_OIL_TEMP_C
      - (COOLING_WATER_TEMP_C + 18 + 6 * (ACTIVE_POWER_MW / 60))
    )
```

### TGB_PAD_RESIDUAL_C

```python
TGB_PAD_RESIDUAL_C =
    (TGB_PAD_TEMP_C - (TGB_OIL_TEMP_C + 10 + 8 * (ACTIVE_POWER_MW / 60)))
```

## AlertExpression rules (13)

### HYD_EFF_DEFICIT_HIGH

High · runner_wear

```python
HYD_EFF_DEFICIT_HIGH =
    (UNIT_STATE > 0.5) & (EFF_DEFICIT_PTS > 3)
```

### HYD_GOV_OIL_PRESSURE_LOW

High · governor_servo_fault

```python
HYD_GOV_OIL_PRESSURE_LOW =
    GOV_OIL_PRESSURE_BAR < 34
```

### HYD_SIGMA_MARGIN_LOW

High · low_tailwater

```python
HYD_SIGMA_MARGIN_LOW =
    (UNIT_STATE > 0.5) & (SIGMA_MARGIN < 1.1)
```

### HYD_DT_PULSATION_HIGH

High · rough_zone_operation

```python
HYD_DT_PULSATION_HIGH =
    (UNIT_STATE > 0.5) & (DT_PULSATION_PCT > 2.5)
```

### HYD_SHAFT_RUNOUT_HIGH

High · guide_bearing_wear

```python
HYD_SHAFT_RUNOUT_HIGH =
    (UNIT_STATE > 0.5) & (SHAFT_RUNOUT_UM > 200)
```

### HYD_THRUST_BRG_TEMP_HIGH

High · bearing_cooling_loss

```python
HYD_THRUST_BRG_TEMP_HIGH =
    THRUST_PAD_TEMP_C > 80
```

### HYD_EFF_DEFICIT

Medium · runner_wear

```python
HYD_EFF_DEFICIT =
    (UNIT_STATE > 0.5) & (EFF_DEFICIT_PTS > 1.5)
```

### HYD_GATE_FLOW_HIGH

Medium · guide_vane_leakage

```python
HYD_GATE_FLOW_HIGH =
    (UNIT_STATE > 0.5) & (GATE_FLOW_RATIO > 1.05)
```

### HYD_GATE_TRACKING

Medium · governor_servo_fault

```python
HYD_GATE_TRACKING =
    (UNIT_STATE > 0.5) & (np.abs(GATE_SETPOINT_PCT - GATE_POSITION_PCT) > 2)
```

### HYD_ROUGH_ZONE

Medium · rough_zone_operation

```python
HYD_ROUGH_ZONE =
    (UNIT_STATE > 0.5) & (Q_RATIO >= 0.4) & (Q_RATIO <= 0.7)
```

### HYD_TGB_TEMP_RESIDUAL

Medium · guide_bearing_wear

```python
HYD_TGB_TEMP_RESIDUAL =
    (UNIT_STATE > 0.5) & (TGB_PAD_RESIDUAL_C > 5)
```

### HYD_COOLING_WATER_LOW

Medium · bearing_cooling_loss

```python
HYD_COOLING_WATER_LOW =
    COOLING_WATER_FLOW_PCT < 70
```

### HYD_HEAD_LOSS_HIGH

Medium · intake_head_loss

```python
HYD_HEAD_LOSS_HIGH =
    (UNIT_STATE > 0.5) & (Q_RATIO >= 0.6) & (HEAD_LOSS_RATIO > 1.5)
```
