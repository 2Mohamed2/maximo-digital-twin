# MBR-5301: Maximo Monitor functions and alert rules

Device type `MBR_MEMBRANE_TRAIN`. Generated from the twin file by `twin_calc.py` (`monitor_expressions()` and `alert_rules()`); the same code computes these numbers in Python. Shown readable: column names without `df['...']`, rounding noise removed from decimals, one operator per line, and the name of another function inside a formula stands for that function's formula. Monitor stores each expression on one line, written out in full.

## PythonExpression functions (18)

### FLUX_LMH

```python
FLUX_LMH =
    (PERMEATE_FLOW_M3H * 1000 / (1920 * CASSETTES_IN_SERVICE))
```

### FLUX_RATIO

```python
FLUX_RATIO =
    FLUX_LMH / 25
```

### TCF

```python
TCF =
    np.exp(507.88 / (ML_TEMP_C + 123.85) - 3.53062217588)
```

### PERM_LMH_BAR

```python
PERM_LMH_BAR =
    FLUX_LMH / (TMP_KPA / 100)
```

### PERM20_LMH_BAR

```python
PERM20_LMH_BAR =
    (
      FLUX_LMH
      / (TMP_KPA / 100)
      * np.exp(507.88 / (ML_TEMP_C + 123.85) - 3.53062217588)
    )
```

### PERM20_RATIO

```python
PERM20_RATIO =
    PERM20_LMH_BAR / 250
```

### TMP_CLEAN_KPA

```python
TMP_CLEAN_KPA =
    FLUX_LMH
    * np.exp(507.88 / (ML_TEMP_C + 123.85) - 3.53062217588)
    / RC_PERM20_LMHBAR
    * 100
```

### TMP_MARGIN_KPA

```python
TMP_MARGIN_KPA =
    55 - TMP_KPA
```

### PERM20_AFTER_MC

```python
PERM20_AFTER_MC =
    (
      MC_FLUX_LMH
      / (MC_TMP_AFTER_KPA / 100)
      * np.exp(507.88 / (MC_TEMP_C + 123.85) - 3.53062217588)
    )
```

### FOULING_RATE_PCT_D

```python
FOULING_RATE_PCT_D =
    (
      (
        (PERM20_AFTER_MC - PERM20_LMH_BAR)
        / (np.maximum(HOURS_SINCE_MC, 24) / 24)
      )
      / PERM20_AFTER_MC
      * 100
    )
```

### DAYS_TO_RC

```python
DAYS_TO_RC =
    (
      (PERM20_LMH_BAR - 100)
      / np.maximum(
          (
            (PERM20_AFTER_MC - PERM20_LMH_BAR)
            / (np.maximum(HOURS_SINCE_MC, 24) / 24)
          ),
          0.01
        )
    )
```

### MC_RECOVERY_PCT

```python
MC_RECOVERY_PCT =
    ((MC_TMP_BEFORE_KPA / MC_TMP_AFTER_KPA - 1) * 100)
```

### IRREVERSIBLE_LOSS_PCT

```python
IRREVERSIBLE_LOSS_PCT =
    ((1 - RC_PERM20_LMHBAR / 250) * 100)
```

### REVERSIBLE_LOSS_PCT

```python
REVERSIBLE_LOSS_PCT =
    (1 - PERM20_LMH_BAR / RC_PERM20_LMHBAR) * 100
```

### SADM

```python
SADM =
    (AIR_SCOUR_NM3H / (1920 * CASSETTES_IN_SERVICE))
```

### SADM_RATIO

```python
SADM_RATIO =
    SADM / 0.25
```

### SADP

```python
SADP =
    AIR_SCOUR_NM3H / PERMEATE_FLOW_M3H
```

### SPEC_ENERGY_KWH_M3

```python
SPEC_ENERGY_KWH_M3 =
    (SCOUR_BLOWER_KW + PERMEATE_PUMP_KW) / PERMEATE_FLOW_M3H
```

## AlertExpression rules (15)

### MBR_INTEGRITY_BREACH

Critical · fibre_breakage

```python
MBR_INTEGRITY_BREACH =
    PERMEATE_TURBIDITY_NTU > 0.5
```

### MBR_TMP_HIGH

High · sludging

```python
MBR_TMP_HIGH =
    TMP_KPA > 40
```

### MBR_PERM_VERY_LOW

High · sludging

```python
MBR_PERM_VERY_LOW =
    PERM20_LMH_BAR < 70
```

### MBR_SCOUR_LOW

High · air_scour_low

```python
MBR_SCOUR_LOW =
    SADM / 0.25 < 0.8
```

### MBR_PERM_LOW

Medium · irreversible_fouling

```python
MBR_PERM_LOW =
    (PERM20_LMH_BAR >= 70) & (PERM20_LMH_BAR < 100)
```

### MBR_CLEAN_DUE_SOON

Medium · poor_filterability

```python
MBR_CLEAN_DUE_SOON =
    (PERM20_LMH_BAR >= 100) & (DAYS_TO_RC < 7)
```

### MBR_FOULING_FAST

Medium · poor_filterability

```python
MBR_FOULING_FAST =
    FOULING_RATE_PCT_D > 4
```

### MBR_MC_INEFFECTIVE

Medium · irreversible_fouling

```python
MBR_MC_INEFFECTIVE =
    MC_RECOVERY_PCT < 5
```

### MBR_IRREVERSIBLE_HIGH

Medium · irreversible_fouling

```python
MBR_IRREVERSIBLE_HIGH =
    IRREVERSIBLE_LOSS_PCT > 30
```

### MBR_FLUX_HIGH

Medium · peak_flux

```python
MBR_FLUX_HIGH =
    FLUX_LMH / 25 > 1.15
```

### MBR_TURBIDITY_HIGH

Medium · fibre_breakage

```python
MBR_TURBIDITY_HIGH =
    (PERMEATE_TURBIDITY_NTU > 0.2) & (PERMEATE_TURBIDITY_NTU <= 0.5)
```

### MBR_MLSS_HIGH

Medium · sludging

```python
MBR_MLSS_HIGH =
    MLSS_MGL > 12000
```

### MBR_FILTERABILITY_POOR

Medium · poor_filterability

```python
MBR_FILTERABILITY_POOR =
    SLUDGE_TTF_S > 100
```

### MBR_MC_OVERDUE

Medium · mc_skipped

```python
MBR_MC_OVERDUE =
    HOURS_SINCE_MC > 252
```

### MBR_RC_OVERDUE

Low

```python
MBR_RC_OVERDUE =
    HOURS_SINCE_RC > 5475
```
