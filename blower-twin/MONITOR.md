# BLW-1301: Maximo Monitor functions and alert rules

Device type `AERATION_BLOWER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (18)

### GRID_PRESSURE_EXPECTED_MBAR

```python
GRID_PRESSURE_EXPECTED_MBAR =
    (
      441.29925
      + 25
      + 4 * (AIRFLOW_NM3H.clip(lower=1) / 1200)
      + 10 * (AIRFLOW_NM3H.clip(lower=1) / 4800) ** 2
    )
```

### GRID_PRESSURE_RESIDUAL_MBAR

```python
GRID_PRESSURE_RESIDUAL_MBAR =
    GRID_PRESSURE_MBAR - GRID_PRESSURE_EXPECTED_MBAR
```

### HEADER_LOSS_MBAR

```python
HEADER_LOSS_MBAR =
    DISCHARGE_PRESSURE_MBAR - GRID_PRESSURE_MBAR
```

### HEADER_LOSS_RESIDUAL_MBAR

```python
HEADER_LOSS_RESIDUAL_MBAR =
    DISCHARGE_PRESSURE_MBAR
    - GRID_PRESSURE_MBAR
    - (25 * (AIRFLOW_NM3H.clip(lower=1) / 4800) ** 2)
```

### PRESSURE_RATIO

```python
PRESSURE_RATIO =
    (
      (
        (AMBIENT_PRESSURE_MBAR - INLET_FILTER_DP_MBAR)
        + DISCHARGE_PRESSURE_MBAR
      )
      / (AMBIENT_PRESSURE_MBAR - INLET_FILTER_DP_MBAR)
    )
```

### POWER_ADIABATIC_KW

```python
POWER_ADIABATIC_KW =
    (
      3.5
      * (AMBIENT_PRESSURE_MBAR - INLET_FILTER_DP_MBAR)
      * 100
      * (
          AIRFLOW_NM3H.clip(lower=1)
          * (1013.25 / (AMBIENT_PRESSURE_MBAR - INLET_FILTER_DP_MBAR))
          * ((INLET_TEMP_C + 273.15) / 273.15)
          / 3600
        )
      * (PRESSURE_RATIO ** 0.285714285714 - 1)
      / 1000
    )
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    (
      (
        POWER_ADIABATIC_KW
        / (0.74 - 0.6 * (AIRFLOW_NM3H.clip(lower=1) / 4800 - 0.75) ** 2)
      ).clip(lower=0.5)
    )
```

### POWER_RESIDUAL_PCT

```python
POWER_RESIDUAL_PCT =
    (MOTOR_POWER_KW - POWER_EXPECTED_KW) / POWER_EXPECTED_KW * 100
```

### WIRE_TO_AIR_EFF_PCT

```python
WIRE_TO_AIR_EFF_PCT =
    POWER_ADIABATIC_KW / MOTOR_POWER_KW.clip(lower=1) * 100
```

### SURGE_FLOW_NM3H

```python
SURGE_FLOW_NM3H =
    (2100 * np.sqrt(DISCHARGE_PRESSURE_MBAR.clip(lower=0) / 800))
```

### SURGE_MARGIN_PCT

```python
SURGE_MARGIN_PCT =
    (
      (AIRFLOW_NM3H.clip(lower=1) - SURGE_FLOW_NM3H)
      / AIRFLOW_NM3H.clip(lower=1)
      * 100
    )
```

### O2_DEMAND_KGH

```python
O2_DEMAND_KGH =
    (INFLUENT_FLOW_M3H * (0.13 + 4.57 * 0.85 * INFLUENT_NH4_MGL / 1000))
```

### SOTE_EXPECTED_PCT

```python
SOTE_EXPECTED_PCT =
    (0.065 * 4.5 * ((AIRFLOW_NM3H.clip(lower=1) / 1200) / 3) ** (-0.15))
    * 100
