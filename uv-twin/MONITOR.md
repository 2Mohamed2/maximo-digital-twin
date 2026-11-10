# UV-1601: Maximo Monitor functions and alert rules

Device type `UV_DISINFECTION`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (17)

### UVA_PER_CM

```python
UVA_PER_CM =
    (-np.log10(UVT_PCT / 100)).clip(lower=0.0001)
```

### DOSE_CALC_MJCM2

```python
DOSE_CALC_MJCM2 =
    np.minimum(
      43228.091
      * (np.minimum(UV_INTENSITY_1_WM2, UV_INTENSITY_2_WM2) / 250)
      * (
          (
            (
              1
              - np.power(
                  10,
                  -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 6
                )
            )
            / ((-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 13.815510558)
          )
          / np.power(10, -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3)
        )
      / FLOW_M3H.clip(lower=10),
      999
    )
```

### DOSE_EXPECTED_MJCM2

```python
DOSE_EXPECTED_MJCM2 =
    np.minimum(
      43228.091
      * (INTENSITY_EXPECTED_WM2 / 250)
      * (
          (
            (
              1
              - np.power(
                  10,
                  -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 6
                )
            )
            / ((-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 13.815510558)
          )
          / np.power(10, -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3)
        )
      / FLOW_M3H.clip(lower=10),
      999
    )
```

### DOSE_MARGIN_PCT

```python
DOSE_MARGIN_PCT =
    (
      np.minimum(
        43228.091
        * (np.minimum(UV_INTENSITY_1_WM2, UV_INTENSITY_2_WM2) / 250)
        * (
            (
              (
                1
                - np.power(
                    10,
                    -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 6
                  )
              )
              / (
                  (-np.log10(UVT_PCT / 100)).clip(lower=0.0001)
                  * 13.815510558
                )
            )
            / np.power(
                10,
                -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3
              )
          )
        / FLOW_M3H.clip(lower=10),
        999
      )
      / 40
      - 1
    )
    * 100
```

### INTENSITY_MEAN_WM2

```python
INTENSITY_MEAN_WM2 =
    ((UV_INTENSITY_1_WM2 + UV_INTENSITY_2_WM2) / 2)
```

### INTENSITY_EXPECTED_WM2

```python
INTENSITY_EXPECTED_WM2 =
    (
      250
      * (LAMP_POWER_KW / 3.84)
      * (1 - 0.2 * LAMP_HOURS / 12000).clip(lower=0.3)
      * 0.97
      * np.power(10, -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3)
    )
```

### INTENSITY_RATIO

```python
INTENSITY_RATIO =
    (INTENSITY_MEAN_WM2 / INTENSITY_EXPECTED_WM2.clip(lower=0.1))
```

### SENSOR_RATIO

```python
SENSOR_RATIO =
    (UV_INTENSITY_1_WM2 / UV_INTENSITY_2_WM2.clip(lower=0.1))
```

### AGE_FACTOR

```python
AGE_FACTOR =
    (1 - 0.2 * LAMP_HOURS / 12000).clip(lower=0.3)
```

### LAMP_POWER_EXPECTED_KW

```python
LAMP_POWER_EXPECTED_KW =
    (0.32 * LAMPS_ON * BALLAST_POWER_PCT / 100)
```

### BALLAST_DEV_PCT

```python
BALLAST_DEV_PCT =
    ((LAMP_POWER_KW / LAMP_POWER_EXPECTED_KW.clip(lower=0.01) - 1) * 100)
```

### REACTOR_TEMP_EXPECTED_C

```python
REACTOR_TEMP_EXPECTED_C =
    WATER_TEMP_C + LAMP_POWER_KW / (1.163 * FLOW_M3H.clip(lower=1))
```

### LOG_CRYPTO

```python
LOG_CRYPTO =
    np.interp(
      np.minimum(
        43228.091
        * (np.minimum(UV_INTENSITY_1_WM2, UV_INTENSITY_2_WM2) / 250)
        * (
            (
              (
                1
                - np.power(
                    10,
                    -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 6
                  )
              )
              / (
                  (-np.log10(UVT_PCT / 100)).clip(lower=0.0001)
                  * 13.815510558
                )
            )
            / np.power(
                10,
                -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3
              )
          )
        / FLOW_M3H.clip(lower=10),
        999
      ),
      [0, 1.6, 2.5, 3.9, 5.8, 8.5, 12, 15, 22],
      [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
    )
```

### LOG_GIARDIA

