# RO-1201: Maximo Monitor functions and alert rules

Device type `REVERSE_OSMOSIS_TRAIN`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (17)

### NDP_BAR

```python
NDP_BAR =
    (
      MEMBRANE_FEED_PRESSURE_BAR
      - VESSEL_DP_BAR / 2
      - PERMEATE_PRESSURE_BAR
      - 0.00079
        * (
            ((MEMBRANE_FEED_TDS_MGL + CONCENTRATE_TDS_MGL) / 2)
            - PERMEATE_TDS_MGL
          )
    )
```

### TCF

```python
TCF =
    np.exp(2640 * (1 / 298.15 - 1 / (273.15 + FEED_TEMP_C)))
```

### NPF_PCT

```python
NPF_PCT =
    (
      (
        PERMEATE_FLOW_M3H
        * (13.782 / NDP_BAR)
        / np.exp(2640 * (1 / 298.15 - 1 / (273.15 + FEED_TEMP_C)))
      )
      / (
          181.98912
          - 0.73573268 * FEED_TEMP_C
          - 0.015519257 * FEED_TEMP_C ** 2
        )
      * 100
    )
```

### NSP_PCT

```python
NSP_PCT =
    (
      (
        (
          PERMEATE_TDS_MGL
          / ((MEMBRANE_FEED_TDS_MGL + CONCENTRATE_TDS_MGL) / 2)
        )
        * (NDP_BAR / 13.782)
      )
      / (
          0.0039228839
          + 2.1795195e-06 * FEED_TEMP_C
          + 1.0935657e-06 * FEED_TEMP_C ** 2
        )
      * 100
    )
```

### NDP_NORM_PCT

```python
NDP_NORM_PCT =
    (
      (
        VESSEL_DP_BAR
        * (
            292.09
            / (
                ((HP_FLOW_M3H + PX_HP_OUT_FLOW_M3H) + CONCENTRATE_FLOW_M3H)
                / 2
              )
          )
          ** 1.5
      )
      / (
          0.79855645
          - 0.002561367 * FEED_TEMP_C
          - 1.1118141e-06 * FEED_TEMP_C ** 2
        )
      * 100
    )
```

### PERMEATE_EXPECTED_M3H

```python
PERMEATE_EXPECTED_M3H =
    (
      (
        181.98912
        - 0.73573268 * FEED_TEMP_C
        - 0.015519257 * FEED_TEMP_C ** 2
      )
      * np.exp(2640 * (1 / 298.15 - 1 / (273.15 + FEED_TEMP_C)))
      * NDP_BAR
      / 13.782
    )
```

### PERMEATE_DEVIATION_PCT

```python
PERMEATE_DEVIATION_PCT =
    (PERMEATE_FLOW_M3H / PERMEATE_EXPECTED_M3H - 1) * 100
```

### RECOVERY_PCT

```python
RECOVERY_PCT =
    (PERMEATE_FLOW_M3H / (HP_FLOW_M3H + PX_HP_OUT_FLOW_M3H) * 100)
```

### HP_PUMP_EFF_PCT

```python
HP_PUMP_EFF_PCT =
    (
      HP_FLOW_M3H
      * (HP_DISCHARGE_PRESSURE_BAR - HP_SUCTION_PRESSURE_BAR)
      / 36
      / HP_POWER_KW.clip(lower=1)
      * 100
    )
```

### HP_PUMP_EFF_EXPECTED_PCT

```python
HP_PUMP_EFF_EXPECTED_PCT =
    (0.82 * (1 - 0.8 * (HP_FLOW_M3H / 162 - 1) ** 2) * 0.96 * 100)
```

### HP_PUMP_EFF_DEV_PTS

```python
HP_PUMP_EFF_DEV_PTS =
    HP_PUMP_EFF_PCT - HP_PUMP_EFF_EXPECTED_PCT
```

### PX_EFF_PCT

```python
PX_EFF_PCT =
    (
      (
        PX_HP_OUT_FLOW_M3H * PX_HP_OUT_PRESSURE_BAR
        + PX_LP_OUT_FLOW_M3H * PX_LP_OUT_PRESSURE_BAR
      )
      / (
          CONCENTRATE_FLOW_M3H * CONCENTRATE_PRESSURE_BAR
          + PX_LP_IN_FLOW_M3H * PX_LP_IN_PRESSURE_BAR
        )
      * 100
    )
```

