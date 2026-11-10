# TR-601: Maximo Monitor functions and alert rules

Device type `OIL_TRANSFORMER`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (18)

### LOAD_PU

```python
LOAD_PU =
    (LOAD_KVA.clip(lower=0) / 1000)
```

### TOP_OIL_EXPECTED_C

```python
TOP_OIL_EXPECTED_C =
    (
      AMBIENT_AVG_C
      + 60
        * ((1 + 10.9668 * LOAD_EQ_PU.clip(lower=0) ** 2) / 11.9668) ** 0.8
    )
```

### TOP_OIL_RESIDUAL_K

```python
TOP_OIL_RESIDUAL_K =
    TOP_OIL_TEMP_C - TOP_OIL_EXPECTED_C
```

### HOT_SPOT_EXPECTED_C

```python
HOT_SPOT_EXPECTED_C =
    (TOP_OIL_TEMP_C + 27.6 * (LOAD_KVA.clip(lower=0) / 1000) ** 1.6)
```

### HOT_SPOT_RESIDUAL_K

```python
HOT_SPOT_RESIDUAL_K =
    WTI_TEMP_C - HOT_SPOT_EXPECTED_C
```

### AGEING_RATE_V

```python
AGEING_RATE_V =
    np.power(2, (WTI_TEMP_C - 98) / 6)
```

### AGEING_RATE_V_UPGRADED

```python
AGEING_RATE_V_UPGRADED =
    np.exp(15000 / 383 - 15000 / (WTI_TEMP_C + 273))
```

### LOSS_OF_LIFE_H_PER_DAY

```python
LOSS_OF_LIFE_H_PER_DAY =
    24 * np.power(2, (WTI_TEMP_C - 98) / 6)
```

### LOSSES_KW

```python
LOSSES_KW =
    (693 + 7600 * (LOAD_KVA.clip(lower=0) / 1000) ** 2) / 1000
```

### PRESSURE_EXPECTED_BAR

```python
PRESSURE_EXPECTED_BAR =
    (0.02 + 0.0035 * (TOP_OIL_TEMP_C - 20))
```

### PRESSURE_RESIDUAL_BAR

```python
PRESSURE_RESIDUAL_BAR =
    TANK_PRESSURE_BAR - PRESSURE_EXPECTED_BAR
```

### TDCG_PPM

```python
TDCG_PPM =
    (
      DGA_H2_PPM
      + DGA_CH4_PPM
      + DGA_C2H2_PPM
      + DGA_C2H4_PPM
      + DGA_C2H6_PPM
      + DGA_CO_PPM
    )
```

### DUVAL_CH4_PCT

```python
DUVAL_CH4_PCT =
    (
      DGA_CH4_PPM
      / (DGA_CH4_PPM + DGA_C2H4_PPM + DGA_C2H2_PPM).clip(lower=0.01)
      * 100
    )
```

### DUVAL_C2H4_PCT

```python
DUVAL_C2H4_PCT =
    (
      DGA_C2H4_PPM
      / (DGA_CH4_PPM + DGA_C2H4_PPM + DGA_C2H2_PPM).clip(lower=0.01)
      * 100
    )
```

### DUVAL_C2H2_PCT

```python
DUVAL_C2H2_PCT =
    (
      DGA_C2H2_PPM
      / (DGA_CH4_PPM + DGA_C2H4_PPM + DGA_C2H2_PPM).clip(lower=0.01)
      * 100
    )
```

### DUVAL_ZONE

```python
DUVAL_ZONE =
    np.where(
      ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
      0,
      np.where(
        DUVAL_CH4_PCT >= 98,
        1,
        np.where(
          (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
          2,
          np.where(
            (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
            3,
            np.where(
              (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
              4,
              np.where(
                (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                5,
                np.where(
                  ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                  | (
                      (DUVAL_C2H4_PCT >= 23)
                      & (DUVAL_C2H4_PCT < 40)
                      & (DUVAL_C2H2_PCT >= 13)
                      & (DUVAL_C2H2_PCT < 29)
                    ),
                  6,
                  7
                )
              )
            )
          )
        )
      )
    )
```

### IEEE_CONDITION

```python
IEEE_CONDITION =
    np.maximum(
      np.maximum(
        np.maximum(
          np.maximum(
            np.maximum(
              np.maximum(
                (
                  1
                  + (DGA_H2_PPM > 100).astype(int)
                  + (DGA_H2_PPM > 700).astype(int)
                  + (DGA_H2_PPM > 1800).astype(int)
                ),
                (
                  1
                  + (DGA_CH4_PPM > 120).astype(int)
                  + (DGA_CH4_PPM > 400).astype(int)
                  + (DGA_CH4_PPM > 1000).astype(int)
                )
              ),
              (
                1
                + (DGA_C2H2_PPM > 35).astype(int)
                + (DGA_C2H2_PPM > 50).astype(int)
                + (DGA_C2H2_PPM > 80).astype(int)
              )
            ),
            (
              1
              + (DGA_C2H4_PPM > 50).astype(int)
              + (DGA_C2H4_PPM > 100).astype(int)
              + (DGA_C2H4_PPM > 200).astype(int)
            )
          ),
          (
            1
            + (DGA_C2H6_PPM > 65).astype(int)
            + (DGA_C2H6_PPM > 100).astype(int)
            + (DGA_C2H6_PPM > 150).astype(int)
          )
        ),
        (
          1
          + (DGA_CO_PPM > 350).astype(int)
          + (DGA_CO_PPM > 570).astype(int)
          + (DGA_CO_PPM > 1400).astype(int)
        )
      ),
      (
        1
        + (TDCG_PPM > 720).astype(int)
        + (TDCG_PPM > 1920).astype(int)
        + (TDCG_PPM > 4630).astype(int)
      )
    )
```

