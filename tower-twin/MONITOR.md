# CT-301: Maximo Monitor functions and alert rules

Device type `COOLING_TOWER_CLOSED`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (14)

### Q_EXPECTED_KW

```python
Q_EXPECTED_KW =
    (
      (
        1
        - np.exp(
            -(
               (
                 107.676
                 * ((45.49 * FAN_SPEED_PCT.clip(lower=1) / 100) / 45.49)
                   ** 0.6
                 * (FLUID_FLOW_M3H.clip(lower=0.1) / 89.26) ** 0.2
               )
               / np.minimum(
                   (
                     (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                     * (
                         (
                           (
                             1.006 * FLUID_IN_TEMP_C
                             + 0.622
                               * (
                                   0.61094
                                   * np.exp(
                                       17.625
                                       * FLUID_IN_TEMP_C
                                       / (FLUID_IN_TEMP_C + 243.04)
                                     )
                                 )
                               / (
                                   101.325
                                   - (
                                       0.61094
                                       * np.exp(
                                           17.625
                                           * FLUID_IN_TEMP_C
                                           / (FLUID_IN_TEMP_C + 243.04)
                                         )
                                     )
                                 )
                               * (2501 + 1.86 * FLUID_IN_TEMP_C)
                           )
                           - (
                               1.006 * AMBIENT_WET_BULB_C
                               + 0.622
                                 * (
                                     0.61094
                                     * np.exp(
                                         17.625
                                         * AMBIENT_WET_BULB_C
                                         / (AMBIENT_WET_BULB_C + 243.04)
                                       )
                                   )
                                 / (
                                     101.325
                                     - (
                                         0.61094
                                         * np.exp(
                                             17.625
                                             * AMBIENT_WET_BULB_C
                                             / (AMBIENT_WET_BULB_C + 243.04)
                                           )
                                       )
                                   )
                                 * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                             )
                         )
                         / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                       )
                   ),
                   (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
                 )
             )
            * (
                1
                - (
                    np.minimum(
                      (
                        (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                        * (
                            (
                              (
                                1.006 * FLUID_IN_TEMP_C
                                + 0.622
                                  * (
                                      0.61094
                                      * np.exp(
                                          17.625
                                          * FLUID_IN_TEMP_C
                                          / (FLUID_IN_TEMP_C + 243.04)
                                        )
                                    )
                                  / (
                                      101.325
                                      - (
                                          0.61094
                                          * np.exp(
                                              17.625
                                              * FLUID_IN_TEMP_C
                                              / (FLUID_IN_TEMP_C + 243.04)
                                            )
                                        )
                                    )
                                  * (2501 + 1.86 * FLUID_IN_TEMP_C)
                              )
                              - (
                                  1.006 * AMBIENT_WET_BULB_C
                                  + 0.622
                                    * (
                                        0.61094
                                        * np.exp(
                                            17.625
                                            * AMBIENT_WET_BULB_C
                                            / (AMBIENT_WET_BULB_C + 243.04)
                                          )
                                      )
                                    / (
                                        101.325
                                        - (
                                            0.61094
                                            * np.exp(
                                                17.625
                                                * AMBIENT_WET_BULB_C
                                                / (
                                                    AMBIENT_WET_BULB_C
                                                    + 243.04
                                                  )
                                              )
                                          )
                                      )
                                    * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                                )
                            )
                            / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                          )
                      ),
                      (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
                    )
                    / np.maximum(
                        (
                          (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                          * (
                              (
                                (
                                  1.006 * FLUID_IN_TEMP_C
                                  + 0.622
                                    * (
                                        0.61094
                                        * np.exp(
                                            17.625
                                            * FLUID_IN_TEMP_C
                                            / (FLUID_IN_TEMP_C + 243.04)
                                          )
                                      )
                                    / (
                                        101.325
                                        - (
                                            0.61094
                                            * np.exp(
                                                17.625
                                                * FLUID_IN_TEMP_C
                                                / (FLUID_IN_TEMP_C + 243.04)
                                              )
                                          )
                                      )
                                    * (2501 + 1.86 * FLUID_IN_TEMP_C)
                                )
                                - (
                                    1.006 * AMBIENT_WET_BULB_C
                                    + 0.622
                                      * (
                                          0.61094
                                          * np.exp(
                                              17.625
                                              * AMBIENT_WET_BULB_C
                                              / (
                                                  AMBIENT_WET_BULB_C
                                                  + 243.04
                                                )
                                            )
                                        )
                                      / (
                                          101.325
                                          - (
                                              0.61094
                                              * np.exp(
                                                  17.625
                                                  * AMBIENT_WET_BULB_C
                                                  / (
                                                      AMBIENT_WET_BULB_C
                                                      + 243.04
                                                    )
                                                )
                                            )
                                        )
                                      * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                                  )
                              )
                              / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                            )
                        ),
                        (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
                      )
                  ).clip(upper=0.995)
              )
          )
      )
      / (
          1
          - (
              np.minimum(
                (
                  (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                  * (
                      (
                        (
                          1.006 * FLUID_IN_TEMP_C
                          + 0.622
                            * (
                                0.61094
                                * np.exp(
                                    17.625
                                    * FLUID_IN_TEMP_C
                                    / (FLUID_IN_TEMP_C + 243.04)
                                  )
                              )
                            / (
                                101.325
                                - (
                                    0.61094
                                    * np.exp(
                                        17.625
                                        * FLUID_IN_TEMP_C
                                        / (FLUID_IN_TEMP_C + 243.04)
                                      )
                                  )
                              )
                            * (2501 + 1.86 * FLUID_IN_TEMP_C)
                        )
                        - (
                            1.006 * AMBIENT_WET_BULB_C
                            + 0.622
                              * (
                                  0.61094
                                  * np.exp(
                                      17.625
                                      * AMBIENT_WET_BULB_C
                                      / (AMBIENT_WET_BULB_C + 243.04)
                                    )
                                )
                              / (
                                  101.325
                                  - (
                                      0.61094
                                      * np.exp(
                                          17.625
                                          * AMBIENT_WET_BULB_C
                                          / (AMBIENT_WET_BULB_C + 243.04)
                                        )
                                    )
                                )
                              * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                          )
                      )
                      / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                    )
                ),
                (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
              )
              / np.maximum(
                  (
                    (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                    * (
                        (
                          (
                            1.006 * FLUID_IN_TEMP_C
                            + 0.622
                              * (
                                  0.61094
                                  * np.exp(
                                      17.625
                                      * FLUID_IN_TEMP_C
                                      / (FLUID_IN_TEMP_C + 243.04)
                                    )
                                )
                              / (
                                  101.325
                                  - (
                                      0.61094
                                      * np.exp(
                                          17.625
                                          * FLUID_IN_TEMP_C
                                          / (FLUID_IN_TEMP_C + 243.04)
                                        )
                                    )
                                )
                              * (2501 + 1.86 * FLUID_IN_TEMP_C)
                          )
                          - (
                              1.006 * AMBIENT_WET_BULB_C
                              + 0.622
                                * (
                                    0.61094
                                    * np.exp(
                                        17.625
                                        * AMBIENT_WET_BULB_C
                                        / (AMBIENT_WET_BULB_C + 243.04)
                                      )
                                  )
                                / (
                                    101.325
                                    - (
                                        0.61094
                                        * np.exp(
                                            17.625
                                            * AMBIENT_WET_BULB_C
                                            / (AMBIENT_WET_BULB_C + 243.04)
                                          )
                                      )
                                  )
                                * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                            )
                        )
                        / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                      )
                  ),
                  (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
                )
            ).clip(upper=0.995)
            * np.exp(
                -(
                   (
                     107.676
                     * ((45.49 * FAN_SPEED_PCT.clip(lower=1) / 100) / 45.49)
                       ** 0.6
                     * (FLUID_FLOW_M3H.clip(lower=0.1) / 89.26) ** 0.2
                   )
                   / np.minimum(
                       (
                         (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                         * (
                             (
                               (
                                 1.006 * FLUID_IN_TEMP_C
                                 + 0.622
                                   * (
                                       0.61094
                                       * np.exp(
                                           17.625
                                           * FLUID_IN_TEMP_C
                                           / (FLUID_IN_TEMP_C + 243.04)
                                         )
                                     )
                                   / (
                                       101.325
                                       - (
                                           0.61094
                                           * np.exp(
                                               17.625
                                               * FLUID_IN_TEMP_C
                                               / (FLUID_IN_TEMP_C + 243.04)
                                             )
                                         )
                                     )
                                   * (2501 + 1.86 * FLUID_IN_TEMP_C)
                               )
                               - (
                                   1.006 * AMBIENT_WET_BULB_C
                                   + 0.622
                                     * (
                                         0.61094
                                         * np.exp(
                                             17.625
                                             * AMBIENT_WET_BULB_C
                                             / (AMBIENT_WET_BULB_C + 243.04)
                                           )
                                       )
                                     / (
                                         101.325
                                         - (
                                             0.61094
                                             * np.exp(
                                                 17.625
                                                 * AMBIENT_WET_BULB_C
                                                 / (
                                                     AMBIENT_WET_BULB_C
                                                     + 243.04
                                                   )
                                               )
                                           )
                                       )
                                     * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                                 )
                             )
                             / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                           )
                       ),
                       (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
                     )
                 )
                * (
                    1
                    - (
                        np.minimum(
                          (
                            (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                            * (
                                (
                                  (
                                    1.006 * FLUID_IN_TEMP_C
                                    + 0.622
                                      * (
                                          0.61094
                                          * np.exp(
                                              17.625
                                              * FLUID_IN_TEMP_C
                                              / (FLUID_IN_TEMP_C + 243.04)
                                            )
                                        )
                                      / (
                                          101.325
                                          - (
                                              0.61094
                                              * np.exp(
                                                  17.625
                                                  * FLUID_IN_TEMP_C
                                                  / (
                                                      FLUID_IN_TEMP_C
                                                      + 243.04
                                                    )
                                                )
                                            )
                                        )
                                      * (2501 + 1.86 * FLUID_IN_TEMP_C)
                                  )
                                  - (
                                      1.006 * AMBIENT_WET_BULB_C
                                      + 0.622
                                        * (
                                            0.61094
                                            * np.exp(
                                                17.625
                                                * AMBIENT_WET_BULB_C
                                                / (
                                                    AMBIENT_WET_BULB_C
                                                    + 243.04
                                                  )
                                              )
                                          )
                                        / (
                                            101.325
                                            - (
                                                0.61094
                                                * np.exp(
                                                    17.625
                                                    * AMBIENT_WET_BULB_C
                                                    / (
                                                        AMBIENT_WET_BULB_C
                                                        + 243.04
                                                      )
                                                  )
                                              )
                                          )
                                        * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                                    )
                                )
                                / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                              )
                          ),
                          (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
                        )
                        / np.maximum(
                            (
                              (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
                              * (
                                  (
                                    (
                                      1.006 * FLUID_IN_TEMP_C
                                      + 0.622
                                        * (
                                            0.61094
                                            * np.exp(
                                                17.625
                                                * FLUID_IN_TEMP_C
                                                / (FLUID_IN_TEMP_C + 243.04)
                                              )
                                          )
                                        / (
                                            101.325
                                            - (
                                                0.61094
                                                * np.exp(
                                                    17.625
                                                    * FLUID_IN_TEMP_C
                                                    / (
                                                        FLUID_IN_TEMP_C
                                                        + 243.04
                                                      )
                                                  )
                                              )
                                          )
                                        * (2501 + 1.86 * FLUID_IN_TEMP_C)
                                    )
                                    - (
                                        1.006 * AMBIENT_WET_BULB_C
                                        + 0.622
                                          * (
                                              0.61094
                                              * np.exp(
                                                  17.625
                                                  * AMBIENT_WET_BULB_C
                                                  / (
                                                      AMBIENT_WET_BULB_C
                                                      + 243.04
                                                    )
                                                )
                                            )
                                          / (
                                              101.325
                                              - (
                                                  0.61094
                                                  * np.exp(
                                                      17.625
                                                      * AMBIENT_WET_BULB_C
                                                      / (
                                                          AMBIENT_WET_BULB_C
                                                          + 243.04
                                                        )
                                                    )
                                                )
                                            )
                                          * (
                                              2501
                                              + 1.86 * AMBIENT_WET_BULB_C
                                            )
                                      )
                                  )
                                  / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
                                )
                            ),
                            (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
                          )
                      ).clip(upper=0.995)
                  )
              )
        )
      * np.minimum(
          (
            (45.49 * FAN_SPEED_PCT.clip(lower=1) / 100)
            * (
                (
                  (
                    1.006 * FLUID_IN_TEMP_C
                    + 0.622
                      * (
                          0.61094
                          * np.exp(
                              17.625
                              * FLUID_IN_TEMP_C
                              / (FLUID_IN_TEMP_C + 243.04)
                            )
                        )
                      / (
                          101.325
                          - (
                              0.61094
                              * np.exp(
                                  17.625
                                  * FLUID_IN_TEMP_C
                                  / (FLUID_IN_TEMP_C + 243.04)
                                )
                            )
                        )
                      * (2501 + 1.86 * FLUID_IN_TEMP_C)
                  )
                  - (
                      1.006 * AMBIENT_WET_BULB_C
                      + 0.622
                        * (
                            0.61094
                            * np.exp(
                                17.625
                                * AMBIENT_WET_BULB_C
                                / (AMBIENT_WET_BULB_C + 243.04)
                              )
                          )
                        / (
                            101.325
                            - (
                                0.61094
                                * np.exp(
                                    17.625
                                    * AMBIENT_WET_BULB_C
                                    / (AMBIENT_WET_BULB_C + 243.04)
                                  )
                              )
                          )
                        * (2501 + 1.86 * AMBIENT_WET_BULB_C)
                    )
                )
                / (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
              )
          ),
          (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
        )
      * (FLUID_IN_TEMP_C - AMBIENT_WET_BULB_C).clip(lower=0.05)
    )
```