### PX_LEAKAGE_PCT

```python
PX_LEAKAGE_PCT =
    (
      (PX_LP_OUT_FLOW_M3H - PX_LP_IN_FLOW_M3H)
      / CONCENTRATE_FLOW_M3H.clip(lower=1)
      * 100
    )
```

### PX_MIXING_PCT

```python
PX_MIXING_PCT =
    (
      (MEMBRANE_FEED_TDS_MGL - FEED_TDS_MGL)
      * (HP_FLOW_M3H + PX_HP_OUT_FLOW_M3H)
      / (
          (CONCENTRATE_TDS_MGL - FEED_TDS_MGL).clip(lower=1)
          * PX_HP_OUT_FLOW_M3H.clip(lower=1)
        )
      * 100
    )
```

### BANK_TDS_RATIO

```python
BANK_TDS_RATIO =
    (
      np.maximum(
        np.maximum(BANK1_PERMEATE_TDS_MGL, BANK2_PERMEATE_TDS_MGL),
        np.maximum(BANK3_PERMEATE_TDS_MGL, BANK4_PERMEATE_TDS_MGL)
      )
      / (
          (
            BANK1_PERMEATE_TDS_MGL
            + BANK2_PERMEATE_TDS_MGL
            + BANK3_PERMEATE_TDS_MGL
            + BANK4_PERMEATE_TDS_MGL
          )
          / 4
        ).clip(lower=1)
    )
```

### SEC_KWH_M3

```python
SEC_KWH_M3 =
    ((HP_POWER_KW + BOOSTER_POWER_KW) / PERMEATE_FLOW_M3H.clip(lower=1))
```

### SALT_REJECTION_PCT

```python
SALT_REJECTION_PCT =
    (1 - PERMEATE_TDS_MGL / MEMBRANE_FEED_TDS_MGL) * 100
```

## AlertExpression rules (13)

### RO_NPF_LOW

Medium

```python
RO_NPF_LOW =
    NPF_PCT < 90
```

### RO_NSP_HIGH

Low

```python
RO_NSP_HIGH =
    NSP_PCT > 110
```

### RO_BIOFOULING

Medium · biofouling

```python
RO_BIOFOULING =
    NDP_NORM_PCT > 115
```

### RO_SCALING

Medium · scaling

```python
RO_SCALING =
    (NPF_PCT < 94) & (NSP_PCT > 105) & (NDP_NORM_PCT < 110)
```

### RO_OXIDATION

High · oxidation

```python
RO_OXIDATION =
    (NSP_PCT > 130) & (NPF_PCT > 103)
```

### RO_OXIDANT_IN_FEED

High · oxidation

```python
RO_OXIDANT_IN_FEED =
    FEED_ORP_MV > 400
```

### RO_BANK_LEAK

Medium · oring_leak

```python
RO_BANK_LEAK =
    BANK_TDS_RATIO > 1.3
```

### RO_HP_PUMP

Medium · hp_pump_wear

```python
RO_HP_PUMP =
    HP_PUMP_EFF_DEV_PTS < -4
```

### RO_ERD

Medium · erd_leakage

```python
RO_ERD =
    (PX_EFF_PCT < 95) | (PX_MIXING_PCT > 5) | (PX_LEAKAGE_PCT > 3.5)
```

### RO_CARTRIDGE_DP

Medium · cartridge_clogging

```python
RO_CARTRIDGE_DP =
    CF_DP_BAR > 1
```

### RO_LOW_SUCTION

High · cartridge_clogging

```python
RO_LOW_SUCTION =
    HP_SUCTION_PRESSURE_BAR < 1
```

### RO_PRESSURE_HIGH

High

```python
RO_PRESSURE_HIGH =
    MEMBRANE_FEED_PRESSURE_BAR > 80
```

### RO_PERMEATE_QUALITY

Medium

```python
RO_PERMEATE_QUALITY =
    PERMEATE_TDS_MGL > 500
```