### CO2_CO_RATIO

```python
CO2_CO_RATIO =
    DGA_CO2_PPM / DGA_CO_PPM.clip(lower=1)
```

## AlertExpression rules (16)

### TR_COOLING_DEGRADED

Medium · cooling_degraded

```python
TR_COOLING_DEGRADED =
    (TOP_OIL_RESIDUAL_K > 8) & (LOAD_EQ_PU > 0.25)
```

### TR_TOP_OIL_HIGH

High

```python
TR_TOP_OIL_HIGH =
    TOP_OIL_TEMP_C > 105
```

### TR_HOT_SPOT_HIGH

High · overload_ageing

```python
TR_HOT_SPOT_HIGH =
    WTI_TEMP_C > 120
```

### TR_OVERLOAD

Medium · overload_ageing

```python
TR_OVERLOAD =
    LOAD_EQ_PU > 1.2
```

### TR_AGEING_FAST

Low · overload_ageing

```python
TR_AGEING_FAST =
    np.power(2, (WTI_TEMP_C - 98) / 6) > 2
```

### TR_PAPER_OVERHEATING

Medium · overload_ageing

```python
TR_PAPER_OVERHEATING =
    DGA_CO_PPM > 570
```

### TR_DGA_THERMAL

Medium · thermal_fault_core

```python
TR_DGA_THERMAL =
    (
      np.where(
        ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
        0,
        np.where(
          DUVAL_CH4_PCT >= 98,
          1,
          np.where(
            (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
            2,
            np.where(
              (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
              3,
              np.where(
                (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
                4,
                np.where(
                  (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                  5,
                  np.where(
                    ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                    | (
                        (DUVAL_C2H4_PCT >= 23)
                        & (DUVAL_C2H4_PCT < 40)
                        & (DUVAL_C2H2_PCT >= 13)
                        & (DUVAL_C2H2_PCT < 29)
                      ),
                    6,
                    7
                  )
                )
              )
            )
          )
        )
      )
      == 2
    )
    | (
        np.where(
          ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
          0,
          np.where(
            DUVAL_CH4_PCT >= 98,
            1,
            np.where(
              (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
              2,
              np.where(
                (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
                3,
                np.where(
                  (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
                  4,
                  np.where(
                    (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                    5,
                    np.where(
                      ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                      | (
                          (DUVAL_C2H4_PCT >= 23)
                          & (DUVAL_C2H4_PCT < 40)
                          & (DUVAL_C2H2_PCT >= 13)
                          & (DUVAL_C2H2_PCT < 29)
                        ),
                      6,
                      7
                    )
                  )
                )
              )
            )
          )
        )
        == 3
      )
```

### TR_DGA_T3

High · thermal_fault_core

```python
TR_DGA_T3 =
    np.where(
      ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
      0,
      np.where(
        DUVAL_CH4_PCT >= 98,
        1,
        np.where(
          (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
          2,
          np.where(
            (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
            3,
            np.where(
              (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
              4,
              np.where(
                (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                5,
                np.where(
                  ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                  | (
                      (DUVAL_C2H4_PCT >= 23)
                      & (DUVAL_C2H4_PCT < 40)
                      & (DUVAL_C2H2_PCT >= 13)
                      & (DUVAL_C2H2_PCT < 29)
                    ),
                  6,
                  7
                )
              )
            )
          )
        )
      )
    )
    == 4
```

### TR_DGA_PD

Medium · partial_discharge

```python
TR_DGA_PD =
    np.where(
      ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
      0,
      np.where(
        DUVAL_CH4_PCT >= 98,
        1,
        np.where(
          (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
          2,
          np.where(
            (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
            3,
            np.where(
              (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
              4,
              np.where(
                (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                5,
                np.where(
                  ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                  | (
                      (DUVAL_C2H4_PCT >= 23)
                      & (DUVAL_C2H4_PCT < 40)
                      & (DUVAL_C2H2_PCT >= 13)
                      & (DUVAL_C2H2_PCT < 29)
                    ),
                  6,
                  7
                )
              )
            )
          )
        )
      )
    )
    == 1
```

### TR_DGA_ARCING

High · arcing

