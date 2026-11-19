# AMI-7301: Maximo Monitor functions and alert rules

Device type `AMI_LV_FEEDER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### FEEDER_KWH

```python
FEEDER_KWH =
    (FEEDER_KWH_L1 + FEEDER_KWH_L2 + FEEDER_KWH_L3)
```

### CUST_KWH

```python
CUST_KWH =
    (CUST_KWH_L1 + CUST_KWH_L2 + CUST_KWH_L3)
```

### READ_COVERAGE_PCT

```python
READ_COVERAGE_PCT =
    (READS_OK / 24 * 100)
```

### TECH_LOSS_KWH

```python
TECH_LOSS_KWH =
    (
      0.00025
      * (
          0.047231
          * (FEEDER_I_L1 ** 2 + FEEDER_I_L2 ** 2 + FEEDER_I_L3 ** 2)
          + 0.047231 * FEEDER_I_N ** 2
          + 37.4
        )
    )
```

### TECH_LOSS_PCT

```python
TECH_LOSS_PCT =
    TECH_LOSS_KWH / FEEDER_KWH * 100
```

### NTL_KWH

```python
NTL_KWH =
    (FEEDER_KWH - CUST_KWH - TECH_LOSS_KWH)
```

### NTL_PCT

```python
NTL_PCT =
    (NTL_KWH / FEEDER_KWH * 100)
```

### NTL_L1_PCT

```python
NTL_L1_PCT =
    (
      (
        FEEDER_KWH_L1
        - CUST_KWH_L1
        - 0.00025
          * (
              0.047231 * FEEDER_I_L1 ** 2
              + 0.0157437 * FEEDER_I_N ** 2
              + 12.4667
            )
      )
      / (FEEDER_KWH / 3)
      * 100
    )
```

### NTL_L2_PCT

```python
NTL_L2_PCT =
    (
      (
        FEEDER_KWH_L2
        - CUST_KWH_L2
        - 0.00025
          * (
              0.047231 * FEEDER_I_L2 ** 2
              + 0.0157437 * FEEDER_I_N ** 2
              + 12.4667
            )
      )
      / (FEEDER_KWH / 3)
      * 100
    )
```

### NTL_L3_PCT

```python
NTL_L3_PCT =
    (
      (
        FEEDER_KWH_L3
        - CUST_KWH_L3
        - 0.00025
          * (
              0.047231 * FEEDER_I_L3 ** 2
              + 0.0157437 * FEEDER_I_N ** 2
              + 12.4667
            )
      )
      / (FEEDER_KWH / 3)
      * 100
    )
```

### PHASE_SPREAD_PCT

```python
PHASE_SPREAD_PCT =
    (
      np.maximum(np.maximum(NTL_L1_PCT, NTL_L2_PCT), NTL_L3_PCT)
      - np.minimum(np.minimum(NTL_L1_PCT, NTL_L2_PCT), NTL_L3_PCT)
    )
```

### V_BUS_AVG

```python
V_BUS_AVG =
    ((V_BUS_L1 + V_BUS_L2 + V_BUS_L3) / 3)
```

### V_END_EXPECTED

```python
V_END_EXPECTED =
    (
      V_BUS_AVG
      - ((FEEDER_I_L1 + FEEDER_I_L2 + FEEDER_I_L3) / 3)
        * (
            0.069373
            * np.minimum(
                FEEDER_KWH
                * 1000
                / 0.25
                / (
                    V_BUS_L1 * FEEDER_I_L1
                    + V_BUS_L2 * FEEDER_I_L2
                    + V_BUS_L3 * FEEDER_I_L3
                  ),
                1
              )
            + 0.024
              * np.sqrt(
                  1
                  - np.minimum(
                      FEEDER_KWH
                      * 1000
                      / 0.25
                      / (
                          V_BUS_L1 * FEEDER_I_L1
                          + V_BUS_L2 * FEEDER_I_L2
                          + V_BUS_L3 * FEEDER_I_L3
                        ),
                      1
                    )
                    ** 2
                )
          )
    )
```

### V_END_RESIDUAL

```python
V_END_RESIDUAL =
    ((V_END_L1 + V_END_L2 + V_END_L3) / 3) - V_END_EXPECTED