### FLUID_OUT_EXPECTED_C

```python
FLUID_OUT_EXPECTED_C =
    (
      FLUID_IN_TEMP_C
      - Q_EXPECTED_KW / (1.15647 * FLUID_FLOW_M3H.clip(lower=0.1))
    )
```

### OUT_TEMP_DEVIATION_K

```python
OUT_TEMP_DEVIATION_K =
    FLUID_OUT_TEMP_C - FLUID_OUT_EXPECTED_C
```

### CAPACITY_RATIO_PCT

```python
CAPACITY_RATIO_PCT =
    (1.15647 * FLUID_FLOW_M3H * RANGE_K) / Q_EXPECTED_KW.clip(lower=1) * 100
```

### APPROACH_K

```python
APPROACH_K =
    FLUID_OUT_TEMP_C - AMBIENT_WET_BULB_C
```

### RANGE_K

```python
RANGE_K =
    FLUID_IN_TEMP_C - FLUID_OUT_TEMP_C
```

### FAN_POWER_EXPECTED_KW

```python
FAN_POWER_EXPECTED_KW =
    (10.73 * (FAN_SPEED_PCT.clip(lower=1) / 100) ** 3)
```

### FAN_POWER_DEVIATION_PCT

```python
FAN_POWER_DEVIATION_PCT =
    (FAN_POWER_KW - FAN_POWER_EXPECTED_KW)
    / FAN_POWER_EXPECTED_KW.clip(lower=0.2)
    * 100
```

