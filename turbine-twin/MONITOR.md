# GT-501: Maximo Monitor functions and alert rules

Device type `GAS_TURBINE`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (24)

### THETA

```python
THETA =
    ((INLET_TEMP_C + 273.15) / 288.15)
```

### DELTA

```python
DELTA =
    (INLET_PRESSURE_KPA / 101.325)
```

### LOAD_CORR

```python
LOAD_CORR =
    (POWER_MW.clip(lower=0) / ((INLET_PRESSURE_KPA / 101.325) * 12.9))
```

### EGT_AVG_C

```python
EGT_AVG_C =
    (EGT_TC1_C + EGT_TC2_C + EGT_TC3_C + EGT_TC4_C + EGT_TC5_C + EGT_TC6_C)
    / 6
```

### EGT_SPREAD_K

```python
EGT_SPREAD_K =
    df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].max(axis=1)
    - df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].min(axis=1)
```

### TC_LOW_DEV_K

```python
TC_LOW_DEV_K =
    (
      (
        (
          EGT_TC1_C
          + EGT_TC2_C
          + EGT_TC3_C
          + EGT_TC4_C
          + EGT_TC5_C
          + EGT_TC6_C
        )
        - df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].max(axis=1)
        - df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].min(axis=1)
      )
      / 4
    )
    - df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].min(axis=1)
```

### TC_HIGH_DEV_K

```python
TC_HIGH_DEV_K =
    df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].max(axis=1)
    - (
        (
          (
            EGT_TC1_C
            + EGT_TC2_C
            + EGT_TC3_C
            + EGT_TC4_C
            + EGT_TC5_C
            + EGT_TC6_C
          )
          - df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].max(axis=1)
          - df[['EGT_TC1_C', 'EGT_TC2_C', 'EGT_TC3_C', 'EGT_TC4_C', 'EGT_TC5_C', 'EGT_TC6_C']].min(axis=1)
        )
        / 4
      )
```

### HEAT_RATE_KJ_KWH

```python
HEAT_RATE_KJ_KWH =
    (FUEL_FLOW_KG_S * 50000 * 3600 / (POWER_MW.clip(lower=0.2) * 1000))
```

### HR_EXPECTED_KJ_KWH

```python
HR_EXPECTED_KJ_KWH =
    (FUEL_EXPECTED_KG_S * 50000 * 3600 / (POWER_MW.clip(lower=0.2) * 1000))
```

### HR_DEV_PCT

```python
HR_DEV_PCT =
    (HEAT_RATE_KJ_KWH / HR_EXPECTED_KJ_KWH - 1) * 100
```

### EFFICIENCY_PCT

```python
EFFICIENCY_PCT =
    360000 / HEAT_RATE_KJ_KWH
```

### FUEL_EXPECTED_KG_S

```python
FUEL_EXPECTED_KG_S =
    (
      (
        0.07843731851
        - 1.400282738e-05 * INLET_TEMP_C
        - 1.878346785e-07 * INLET_TEMP_C**2
        + 0.8058044741 * LOAD_CORR
        + 0.001116162677 * LOAD_CORR * INLET_TEMP_C
        + 3.506419802e-06 * LOAD_CORR * INLET_TEMP_C**2
        - 0.2109558334 * LOAD_CORR**2
        - 0.001552181424 * LOAD_CORR**2 * INLET_TEMP_C
        - 1.592434052e-05 * LOAD_CORR**2 * INLET_TEMP_C**2
        + 0.0655787568 * LOAD_CORR**3
        + 0.000779395039 * LOAD_CORR**3 * INLET_TEMP_C
        + 1.555737152e-05 * LOAD_CORR**3 * INLET_TEMP_C**2
      )
      * (INLET_PRESSURE_KPA / 101.325)
    )
```

### CDP_EXPECTED_BAR

