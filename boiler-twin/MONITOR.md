# BL-4501: Maximo Monitor functions and alert rules

Device type `STEAM_BOILER_SHELL`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### TSAT_C

```python
TSAT_C =
    (
      104.821571
      + 21.628559 * np.log(STEAM_PRESSURE_BARG + 1.013)
      + 4.761333 * np.log(STEAM_PRESSURE_BARG + 1.013) ** 2
    )
```

### H_STEAM_KJKG

```python
H_STEAM_KJKG =
    (
      2645.230834
      + 77.251933 * np.log(STEAM_PRESSURE_BARG + 1.013)
      - 8.828314 * np.log(STEAM_PRESSURE_BARG + 1.013) ** 2
    )
```

### LOAD_PCT

```python
LOAD_PCT =
    100 * (STEAM_FLOW_KGH / 10000)
```

### FUEL_INPUT_KW

```python
FUEL_INPUT_KW =
    (GAS_FLOW_NM3H * 36 / 3.6)
```

### BLOWDOWN_KGH

```python
BLOWDOWN_KGH =
    (FEED_FLOW_KGH - STEAM_FLOW_KGH)
```

### BLOWDOWN_PCT

```python
BLOWDOWN_PCT =
    100 * BLOWDOWN_KGH / STEAM_FLOW_KGH
```

### HEAT_OUTPUT_KW

```python
HEAT_OUTPUT_KW =
    (
      (
        STEAM_FLOW_KGH
        * (
            H_STEAM_KJKG
            - (
                4.2208978379 * FEED_TEMP_C
                - 0.0008006071 * FEED_TEMP_C ** 2
                + 5.0305e-06 * FEED_TEMP_C ** 3
              )
          )
        + BLOWDOWN_KGH
          * (
              (
                453.199563
                + 75.77989 * np.log(STEAM_PRESSURE_BARG + 1.013)
                + 25.419768 * np.log(STEAM_PRESSURE_BARG + 1.013) ** 2
              )
              - (
                  4.2208978379 * FEED_TEMP_C
                  - 0.0008006071 * FEED_TEMP_C ** 2
                  + 5.0305e-06 * FEED_TEMP_C ** 3
                )
            )
      )
      / 3600
    )
```

### EFF_DIRECT_PCT

```python
EFF_DIRECT_PCT =
    (100 * HEAT_OUTPUT_KW / (GAS_FLOW_NM3H * 36 / 3.6))
```

### EXCESS_AIR_PCT

```python
EXCESS_AIR_PCT =
    87 * O2_PCT / (21 - O2_PCT)
```

### FLUE_LOSS_PCT

```python
FLUE_LOSS_PCT =
    (
      (0.4731 - 0.00524 * O2_PCT)
      * (STACK_C - AIR_TEMP_C)
      / (11.94 * (1 - O2_PCT / 21))
    )
```

### EFF_INDIRECT_PCT

```python
EFF_INDIRECT_PCT =
    (
      100
      - FLUE_LOSS_PCT
      - (0.4 / np.maximum((STEAM_FLOW_KGH / 10000), 0.2))
    )
```

### EFF_EXPECTED_PCT

```python
EFF_EXPECTED_PCT =
    (
      100
      - (
          (0.4731 - 0.00524 * 3)
          * (
              (
                (
                  TSAT_C
                  + 60 * np.maximum((STEAM_FLOW_KGH / 10000), 0.2) ** 0.5
                )
                - 0.88823500795
                  * (
                      (
                        TSAT_C
                        + 60
                          * np.maximum((STEAM_FLOW_KGH / 10000), 0.2) ** 0.5
                      )
                      - FEED_TEMP_C
                    )
              )
              - AIR_TEMP_C
            )
          / (11.94 * (1 - 3 / 21))
        )
      - (0.4 / np.maximum((STEAM_FLOW_KGH / 10000), 0.2))
    )
```

### EFF_GAP_PCT

```python
EFF_GAP_PCT =
    EFF_DIRECT_PCT - EFF_INDIRECT_PCT
```

### EXIT_TEMP_RESIDUAL_K

```python
EXIT_TEMP_RESIDUAL_K =
    FLUE_EXIT_C
    - (TSAT_C + 60 * np.maximum((STEAM_FLOW_KGH / 10000), 0.2) ** 0.5)
```

### FLUE_DP_RATIO

