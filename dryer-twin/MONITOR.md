# PM-4301: Maximo Monitor functions and alert rules

Device type `PAPER_DRYER_SECTION`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### PRODUCTION_TH

```python
PRODUCTION_TH =
    (SPEED_MPM * 60 * 5.5 * BASIS_WEIGHT_GSM / 1000000)
```

### FIBRE_TH

```python
FIBRE_TH =
    (PRODUCTION_TH * 1000 * (1 - REEL_MOISTURE_PCT / 100)) / 1000
```

### EVAP_TH

```python
EVAP_TH =
    (
      (PRODUCTION_TH * 1000 * (1 - REEL_MOISTURE_PCT / 100))
      * (
          (100 - PRESS_DRYNESS_PCT) / PRESS_DRYNESS_PCT
          - REEL_MOISTURE_PCT / (100 - REEL_MOISTURE_PCT)
        )
    )
    / 1000
```

### EVAP_RATE_KGM2H

```python
EVAP_RATE_KGM2H =
    (
      (PRODUCTION_TH * 1000 * (1 - REEL_MOISTURE_PCT / 100))
      * (
          (100 - PRESS_DRYNESS_PCT) / PRESS_DRYNESS_PCT
          - REEL_MOISTURE_PCT / (100 - REEL_MOISTURE_PCT)
        )
    )
    / 1638.49764848
```

### SPEC_STEAM_KGKG

```python
SPEC_STEAM_KGKG =
    (
      STEAM_TOTAL_KGH
      / (
          (PRODUCTION_TH * 1000 * (1 - REEL_MOISTURE_PCT / 100))
          * (
              (100 - PRESS_DRYNESS_PCT) / PRESS_DRYNESS_PCT
              - REEL_MOISTURE_PCT / (100 - REEL_MOISTURE_PCT)
            )
        )
    )
```

### STEAM_COST_USD_T

```python
STEAM_COST_USD_T =
    STEAM_TOTAL_KGH / 1000 * 25 / PRODUCTION_TH
```

### EXCESS_STEAM_KUSD_Y

```python
EXCESS_STEAM_KUSD_Y =
    (
      STEAM_TOTAL_KGH
      - 1.35
        * (
            (PRODUCTION_TH * 1000 * (1 - REEL_MOISTURE_PCT / 100))
            * (
                (100 - PRESS_DRYNESS_PCT) / PRESS_DRYNESS_PCT
                - REEL_MOISTURE_PCT / (100 - REEL_MOISTURE_PCT)
              )
          )
    )
    / 1000
    * 25
    * 8400
    / 1000
```

### TSAT_MAIN_C

```python
TSAT_MAIN_C =
    np.interp(
      P3_BARG + 1.01325,
      [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
      [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
    )
```

### DT_SURF_MAX_C

```python
DT_SURF_MAX_C =
    np.maximum(
      (
        np.interp(
          P2_BARG + 1.01325,
          [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
          [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
        )
        - TS2_C
      ),
      np.maximum(
        (
          np.interp(
            P3_BARG + 1.01325,
            [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
            [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
          )
          - TS3_C
        ),
        (
          np.interp(
            P4_BARG + 1.01325,
            [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
            [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
          )
          - TS4_C
        )
      )
    )
```

### COLD_CYL_MAX_K

```python
COLD_CYL_MAX_K =
    np.maximum(
      (TS1_C - TSMIN1_C),
      np.maximum(
        (TS2_C - TSMIN2_C),
        np.maximum((TS3_C - TSMIN3_C), (TS4_C - TSMIN4_C))
      )
    )
```

### DP_MIN_KPA

```python
DP_MIN_KPA =
    np.minimum(DP1_KPA, np.minimum(DP2_KPA, np.minimum(DP3_KPA, DP4_KPA)))
```

### DP_MAX_KPA

```python
DP_MAX_KPA =
    np.maximum(DP1_KPA, np.maximum(DP2_KPA, np.maximum(DP3_KPA, DP4_KPA)))
```

### BLOWTHROUGH_PCT

```python
BLOWTHROUGH_PCT =
    (BT_MAIN_KGH / COND_MAIN_KGH * 100)
```

### BT_EXPECTED_PCT

```python
BT_EXPECTED_PCT =
    (12.5 * np.sqrt(np.maximum((DP3_KPA + DP4_KPA) / 2, 0) / 25))
```

### BT_RATIO

```python
BT_RATIO =
    (BLOWTHROUGH_PCT / BT_EXPECTED_PCT)
```

### VENT_PCT

```python
VENT_PCT =
    (VENT_KGH / STEAM_TOTAL_KGH * 100)
```

### AIR_BALANCE

```python
AIR_BALANCE =
    (HOOD_SUPPLY_KGS / HOOD_EXHAUST_KGS)
```

### DRY_COEF_RATIO