```python
CDP_EXPECTED_BAR =
    (
      (
        5.018874154
        - 0.006293877801 * INLET_TEMP_C
        + 4.712182946e-06 * INLET_TEMP_C**2
        + 17.78201825 * LOAD_CORR
        + 0.005374813552 * LOAD_CORR * INLET_TEMP_C
        + 0.0001654167689 * LOAD_CORR * INLET_TEMP_C**2
        - 7.452673756 * LOAD_CORR**2
        - 0.03932254532 * LOAD_CORR**2 * INLET_TEMP_C
        - 0.0005430829932 * LOAD_CORR**2 * INLET_TEMP_C**2
        + 2.331041303 * LOAD_CORR**3
        + 0.02229807939 * LOAD_CORR**3 * INLET_TEMP_C
        + 0.0005291074209 * LOAD_CORR**3 * INLET_TEMP_C**2
      )
      * (INLET_PRESSURE_KPA / 101.325)
    )
```

### CDP_DEV_PCT

```python
CDP_DEV_PCT =
    (CDP_BAR / CDP_EXPECTED_BAR - 1) * 100
```

### CDT_EXPECTED_C

```python
CDT_EXPECTED_C =
    (
      196.2128563
      + 1.456807636 * INLET_TEMP_C
      - 0.0003833087149 * INLET_TEMP_C**2
      + 377.894627 * LOAD_CORR
      + 2.255640716 * LOAD_CORR * INLET_TEMP_C
      + 0.007022437972 * LOAD_CORR * INLET_TEMP_C**2
      - 258.6114513 * LOAD_CORR**2
      - 2.763303929 * LOAD_CORR**2 * INLET_TEMP_C
      - 0.02683576912 * LOAD_CORR**2 * INLET_TEMP_C**2
      + 85.62222038 * LOAD_CORR**3
      + 1.297498567 * LOAD_CORR**3 * INLET_TEMP_C
      + 0.02517288644 * LOAD_CORR**3 * INLET_TEMP_C**2
    )
```

### EGT_EXPECTED_C

```python
EGT_EXPECTED_C =
    (
      244.9681467
      + 1.371819846 * INLET_TEMP_C
      - 0.0008327172789 * INLET_TEMP_C**2
      + 573.1160254 * LOAD_CORR
      + 4.048691849 * LOAD_CORR * INLET_TEMP_C
      + 0.01434416346 * LOAD_CORR * INLET_TEMP_C**2
      - 454.4797465 * LOAD_CORR**2
      - 5.383659653 * LOAD_CORR**2 * INLET_TEMP_C
      - 0.05382084186 * LOAD_CORR**2 * INLET_TEMP_C**2
      + 156.4708829 * LOAD_CORR**3
      + 2.54992425 * LOAD_CORR**3 * INLET_TEMP_C
      + 0.0502824938 * LOAD_CORR**3 * INLET_TEMP_C**2
    )
```

### EGT_DEV_K

```python
EGT_DEV_K =
    (EGT_TC1_C + EGT_TC2_C + EGT_TC3_C + EGT_TC4_C + EGT_TC5_C + EGT_TC6_C)
    / 6
    - EGT_EXPECTED_C
```

### NGG_EXPECTED_PCT

```python
NGG_EXPECTED_PCT =
    (
      66.59504838
      - 0.033824934 * INLET_TEMP_C
      + 2.794152706e-05 * INLET_TEMP_C**2
      + 59.18359815 * LOAD_CORR
      + 0.09086913492 * LOAD_CORR * INLET_TEMP_C
      + 0.0007111709457 * LOAD_CORR * INLET_TEMP_C**2
      - 37.00341868 * LOAD_CORR**2
      - 0.2191961849 * LOAD_CORR**2 * INLET_TEMP_C
      - 0.002799450863 * LOAD_CORR**2 * INLET_TEMP_C**2
      + 11.97369851 * LOAD_CORR**3
      + 0.1217130541 * LOAD_CORR**3 * INLET_TEMP_C
      + 0.002754236464 * LOAD_CORR**3 * INLET_TEMP_C**2
    )
```