```python
TR_DGA_ARCING =
    (
      np.where(
        ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
        0,
        np.where(
          DUVAL_CH4_PCT >= 98,
          1,
          np.where(
            (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
            2,
            np.where(
              (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
              3,
              np.where(
                (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
                4,
                np.where(
                  (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                  5,
                  np.where(
                    ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                    | (
                        (DUVAL_C2H4_PCT >= 23)
                        & (DUVAL_C2H4_PCT < 40)
                        & (DUVAL_C2H2_PCT >= 13)
                        & (DUVAL_C2H2_PCT < 29)
                      ),
                    6,
                    7
                  )
                )
              )
            )
          )
        )
      )
      == 5
    )
    | (
        np.where(
          ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
          0,
          np.where(
            DUVAL_CH4_PCT >= 98,
            1,
            np.where(
              (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
              2,
              np.where(
                (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
                3,
                np.where(
                  (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
                  4,
                  np.where(
                    (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                    5,
                    np.where(
                      ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                      | (
                          (DUVAL_C2H4_PCT >= 23)
                          & (DUVAL_C2H4_PCT < 40)
                          & (DUVAL_C2H2_PCT >= 13)
                          & (DUVAL_C2H2_PCT < 29)
                        ),
                      6,
                      7
                    )
                  )
                )
              )
            )
          )
        )
        == 6
      )
```

### TR_DGA_DT

Medium · arcing

```python
TR_DGA_DT =
    np.where(
      ~((DGA_H2_PPM > 100) | (DGA_CH4_PPM > 120) | (DGA_C2H4_PPM > 50) | (DGA_C2H2_PPM > 1)),
      0,
      np.where(
        DUVAL_CH4_PCT >= 98,
        1,
        np.where(
          (DUVAL_C2H4_PCT < 20) & (DUVAL_C2H2_PCT < 4),
          2,
          np.where(
            (DUVAL_C2H4_PCT < 50) & (DUVAL_C2H2_PCT < 4),
            3,
            np.where(
              (DUVAL_C2H4_PCT >= 50) & (DUVAL_C2H2_PCT < 15),
              4,
              np.where(
                (DUVAL_C2H4_PCT < 23) & (DUVAL_C2H2_PCT >= 13),
                5,
                np.where(
                  ((DUVAL_C2H4_PCT >= 23) & (DUVAL_C2H2_PCT >= 29))
                  | (
                      (DUVAL_C2H4_PCT >= 23)
                      & (DUVAL_C2H4_PCT < 40)
                      & (DUVAL_C2H2_PCT >= 13)
                      & (DUVAL_C2H2_PCT < 29)
                    ),
                  6,
                  7
                )
              )
            )
          )
        )
      )
    )
    == 7
```

### TR_DGA_CONDITION

High

```python
TR_DGA_CONDITION =
    np.maximum(
      np.maximum(
        np.maximum(
          np.maximum(
            np.maximum(
              np.maximum(
                (
                  1
                  + (DGA_H2_PPM > 100).astype(int)
                  + (DGA_H2_PPM > 700).astype(int)
                  + (DGA_H2_PPM > 1800).astype(int)
                ),
                (
                  1
                  + (DGA_CH4_PPM > 120).astype(int)
                  + (DGA_CH4_PPM > 400).astype(int)
                  + (DGA_CH4_PPM > 1000).astype(int)
                )
              ),
              (
                1
                + (DGA_C2H2_PPM > 35).astype(int)
                + (DGA_C2H2_PPM > 50).astype(int)
                + (DGA_C2H2_PPM > 80).astype(int)
              )
            ),
            (
              1
              + (DGA_C2H4_PPM > 50).astype(int)
              + (DGA_C2H4_PPM > 100).astype(int)
              + (DGA_C2H4_PPM > 200).astype(int)
            )
          ),
          (
            1
            + (DGA_C2H6_PPM > 65).astype(int)
            + (DGA_C2H6_PPM > 100).astype(int)
            + (DGA_C2H6_PPM > 150).astype(int)
          )
        ),
        (
          1
          + (DGA_CO_PPM > 350).astype(int)
          + (DGA_CO_PPM > 570).astype(int)
          + (DGA_CO_PPM > 1400).astype(int)
        )
      ),
      (
        1
        + (TDCG_PPM > 720).astype(int)
        + (TDCG_PPM > 1920).astype(int)
        + (TDCG_PPM > 4630).astype(int)
      )
    )
    >= 3
```

### TR_MOISTURE

Medium · moisture_ingress

```python
TR_MOISTURE =
    MOISTURE_PPM > 25
```

### TR_OIL_LOSS

Medium · oil_leak

```python
TR_OIL_LOSS =
    (OIL_LEVEL_PCT < 90) | (PRESSURE_RESIDUAL_BAR < -0.05)
```

### TR_RELAY_ALARM

High

```python
TR_RELAY_ALARM =
    RELAY_STATUS == 1
```

### TR_RELAY_TRIP

Critical

```python
TR_RELAY_TRIP =
    RELAY_STATUS >= 2
```
