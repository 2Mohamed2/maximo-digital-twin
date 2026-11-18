# AD-4901: Maximo Monitor functions and alert rules

Device type `ANAEROBIC_DIGESTER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### HRT_D

```python
HRT_D =
    3000 / FEED_FLOW_M3D
```

### SRT_EFFECTIVE_D

```python
SRT_EFFECTIVE_D =
    (3000 * ACTIVE_VOLUME_PCT / 100 / FEED_FLOW_M3D)
```

### VS_LOAD_KGD

```python
VS_LOAD_KGD =
    (FEED_FLOW_M3D * 0.1 * FEED_DS_PCT * FEED_VS_PCT)
```

### OLR_KGVS_M3D

```python
OLR_KGVS_M3D =
    VS_LOAD_KGD / 3000
```

### VSR_PCT

```python
VSR_PCT =
    100
    * (
        (FEED_VS_PCT / 100 - DIGESTED_VS_PCT / 100)
        / (FEED_VS_PCT / 100 - FEED_VS_PCT * DIGESTED_VS_PCT / 10000)
      )
```

### VS_DESTROYED_KGD

```python
VS_DESTROYED_KGD =
    VS_LOAD_KGD
    * (
        (FEED_VS_PCT / 100 - DIGESTED_VS_PCT / 100)
        / (FEED_VS_PCT / 100 - FEED_VS_PCT * DIGESTED_VS_PCT / 10000)
      )
```

### BIOGAS_EXPECTED_M3H

```python
BIOGAS_EXPECTED_M3H =
    (
      VS_LOAD_KGD
      * (
          (FEED_VS_PCT / 100 - DIGESTED_VS_PCT / 100)
          / (FEED_VS_PCT / 100 - FEED_VS_PCT * DIGESTED_VS_PCT / 10000)
        )
      * 0.94
      / 24
    )
```

### GAS_YIELD_RATIO

```python
GAS_YIELD_RATIO =
    BIOGAS_FLOW_M3H / BIOGAS_EXPECTED_M3H
```

### SGP_M3_KGVS

```python
SGP_M3_KGVS =
    BIOGAS_FLOW_M3H * 24 / VS_LOAD_KGD
```

### METHANE_POWER_KW

```python
METHANE_POWER_KW =
    BIOGAS_FLOW_M3H * CH4_PCT / 100 * 9.97
```

### TEMP_MEAN_C

```python
TEMP_MEAN_C =
    ((TEMP_TOP_C + TEMP_MID_C + TEMP_BOTTOM_C) / 3)
```

### TEMP_SPREAD_K

```python
TEMP_SPREAD_K =
    (
      np.maximum(np.maximum(TEMP_TOP_C, TEMP_MID_C), TEMP_BOTTOM_C)
      - np.minimum(np.minimum(TEMP_TOP_C, TEMP_MID_C), TEMP_BOTTOM_C)
    )
```

### MIXING_W_M3

```python
MIXING_W_M3 =
    MIXER_POWER_KW * 1000 / 3000
```

### HEAT_DELIVERED_KW

```python
HEAT_DELIVERED_KW =
    (HW_FLOW_M3H * 1.163 * (HW_SUPPLY_C - HW_RETURN_C))
```

### HEAT_DEMAND_KW

```python
HEAT_DEMAND_KW =
    (
      FEED_FLOW_M3D / 24 * 1.163 * (37 - FEED_TEMP_C)
      + 0.7 * (37 - AMBIENT_TEMP_C)
    )
```

### HX_UA_RATIO

```python
HX_UA_RATIO =
    HEAT_DELIVERED_KW
    / (
        ((HW_SUPPLY_C - HX_SLUDGE_OUT_C) - (HW_RETURN_C - HX_SLUDGE_IN_C))
        / np.log(
            (HW_SUPPLY_C - HX_SLUDGE_OUT_C) / (HW_RETURN_C - HX_SLUDGE_IN_C)
          )
      )
    / 9
```

### CHP_EFF_EL

```python
CHP_EFF_EL =
    CHP_POWER_KW / (CHP_GAS_M3H * CH4_PCT / 100 * 9.97)
```

### CHP_HEAT_EXPECTED_KW

```python
CHP_HEAT_EXPECTED_KW =
    (CHP_GAS_M3H * CH4_PCT / 100 * 9.97) * 0.402
```

### HEAT_COVER_RATIO

```python
HEAT_COVER_RATIO =
    (CHP_GAS_M3H * CH4_PCT / 100 * 9.97) * 0.402 / HEAT_DEMAND_KW
```

## AlertExpression rules (15)

### DIG_FOSTAC_HIGH

High · souring

```python
DIG_FOSTAC_HIGH =
    FOS_TAC >= 0.6
```

### DIG_PH_LOW

High · souring

```python
DIG_PH_LOW =
    PH < 6.8
```

### DIG_TEMP_LOW

High · hx_fouling

```python
DIG_TEMP_LOW =
    TEMP_MEAN_C < 35.5
```

### DIG_SRT_LOW

High · grit_accumulation

```python
DIG_SRT_LOW =
    SRT_EFFECTIVE_D < 15
```

### DIG_FOAM_HIGH

High · foaming

```python
DIG_FOAM_HIGH =
    FOAM_LAYER_M > 0.8
```

### DIG_FOSTAC_RISING

Medium · souring

```python
DIG_FOSTAC_RISING =
    (FOS_TAC >= 0.4) & (FOS_TAC < 0.6)
```

### DIG_CH4_LOW

Medium · souring

```python
DIG_CH4_LOW =
    CH4_PCT < 55
```

### DIG_GAS_YIELD_LOW

Medium · souring

```python
DIG_GAS_YIELD_LOW =
    BIOGAS_FLOW_M3H / BIOGAS_EXPECTED_M3H < 0.8
```

### DIG_HX_FOULED

Medium · hx_fouling

```python
DIG_HX_FOULED =
    HEAT_DELIVERED_KW
    / (
        ((HW_SUPPLY_C - HX_SLUDGE_OUT_C) - (HW_RETURN_C - HX_SLUDGE_IN_C))
        / np.log(
            (HW_SUPPLY_C - HX_SLUDGE_OUT_C) / (HW_RETURN_C - HX_SLUDGE_IN_C)
          )
      )
    / 9
    < 0.7
```

### DIG_STRATIFIED

Medium · mixing_failure

```python
DIG_STRATIFIED =
    TEMP_SPREAD_K > 2
```

### DIG_MIXING_LOW

Medium · mixing_failure

```python
DIG_MIXING_LOW =
    MIXER_POWER_KW < 9
```

### DIG_ACTIVE_VOLUME_LOW

Medium · grit_accumulation

```python
DIG_ACTIVE_VOLUME_LOW =
    ACTIVE_VOLUME_PCT < 85
```

### DIG_VSR_LOW

Medium

```python
DIG_VSR_LOW =
    100
    * (
        (FEED_VS_PCT / 100 - DIGESTED_VS_PCT / 100)
        / (FEED_VS_PCT / 100 - FEED_VS_PCT * DIGESTED_VS_PCT / 10000)
      )
    < 38
```

### DIG_H2S_HIGH

Medium · h2s_high

```python
DIG_H2S_HIGH =
    H2S_PPM > 500
```

### DIG_CHP_EFF_LOW

Medium · chp_degradation

```python
DIG_CHP_EFF_LOW =
    CHP_POWER_KW / (CHP_GAS_M3H * CH4_PCT / 100 * 9.97) < 0.3825
```