```

### V_END_SPREAD_EXCESS

```python
V_END_SPREAD_EXCESS =
    (
      (
        np.maximum(np.maximum(V_END_L1, V_END_L2), V_END_L3)
        - np.minimum(np.minimum(V_END_L1, V_END_L2), V_END_L3)
      )
      - (
          np.maximum(np.maximum(V_BUS_L1, V_BUS_L2), V_BUS_L3)
          - np.minimum(np.minimum(V_BUS_L1, V_BUS_L2), V_BUS_L3)
        )
      - (
          np.maximum(np.maximum(FEEDER_I_L1, FEEDER_I_L2), FEEDER_I_L3)
          - np.minimum(np.minimum(FEEDER_I_L1, FEEDER_I_L2), FEEDER_I_L3)
        )
        * 0.069373
      - 0.120158 * FEEDER_I_N
    )
```

### V_MAX_HEADROOM

```python
V_MAX_HEADROOM =
    253 - V_MAX_CUST
```

### V_MIN_HEADROOM

```python
V_MIN_HEADROOM =
    V_MIN_CUST - 207
```

### TRAFO_LOAD_PCT

```python
TRAFO_LOAD_PCT =
    (
      (
        V_BUS_L1 * FEEDER_I_L1
        + V_BUS_L2 * FEEDER_I_L2
        + V_BUS_L3 * FEEDER_I_L3
      )
      / 1000
      / 250
      * 100
    )
```

### TRAFO_LOSS_KWH

```python
TRAFO_LOSS_KWH =
    0.25 * (270 + 2350 * (TRAFO_LOAD_PCT / 100) ** 2) / 1000
```

## AlertExpression rules (11)

### AMI_LOSS_UNEXPLAINED

High · bypass_theft

```python
AMI_LOSS_UNEXPLAINED =
    ((READS_OK / 24 * 100) >= 99) & (NTL_PCT > 3)
```

### AMI_LOSS_NEGATIVE

High · ct_polarity

```python
AMI_LOSS_NEGATIVE =
    ((READS_OK / 24 * 100) >= 99) & (NTL_PCT < -2)
```

### AMI_TAMPER

High · bypass_theft

```python
AMI_TAMPER =
    TAMPER_EVENTS_24H > 0.5
```

### AMI_NEUTRAL_SHIFT

High · loose_neutral

```python
AMI_NEUTRAL_SHIFT =
    V_END_SPREAD_EXCESS > 8
```

### AMI_RELAY_MISMATCH

High · relay_stuck

```python
AMI_RELAY_MISMATCH =
    ((RELAYS_CMD_OPEN - RELAYS_OPEN) > 0.5) | (KWH_ON_OPEN_RELAYS > 0.01)
```

### AMI_PHASE_MAPPING

Medium · phase_mismapping

```python
AMI_PHASE_MAPPING =
    ((READS_OK / 24 * 100) >= 99)
    & (NTL_PCT <= 3)
    & (NTL_PCT >= -2)
    & (V_END_SPREAD_EXCESS <= 8)
    & (PHASE_SPREAD_PCT > 8)
```

### AMI_REVERSE_ENERGY

Medium · ct_polarity

```python
AMI_REVERSE_ENERGY =
    FEEDER_KWH_EXPORT > 0.05
```

### AMI_VOLTAGE_OUT

Medium · loose_neutral

```python
AMI_VOLTAGE_OUT =
    ((V_MIN_CUST < 207) | (V_MAX_CUST > 253))
    & (V_BUS_AVG <= 246)
    & (V_BUS_AVG >= 226)
```

### AMI_BUS_VOLTAGE

Medium · tap_setting

```python
AMI_BUS_VOLTAGE =
    (V_BUS_AVG > 246) | (V_BUS_AVG < 226)
```

### AMI_READS_LOW

Medium · concentrator_comms

```python
AMI_READS_LOW =
    (READS_OK / 24 * 100) < 99
```

### AMI_CLOCK_DRIFT

Low · clock_drift

```python
AMI_CLOCK_DRIFT =
    CLOCK_OFFSET_MAX_S > 10
```