```

### AIRFLOW_EXPECTED_NM3H

```python
AIRFLOW_EXPECTED_NM3H =
    (
      O2_DEMAND_KGH
      / (
          0.2997
          * (
              0.065
              * 4.5
              * ((AIRFLOW_NM3H.clip(lower=1) / 1200) / 3) ** (-0.15)
            )
          * 0.55
          * (
              (
                0.95
                * (
                    (
                      14.652
                      - 0.41022 * WATER_TEMP_C
                      + 0.007991 * WATER_TEMP_C ** 2
                      - 7.7774e-05 * WATER_TEMP_C ** 3
                    )
                    * AMBIENT_PRESSURE_MBAR
                    / 1013.25
                    * (1 + 0.4 * 4.5 / 10.33)
                  )
                - ((DO_CONTROL_MGL + DO_OUTLET_MGL) / 2)
              ).clip(lower=0.1)
              / 10.5938558606
              * 1.024 ** (WATER_TEMP_C - 20)
            )
        )
    )
```

### AIR_RATIO

```python
AIR_RATIO =
    AIRFLOW_NM3H.clip(lower=1) / AIRFLOW_EXPECTED_NM3H
```

### SPECIFIC_ENERGY_KWH_KG

```python
SPECIFIC_ENERGY_KWH_KG =
    MOTOR_POWER_KW / O2_DEMAND_KGH.clip(lower=1)
```

### SPECIFIC_ENERGY_EXPECTED_KWH_KG

```python
SPECIFIC_ENERGY_EXPECTED_KWH_KG =
    POWER_EXPECTED_KW
    * (AIRFLOW_EXPECTED_NM3H / AIRFLOW_NM3H.clip(lower=1))
    / O2_DEMAND_KGH.clip(lower=1)
```

### DO_SPREAD_MGL

```python
DO_SPREAD_MGL =
    DO_CONTROL_MGL - DO_OUTLET_MGL
```

## AlertExpression rules (13)

### BLW_DIFFUSER_FOULING

Medium · diffuser_fouling

```python
BLW_DIFFUSER_FOULING =
    (AIRFLOW_NM3H > 500)
    & (GRID_PRESSURE_RESIDUAL_MBAR > 25)
    & (AIR_RATIO > 1.15)
```

### BLW_DIFFUSER_TEAR

High · membrane_tear

```python
BLW_DIFFUSER_TEAR =
    (AIRFLOW_NM3H > 500) & (GRID_PRESSURE_RESIDUAL_MBAR < -15)
```

### BLW_AIR_DEMAND_HIGH

Low

```python
BLW_AIR_DEMAND_HIGH =
    (AIRFLOW_NM3H > 500) & (AIR_RATIO > 1.35)
```

### BLW_INLET_FILTER

Medium · inlet_filter

```python
BLW_INLET_FILTER =
    (INLET_FILTER_DP_MBAR > 25) & (INLET_FILTER_DP_MBAR <= 40)
```

### BLW_INLET_FILTER_HIGH

High · inlet_filter

```python
BLW_INLET_FILTER_HIGH =
    INLET_FILTER_DP_MBAR > 40
```

### BLW_SURGE_MARGIN

High · surge_approach

```python
BLW_SURGE_MARGIN =
    (AIRFLOW_NM3H > 500) & (SURGE_MARGIN_PCT < 10)
```

### BLW_VALVE_THROTTLED

Medium · surge_approach

```python
BLW_VALVE_THROTTLED =
    (AIRFLOW_NM3H > 500) & (HEADER_LOSS_RESIDUAL_MBAR > 60)
```

### BLW_BEARING

Medium · bearing_wear

```python
BLW_BEARING =
    (VIBRATION_MM_S > 4.5) | (BEARING_TEMP_C > 95)
```

### BLW_EFFICIENCY_LOW

Low · bearing_wear

```python
BLW_EFFICIENCY_LOW =
    (AIRFLOW_NM3H > 500) & (POWER_RESIDUAL_PCT > 8)
```

### BLW_DO_PROBE

Medium · do_probe_drift

```python
BLW_DO_PROBE =
    (AIRFLOW_NM3H > 500)
    & (DO_SPREAD_MGL.abs() > 0.9)
    & (GRID_PRESSURE_RESIDUAL_MBAR >= -15)
```

### BLW_DO_LOW

High

```python
BLW_DO_LOW =
    DO_OUTLET_MGL < 0.8
```

### BLW_VFD_HOT

High · vfd_overheating

```python
BLW_VFD_HOT =
    (VFD_TEMP_C > 62) | (MOTOR_TEMP_C > 135)
```

### BLW_TRIP

Critical

```python
BLW_TRIP =
    TRIP_CODE > 0
```