### BELT_SLIP_PCT

```python
BELT_SLIP_PCT =
    (1 - FAN_RPM / (420 * FAN_SPEED_PCT.clip(lower=1) / 100)) * 100
```

### NOZZLE_K_RATIO

```python
NOZZLE_K_RATIO =
    (SPRAY_PRESSURE_BAR / 0.35)
    / ((SPRAY_FLOW_M3H.clip(lower=1) / 163.3) ** 2)
```

### EVAPORATION_EXPECTED_M3H

```python
EVAPORATION_EXPECTED_M3H =
    (0.9 * (1.15647 * FLUID_FLOW_M3H * RANGE_K).clip(lower=0) / 2430 * 3.6)
```

### UNACCOUNTED_WATER_M3H

```python
UNACCOUNTED_WATER_M3H =
    MAKEUP_FLOW_M3H
    - EVAPORATION_EXPECTED_M3H
    - BLOWDOWN_FLOW_M3H
    - 1e-05 * SPRAY_FLOW_M3H
```

### CYCLES_OF_CONCENTRATION

```python
CYCLES_OF_CONCENTRATION =
    CONDUCTIVITY_US_CM / 500
```

### AUX_KW_PER_KW

```python
AUX_KW_PER_KW =
    (FAN_POWER_KW + SPRAY_PUMP_POWER_KW)
    / (1.15647 * FLUID_FLOW_M3H * RANGE_K).clip(lower=1)
```

