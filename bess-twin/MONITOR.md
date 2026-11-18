# BESS-3501: Maximo Monitor functions and alert rules

Device type `BESS_LFP_CONTAINER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### STRING_CURRENT_A

```python
STRING_CURRENT_A =
    (DC_CURRENT_A / 4)
```

### CELL_V_SPREAD_MV

```python
CELL_V_SPREAD_MV =
    ((CELL_V_MAX_V - CELL_V_MIN_V) * 1000)
```

### CELL_R_EXCESS_MOHM

```python
CELL_R_EXCESS_MOHM =
    (
      (CELL_V_SPREAD_MV - CELL_V_SPREAD_REST_MV)
      / np.maximum(np.abs((DC_CURRENT_A / 4)), 10)
    )
```

### CELL_T_SPREAD_C

```python
CELL_T_SPREAD_C =
    (CELL_T_MAX_C - CELL_T_MIN_C)
```

### BATTERY_HEAT_KW

```python
BATTERY_HEAT_KW =
    (4 * (DC_CURRENT_A / 4) ** 2 * 0.18 / 1000)
```

### HEAT_LOAD_KW

```python
HEAT_LOAD_KW =
    (BATTERY_HEAT_KW + 1.2 + 0.1 * (AMBIENT_C - HVAC_RETURN_AIR_C))
```

### HVAC_COOLING_KW

```python
HVAC_COOLING_KW =
    (0.000335 * HVAC_AIRFLOW_M3H * (HVAC_RETURN_AIR_C - HVAC_SUPPLY_AIR_C))
```

### HVAC_CAPACITY_KW

```python
HVAC_CAPACITY_KW =
    (25 * (1 - 0.015 * (AMBIENT_C - 35)))
```

### HVAC_LOAD_RATIO

```python
HVAC_LOAD_RATIO =
    HEAT_LOAD_KW / HVAC_CAPACITY_KW
```

### HVAC_COP

```python
HVAC_COP =
    (HVAC_COOLING_KW / np.maximum(HVAC_POWER_KW, 0.1))
```

### HVAC_COP_RATIO

```python
HVAC_COP_RATIO =
    HVAC_COP / (2.8 * (1 - 0.02 * (AMBIENT_C - 35)))
```

### SOH_MODEL_PCT

```python
SOH_MODEL_PCT =
    (
      100
      - np.power(2, (LIFE_CELL_TEMP_AVG_C - 25) / 15)
        * (
            2 * np.sqrt(np.maximum(DAYS_IN_SERVICE, 1) / 365)
            + 0.00333333333333 * EFC_COUNT
          )
    )
```

### SOH_RESIDUAL_PCT

```python
SOH_RESIDUAL_PCT =
    SOH_BMS_PCT - SOH_MODEL_PCT
```

### USABLE_ENERGY_KWH

```python
USABLE_ENERGY_KWH =
    1345.2 * SOH_BMS_PCT / 100
```

### SOH_FADE_PCT_PER_YEAR

```python
SOH_FADE_PCT_PER_YEAR =
    (
      np.power(2, (LIFE_CELL_TEMP_AVG_C - 25) / 15)
      * (
          0.00333333333333
          * EFC_COUNT
          / np.maximum(DAYS_IN_SERVICE, 1)
          * 365
          + 2 / (2 * np.sqrt(np.maximum(DAYS_IN_SERVICE, 1) / 365))
        )
      * np.maximum(100 - SOH_BMS_PCT, 0.1)
      / (100 - SOH_MODEL_PCT)
    )
```

### YEARS_TO_AUGMENT

```python
YEARS_TO_AUGMENT =
    ((SOH_BMS_PCT - 81.7722271781) / SOH_FADE_PCT_PER_YEAR)
```

### RTE_AC_PCT

```python
RTE_AC_PCT =
    (
      ENERGY_DISCHARGED_24H_KWH
      / np.maximum(ENERGY_CHARGED_24H_KWH, 1)
      * 100
    )
```

### PCS_LOSS_KW

```python
PCS_LOSS_KW =
    np.abs(PCS_DC_POWER_KW - AC_POWER_KW)
```

### PCS_LOSS_RATIO

```python
PCS_LOSS_RATIO =
    (
      np.abs(PCS_DC_POWER_KW - AC_POWER_KW)
      / (3 + 1.83673469388e-05 * AC_POWER_KW ** 2)
    )
```

### PCS_EFFICIENCY_PCT

```python
PCS_EFFICIENCY_PCT =
    (
      100
      * (
          1
          - np.abs(PCS_DC_POWER_KW - AC_POWER_KW)
            / np.maximum(
                np.maximum(np.abs(PCS_DC_POWER_KW), np.abs(AC_POWER_KW)),
                1
              )
        )
    )
```

## AlertExpression rules (15)

### BESS_OFFGAS_DETECTED

Critical · thermal_runaway_precursor

```python
BESS_OFFGAS_DETECTED =
    (OFFGAS_PPM > 10) | (GAS_LEL_PCT > 10)
```

### BESS_CELL_TEMP_RATE

Critical · thermal_runaway_precursor

```python
BESS_CELL_TEMP_RATE =
    CELL_T_MAX_RATE_C_MIN > 1
```

### BESS_CELL_TEMP_HIGH

High

```python
BESS_CELL_TEMP_HIGH =
    CELL_T_MAX_C > 50
```

### BESS_CELL_V_LIMIT

High

```python
BESS_CELL_V_LIMIT =
    (CELL_V_MAX_V > 3.65) | (CELL_V_MIN_V < 2.5)
```

### BESS_INSULATION_LOW

High · insulation_fault

```python
BESS_INSULATION_LOW =
    INSULATION_KOHM < 138.6
```

### BESS_HVAC_MARGIN_LOW

High

```python
BESS_HVAC_MARGIN_LOW =
    HEAT_LOAD_KW / HVAC_CAPACITY_KW > 0.9
```

### BESS_WEAK_CELL_R

High · weak_module

```python
BESS_WEAK_CELL_R =
    (CELL_R_EXCESS_MOHM > 0.3) & (np.abs((DC_CURRENT_A / 4)) > 50)
```

### BESS_CELL_T_SPREAD_HIGH

Medium · weak_module

```python
BESS_CELL_T_SPREAD_HIGH =
    CELL_T_SPREAD_C > 8
```

### BESS_CELL_IMBALANCE

Medium · cell_imbalance

```python
BESS_CELL_IMBALANCE =
    CELL_V_SPREAD_REST_MV > 30
```

### BESS_HVAC_COP_LOW

Medium · hvac_degraded

```python
BESS_HVAC_COP_LOW =
    HVAC_COP / (2.8 * (1 - 0.02 * (AMBIENT_C - 35))) < 0.75
```

### BESS_HVAC_SUPPLY_HIGH

Medium · hvac_degraded

```python
BESS_HVAC_SUPPLY_HIGH =
    (HVAC_SUPPLY_AIR_C - 20) > 4
```

### BESS_SOH_BELOW_MODEL

Medium · capacity_fade_fast

```python
BESS_SOH_BELOW_MODEL =
    SOH_RESIDUAL_PCT < -3
```

### BESS_AUGMENT_DUE

Medium · capacity_fade_fast

```python
BESS_AUGMENT_DUE =
    YEARS_TO_AUGMENT < 2
```

### BESS_PCS_LOSS_HIGH

Medium · pcs_degradation

```python
BESS_PCS_LOSS_HIGH =
    PCS_LOSS_RATIO > 1.5
```

### BESS_RTE_LOW

Medium · pcs_degradation

```python
BESS_RTE_LOW =
    RTE_AC_PCT < 89.8838024064
```
