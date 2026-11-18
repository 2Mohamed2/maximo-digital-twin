# H-2401: Maximo Monitor functions and alert rules

Device type `FIRED_HEATER_PROCESS`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### CHARGE_TH

```python
CHARGE_TH =
    (FLOW_A_TH + FLOW_B_TH + FLOW_C_TH + FLOW_D_TH)
```

### ABSORBED_DUTY_MW

```python
ABSORBED_DUTY_MW =
    (CHARGE_TH / 3.6 * 4.59330143541 * (COT_C - INLET_TEMP_C) / 1000)
```

### FIRED_DUTY_MW

```python
FIRED_DUTY_MW =
    (FUEL_FLOW_KGH / 3600 * FUEL_LHV_MJKG)
```

### THERMAL_EFF_PCT

```python
THERMAL_EFF_PCT =
    (ABSORBED_DUTY_MW / FIRED_DUTY_MW * 100)
```

### EXCESS_AIR_PCT

```python
EXCESS_AIR_PCT =
    (92 * O2_PCT / (21 - O2_PCT))
```

### STACK_LOSS_PCT

```python
STACK_LOSS_PCT =
    (
      (1 + 17.12 * (1 + EXCESS_AIR_PCT / 100))
      * 1.15
      * (STACK_TEMP_C - AMBIENT_TEMP_C)
      / (FUEL_LHV_MJKG * 1000)
      * 100
    )
```

### EFF_FLUEGAS_PCT

```python
EFF_FLUEGAS_PCT =
    (100 - STACK_LOSS_PCT - 1.5)
```

### EFF_RESIDUAL_PCT

```python
EFF_RESIDUAL_PCT =
    THERMAL_EFF_PCT - EFF_FLUEGAS_PCT
```

### STACK_RISE_C

```python
STACK_RISE_C =
    (STACK_TEMP_C - (300 + 110 * (ABSORBED_DUTY_MW / 40 - 1)))
```

### FUEL_COST_EXCESS_KUSD_Y

```python
FUEL_COST_EXCESS_KUSD_Y =
    (ABSORBED_DUTY_MW * (100 / EFF_FLUEGAS_PCT - 1.17125169279) * 189.216)
```

### FLOW_IMBALANCE_PCT

```python
FLOW_IMBALANCE_PCT =
    (
      (
        np.maximum(
          np.maximum(FLOW_A_TH, FLOW_B_TH),
          np.maximum(FLOW_C_TH, FLOW_D_TH)
        )
        - np.minimum(
            np.minimum(FLOW_A_TH, FLOW_B_TH),
            np.minimum(FLOW_C_TH, FLOW_D_TH)
          )
      )
      / (CHARGE_TH / 4)
      * 100
    )
```

### DP_RATIO_MAX

```python
DP_RATIO_MAX =
    np.maximum(
      np.maximum(
        (DP_A_BAR / (8 * (FLOW_A_TH / 71.25) ** 1.8)),
        (DP_B_BAR / (8 * (FLOW_B_TH / 71.25) ** 1.8))
      ),
      np.maximum(
        (DP_C_BAR / (8 * (FLOW_C_TH / 71.25) ** 1.8)),
        (DP_D_BAR / (8 * (FLOW_D_TH / 71.25) ** 1.8))
      )
    )
```

### TMT_MAX_C

```python
TMT_MAX_C =
    (np.maximum(np.maximum(TMT_A_C, TMT_B_C), np.maximum(TMT_C_C, TMT_D_C)))
```

### TMT_SPREAD_C

```python
TMT_SPREAD_C =
    (
      np.maximum(np.maximum(TMT_A_C, TMT_B_C), np.maximum(TMT_C_C, TMT_D_C))
      - np.minimum(
          np.minimum(TMT_A_C, TMT_B_C),
          np.minimum(TMT_C_C, TMT_D_C)
        )
    )
```

### PEAK_FLUX_KWM2

```python
PEAK_FLUX_KWM2 =
    (57.6 * ABSORBED_DUTY_MW / 40)
```

### TMT_CLEAN_C

```python
TMT_CLEAN_C =
    (COT_C + PEAK_FLUX_KWM2 * 1000 * 0.000987747252747)
```

### COKE_MM

```python
COKE_MM =
    ((TMT_MAX_C - TMT_CLEAN_C) / (PEAK_FLUX_KWM2 * 1000) * 1 * 1000)
```

### BURNER_P_RATIO