```python
DRY_COEF_RATIO =
    (
      (
        (PRODUCTION_TH * 1000 * (1 - REEL_MOISTURE_PCT / 100))
        * (
            (100 - PRESS_DRYNESS_PCT) / PRESS_DRYNESS_PCT
            - REEL_MOISTURE_PCT / (100 - REEL_MOISTURE_PCT)
          )
      )
      / (
          196.619717818 * (TS1_C - 60)
          + 393.239435635 * (TS2_C - 60)
          + 655.399059392 * (TS3_C - 60)
          + 393.239435635 * (TS4_C - 60)
        )
      / 0.268074995258
    )
```

### EVAP_STEAMSIDE_TH

```python
EVAP_STEAMSIDE_TH =
    (
      (STEAM_TOTAL_KGH - VENT_KGH)
      * np.interp(
          P3_BARG + 1.01325,
          [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
          [2257.5, 2226, 2201.6, 2163.5, 2133.4, 2107.4, 2085.8, 2066, 2047.5, 2014.6, 1985.4, 1959]
        )
      / 2815.87351185
      / 1000
    )
```

### BALANCE_RESIDUAL_PCT

```python
BALANCE_RESIDUAL_PCT =
    (
      (
        (
          (PRODUCTION_TH * 1000 * (1 - REEL_MOISTURE_PCT / 100))
          * (
              (100 - PRESS_DRYNESS_PCT) / PRESS_DRYNESS_PCT
              - REEL_MOISTURE_PCT / (100 - REEL_MOISTURE_PCT)
            )
        )
        / 1000
        / EVAP_STEAMSIDE_TH
        - 1
      )
      * 100
    )
```

## AlertExpression rules (14)

### DRY_COLD_CYLINDER

High · flooded_cylinder

```python
DRY_COLD_CYLINDER =
    np.maximum(
      (TS1_C - TSMIN1_C),
      np.maximum(
        (TS2_C - TSMIN2_C),
        np.maximum((TS3_C - TSMIN3_C), (TS4_C - TSMIN4_C))
      )
    )
    > 12
```

### DRY_DP_LOW

High · low_dp

```python
DRY_DP_LOW =
    np.minimum(DP1_KPA, np.minimum(DP2_KPA, np.minimum(DP3_KPA, DP4_KPA)))
    < 15
```

### DRY_SURF_DT_HIGH

Medium · low_dp

```python
DRY_SURF_DT_HIGH =
    np.maximum(
      (
        np.interp(
          P2_BARG + 1.01325,
          [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
          [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
        )
        - TS2_C
      ),
      np.maximum(
        (
          np.interp(
            P3_BARG + 1.01325,
            [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
            [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
          )
          - TS3_C
        ),
        (
          np.interp(
            P4_BARG + 1.01325,
            [1, 1.5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
            [99.61, 111.35, 120.21, 133.52, 143.61, 151.83, 158.83, 164.95, 170.41, 179.88, 187.96, 195.04]
          )
          - TS4_C
        )
      )
    )
    > 30
```

### DRY_DP_HIGH

Medium

```python
DRY_DP_HIGH =
    np.maximum(DP1_KPA, np.maximum(DP2_KPA, np.maximum(DP3_KPA, DP4_KPA)))
    > 35
```

### DRY_BLOWTHROUGH_HIGH

Medium · syphon_wear

```python
DRY_BLOWTHROUGH_HIGH =
    BT_RATIO > 1.5
```

### DRY_BLOWTHROUGH_LOW

Medium · low_dp

```python
DRY_BLOWTHROUGH_LOW =
    BT_RATIO < 0.65
```

### DRY_VENT_HIGH

Medium · vent_valve_passing

```python
DRY_VENT_HIGH =
    VENT_PCT > 2
```

### DRY_SSC_HIGH

Medium · vent_valve_passing

```python
DRY_SSC_HIGH =
    SPEC_STEAM_KGKG > 1.5
```

### DRY_RATE_LOW

Medium · fabric_filling

```python
DRY_RATE_LOW =
    DRY_COEF_RATIO < 0.87
```

### DRY_POCKET_HUMID_HIGH

Medium · fabric_filling

```python
DRY_POCKET_HUMID_HIGH =
    POCKET_HUMIDITY_GKG > 200
```

### DRY_HOOD_HUMID_LOW

Medium · hood_exhaust_high

```python
DRY_HOOD_HUMID_LOW =
    HOOD_HUMIDITY_GKG < 120
```

### DRY_HOOD_HUMID_HIGH

High · hood_exhaust_low

```python
DRY_HOOD_HUMID_HIGH =
    HOOD_HUMIDITY_GKG > 200
```

### DRY_AIR_BALANCE

Medium · hood_exhaust_high

```python
DRY_AIR_BALANCE =
    (AIR_BALANCE < 0.7) | (AIR_BALANCE > 0.9)
```

### DRY_BALANCE_MISMATCH

Medium · steam_meter_drift

```python
DRY_BALANCE_MISMATCH =
    np.abs(BALANCE_RESIDUAL_PCT) > 8
```
