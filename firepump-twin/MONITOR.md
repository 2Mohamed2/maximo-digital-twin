# FP-6501: Maximo Monitor functions and alert rules

Device type `FIRE_PUMP_ELECTRIC`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### NET_PSI

```python
NET_PSI =
    (DISCHARGE_PSI - SUCTION_PSI)
```

### EXPECTED_NET_PSI

```python
EXPECTED_NET_PSI =
    np.where(
      ((PUMP_RUNNING > 0.5) & (SPEED_RPM > 300)),
      (
        (np.maximum(SPEED_RPM, 300) / 1780) ** 2
        * (
            112.909091
            + 1.035354
              * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000)
            - 3.309091
              * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000) ** 2
            - 3.620202
              * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000) ** 3
          )
      ),
      0
    )
```

### LIVE_PERF_RATIO

```python
LIVE_PERF_RATIO =
    np.where(
      ((PUMP_RUNNING > 0.5) & (SPEED_RPM > 300)),
      NET_PSI
      / (
          (np.maximum(SPEED_RPM, 300) / 1780) ** 2
          * (
              112.909091
              + 1.035354
                * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000)
              - 3.309091
                * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000) ** 2
              - 3.620202
                * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000) ** 3
            )
        ),
      1
    )
```

### EXPECTED_CURRENT_A

```python
EXPECTED_CURRENT_A =
    np.where(
      ((PUMP_RUNNING > 0.5) & (SPEED_RPM > 300)),
      (
        (
          47.753535
          + 38.256614
            * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000)
          + 15.015296
            * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000) ** 2
          - 9.088215
            * (FLOW_GPM * 1780 / np.maximum(SPEED_RPM, 300) / 1000) ** 3
        )
        * (np.maximum(SPEED_RPM, 300) / 1780) ** 3
        * 523.663681
        / SUPPLY_VOLTAGE_V
      ),
      0
    )
```

### MOTOR_LOAD_PCT

```python
MOTOR_LOAD_PCT =
    MOTOR_CURRENT_A / 156 * 100
```

### CHURN_NET_CORR_PSI

```python
CHURN_NET_CORR_PSI =
    (CHURN_NET_PSI * (1780 / CHURN_RPM) ** 2)
```

### CHURN_RATIO

```python
CHURN_RATIO =
    (CHURN_NET_CORR_PSI / 112.909091)
```

### CHURN_PCT_RATED

```python
CHURN_PCT_RATED =
    CHURN_NET_CORR_PSI / 107 * 100
```

### FT_RATED_GPM_CORR

```python
FT_RATED_GPM_CORR =
    (FT_RATED_GPM * 1780 / FT_RATED_RPM)
```

### FT_RATED_NET_CORR_PSI

```python
FT_RATED_NET_CORR_PSI =
    (FT_RATED_NET_PSI * (1780 / FT_RATED_RPM) ** 2)
```

### FT_RATED_RATIO

```python
FT_RATED_RATIO =
    (
      FT_RATED_NET_CORR_PSI
      / (
          112.909091
          + 1.035354 * (FT_RATED_GPM_CORR / 1000)
          - 3.309091 * (FT_RATED_GPM_CORR / 1000) ** 2
          - 3.620202 * (FT_RATED_GPM_CORR / 1000) ** 3
        )
    )
```

### FT_PEAK_GPM_CORR

```python
FT_PEAK_GPM_CORR =
    (FT_PEAK_GPM * 1780 / FT_PEAK_RPM)
```

### FT_PEAK_NET_CORR_PSI

```python
FT_PEAK_NET_CORR_PSI =
    (FT_PEAK_NET_PSI * (1780 / FT_PEAK_RPM) ** 2)
```

### FT_PEAK_RATIO

```python
FT_PEAK_RATIO =
    (
      FT_PEAK_NET_CORR_PSI
      / (
          112.909091
          + 1.035354 * (FT_PEAK_GPM_CORR / 1000)
          - 3.309091 * (FT_PEAK_GPM_CORR / 1000) ** 2
          - 3.620202 * (FT_PEAK_GPM_CORR / 1000) ** 3
        )
    )
```

### FT_PEAK_PCT_RATED

```python
FT_PEAK_PCT_RATED =
    FT_PEAK_NET_CORR_PSI / 107 * 100
```

### FT_MIN_RATIO

```python
FT_MIN_RATIO =
    np.minimum(FT_RATED_RATIO, FT_PEAK_RATIO)
```

### JOCKEY_LEAK_GPM

```python
JOCKEY_LEAK_GPM =
    (JOCKEY_RUN_MIN_24H * 10 / 1440)
```

### START_PSI_DEV

```python
START_PSI_DEV =
    LAST_START_PSI - 148
```

### SUCTION_MARGIN_TEST_PSI

```python
SUCTION_MARGIN_TEST_PSI =
    FT_PEAK_SUCTION_PSI - 20
```

## AlertExpression rules (15)

### FP_PEAK_BELOW_65

Critical

```python
FP_PEAK_BELOW_65 =
    FT_PEAK_NET_CORR_PSI / 107 * 100 < 65
```

### FP_CURVE_DEGRADED

High · impeller_wear

```python
FP_CURVE_DEGRADED =
    np.minimum(FT_RATED_RATIO, FT_PEAK_RATIO) < 0.95
```

### FP_SUCTION_LOW_TEST

High · weak_supply

```python
FP_SUCTION_LOW_TEST =
    FT_PEAK_SUCTION_PSI < 20
```

### FP_JOCKEY_FAILED

High · jockey_failed

```python
FP_JOCKEY_FAILED =
    (JOCKEY_STARTS_24H < 0.5) & (PUMP_RUNNING < 0.5) & (DISCHARGE_PSI < 153)
```

### FP_START_SLOW

High · starter_fault

```python
FP_START_SLOW =
    TIME_TO_RUN_S > 10
```

### FP_ROOM_COLD

High

```python
FP_ROOM_COLD =
    ROOM_TEMP_C < 4.4
```

### FP_FLOW_TEST_OVERDUE

High · tests_skipped

```python
FP_FLOW_TEST_OVERDUE =
    DAYS_SINCE_FLOW_TEST > 395
```

### FP_CHURN_DEVIATION

Medium · impeller_wear

```python
FP_CHURN_DEVIATION =
    np.abs(CHURN_RATIO - 1) > 0.05
```

### FP_SUPPLY_STATIC_LOW

Medium · weak_supply

```python
FP_SUPPLY_STATIC_LOW =
    (PUMP_RUNNING < 0.5) & (SUCTION_PSI < 45)
```

### FP_JOCKEY_CYCLING

Medium · system_leak

```python
FP_JOCKEY_CYCLING =
    JOCKEY_STARTS_24H > 24
```

### FP_LEAK_HIGH

Medium · system_leak

```python
FP_LEAK_HIGH =
    JOCKEY_LEAK_GPM > 1
```

### FP_UNPLANNED_STARTS

Medium · jockey_failed

```python
FP_UNPLANNED_STARTS =
    AUTO_STARTS_30D > 0.5
```

### FP_START_PRESSURE_OFF

Medium · pressure_sensing_drift

```python
FP_START_PRESSURE_OFF =
    np.abs(LAST_START_PSI - 148) > 5
```

### FP_PACKING_HOT

Medium · packing_overtight

```python
FP_PACKING_HOT =
    CHURN_PACKING_C > 70
```

### FP_CHURN_TEST_OVERDUE

Medium · tests_skipped

```python
FP_CHURN_TEST_OVERDUE =
    DAYS_SINCE_CHURN > 10
```
