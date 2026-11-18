# GEN-3401: Maximo Monitor functions and alert rules

Device type `TURBO_GENERATOR_AIR`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (19)

### APPARENT_POWER_PU

```python
APPARENT_POWER_PU =
    np.sqrt((ACTIVE_POWER_MW / 300) ** 2 + (REACTIVE_POWER_MVAR / 300) ** 2)
```

### STATOR_CURRENT_PU

```python
STATOR_CURRENT_PU =
    (STATOR_CURRENT_A / 10997.147985)
```

### INTERNAL_EMF_PU

```python
INTERNAL_EMF_PU =
    np.sqrt(
      (
        (TERMINAL_VOLTAGE_KV / 15.75)
        + (REACTIVE_POWER_MVAR / 300) * 2 / (TERMINAL_VOLTAGE_KV / 15.75)
      )
      ** 2
      + ((ACTIVE_POWER_MW / 300) * 2 / (TERMINAL_VOLTAGE_KV / 15.75)) ** 2
    )
```

### LOAD_ANGLE_DEG

```python
LOAD_ANGLE_DEG =
    (
      np.degrees(
        np.arctan2(
          ((ACTIVE_POWER_MW / 300) * 2 / (TERMINAL_VOLTAGE_KV / 15.75)),
          (
            (TERMINAL_VOLTAGE_KV / 15.75)
            + (REACTIVE_POWER_MVAR / 300)
              * 2
              / (TERMINAL_VOLTAGE_KV / 15.75)
          )
        )
      )
    )
```

### FIELD_CURRENT_EXPECTED_A

```python
FIELD_CURRENT_EXPECTED_A =
    (
      845.496815
      * np.sqrt(
          (
            (TERMINAL_VOLTAGE_KV / 15.75)
            + (REACTIVE_POWER_MVAR / 300)
              * 2
              / (TERMINAL_VOLTAGE_KV / 15.75)
          )
          ** 2
          + ((ACTIVE_POWER_MW / 300) * 2 / (TERMINAL_VOLTAGE_KV / 15.75))
            ** 2
        )
    )
```

### FIELD_CURRENT_RATIO

```python
FIELD_CURRENT_RATIO =
    FIELD_CURRENT_A / FIELD_CURRENT_EXPECTED_A
```

### FIELD_CURRENT_PU

```python
FIELD_CURRENT_PU =
    FIELD_CURRENT_A / 2300
```

### ROTOR_TEMP_C

```python
ROTOR_TEMP_C =
    (FIELD_VOLTAGE_V / FIELD_CURRENT_A / 0.13 * (235 + 20) - 235)
```

### STATOR_RTD_EXPECTED_C

```python
STATOR_RTD_EXPECTED_C =
    (
      COLD_AIR_C
      + 12 * (TERMINAL_VOLTAGE_KV / 15.75) ** 2
      + 55 * (STATOR_CURRENT_A / 10997.147985) ** 2
    )
```

### STATOR_RTD_RESIDUAL_K

```python
STATOR_RTD_RESIDUAL_K =
    STATOR_RTD_MAX_C - STATOR_RTD_EXPECTED_C
```

### STATOR_RTD_SPREAD_K

```python
STATOR_RTD_SPREAD_K =
    STATOR_RTD_MAX_C - STATOR_RTD_MEAN_C
```

### STATOR_HEADROOM_K

```python
STATOR_HEADROOM_K =
    121 - STATOR_RTD_MAX_C
```

### THERMAL_AGEING_RATE

```python
THERMAL_AGEING_RATE =
    2 ** ((STATOR_RTD_MAX_C - 121) / 10)
```

### HOT_AIR_EXPECTED_C

```python
HOT_AIR_EXPECTED_C =
    COLD_AIR_C + 8 + 16 * (STATOR_CURRENT_A / 10997.147985) ** 2
```

### HOT_AIR_RESIDUAL_K

```python
HOT_AIR_RESIDUAL_K =
    HOT_AIR_C - HOT_AIR_EXPECTED_C
```

### COOLER_APPROACH_K

```python
COOLER_APPROACH_K =
    COLD_AIR_C - COOLER_WATER_IN_C
```

### PD_TREND_RATIO

```python
PD_TREND_RATIO =
    PD_QM_MV / PD_QM_6MO_MV
```

### BEARING_TEMP_EXPECTED_C

```python
BEARING_TEMP_EXPECTED_C =
    (OIL_IN_C + 28 + 4 * ACTIVE_POWER_MW / 240)
```

### BEARING_TEMP_RESIDUAL_K

```python
BEARING_TEMP_RESIDUAL_K =
    np.maximum(BRG_DE_TEMP_C, BRG_NDE_TEMP_C) - BEARING_TEMP_EXPECTED_C
```

## AlertExpression rules (15)

### GEN_ROTOR_TEMP_HIGH

High · over_excitation

```python
GEN_ROTOR_TEMP_HIGH =
    ROTOR_TEMP_C > 130
```

### GEN_STATOR_TEMP_LIMIT

High · over_excitation

```python
GEN_STATOR_TEMP_LIMIT =
    STATOR_RTD_MAX_C > 121
```

### GEN_LOAD_ANGLE_HIGH

High · under_excitation

```python
GEN_LOAD_ANGLE_HIGH =
    LOAD_ANGLE_DEG > 70
```

### GEN_ROTOR_OVERLOAD

High · over_excitation

```python
GEN_ROTOR_OVERLOAD =
    FIELD_CURRENT_A / 2300 > 1
```

### GEN_PD_HIGH

High · stator_insulation_pd

```python
GEN_PD_HIGH =
    PD_QM_MV > 400
```

### GEN_VIB_HIGH

High · bearing_wear

```python
GEN_VIB_HIGH =
    np.maximum(VIB_DE_UM, VIB_NDE_UM) > 120
```

### GEN_STATOR_OVERLOAD

Medium · over_excitation

```python
GEN_STATOR_OVERLOAD =
    (STATOR_CURRENT_A / 10997.147985) > 1
```

### GEN_STATOR_RESIDUAL

Medium · stator_vent_blockage

```python
GEN_STATOR_RESIDUAL =
    STATOR_RTD_RESIDUAL_K > 8
```

### GEN_RTD_SPREAD

Medium · stator_vent_blockage

```python
GEN_RTD_SPREAD =
    STATOR_RTD_SPREAD_K > 12
```

### GEN_COLD_AIR_HIGH

Medium · cooler_fouling

```python
GEN_COLD_AIR_HIGH =
    COLD_AIR_C > 40
```

### GEN_COOLER_APPROACH

Medium · cooler_fouling

```python
GEN_COOLER_APPROACH =
    COOLER_APPROACH_K > 12
```

### GEN_PD_TREND

Medium · stator_insulation_pd

```python
GEN_PD_TREND =
    (PD_QM_MV / PD_QM_6MO_MV > 2) & (PD_QM_MV > 150)
```

### GEN_FIELD_CURRENT_HIGH

Medium · rotor_shorted_turns

```python
GEN_FIELD_CURRENT_HIGH =
    FIELD_CURRENT_A / FIELD_CURRENT_EXPECTED_A > 1.04
```

### GEN_SHORTED_TURNS

Medium · rotor_shorted_turns

```python
GEN_SHORTED_TURNS =
    SHORTED_TURNS > 0.5
```

### GEN_BEARING_TEMP

Medium · bearing_wear

```python
GEN_BEARING_TEMP =
    BEARING_TEMP_RESIDUAL_K > 8
```
