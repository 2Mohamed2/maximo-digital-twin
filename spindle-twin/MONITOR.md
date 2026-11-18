# MC-4801: Maximo Monitor functions and alert rules

Device type `CNC_MOTOR_SPINDLE`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (20)

### CUT_SPEED_M_MIN

```python
CUT_SPEED_M_MIN =
    np.pi * TOOL_DIAMETER_MM * SPEED_RPM / 1000
```

### FEED_PER_TOOTH_MM

```python
FEED_PER_TOOTH_MM =
    (FEED_MM_MIN / (np.maximum(SPEED_RPM, 1) * TOOL_TEETH))
```

### CHIP_THICK_MEAN_MM

```python
CHIP_THICK_MEAN_MM =
    np.maximum(
      2
      * FEED_PER_TOOTH_MM
      * np.maximum(AE_MM, 0.01)
      / (
          TOOL_DIAMETER_MM
          * np.arccos(
              np.clip(
                1 - 2 * np.maximum(AE_MM, 0.01) / TOOL_DIAMETER_MM,
                -1,
                1
              )
            )
        ),
      0.0001
    )
```

### KC_N_MM2

```python
KC_N_MM2 =
    (
      1700
      * np.maximum(
          2
          * FEED_PER_TOOTH_MM
          * np.maximum(AE_MM, 0.01)
          / (
              TOOL_DIAMETER_MM
              * np.arccos(
                  np.clip(
                    1 - 2 * np.maximum(AE_MM, 0.01) / TOOL_DIAMETER_MM,
                    -1,
                    1
                  )
                )
            ),
          0.0001
        )
        ** (-0.25)
      * (1 - TOOL_RAKE_DEG / 100)
    )
```

### MRR_CM3_MIN

```python
MRR_CM3_MIN =
    IN_CUT * AP_MM * AE_MM * FEED_MM_MIN / 1000
```

### CUT_POWER_KW

```python
CUT_POWER_KW =
    (AE_MM * AP_MM * FEED_MM_MIN * KC_N_MM2 / 60000000)
```

### IDLE_POWER_KW

```python
IDLE_POWER_KW =
    (0.25 + 0.03 * SPEED_RPM / 1000 + 0.004 * (SPEED_RPM / 1000) ** 2)
```

### POWER_EXPECTED_KW

```python
POWER_EXPECTED_KW =
    (IN_CUT * CUT_POWER_KW / 0.9 + IDLE_POWER_KW)
```

### POWER_RATIO

```python
POWER_RATIO =
    (POWER_KW / np.maximum(POWER_EXPECTED_KW, 0.5))
```

### POWER_AVAILABLE_KW

```python
POWER_AVAILABLE_KW =
    np.minimum(40, 85 * 2 * np.pi * SPEED_RPM / 60 / 1000)
```

### SPINDLE_TORQUE_NM

```python
SPINDLE_TORQUE_NM =
    POWER_KW * 30000 / (np.pi * np.maximum(SPEED_RPM, 1))
```

### FRONT_BRG_RESIDUAL_C

```python
FRONT_BRG_RESIDUAL_C =
    (FRONT_BRG_TEMP_C - (COOLANT_IN_C + 4 + 1 * SPEED_AVG_RPM / 1000))
```

### REAR_BRG_RESIDUAL_C

```python
REAR_BRG_RESIDUAL_C =
    (REAR_BRG_TEMP_C - (COOLANT_IN_C + 3 + 0.8 * SPEED_AVG_RPM / 1000))
```

### MOTOR_TEMP_RESIDUAL_C

```python
MOTOR_TEMP_RESIDUAL_C =
    (MOTOR_TEMP_C - (COOLANT_IN_C + 5 + 1.2 * POWER_AVG_KW))
```

### GROWTH_RESIDUAL_UM

```python
GROWTH_RESIDUAL_UM =
    (Z_GROWTH_UM - (2 + 2.2 * SPEED_AVG_RPM / 1000))
```

### BPFO_HZ

```python
BPFO_HZ =
    9.249126 * SPEED_RPM / 60
```

### ENV_RATIO

```python
ENV_RATIO =
    (VIB_ENV_G / (0.3 + 0.5 * SPEED_RPM / 20000))
```

### VIB_1X_RATIO

```python
VIB_1X_RATIO =
    (VIB_1X_MMS / (0.2 + 0.6 * (SPEED_RPM / 10000) ** 2))
```

### UNBALANCE_PERMISSIBLE_GMM

```python
UNBALANCE_PERMISSIBLE_GMM =
    9549 * 2.5 * TOOL_MASS_KG / np.maximum(SPEED_RPM, 1)
```

### CLAMP_FORCE_RATIO

```python
CLAMP_FORCE_RATIO =
    CLAMP_FORCE_KN / 18
```

## AlertExpression rules (13)

### SP_CRASH

Critical · spindle_crash

```python
SP_CRASH =
    SHOCK_MAX_G_24H > 10
```

### SP_CLAMP_FORCE_LOW

High · clamping_force_loss

```python
SP_CLAMP_FORCE_LOW =
    (CLAMP_FORCE_KN / 18) < 0.7
```

### SP_BRG_ENV

High · bearing_damage

```python
SP_BRG_ENV =
    (SPEED_RPM > 100) & (ENV_RATIO > 3)
```

### SP_OILAIR_LOW

High · lubrication_starvation

```python
SP_OILAIR_LOW =
    OILAIR_PRESSURE_BAR < 3.5
```

### SP_COOLING_FLOW_LOW

High · cooling_failure

```python
SP_COOLING_FLOW_LOW =
    COOLANT_FLOW_LPM < 5
```

### SP_POWER_ABOVE_AVAILABLE

High

```python
SP_POWER_ABOVE_AVAILABLE =
    (SPEED_RPM > 100)
    & (POWER_KW > np.minimum(40, 85 * 2 * np.pi * SPEED_RPM / 60 / 1000))
```

### SP_FRONT_BRG_TEMP

Medium · bearing_damage

```python
SP_FRONT_BRG_TEMP =
    FRONT_BRG_RESIDUAL_C > 6
```

### SP_REAR_BRG_TEMP

Medium · lubrication_starvation

```python
SP_REAR_BRG_TEMP =
    REAR_BRG_RESIDUAL_C > 6
```

### SP_MOTOR_TEMP

Medium · cooling_failure

```python
SP_MOTOR_TEMP =
    MOTOR_TEMP_RESIDUAL_C > 10
```

### SP_THERMAL_GROWTH

Medium · cooling_failure

```python
SP_THERMAL_GROWTH =
    GROWTH_RESIDUAL_UM > 8
```

### SP_IMBALANCE

Medium · tool_imbalance

```python
SP_IMBALANCE =
    (SPEED_RPM > 100) & (VIB_1X_RATIO > 2.5)
```

### SP_CLAMP_FORCE_WARN

Medium · clamping_force_loss

```python
SP_CLAMP_FORCE_WARN =
    ((CLAMP_FORCE_KN / 18) < 0.85) & ((CLAMP_FORCE_KN / 18) >= 0.7)
```

### SP_TOOL_WEAR

Medium · tool_wear

```python
SP_TOOL_WEAR =
    (SPEED_RPM > 100)
    & (IN_CUT > 0.5)
    & (CUT_POWER_KW >= 1.5)
    & (POWER_RATIO > 1.3)
```
