# TM-5401: Maximo Monitor functions and alert rules

Device type `TRACTION_MOTOR_TCMS`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### WHEEL_SPEED_KMH

```python
WHEEL_SPEED_KMH =
    (MOTOR_RPM * 4.71238898038e-05 * WHEEL_D_MM)
```

### CREEP_PCT

```python
CREEP_PCT =
    ((WHEEL_SPEED_KMH - SPEED_KMH) / np.maximum(SPEED_KMH, 5) * 100)
```

### CREEP_NET_PCT

```python
CREEP_NET_PCT =
    (CREEP_PCT - CREEP_COAST_PCT)
```

### TE_AVAILABLE_KN

```python
TE_AVAILABLE_KN =
    np.minimum(80, 5760 / np.maximum(SPEED_KMH, 1))
```

### TE_EXPECTED_KN

```python
TE_EXPECTED_KN =
    (DEMAND_PCT / 100 * np.minimum(80, 5760 / np.maximum(SPEED_KMH, 1)))
```

### TE_MEASURED_KN

```python
TE_MEASURED_KN =
    (MOTOR_TORQUE_KNM * 7840 / WHEEL_D_MM)
```

### TE_RATIO

```python
TE_RATIO =
    np.where(
      TE_EXPECTED_KN > 10,
      TE_MEASURED_KN / np.maximum(TE_EXPECTED_KN, 10),
      1
    )
```

### CURRENT_EXPECTED_A

```python
CURRENT_EXPECTED_A =
    np.sqrt(
      (150 * np.minimum(1, 1267.96 / np.maximum(MOTOR_RPM, 1))) ** 2
      + (
          41.341
          * np.maximum(1, np.maximum(MOTOR_RPM, 1) / 1267.96)
          * np.abs(MOTOR_TORQUE_KNM)
        )
        ** 2
    )
```

### CURRENT_RATIO

```python
CURRENT_RATIO =
    MOTOR_CURRENT_A
    / np.sqrt(
        (150 * np.minimum(1, 1267.96 / np.maximum(MOTOR_RPM, 1))) ** 2
        + (
            41.341
            * np.maximum(1, np.maximum(MOTOR_RPM, 1) / 1267.96)
            * np.abs(MOTOR_TORQUE_KNM)
          )
          ** 2
      )
```

### STATOR_EXPECTED_C

```python
STATOR_EXPECTED_C =
    (
      AIR_IN_C
      + 125
        * (CURRENT_RMS30_A / 530) ** 2
        * (100 / np.maximum(BLOWER_FLOW_PCT, 10)) ** 0.8
    )
```

### STATOR_RESIDUAL_K

```python
STATOR_RESIDUAL_K =
    STATOR_C - STATOR_EXPECTED_C
```

### AGING_RATE

```python
AGING_RATE =
    (2 ** ((STATOR_C + 10 - 150) / 10))
```

### BEARING_DE_EXPECTED_C

```python
BEARING_DE_EXPECTED_C =
    (AIR_IN_C + 0.0113568609636 * RPM_AVG30)
```

### BEARING_DE_RESIDUAL_K

```python
BEARING_DE_RESIDUAL_K =
    BEARING_DE_C - BEARING_DE_EXPECTED_C
```

### BPFO_HZ

```python
BPFO_HZ =
    MOTOR_RPM * 0.0970175438596
```

### IR_40C_MOHM

```python
IR_40C_MOHM =
    IR_MOHM * 2 ** ((IR_TEMP_C - 40) / 10)
```

### IGBT_BASEPLATE_EXPECTED_C

```python
IGBT_BASEPLATE_EXPECTED_C =
    (
      COOLANT_C
      + 30
        * (0.4 * (CURRENT_RMS5_A / 530) + 0.6 * (CURRENT_RMS5_A / 530) ** 2)
    )
```

### IGBT_BASEPLATE_RESIDUAL_K

```python
IGBT_BASEPLATE_RESIDUAL_K =
    IGBT_BASEPLATE_C - IGBT_BASEPLATE_EXPECTED_C
```

### IGBT_CYCLES_TO_FAILURE

```python
IGBT_CYCLES_TO_FAILURE =
    (
      302500
      * IGBT_TJ_SWING_K ** -5.039
      * np.exp(7163.29784036 / (IGBT_TJ_MEAN_C + 273.15))
    )
```

### IGBT_LIFE_YEARS

```python
IGBT_LIFE_YEARS =
    (IGBT_CYCLES_TO_FAILURE / (np.maximum(IGBT_CYCLES_DAY, 1) * 365))
```

## AlertExpression rules (13)

### TM_TE_SHORTFALL

High · rotor_cage_damage

```python
TM_TE_SHORTFALL =
    (TE_EXPECTED_KN > 10)
    & ((TE_MEASURED_KN / np.maximum(TE_EXPECTED_KN, 10)) < 0.85)
    & (CREEP_NET_PCT <= 3)
```

### TM_INSULATION_LOW

High · insulation_moisture

```python
TM_INSULATION_LOW =
    IR_40C_MOHM < 100
```

### TM_BEARING_HOT

High · bearing_lubrication

```python
TM_BEARING_HOT =
    BEARING_DE_RESIDUAL_K > 20
```

### TM_IGBT_HOT

High · inverter_cooling

```python
TM_IGBT_HOT =
    IGBT_BASEPLATE_RESIDUAL_K > 10
```

### TM_AGING_FAST

Medium · cooling_ducts_blocked

```python
TM_AGING_FAST =
    AGING_RATE > 2
```

### TM_WINDING_RESIDUAL

Medium · cooling_ducts_blocked

```python
TM_WINDING_RESIDUAL =
    (STATOR_RESIDUAL_K > 15) & (CURRENT_RMS30_A > 159)
```

### TM_VENT_FLOW_LOW

Medium · blower_degraded

```python
TM_VENT_FLOW_LOW =
    BLOWER_FLOW_PCT < 70
```

### TM_BEARING_ENVELOPE

Medium · bearing_outer_race

```python
TM_BEARING_ENVELOPE =
    ENV_BPFO_G > 1.5
```

### TM_WHEEL_SLIP

Medium · low_adhesion

```python
TM_WHEEL_SLIP =
    (CREEP_NET_PCT > 3) & (DEMAND_PCT > 5)
```

### TM_SLIP_EVENTS

Medium · low_adhesion

```python
TM_SLIP_EVENTS =
    SLIP_EVENTS_100KM > 5
```

### TM_CURRENT_HIGH

Medium · rotor_cage_damage

```python
TM_CURRENT_HIGH =
    (CURRENT_RATIO > 1.15) & (np.abs(MOTOR_TORQUE_KNM) > 2.45918)
```

### TM_IGBT_LIFE_SHORT

Medium · inverter_cooling

```python
TM_IGBT_LIFE_SHORT =
    IGBT_LIFE_YEARS < 30
```

### TM_CREEP_OFFSET

Low

```python
TM_CREEP_OFFSET =
    np.abs(CREEP_COAST_PCT) > 1.5
```
