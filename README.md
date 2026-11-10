# Digital Twin for Maximo

Code that goes with sixteen IBM Community posts on building physics-based digital twins of Maximo assets
with standard Maximo Monitor and Maximo Manage features:

| Asset | Twin folder | Post |
|---|---|---|
| PUMP-101, KSB Etanorm R 200-500 centrifugal pump | `pump-twin` | Centrifugal pump digital twin |
| CH-201, BITZER screw chiller | `chiller-twin` | Screw chiller digital twin |
| CT-301, BAC FXV closed-circuit cooling tower | `tower-twin` | Cooling tower digital twin |
| FCV-401, KSB BOA-CVE IMS control valve | `valve-twin` | Control valve digital twin |
| GT-501, Siemens Energy SGT-400 13 MW gas turbine | `turbine-twin` | Gas turbine digital twin |
| TR-601, SGB-SMIT DOTML 1000 kVA oil distribution transformer | `transformer-twin` | Oil transformer digital twin |
| CB-701, Siemens Energy 3AP1 FG 145 kV SF6 circuit breaker | `breaker-twin` | SF6 circuit breaker digital twin |
| UGC-801, 132 kV Prysmian XLPE cable circuit with fibre temperature sensing | `cable-twin` | Underground cable digital twin |
| OHL-901, 132 kV overhead line span, ACSR Drake conductor | `line-twin` | Overhead line digital twin |
| BAT-1001, 110 V substation battery, 54 EnerSys PowerSafe OPzV cells | `battery-twin` | Substation battery digital twin |
| CAP-1101, 33 kV double-wye shunt capacitor bank, Vishay ESTA units | `capbank-twin` | Capacitor bank digital twin |
| RO-1201, seawater reverse osmosis train, DuPont FilmTec SW30HRLE-440i + ERI PX | `ro-twin` | Reverse osmosis train digital twin |
| BLW-1301, Aerzen AT 150 turbo aeration blower with fine-bubble diffusers | `blower-twin` | Aeration blower digital twin |
| FLT-1401, dual-media rapid gravity filter on a Xylem Leopold underdrain | `filter-twin` | Rapid gravity filter digital twin |
| PIPE-1501, 14 km DN 1200 ductile iron water transmission main | `pipeline-twin` | Water transmission main digital twin |
| UV-1601, TrojanUVSwiftSC D12 UV disinfection reactor | `uv-twin` | UV disinfection digital twin |

The posts are on the IBM Community (Maximo group), by Mohamed Chihaoui.

## What is where

```
<asset>-twin/twin/*.twin.json     the twin file: identity, manufacturer design data, sensors (payload path -> Monitor metric),
                                  limits and failure modes
<asset>-twin/twin_calc.py         the twin's physics: Monitor PythonExpression formulas and AlertExpression rules generated
                                  from the twin file, and the same numbers computed in Python
<asset>-twin/MONITOR.md          every Monitor function and alert rule of the twin, written out readably
<asset>-twin/build_twin.py        (all but the pump) builds the twin file from the manufacturer's published data
chiller-twin/data/                BITZER EN 12900 polynomial coefficients fitted to BITZER SOFTWARE
tower-twin/tools/sat2glb.py       turns BAC's ACIS (.sat) CAD into glTF for the 3D view
<asset>-twin/physics.py          (turbine and later) the stand-in plant that produces the sensor readings in the lab

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
