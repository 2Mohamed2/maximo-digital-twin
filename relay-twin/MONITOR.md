# PR-7201: Maximo Monitor functions and alert rules

Device type `PROTECTION_RELAY_IED`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (17)

### PICKUP_MULTIPLE

```python
PICKUP_MULTIPLE =
    (FAULT_CURRENT_A / 360)
```

### OPERATE_EXPECTED_MS

```python
OPERATE_EXPECTED_MS =
    (
      1000
      * 0.15
      * (0.14 / (np.maximum((FAULT_CURRENT_A / 360), 1.05) ** 0.02 - 1) + 0)
    )
```

### OPERATE_ERROR_MS

```python
OPERATE_ERROR_MS =
    (FAULT_OPERATE_MS - OPERATE_EXPECTED_MS)
```

### OPERATE_TOLERANCE_MS

```python
OPERATE_TOLERANCE_MS =
    np.maximum(0.05 * OPERATE_EXPECTED_MS, 20)
```

### OPERATE_ERROR_RATIO

```python
OPERATE_ERROR_RATIO =
    (np.abs(OPERATE_ERROR_MS) / np.maximum(0.05 * OPERATE_EXPECTED_MS, 20))
```

### CLEARING_TIME_MS

```python
CLEARING_TIME_MS =
    FAULT_OPERATE_MS + CB_OPEN_MS
```

### CB_OPEN_RATIO

```python
CB_OPEN_RATIO =
    CB_OPEN_MS / 45
```

### BF_MARGIN_MS

```python
BF_MARGIN_MS =
    150 - CB_OPEN_MS
```

### CB_WEAR_PCT

```python
CB_WEAR_PCT =
    (CB_WEAR_KA2S / 312.5 * 100)
```

### BREAKS_LEFT_AT_RATED

```python
BREAKS_LEFT_AT_RATED =
    (312.5 - CB_WEAR_KA2S) / 6.25
```

### SETTINGS_OK

```python
SETTINGS_OK =
    np.where((SETTINGS_CRC == 1514967522) & (ACTIVE_GROUP == 1), 1, 0)
```

### SYNC_OFFSET_ABS_US

```python
SYNC_OFFSET_ABS_US =
    np.abs(SYNC_OFFSET_US)
```

### DC_PCT_OF_NOMINAL

```python
DC_PCT_OF_NOMINAL =
    AUX_DC_V / 110 * 100
```

### TRIP_DC_MARGIN_V

```python
TRIP_DC_MARGIN_V =
    AUX_DC_V - 77
```

### CT_MISMATCH_IN

```python
CT_MISMATCH_IN =
    (np.abs(IO_CALC_A - IO_MEAS_A) / 400)
```

### LOAD_PCT_OF_PICKUP

```python
LOAD_PCT_OF_PICKUP =
    LOAD_CURRENT_A / 360 * 100
```

### GOOSE_MISS_PCT

```python
GOOSE_MISS_PCT =
    (GOOSE_MISSED / 2400 * 100)
```

## AlertExpression rules (14)

### PROT_SELF_SUPERVISION

Critical

```python
PROT_SELF_SUPERVISION =
    IRF_ALARM > 0.5
```

### PROT_TCS_ALARM

Critical · trip_circuit_open

```python
PROT_TCS_ALARM =
    TCS_ALARM > 0.5
```

### PROT_DC_TRIP_RISK

Critical · dc_supply_low

```python
PROT_DC_TRIP_RISK =
    AUX_DC_V < 77
```

### PROT_SETTINGS_MISMATCH

High · settings_change

```python
PROT_SETTINGS_MISMATCH =
    np.where((SETTINGS_CRC == 1514967522) & (ACTIVE_GROUP == 1), 1, 0) < 0.5
```

### PROT_TIMING_DEVIATION

High · settings_change

```python
PROT_TIMING_DEVIATION =
    OPERATE_ERROR_RATIO > 1
```

### PROT_BF_MARGIN_LOW

High · breaker_slow

```python
PROT_BF_MARGIN_LOW =
    (150 - CB_OPEN_MS) < 40
```

### PROT_CB_WEAR_LIMIT

High · contact_wear

```python
PROT_CB_WEAR_LIMIT =
    (CB_WEAR_KA2S / 312.5 * 100) >= 100
```

### PROT_CT_SUPERVISION

High · ct_circuit_fault

```python
PROT_CT_SUPERVISION =
    CT_MISMATCH_IN > 0.1
```

### PROT_CB_SLOW

Medium · breaker_slow

```python
PROT_CB_SLOW =
    (CB_OPEN_MS / 45) > 1.3
```

### PROT_CB_WEAR

Medium · contact_wear

```python
PROT_CB_WEAR =
    (CB_WEAR_KA2S / 312.5 * 100) >= 80
```

### PROT_DC_LOW

Medium · dc_supply_low

```python
PROT_DC_LOW =
    AUX_DC_V < 88
```

### PROT_TIME_SYNC

Medium · time_sync_loss

```python
PROT_TIME_SYNC =
    (SYNC_OK < 0.5) | (np.abs(SYNC_OFFSET_US) > 1000)
```

### PROT_GOOSE_DEGRADED

Medium · goose_degraded

```python
PROT_GOOSE_DEGRADED =
    ((GOOSE_MISSED / 2400 * 100) > 1) | (GOOSE_MAX_LATENCY_MS > 10)
```

### PROT_TRIP_PATH_UNPROVEN

Medium

```python
PROT_TRIP_PATH_UNPROVEN =
    TRIP_VERIFIED_DAYS > 2190
```