```python
BURNER_P_RATIO =
    (
      (FUEL_PRESSURE_BARG + 1.01325)
      / (2.41325 * FUEL_FLOW_KGH / 3373.20487524)
    )
```

### HOOP_STRESS_MPA

```python
HOOP_STRESS_MPA =
    (INLET_PRESSURE_BARG / 10 * 13.0725806452)
```

### CREEP_LIFE_Y

```python
CREEP_LIFE_Y =
    np.minimum(
      0.8
      * 10
        ** (
             1000
             * (28.19 - 3.85 * np.log10(HOOP_STRESS_MPA))
             / (TMT_MAX_C + 273.15)
             - 20
           )
      / 8760,
      100
    )
```

## AlertExpression rules (15)

### HTR_TMT_LIMIT

Critical · coking

```python
HTR_TMT_LIMIT =
    TMT_MAX_C > 600
```

### HTR_COKE_BUILDUP

High · coking

```python
HTR_COKE_BUILDUP =
    COKE_MM > 1.5
```

### HTR_CREEP_LIFE_LOW

High · coking

```python
HTR_CREEP_LIFE_LOW =
    np.minimum(
      0.8
      * 10
        ** (
             1000
             * (28.19 - 3.85 * np.log10(HOOP_STRESS_MPA))
             / (TMT_MAX_C + 273.15)
             - 20
           )
      / 8760,
      100
    )
    < 10
```

### HTR_DRAFT_LOW

High · draft_loss

```python
HTR_DRAFT_LOW =
    ARCH_DRAFT_MMH2O > -1
```

### HTR_O2_LOW

High · air_starvation

```python
HTR_O2_LOW =
    O2_PCT < 1.5
```

### HTR_TMT_ALERT

Medium · coking

```python
HTR_TMT_ALERT =
    (TMT_MAX_C > 575) & (TMT_MAX_C <= 600)
```

### HTR_PASS_DP_HIGH

Medium · coking

```python
HTR_PASS_DP_HIGH =
    np.maximum(
      np.maximum(
        (DP_A_BAR / (8 * (FLOW_A_TH / 71.25) ** 1.8)),
        (DP_B_BAR / (8 * (FLOW_B_TH / 71.25) ** 1.8))
      ),
      np.maximum(
        (DP_C_BAR / (8 * (FLOW_C_TH / 71.25) ** 1.8)),
        (DP_D_BAR / (8 * (FLOW_D_TH / 71.25) ** 1.8))
      )
    )
    > 1.3
```

### HTR_PASS_IMBALANCE

Medium · pass_imbalance

```python
HTR_PASS_IMBALANCE =
    FLOW_IMBALANCE_PCT > 10
```

### HTR_FLAME_IMPINGEMENT

Medium · flame_impingement

```python
HTR_FLAME_IMPINGEMENT =
    (TMT_SPREAD_C > 50)
    & (
        np.maximum(
          np.maximum(
            (DP_A_BAR / (8 * (FLOW_A_TH / 71.25) ** 1.8)),
            (DP_B_BAR / (8 * (FLOW_B_TH / 71.25) ** 1.8))
          ),
          np.maximum(
            (DP_C_BAR / (8 * (FLOW_C_TH / 71.25) ** 1.8)),
            (DP_D_BAR / (8 * (FLOW_D_TH / 71.25) ** 1.8))
          )
        )
        <= 1.3
      )
    & (FLOW_IMBALANCE_PCT <= 10)
```

### HTR_BURNER_DP_HIGH

Medium · flame_impingement

```python
HTR_BURNER_DP_HIGH =
    BURNER_P_RATIO > 1.15
```

### HTR_CO_HIGH

Medium · air_starvation

```python
HTR_CO_HIGH =
    CO_PPM > 400
```

### HTR_EXCESS_AIR_HIGH

Medium · excess_air_high

```python
HTR_EXCESS_AIR_HIGH =
    EXCESS_AIR_PCT > 35
```

### HTR_EFF_LOW

Medium · convection_fouling

```python
HTR_EFF_LOW =
    EFF_FLUEGAS_PCT < 83.3787453333
```

### HTR_STACK_HIGH

Medium · convection_fouling

```python
HTR_STACK_HIGH =
    STACK_RISE_C > 35
```

### HTR_EFF_MISMATCH

Medium · fuel_meter_drift

```python
HTR_EFF_MISMATCH =
    np.absEFF_RESIDUAL_PCT > 4
```
