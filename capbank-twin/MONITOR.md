# CAP-1101: Maximo Monitor functions and alert rules

Device type `CAPACITOR_BANK`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (14)

### Q_EXPECTED_MVAR

```python
Q_EXPECTED_MVAR =
    (BUS_VOLTAGE_KV ** 2 * 314.159265359 * 24.963 * 1e-06)
```

### Q_DEVIATION_PCT

```python
Q_DEVIATION_PCT =
    np.where(
      BREAKER_CLOSED > 0,
      (BANK_Q_MVAR / Q_EXPECTED_MVAR - 1) * 100,
      0
    )
```

### CURRENT_EXPECTED_A

```python
CURRENT_EXPECTED_A =
    BREAKER_CLOSED
    * Q_EXPECTED_MVAR
    * 1000000
    / (1.73205080757 * BUS_VOLTAGE_KV.clip(lower=1) * 1000)
```

### CURRENT_RMS_PU

```python
CURRENT_RMS_PU =
    (
      ((BANK_CURRENT_L1_A + BANK_CURRENT_L2_A + BANK_CURRENT_L3_A) / 3)
      / 158.42
    )
```

### UNIT_VOLTAGE_PU

```python
UNIT_VOLTAGE_PU =
    (BUS_VOLTAGE_KV / 1.73205080757 / 2 / 10.1)
```

### NEUTRAL_COMPENSATED_A

```python
NEUTRAL_COMPENSATED_A =
    (NEUTRAL_CURRENT_A - 0.0006791 * BUS_VOLTAGE_KV).clip(lower=0)
```

### FAILED_ELEMENTS_EST

```python
FAILED_ELEMENTS_EST =
    (
      (NEUTRAL_CURRENT_A - 0.0006791 * BUS_VOLTAGE_KV).clip(lower=0)
      / (0.0041187 * BUS_VOLTAGE_KV.clip(lower=1))
    )
```

### PHASE_ASYMMETRY_PCT

```python
PHASE_ASYMMETRY_PCT =
    (
      (
        np.maximum(
          np.maximum(BANK_CURRENT_L1_A, BANK_CURRENT_L2_A),
          BANK_CURRENT_L3_A
        )
        - np.minimum(
            np.minimum(BANK_CURRENT_L1_A, BANK_CURRENT_L2_A),
            BANK_CURRENT_L3_A
          )
      )
      / ((BANK_CURRENT_L1_A + BANK_CURRENT_L2_A + BANK_CURRENT_L3_A) / 3).clip(lower=1)
      * 100
    )
```

### FAILED_FROM_ASYMMETRY

```python
FAILED_FROM_ASYMMETRY =
    ((PHASE_ASYMMETRY_PCT - 0) / 0.09103)
```

### ELEMENT_OVERVOLTAGE_PCT

```python
ELEMENT_OVERVOLTAGE_PCT =
    (
      (
        4
        * (18 / (18 - FAILED_ELEMENTS_EST.clip(lower=0, upper=17)))
        / (3 + (18 / (18 - FAILED_ELEMENTS_EST.clip(lower=0, upper=17))))
      )
      - 1
    )
    * 100
```

### ELEMENT_VOLTAGE_PU

```python
ELEMENT_VOLTAGE_PU =
    UNIT_VOLTAGE_PU
    * (
        4
        * (18 / (18 - FAILED_ELEMENTS_EST.clip(lower=0, upper=17)))
        / (3 + (18 / (18 - FAILED_ELEMENTS_EST.clip(lower=0, upper=17))))
      )
```

### REACTOR_TEMP_EXPECTED_C

```python
REACTOR_TEMP_EXPECTED_C =
    (
      AMBIENT_TEMP_C
      + 55
        * (
            (
              (BANK_CURRENT_L1_A + BANK_CURRENT_L2_A + BANK_CURRENT_L3_A)
              / 3
            )
            / 200
          )
          ** 2
    )
```

### REACTOR_RESIDUAL_K

```python
REACTOR_RESIDUAL_K =
    REACTOR_TEMP_C - REACTOR_TEMP_EXPECTED_C
```

### RESONANCE_ORDER

```python
RESONANCE_ORDER =
    np.sqrt(700 / BANK_Q_MVAR.clip(lower=0.1))
```

## AlertExpression rules (13)

### CAP_ELEMENT_FAILURES

Medium · element_failures

```python
CAP_ELEMENT_FAILURES =
    (BREAKER_CLOSED > 0)
    & (FAILED_ELEMENTS_EST >= 0.5)
    & (FAILED_ELEMENTS_EST < 2.5)
```

### CAP_UNBALANCE_TRIP_LEVEL

High · element_failures

```python
CAP_UNBALANCE_TRIP_LEVEL =
    (BREAKER_CLOSED > 0) & (FAILED_ELEMENTS_EST >= 2.5)
```

### CAP_PROTECTION_BLIND

High · neutral_ct_fault

```python
CAP_PROTECTION_BLIND =
    (BREAKER_CLOSED > 0)
    & (FAILED_FROM_ASYMMETRY >= 2)
    & (FAILED_ELEMENTS_EST < 0.5)
```

### CAP_UNIT_PRESSURE

High · can_bulging

```python
CAP_UNIT_PRESSURE =
    PRESSURE_SWITCH_COUNT > 0
```

### CAP_Q_LOW

Medium · element_failures

```python
CAP_Q_LOW =
    (BREAKER_CLOSED > 0) & ((BANK_Q_MVAR / Q_EXPECTED_MVAR - 1) * 100 < -2)
```

### CAP_OVERVOLTAGE

Medium · overvoltage_stress

```python
CAP_OVERVOLTAGE =
    (BREAKER_CLOSED > 0) & (UNIT_VOLTAGE_PU > 1.05)
```

### CAP_PEAK_VOLTAGE

High · overvoltage_stress

```python
CAP_PEAK_VOLTAGE =
    (BREAKER_CLOSED > 0) & (PEAK_VOLTAGE_PU > 1.2)
```

### CAP_HARMONIC_CURRENT

Medium · harmonic_resonance

```python
CAP_HARMONIC_CURRENT =
    (BREAKER_CLOSED > 0)
    & ((CURRENT_THD_PCT > 25) | (CURRENT_RMS_PU > 1.35))
```

### CAP_REACTOR_HOT

Medium · reactor_overheating

```python
CAP_REACTOR_HOT =
    (BREAKER_CLOSED > 0)
    & (CURRENT_RMS_PU > 0.5)
    & (REACTOR_RESIDUAL_K > 15)
```

### CAP_RESTRIKE

High · restrike

```python
CAP_RESTRIKE =
    LAST_SWITCH_OVERVOLTAGE_PU > 2
```

### CAP_AMBIENT_HIGH

Low

```python
CAP_AMBIENT_HIGH =
    AMBIENT_TEMP_C > 55
```

### CAP_RELAY_ALARM

Medium

```python
CAP_RELAY_ALARM =
    RELAY_STATUS == 1
```

### CAP_RELAY_TRIP

Critical

```python
CAP_RELAY_TRIP =
    RELAY_STATUS >= 2
```