```python
FLUE_DP_RATIO =
    (FLUE_DP_MBAR / (12 * np.maximum((STEAM_FLOW_KGH / 10000), 0.2) ** 1.8))
```

### ECO_EFFECTIVENESS

```python
ECO_EFFECTIVENESS =
    ((FLUE_EXIT_C - STACK_C) / (FLUE_EXIT_C - FEED_TEMP_C))
```

### STACK_RESIDUAL_K

```python
STACK_RESIDUAL_K =
    STACK_C
    - (
        (TSAT_C + 60 * np.maximum((STEAM_FLOW_KGH / 10000), 0.2) ** 0.5)
        - 0.88823500795
          * (
              (
                TSAT_C
                + 60 * np.maximum((STEAM_FLOW_KGH / 10000), 0.2) ** 0.5
              )
              - FEED_TEMP_C
            )
      )
```

### CYCLES_OF_CONCENTRATION

```python
CYCLES_OF_CONCENTRATION =
    BOILER_COND_USCM / FEED_COND_USCM
```

### FEED_MARGIN_BAR

```python
FEED_MARGIN_BAR =
    FEED_PUMP_P_BARG - STEAM_PRESSURE_BARG
```

### EXCESS_FUEL_KW

```python
EXCESS_FUEL_KW =
    (GAS_FLOW_NM3H * 36 / 3.6) * (1 - EFF_INDIRECT_PCT / EFF_EXPECTED_PCT)
```

## AlertExpression rules (15)

### BLR_CO_HIGH

High

```python
BLR_CO_HIGH =
    CO_PPM > 100
```

### BLR_TDS_HIGH

High · tds_control_fault

```python
BLR_TDS_HIGH =
    BOILER_COND_USCM > 6000
```

### BLR_LEVEL_DEVIATION

High · feed_pump_wear

```python
BLR_LEVEL_DEVIATION =
    np.abs(DRUM_LEVEL_MM) > 50
```

### BLR_HARDNESS

High · waterside_scale

```python
BLR_HARDNESS =
    FEED_HARDNESS_MMOL > 0.02
```

### BLR_LWCO_TEST_OVERDUE

High · safety_tests_overdue

```python
BLR_LWCO_TEST_OVERDUE =
    LWCO_TEST_HOURS_SINCE > 30
```

### BLR_FIRESIDE_FOULING

Medium · fireside_fouling

```python
BLR_FIRESIDE_FOULING =
    (EXIT_TEMP_RESIDUAL_K > 20) & (FLUE_DP_RATIO > 1.25)
```

### BLR_WATERSIDE_SCALE

Medium · waterside_scale

```python
BLR_WATERSIDE_SCALE =
    (EXIT_TEMP_RESIDUAL_K > 20) & (FLUE_DP_RATIO <= 1.25)
```

### BLR_ECO_EFFECTIVENESS_LOW

Medium · economiser_fouling

```python
BLR_ECO_EFFECTIVENESS_LOW =
    ECO_EFFECTIVENESS < 0.78
```

### BLR_STACK_HIGH

Medium · economiser_fouling

```python
BLR_STACK_HIGH =
    STACK_RESIDUAL_K > 15
```

### BLR_EXCESS_AIR_HIGH

Medium · excess_air_high

```python
BLR_EXCESS_AIR_HIGH =
    O2_PCT > 4.5
```

### BLR_EFF_LOW

Medium · excess_air_high

```python
BLR_EFF_LOW =
    EFF_INDIRECT_PCT < EFF_EXPECTED_PCT - 1
```

### BLR_EFF_MISMATCH

Medium

```python
BLR_EFF_MISMATCH =
    np.absEFF_GAP_PCT > 2.5
```

### BLR_BLOWDOWN_HIGH

Medium · blowdown_valve_passing

```python
BLR_BLOWDOWN_HIGH =
    BLOWDOWN_PCT > 1.6 * (100 * FEED_COND_USCM / (5000 - FEED_COND_USCM))
```

### BLR_FEED_MARGIN_LOW

Medium · feed_pump_wear

```python
BLR_FEED_MARGIN_LOW =
    FEED_MARGIN_BAR < 2
```

### BLR_SV_TEST_OVERDUE

Medium · safety_tests_overdue

```python
BLR_SV_TEST_OVERDUE =
    SV_TEST_HOURS_SINCE > 210
```