```python
LOG_GIARDIA =
    np.interp(
      np.minimum(
        43228.091
        * (np.minimum(UV_INTENSITY_1_WM2, UV_INTENSITY_2_WM2) / 250)
        * (
            (
              (
                1
                - np.power(
                    10,
                    -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 6
                  )
              )
              / (
                  (-np.log10(UVT_PCT / 100)).clip(lower=0.0001)
                  * 13.815510558
                )
            )
            / np.power(
                10,
                -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3
              )
          )
        / FLOW_M3H.clip(lower=10),
        999
      ),
      [0, 1.5, 2.1, 3, 5.2, 7.7, 11, 15, 22],
      [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
    )
```

### LOG_VIRUS

```python
LOG_VIRUS =
    np.interp(
      np.minimum(
        43228.091
        * (np.minimum(UV_INTENSITY_1_WM2, UV_INTENSITY_2_WM2) / 250)
        * (
            (
              (
                1
                - np.power(
                    10,
                    -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 6
                  )
              )
              / (
                  (-np.log10(UVT_PCT / 100)).clip(lower=0.0001)
                  * 13.815510558
                )
            )
            / np.power(
                10,
                -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3
              )
          )
        / FLOW_M3H.clip(lower=10),
        999
      ),
      [0, 39, 58, 79, 100, 121, 143, 163, 186],
      [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
    )
```

### OFFSPEC_MONTH_PCT

```python
OFFSPEC_MONTH_PCT =
    (OFFSPEC_MONTH_M3 / VOLUME_MONTH_M3.clip(lower=1) * 100)
```

### ENERGY_KWH_PER_M3

```python
ENERGY_KWH_PER_M3 =
    LAMP_POWER_KW / FLOW_M3H.clip(lower=1)
```

## AlertExpression rules (12)

### UV_LOW_DOSE

High

```python
UV_LOW_DOSE =
    (
      np.minimum(
        43228.091
        * (np.minimum(UV_INTENSITY_1_WM2, UV_INTENSITY_2_WM2) / 250)
        * (
            (
              (
                1
                - np.power(
                    10,
                    -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 6
                  )
              )
              / (
                  (-np.log10(UVT_PCT / 100)).clip(lower=0.0001)
                  * 13.815510558
                )
            )
            / np.power(
                10,
                -(-np.log10(UVT_PCT / 100)).clip(lower=0.0001) * 3
              )
          )
        / FLOW_M3H.clip(lower=10),
        999
      )
      < 40
    )
    & (FLOW_M3H > 25)
```

### UV_OFF_SPEC_MONTH

High

```python
UV_OFF_SPEC_MONTH =
    OFFSPEC_MONTH_PCT > 5
```

### UV_LOW_UVT

High · uvt_drop

```python
UV_LOW_UVT =
    UVT_PCT < 80
```

### UV_HIGH_FLOW

High · high_flow

```python
UV_HIGH_FLOW =
    FLOW_M3H > 800
```

### UV_LAMP_FAILURE

High · lamp_failure

```python
UV_LAMP_FAILURE =
    (LAMPS_ON < 12) & (REACTOR_STATUS != 2)
```

### UV_LAMP_END_OF_LIFE

Low · lamp_end_of_life

```python
UV_LAMP_END_OF_LIFE =
    LAMP_HOURS > 12000
```

### UV_SLEEVE_FOULING

Medium · sleeve_fouling

```python
UV_SLEEVE_FOULING =
    (INTENSITY_RATIO < 0.85) & (LAMPS_ON > 0) & (REACTOR_STATUS != 2)
```

### UV_WIPER_FAULT

Medium · sleeve_fouling

```python
UV_WIPER_FAULT =
    WIPER_STATUS == 2
```

### UV_SENSOR_DRIFT

Medium · sensor_drift

```python
UV_SENSOR_DRIFT =
    ((SENSOR_RATIO - 1).abs() > 0.1)
    & (LAMPS_ON == 12)
    & (REACTOR_STATUS != 2)
```

### UV_BALLAST_FAULT

Medium · ballast_fault

```python
UV_BALLAST_FAULT =
    ((BALLAST_DEV_PCT < -10) & (LAMPS_ON > 0) & (BALLAST_POWER_PCT > 0))
    | (BALLAST_TEMP_C > 60)
```

### UV_NO_FLOW

Medium · no_flow_overheat

```python
UV_NO_FLOW =
    (FLOW_M3H < 25) & (LAMPS_ON > 0)
```

### UV_OVERHEAT

Critical · no_flow_overheat

```python
UV_OVERHEAT =
    (REACTOR_TEMP_C > 45) | (REACTOR_STATUS == 2)
```
