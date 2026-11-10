# Digital Twin for Maximo

Code that goes with six IBM Community posts on building physics-based digital twins of Maximo assets
with standard Maximo Monitor and Maximo Manage features:

| Asset | Twin folder | Post |
|---|---|---|
| PUMP-101, KSB Etanorm R 200-500 centrifugal pump | `pump-twin` | A pump that knows its own curve |
| CH-201, BITZER screw chiller | `chiller-twin` | A chiller that knows its compressor map |
| CT-301, BAC FXV closed-circuit cooling tower | `tower-twin` | A cooling tower that knows the weather |
| FCV-401, KSB BOA-CVE IMS control valve | `valve-twin` | A valve that knows its Kv |
| GT-501, Siemens Energy SGT-400 13 MW gas turbine | `turbine-twin` | A gas turbine that knows its heat rate |
| TR-601, SGB-SMIT DOTML 1000 kVA oil distribution transformer | `transformer-twin` | A transformer that knows its hot spot |

The posts are on the IBM Community (Maximo group), by Mohamed Chihaoui.

## What is where

```
<asset>-twin/twin/*.twin.json     the twin file: identity, manufacturer design data, sensors (payload path -> Monitor metric),
                                  limits and failure modes
<asset>-twin/twin_calc.py         the twin's physics: Monitor PythonExpression formulas and AlertExpression rules generated
                                  from the twin file, and the same numbers computed in Python
<asset>-twin/build_twin.py        (all but the pump) builds the twin file from the manufacturer's published data
chiller-twin/data/                BITZER EN 12900 polynomial coefficients fitted to BITZER SOFTWARE
tower-twin/tools/sat2glb.py       turns BAC's ACIS (.sat) CAD into glTF for the 3D view
turbine-twin, transformer-twin    also physics.py: the stand-in plant (calibrated gas turbine cycle; IEC 60076-7 thermal model + gas-in-oil)

digital-twin/monitor/twin_monitor.py   creates, through the Monitor API, the device type (one metric per sensor), the device
                                       (id = Manage asset number), the functions, the alert rules and the dashboard
digital-twin/manage/twins.json         which asset uses which twin folder and Monitor device type
digital-twin/manage/setup_registry.py  Manage: TWIN* asset attributes, classification DIGITALTWIN, values on each asset
digital-twin/manage/maximo.py          small Manage REST client (API key) used by setup_registry.py
digital-twin/manage/digital_twin_app_1.0.0.dbc   registers the Digital Twin app in Manage (menu entry, READ option)
digital-twin/maf-app/src/app.xml       the Digital Twin app (Maximo Application Framework): pages, tabs, tables, charts
digital-twin/maf-app/src/AppController.js   reads the twinned assets from Manage, polls each twin, conditions, add/edit
```

## Add a twin to your own asset

1. Choose an asset that has sensors and published manufacturer data (curves, data sheet, limits).
2. Write its twin file, using one of the `*.twin.json` files as a template.
3. Generate the Monitor formulas and alert rules with a `twin_calc.py` for that asset class.
4. Run `digital-twin/monitor/twin_monitor.py <ASSETNUM>` to create the device type, device, functions, alerts and dashboard.
5. Send the sensor readings to Monitor over MQTT.
6. Run `digital-twin/manage/setup_registry.py` to give the asset the `DIGITALTWIN` classification and its TWIN attributes.

## Notes

- Host names are placeholders such as `<your-mas-domain>` and `<monitor-api-host>`. API keys and device tokens are read
  from files outside the code (see the top of each script); never commit them.
- The app files are the app's own sources; building and deploying a MAF app needs IBM's MAF toolchain. The app imports
  `src/demokeys.js` (demo keys for fault injection, not in this repository): create it with `export default {};`.
- The physics simulators, 3D viewers and CAD models used in the lab are not part of this repository.