### NGG_CORR_PCT

```python
NGG_CORR_PCT =
    NGG_PCT / np.sqrt(THETA)
```

### PRESSURE_RATIO

```python
PRESSURE_RATIO =
    (CDP_BAR * 100 / INLET_PRESSURE_KPA)
```

### ETA_C_PCT

```python
ETA_C_PCT =
    (
      (INLET_TEMP_C + 273.15)
      * (PRESSURE_RATIO.clip(lower=1.01) ** 0.2857142857 - 1)
      / (CDT_C - INLET_TEMP_C).clip(lower=1)
      * 100
    )
```

### ETA_C_EXPECTED_PCT

```python
ETA_C_EXPECTED_PCT =
    INLET_TEMP_C * 0 + 86
```

### ETA_C_DEV_PTS

```python
ETA_C_DEV_PTS =
    ETA_C_PCT - 86
```

### POWER_CORR_MW

```python
POWER_CORR_MW =
    POWER_MW / ((INLET_PRESSURE_KPA / 101.325) * np.sqrt(THETA))
```

## AlertExpression rules (12)

### GT_COMPRESSOR_FOULING

Medium · compressor_fouling

```python
GT_COMPRESSOR_FOULING =
    ((POWER_MW > 3.87) & (FAULT_CODE == 0)) & (ETA_C_DEV_PTS < -1)
```

### GT_HOT_SECTION

Medium · hot_section

```python
GT_HOT_SECTION =
    ((POWER_MW > 3.87) & (FAULT_CODE == 0))
    & (EGT_DEV_K > 12)
    & (ETA_C_DEV_PTS > -0.6)
```

### GT_HEAT_RATE_HIGH

Low

```python
GT_HEAT_RATE_HIGH =
    ((POWER_MW > 3.87) & (FAULT_CODE == 0)) & (HR_DEV_PCT > 3)
```

### GT_EGT_SPREAD

High · burner_fault

```python
GT_EGT_SPREAD =
    ((POWER_MW > 3.87) & (FAULT_CODE == 0))
    & (EGT_SPREAD_K > 45)
    & (EGT_SPREAD_K <= 80)
    & (TC_LOW_DEV_K < 40)
```

### GT_EGT_SPREAD_TRIP_LEVEL

Critical · burner_fault

```python
GT_EGT_SPREAD_TRIP_LEVEL =
    ((POWER_MW > 3.87) & (FAULT_CODE == 0))
    & (EGT_SPREAD_K > 80)
    & (TC_LOW_DEV_K < 40)
```

### GT_EGT_TC_FAULT

Low · thermocouple_fault

```python
GT_EGT_TC_FAULT =
    ((POWER_MW > 3.87) & (FAULT_CODE == 0))
    & (TC_LOW_DEV_K > 40)
    & (TC_HIGH_DEV_K < 25)
```

### GT_INLET_FILTER_DP

Medium · inlet_filter

```python
GT_INLET_FILTER_DP =
    (INLET_FILTER_DP_PA > 1500) & (INLET_FILTER_DP_PA <= 2000)
```

### GT_INLET_FILTER_DP_HIGH

High · inlet_filter

```python
GT_INLET_FILTER_DP_HIGH =
    INLET_FILTER_DP_PA > 2000
```

### GT_GG_VIBRATION

Medium

```python
GT_GG_VIBRATION =
    GG_VIB_MM_S > 9.3
```

### GT_PT_BEARING

High · bearing_wear

```python
GT_PT_BEARING =
    (PT_PROX_UM > 75) | (BRG_PT_TEMP_C > 110)
```

### GT_LUBE_OIL_HOT

Medium · lube_cooler

```python
GT_LUBE_OIL_HOT =
    LUBE_OIL_TEMP_C > 65
```

### GT_TRIP

Critical

```python
GT_TRIP =
    FAULT_CODE > 0
```