## AlertExpression rules (11)

### CT_COIL_SCALING

Medium · coil_scaling

```python
CT_COIL_SCALING =
    (RUNNING > 0)
    & (OUT_TEMP_DEVIATION_K > 1)
    & (NOZZLE_K_RATIO < 1.3)
    & (BELT_SLIP_PCT < 4)
```

### CT_NOZZLE_BLOCKAGE

Medium · nozzle_blockage

```python
CT_NOZZLE_BLOCKAGE =
    (RUNNING > 0) & (NOZZLE_K_RATIO > 1.3)
```

### CT_BELT_SLIP

Medium · belt_slip

```python
CT_BELT_SLIP =
    (RUNNING > 0) & (FAN_SPEED_PCT > 30) & (BELT_SLIP_PCT > 4)
```

### CT_FAN_VIBRATION

Medium · fan_bearing

```python
CT_FAN_VIBRATION =
    (RUNNING > 0) & (FAN_VIB_MM_S > 4.5)
```

### CT_FAN_BEARING_TEMP

High · fan_bearing

```python
CT_FAN_BEARING_TEMP =
    FAN_BEARING_TEMP_C > 80
```

### CT_FAN_MOTOR_IMBALANCE

Medium · fan_motor_winding

```python
CT_FAN_MOTOR_IMBALANCE =
    (RUNNING > 0) & (FAN_CURRENT_IMBALANCE_PCT > 5)
```

### CT_FAN_WINDING_TEMP

High · fan_motor_winding

```python
CT_FAN_WINDING_TEMP =
    FAN_WINDING_TEMP_C > 130
```

### CT_DRIFT_LOSS

Medium · drift_eliminator

```python
CT_DRIFT_LOSS =
    (RUNNING > 0) & (UNACCOUNTED_WATER_M3H > 0.25)
```

### CT_WATER_TREATMENT

Medium · water_treatment

```python
CT_WATER_TREATMENT =
    CONDUCTIVITY_US_CM > 2800
```

### CT_CAPACITY_LIMIT

Low

```python
CT_CAPACITY_LIMIT =
    (RUNNING > 0)
    & (FAN_SPEED_PCT > 98)
    & (FLUID_OUT_TEMP_C > FLUID_OUT_SETPOINT_C + 1.5)
```

### CT_TRIPPED

Critical

```python
CT_TRIPPED =
    TRIP_CODE > 0
```
