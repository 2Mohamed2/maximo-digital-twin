# Digital Twin for Maximo

Code that goes with sixty-seven IBM Community posts on building physics-based digital twins of Maximo assets
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
| ESDV-2101, 12 in Class 600 ball valve with spring-return actuator, final element of a SIL 2 SIF | `esdv-twin` | Emergency shutdown valve digital twin |
| K-2201, Hydrotreater hydrogen make-up compressor, two stages, motor driven | `recip-twin` | Reciprocating compressor digital twin in Maximo |
| K-2301, Process gas compressor of a refinery unit, one section, six impellers, motor + VSD + | `centcomp-twin` | Process centrifugal compressor digital twin in Maximo |
| H-2401, Crude distillation unit charge heater: cabin type, radiant + convection, natural draft, 4 | `heater-twin` | Fired heater digital twin in Maximo |
| E-2501, Crude / kerosene product exchanger, cold end of the crude preheat train (crude in the | `hex-twin` | Shell-and-tube heat exchanger digital twin in Maximo |
| PSV-2601, Pressure relief valve on the overhead vapour drum D-2601, discharging to the flare header | `psv-twin` | Pressure relief valve digital twin in Maximo |
| TK-2701, Crude oil storage tank in a terminal tank farm, external floating roof, 40 m x 18 m | `tank-twin` | Storage tank digital twin in Maximo |
| ESP-2801, Electric submersible pump in a vertical oil well, variable speed drive, downhole gauge | `esp-twin` | Electric submersible pump digital twin in Maximo |
| RP-2901, Rod-lifted oil well: beam pumping unit, tapered steel rod string, insert pump at 6,000 | `rodpump-twin` | Sucker-rod pumping system digital twin in Maximo |
| WTG-3001, Onshore wind turbine, drivetrain twin: main bearing, three-stage gearbox and doubly fed | `windgbx-twin` | Wind turbine digital twin in Maximo |
| PV-3101, PV block 31, inverter 01: 375.84 kWp DC / 330 kVA AC, fixed-tilt bifacial array with | `pv-twin` | Utility PV block digital twin in Maximo |
| ST-3201, Turbine-generator of a cogeneration plant: process steam extraction at 12 bar(a) | `steamturb-twin` | Steam turbine digital twin in Maximo |
| BFP-3301, Boiler feed pump A (2 x 50 %) of a steam power unit, VSD motor drive, balance drum | `bfp-twin` | Boiler feed pump digital twin in Maximo |
| GEN-3401, Gas turbine generator of a combined-cycle power plant: 2-pole cylindrical rotor | `generator-twin` | Turbo-generator digital twin in Maximo |
| BESS-3501, Grid battery energy storage container 3501: 1.4 MWh LFP, BMS, embedded HVAC, with its PCS | `bess-twin` | Battery energy storage digital twin in Maximo |
| HYD-3601, Unit 1 of a high-head storage hydro plant: vertical Francis turbine, 22-pole synchronous | `hydro-twin` | Hydro turbine digital twin in Maximo |
| INT-3701, Seawater cooling water intake line A: fine band screen with spray wash and circulating | `intake-twin` | Cooling water intake digital twin in Maximo |
| CV-3801, Overland ore conveyor, primary crusher to stockpile: 2.5 km, +40 m lift, 2 x 560 kW head | `conveyor-twin` | Overland belt conveyor digital twin in Maximo |
| ML-3901, Primary SAG mill of the SABC grinding circuit (SAG mill, pebble crusher, ball mill) | `sagmill-twin` | SAG mill digital twin in Maximo |
| HT-4001, Rigid-frame mining haul truck, ore and waste haulage from the pit to the crusher and the | `haultruck-twin` | Mining haul truck digital twin in Maximo |
| SP-4101, Flotation tailings pump, tailings sump to thickener, on a variable speed drive | `slurry-twin` | Slurry pump digital twin in Maximo |
| KL-4201, Clinker line rotary kiln, 4.8 m x 74 m on three tyres, 5-stage preheater with calciner | `kiln-twin` | Cement rotary kiln digital twin in Maximo |
| PM-4301, Dryer section of a testliner board machine: 50 steam-heated cylinders in 4 cascade steam | `dryer-twin` | Paper machine dryer section digital twin in Maximo |
| EX-4401, Main extruder of a PE 100 pressure pipe line (pipe up to 250 mm) | `extruder-twin` | Single-screw extruder digital twin in Maximo |
| BL-4501, Process steam boiler, gas-fired, 10 t/h saturated steam at 13 bar g, plant utilities | `boiler-twin` | Steam boiler digital twin in Maximo |
| AC-4601, Base-load plant air compressor: oil-injected rotary screw, load/unload, with refrigerant | `aircomp-twin` | Rotary screw air compressor digital twin in Maximo |
| ST-4701, Drip-leg trap on the 10 bar g saturated steam main, one of 800 traps on the site steam | `steamtrap-twin` | Steam trap digital twin in Maximo |
| MC-4801, Main spindle of a 3-axis vertical machining centre (job shop, steel and aluminium parts) | `spindle-twin` | Machine tool spindle digital twin in Maximo |
| AD-4901, Mesophilic anaerobic digester no. 1 of a municipal wastewater treatment plant (primary + | `digester-twin` | Anaerobic digester digital twin in Maximo |
| BP-5001, Digested sludge dewatering press, municipal wastewater treatment plant, with polymer | `beltpress-twin` | Belt filter press digital twin in Maximo |
| CL-5101, Chlorine contact tank (clearwell) after the filters of a surface water treatment works | `chlorine-twin` | Chlorine contact tank digital twin in Maximo |
| LS-5201, Municipal sewage lift station: wet well, two submersible pumps duty/standby, check | `liftstation-twin` | Sewage lift station digital twin in Maximo |
| MBR-5301, Membrane train 1 of a municipal wastewater works: submerged hollow-fibre ultrafiltration | `mbr-twin` | Membrane bioreactor digital twin in Maximo |
| TM-5401, Traction motor 1 of locomotive 5401 with its IGBT traction inverter, blower and bearings | `traction-twin` | Traction motor digital twin in Maximo |
| PM-5501, Point machine of a main-line turnout with external clamp locks, with a condition | `points-twin` | Railway point machine digital twin in Maximo |
| ES-5601, Heavy-duty public transport escalator, platform to ticket hall (up), 10 m rise | `escalator-twin` | Metro escalator digital twin in Maximo |
| EL-5701, Passenger elevator 1 of the office tower lobby group: 12 stops, 44 m travel | `elevator-twin` | Passenger elevator digital twin in Maximo |
| QC-5801, Quay crane on berth 58 of a container terminal: discharges and loads container ships | `stscrane-twin` | Ship-to-shore container crane digital twin in Maximo |
| GPU-5901, 400 Hz ground power for a narrow-body contact stand: 3 x 115/200 V 400 Hz through a 28 m | `gpu-twin` | 400 Hz ground power unit digital twin in Maximo |
| BR-6001, Road bridge, 3 continuous spans 60 + 80 + 60 m, steel-concrete composite girders | `bridge-twin` | Road bridge digital twin in Maximo |
| UPS-6101, Data hall A UPS: three-phase double-conversion, 150 kW N+1, with two VRLA battery strings | `ups-twin` | Data centre UPS digital twin in Maximo |

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
