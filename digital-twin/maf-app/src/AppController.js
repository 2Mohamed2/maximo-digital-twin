/*
 * Digital Twin - Graphite (MAF) application.
 *
 * The twin registry is Maximo data: assets of classification DIGITALTWIN whose specification attributes
 * (TWINURL, TWINDEVTYPE, TWINDEVICE, TWINMODEL, TWINVERSION) point to each asset's live twin service.
 * The twin service runs the physics model, publishes to Maximo Monitor and serves the 3D twin and the
 * performance view, which this app embeds. Work orders are created in Maximo with the app's own datasource.
 */
import { log } from '@maximo/maximo-js-api';
import DEMO_KEYS from './demokeys';

const TAG = 'digitaltwin';
const SEV = { Critical: 0, High: 1, Medium: 2, Low: 3 };
const REFRESH_MS = 5000;

function fmt(v, d) {
  if (v === null || v === undefined || isNaN(v)) {
    return '-';
  }
  return Number(v).toFixed(d === undefined ? 1 : d);
}

function band(h) {
  if (h === null || h === undefined) {
    return '';
  }
  return h >= 85 ? 'good' : (h >= 60 ? 'watch' : 'alarm');
}

class AppController {
  applicationInitialized(app) {
    this.app = app;
    this.twins = [];
    this.detail = null;               // twin definition of the open asset (from its twin service)
    this.app.state.kpi = { twins: 0, twinsText: '0', running: 0, runningCount: '0', runningText: '', conditions: 0, condCount: '0', condText: '', health: '-', alarm: false, statusText: 'Loading twins' };
    this.app.state.sel = { title: 'Digital twin', subtitle: '', url3d: 'about:blank', urlCurves: 'about:blank', health: '-', ncond: 0, ncondText: '0',
      k1label: '', k1value: '', k2label: '', k2value: '', statusText: '', alarm: false, standards: '', assetnum: '', siteid: '',
      partTitle: 'Component', partSub: 'Click a component or a sensor tag in the model.', tr1: '', tr2: '', tr3: '', tr4: '',
      twinUrl: '', devtype: '' };
    this.app.state.faultMsg = '';
    this.app.state.twinDialogTitle = 'Add digital twin';
    this.app.state.twinReadMsg = '';
    this.app.state.demoKey = '';
    this.demoKey = '';
    this.faultSig = '';
    // the 3D twin page (host=maf) posts the component the user clicked; shown natively beside the model
    window.addEventListener('message', e => this.onTwinMessage(e));
    // the app's own <twin-scene> component reports the clicked component directly
    window.addEventListener('twin-select', e => this.onTwinMessage({ data: e.detail, own: true }));
    this.app.state.woCond = '';
    this.app.state.woAction = '';
    this.refreshPortfolio();
    this.timer = setInterval(() => this.tick(), REFRESH_MS);
  }

  ds(name) {
    return this.app.findDatasource(name);
  }

  async loadJson(name, items) {
    const ds = this.ds(name);
    if (!ds) {
      return;
    }
    ds.lastQuery = {};
    await ds.load({ src: items });
  }

  // Maximo REST with the signed-in user's own session (same origin: /maximo/oslc/...)
  async oslc(path) {
    const r = await fetch('../../' + path, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
    if (!r.ok) {
      throw new Error('Maximo ' + r.status + ' on ' + path.split('?')[0]);
    }
    return r.json();
  }

  async twinGet(url, path) {
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const t = ctl ? setTimeout(() => ctl.abort(), 8000) : null;
    try {
      const r = await fetch(url.replace(/\/$/, '') + path, ctl ? { signal: ctl.signal } : {});
      if (!r.ok) {
        throw new Error('twin ' + r.status);
      }
      return await r.json();
    } finally {
      if (t) {
        clearTimeout(t);
      }
    }
  }

  // ── registry (Maximo) ─────────────────────────────────────────────────────
  async loadRegistry() {
    const cls = await this.oslc('os/mxapiclassstructure?lean=1&oslc.select=classstructureid&oslc.where=' +
      encodeURIComponent('classificationid="DIGITALTWIN"'));
    const id = cls.member && cls.member[0] && cls.member[0].classstructureid;
    if (!id) {
      this.twins = [];
      return;
    }
    const a = await this.oslc('os/mxapiasset?lean=1&oslc.pageSize=200&oslc.select=' +
      encodeURIComponent('assetnum,siteid,description,status,location,assetspec{assetattrid,alnvalue}') +
      '&oslc.where=' + encodeURIComponent('classstructureid="' + id + '"'));
    this.twins = (a.member || []).map(x => {
      const spec = {};
      (x.assetspec || []).forEach(s => {
        spec[s.assetattrid] = s.alnvalue;
      });
      return { assetnum: x.assetnum, siteid: x.siteid, description: x.description || '', status: x.status || '',
        location: x.location || '', url: spec.TWINURL, devtype: spec.TWINDEVTYPE, device: spec.TWINDEVICE,
        model: spec.TWINMODEL || '', version: spec.TWINVERSION || '' };
    }).filter(t => t.url);
  }

  // ── portfolio ─────────────────────────────────────────────────────────────
  async refreshPortfolio() {
    try {
      if (!this.twins.length) {
        await this.loadRegistry();
      }
      await Promise.all(this.twins.map(async t => {
        try {
          t.sum = await this.twinGet(t.url, '/api/summary');
        } catch (e) {
          t.sum = null;
        }
      }));
      const rows = this.twins.map(t => {
        const s = t.sum || {};
        const conds = (s.conditions || []).slice().sort((a, b) => SEV[a.severity] - SEV[b.severity]);
        return {
          assetnum: t.assetnum, siteid: t.siteid, description: t.description, category: s.category || '',
          model: t.model, health: s.ready ? String(s.health) : 'offline', healthband: s.ready ? band(s.health) : 'alarm',
          state: !s.ready ? 'No data' : (s.running ? 'Running' : 'Tripped'),
          topcond: conds.length ? conds[0].severity + ': ' + conds[0].text : (s.ready ? 'None' : ''),
          ncond: conds.length, version: t.version, device: t.device,
          kpis: (s.kpis || []).map(k => k.label + ' ' + k.value + ' ' + k.unit).join(' · '),
          twinkpis: (s.twin_kpis || []).map(k => k.label + ' ' + k.value + ' ' + k.unit).join(' · ')
        };
      });
      await this.loadJson('twinsDS', rows);
      await this.loadJson('healthDS', rows.filter(r => r.health !== 'offline')
        .map(r => ({ key: r.assetnum, group: r.healthband === 'good' ? 'Runs as designed' : (r.healthband === 'watch' ? 'Watch' : 'Alarm'), value: Number(r.health) })));
      const live = this.twins.filter(t => t.sum && t.sum.ready);
      const nCond = live.reduce((n, t) => n + (t.sum.conditions || []).length, 0);
      const k = this.app.state.kpi;
      k.twins = this.twins.length;
      k.twinsText = '' + k.twins;
      k.running = live.filter(t => t.sum.running).length;
      k.runningCount = '' + k.running;
      k.runningText = (this.twins.length - live.length) ? (this.twins.length - live.length) + ' twin(s) not reachable' : 'all twins reporting';
      k.conditions = nCond;
      k.condCount = '' + nCond;
      k.condText = nCond ? 'on ' + live.filter(t => (t.sum.conditions || []).length).length + ' asset(s)' : 'all assets run as designed';
      k.health = live.length ? String(Math.round(live.reduce((n, t) => n + t.sum.health, 0) / live.length)) : '-';
      k.alarm = nCond > 0;
      k.statusText = nCond ? nCond + ' active condition(s)' : 'All twins run as designed';
    } catch (e) {
      log.e(TAG, 'portfolio', e);
      this.app.state.kpi.statusText = 'Could not load the twins: ' + e.message;
    }
  }

  // ── one twin ──────────────────────────────────────────────────────────────
  async openTwin(item) {
    const t = this.twins.find(x => x.assetnum === item.assetnum && x.siteid === item.siteid) || this.twins.find(x => x.assetnum === item.assetnum);
    if (!t) {
      return;
    }
    this.current = t;
    const base = t.url.replace(/\/$/, '');
    Object.assign(this.app.state.sel, {
      assetnum: t.assetnum, siteid: t.siteid, title: t.assetnum + ' · ' + t.description,
      subtitle: t.model + ' · site ' + t.siteid + ' · Monitor device ' + (t.devtype || '') + '/' + (t.device || '') + ' · twin v' + t.version,
      url3d: base + '/?embed=1&host=maf&device=' + encodeURIComponent(t.assetnum), urlCurves: base + '/curves?embed=1&host=maf',
      partTitle: 'Component', partSub: 'Click a component or a sensor tag in the model.',
      twinUrl: base, devtype: t.devtype || ''
    });
    this.faultSig = '';
    // prefill the demo key of this twin so fault injection works without typing it
    this.demoKey = (DEMO_KEYS && DEMO_KEYS[t.devtype]) || '';
    this.app.state.demoKey = this.demoKey;
    await this.loadJson('partDS', []);
    this.app.setCurrentPage({ name: 'twin', resetScroll: true });
    try {
      this.detail = await this.twinGet(t.url, '/api/twin');
      await this.loadDefinition(this.detail);
    } catch (e) {
      log.e(TAG, 'twin definition', e);
    }
    await this.refreshTwin(true);
    await this.refreshWork();
  }

  goPortfolio() {
    this.current = null;
    this.app.setCurrentPage({ name: 'portfolio' });
    this.refreshPortfolio();
  }

  async loadDefinition(tw) {
    const d = tw.design || {};
    const id = tw.identification || {};
    const rows = [
      ['Manufacturer and model', (id.manufacturer || '') + ' ' + (id.model || '')],
      ['Asset type', (tw.twin && tw.twin.kind) || ''],
      ['Twin id and version', ((tw.twin && tw.twin.id) || '') + ' v' + ((tw.twin && tw.twin.version) || '')]
    ];
    if (d.curve_source) {
      rows.push(['Performance data', d.curve_source.document + (d.curve_source.curve ? ', curve ' + d.curve_source.curve : '')]);
    }
    if (d.bep_flow_m3h) {
      rows.push(['Best efficiency point', d.bep_flow_m3h + ' m³/h at ' + d.bep_head_m + ' m, ' + fmt(d.bep_efficiency * 100, 1) + ' %, ' + d.bep_power_kw + ' kW']);
    }
    if (d.rated_speed_rpm) {
      rows.push(['Rated speed', d.rated_speed_rpm + ' rpm']);
    }
    if (d.motor) {
      rows.push(['Motor', d.motor.rated_power_kw + ' kW, ' + d.motor.rated_voltage_v + ' V, ' + d.motor.rated_current_a + ' A, ' + (d.motor.poles || '') + '-pole ' + (d.motor.efficiency_class || '')]);
    }
    (tw.presentation && tw.presentation.design || []).forEach(x => rows.push([x.label, x.value]));
    await this.loadJson('designDS', rows.map((r, i) => ({ key: String(i), label: r[0], value: r[1] })));
    const pts = (tw.telemetry && tw.telemetry.points) || [];
    await this.loadJson('sensorsDS', pts.map(p => ({ key: p.metric, label: p.label, opc: p.opc || 'extension', path: 'd.' + p.path, unit: p.unit, metric: p.metric.toUpperCase() })));
    const fm = tw.failure_modes || {};
    await this.loadJson('fmDS', Object.keys(fm).filter(k => k.charAt(0) !== '$').map(k => ({
      key: k, label: fm[k].label, cause: fm[k].cause, action: fm[k].action,
      detect: (fm[k].detect || []).map((m, i) => (i + 1) + '. ' + ((pts.find(p => p.metric === m) || {}).label || m.replace(/_/g, ' '))).join('   '),
      ramp: fm[k].default_ramp_min || 5, active: 'N', btn: 'Inject'
    })));
    const st = (tw.twin && tw.twin.standards) || {};
    this.app.state.sel.standards = Object.keys(st).map(k => st[k]).join(' · ');
  }

  async refreshTwin(withHistory) {
    const t = this.current;
    if (!t) {
      return;
    }
    try {
      const s = await this.twinGet(t.url, '/api/state');
      const tw = this.detail || {};
      const v = Object.assign({}, s.reading || {}, s.twin || {});
      const pres = tw.presentation || {};
      const conds = (s.conditions || []).slice().sort((a, b) => SEV[a.severity] - SEV[b.severity]);
      const fm = tw.failure_modes || {};
      const sel = this.app.state.sel;
      sel.health = String(s.health);
      sel.ncond = conds.length;
      sel.ncondText = '' + conds.length;
      sel.alarm = conds.length > 0 || !s.running;
      sel.statusText = !s.running ? 'Tripped' : (conds.length ? conds.length + ' active condition(s)' : 'Runs as designed');
      const tk = pres.twin_kpis || [];
      if (tk[0]) {
        sel.k1label = tk[0].label;
        sel.k1value = fmt(v[tk[0].metric], tk[0].decimals) + ' ' + tk[0].unit;
      }
      if (tk[1]) {
        sel.k2label = tk[1].label;
        sel.k2value = fmt(v[tk[1].metric], tk[1].decimals) + ' ' + tk[1].unit;
      }
      const faults = s.faults || {};
      const sig = Object.keys(faults).filter(k => faults[k] > 0.01).sort().map(k => k + ':' + Math.round(faults[k] * 100)).join(',');
      if (sig !== this.faultSig) {
        this.faultSig = sig;
        await this.loadJson('fmDS', ((this.ds('fmDS') && this.ds('fmDS').items) || []).map(x => {
          const o = Object.assign({}, x);
          const on = (faults[x.key] || 0) > 0.01;
          o.active = on ? 'Y' : 'N';
          o.btn = on ? 'Stop (' + Math.round(faults[x.key] * 100) + ' %)' : 'Inject';
          return o;
        }));
      }
      await this.loadJson('condDS', conds.map((c, i) => ({ key: c.name + i, severity: c.severity, name: c.name, text: c.text, part: c.part,
        action: (c.failure_mode && fm[c.failure_mode] && fm[c.failure_mode].action) || 'Inspect and confirm' })));
      await this.loadJson('measDS', (pres.compare || []).map((c, i) => {
        const m = v[c.measured];
        const e = c.expected ? v[c.expected] : null;
        let dev = '';
        if (e !== null && e !== undefined && m !== undefined) {
          dev = (m - e >= 0 ? '+' : '') + fmt(m - e, c.decimals) + ' ' + c.unit;
        }
        return { key: String(i), label: c.label, measured: fmt(m, c.decimals) + ' ' + c.unit,
          expected: e === null || e === undefined ? '' : fmt(e, c.decimals) + ' ' + c.unit, deviation: dev, basis: c.basis || '' };
      }));
      const pts = (tw.telemetry && tw.telemetry.points) || [];
      const groups = (tw.telemetry && tw.telemetry.groups) || {};
      await this.loadJson('liveDS', pts.map(p => ({ key: p.metric, group: p.path.split('.')[0], label: p.label,
        value: fmt((s.reading || {})[p.metric], Math.abs((s.reading || {})[p.metric]) < 10 ? 2 : 1) + ' ' + p.unit,
        opc: p.opc ? p.opc : (groups[p.path.split('.')[0]] ? 'extension' : '') })));
      if (withHistory || !this.histAt || Date.now() - this.histAt > 30000) {
        this.histAt = Date.now();
        const h = await this.twinGet(t.url, '/api/history');
        const tr = pres.trends || [];
        const hist = (h.history || []).filter((r, i, arr) => i % Math.max(1, Math.floor(arr.length / 240)) === 0);
        for (let n = 1; n <= 4; n++) {
          const m = tr[n - 1];
          sel['tr' + n] = m ? m.label : '';
          const rows = [];
          if (m) {
            hist.forEach(r => {
              if (r[m.metric] !== undefined && r[m.metric] !== null) {
                rows.push({ key: m.metric + '|' + r.t, group: m.label, date: new Date(r.t * 1000).toISOString(), value: Number(r[m.metric]) });
              }
            });
          }
          await this.loadJson('trend' + n + 'DS', rows);
        }
      }
    } catch (e) {
      log.e(TAG, 'twin state', e);
      this.app.state.sel.statusText = 'Twin not reachable: ' + e.message;
    }
  }

  // ── add / edit a digital twin (Maximo registry: DIGITALTWIN classification + TWIN* attributes) ────
  async openTwinForm(title, values) {
    this.app.state.twinDialogTitle = title;
    this.app.state.twinReadMsg = '';
    await this.loadJson('twinFormDS', [Object.assign({ formid: '1', twinurl: '', assetnum: '', siteid: (this.twins[0] && this.twins[0].siteid) || '',
      devtype: '', device: '', model: '', version: '' }, values || {})]);
    this.app.showDialog('twinDialog');
  }

  addTwin() {
    return this.openTwinForm('Add digital twin', {});
  }

  editTwin() {
    const t = this.current;
    if (!t) {
      return null;
    }
    return this.openTwinForm('Edit digital twin · ' + t.assetnum, { twinurl: t.url, assetnum: t.assetnum, siteid: t.siteid,
      devtype: t.devtype || '', device: t.device || '', model: t.model || '', version: t.version || '' });
  }

  async readTwinDef() {
    const f = this.ds('twinFormDS').item;
    const url = String(f.twinurl || '').trim().replace(/\/$/, '');
    if (!/^https?:\/\//.test(url)) {
      this.app.state.twinReadMsg = 'Enter the twin service URL first (https://...).';
      return;
    }
    try {
      const tw = await this.twinGet(url, '/api/twin');
      const id = tw.identification || {};
      const tel = tw.telemetry || {};
      f.twinurl = url;
      f.assetnum = f.assetnum || id.assetnum || '';
      f.devtype = tel.device_type || f.devtype;
      f.device = id.assetnum || f.device;
      f.model = ((id.manufacturer || '') + ' ' + (id.model || '')).trim() || f.model;
      f.version = (tw.twin && tw.twin.version) || f.version;
      this.app.state.twinReadMsg = 'Read: ' + (id.description || id.assetnum || 'twin') + ' · ' + ((tw.twin && tw.twin.kind) || '') +
        ' · ' + ((tel.points || []).length) + ' sensors, ' + Object.keys(tw.failure_modes || {}).filter(k => k.charAt(0) !== '$').length + ' failure modes.';
      await this.loadJson('twinFormDS', [Object.assign({}, f)]);
    } catch (e) {
      this.app.state.twinReadMsg = 'Could not read the twin definition: ' + e.message;
    }
  }

  async csrf() {
    const r = await fetch('../../login?csrf=1&lean=1', { credentials: 'same-origin', headers: { Accept: 'application/json' } });
    return r.headers.get('csrftoken') || '';
  }

  async saveTwin() {
    const f = Object.assign({}, this.ds('twinFormDS').item);
    const need = ['twinurl', 'assetnum', 'siteid', 'devtype', 'device'].filter(k => !String(f[k] || '').trim());
    if (need.length) {
      this.app.toast('Missing: ' + need.join(', '), 'error');
      return;
    }
    try {
      const cls = await this.oslc('os/mxapiclassstructure?lean=1&oslc.select=classstructureid&oslc.where=' +
        encodeURIComponent('classificationid="DIGITALTWIN"'));
      const csid = cls.member && cls.member[0] && cls.member[0].classstructureid;
      const a = await this.oslc('os/mxapiasset?lean=1&oslc.select=' + encodeURIComponent('assetnum,siteid,href,assetspec{assetspecid,assetattrid,alnvalue}') +
        '&oslc.where=' + encodeURIComponent('assetnum="' + f.assetnum.trim().toUpperCase() + '" and siteid="' + f.siteid.trim().toUpperCase() + '"'));
      const asset = a.member && a.member[0];
      if (!csid || !asset) {
        throw new Error(!csid ? 'classification DIGITALTWIN is missing' : 'asset ' + f.assetnum + ' not found at site ' + f.siteid);
      }
      const have = {};
      (asset.assetspec || []).forEach(s => {
        have[s.assetattrid] = s;
      });
      const spec = [['TWINURL', f.twinurl.trim().replace(/\/$/, '')], ['TWINDEVTYPE', f.devtype.trim()], ['TWINDEVICE', f.device.trim()],
        ['TWINMODEL', String(f.model || '').trim()], ['TWINVERSION', String(f.version || '').trim()]].map(([k, v]) => {
        const row = { assetattrid: k, alnvalue: v, linearassetspecid: 0 };   // key part on Manage spec rows (BMXAA1339E without it)
        if (have[k]) {
          row.assetspecid = have[k].assetspecid;
        }
        return row;
      });
      // address the record by its key; the href's own prefix differs between session and API-key calls
      const href = '../../os/mxapiasset/' + asset.href.split('/mxapiasset/')[1].split('?')[0] + '?lean=1';
      const r = await fetch(href, { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'x-method-override': 'PATCH', patchtype: 'MERGE',
          csrftoken: await this.csrf() },
        body: JSON.stringify({ classstructureid: csid, assetspec: spec }) });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error('Maximo ' + r.status + ' ' + txt.slice(0, 200));
      }
      this.app.toast('Digital twin saved on ' + asset.assetnum + '.', 'success');
      try {
        const dlg = this.app.currentPage && this.app.currentPage.findDialog && this.app.currentPage.findDialog('twinDialog');
        if (dlg && dlg.closeDialog) {
          dlg.closeDialog();
        }
      } catch (err) {
        // the dialog may already be closing
      }
      this.twins = [];
      await this.refreshPortfolio();
    } catch (e) {
      log.e(TAG, 'save twin', e);
      this.app.toast('Digital twin not saved: ' + e.message, 'error');
    }
  }

  // ── component selected in the 3D twin ───────────────────────────────────────
  async onTwinMessage(e) {
    const d = e.data;
    if (!d || d.type !== 'twin-select' || !this.current) {
      return;
    }
    try {
      if (!e.own && e.origin !== new URL(this.current.url).origin) {
        return;
      }
    } catch (err) {
      return;
    }
    const strip = x => String(x === null || x === undefined ? '' : x).replace(/<[^>]*>/g, '');
    this.app.state.sel.partTitle = strip(d.title);
    this.app.state.sel.partSub = strip(d.sub);
    let section = '';
    const rows = [];
    (d.rows || []).forEach((r, i) => {
      if (r[0] === 'h') {
        section = strip(r[1]);
        return;
      }
      rows.push({ key: String(i), label: strip(r[0]), measured: strip(r[1]), expected: strip(r[2]) });
    });
    const sig = JSON.stringify(rows);
    if (sig !== this.partSig) {
      this.partSig = sig;
      await this.loadJson('partDS', rows);
    }
    this.partSection = section;
  }

  // ── failure injection on the twin's physical model (demo key protected) ────
  setDemoKey(evt) {
    this.app.state.demoKey = (evt && evt.target && evt.target.value) || '';
    this.demoKey = this.app.state.demoKey.trim();
  }

  async twinPost(path, body) {
    const t = this.current;
    if (!t) {
      return;
    }
    try {
      const r = await fetch(t.url.replace(/\/$/, '') + path, { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Demo-Key': this.demoKey }, body: JSON.stringify(body || {}) });
      this.app.state.faultMsg = r.ok ? 'Done. The twin updates within a few seconds.' : (r.status === 403 ? 'Enter the demo key first.' : 'Twin answered ' + r.status);
    } catch (e) {
      this.app.state.faultMsg = 'Twin not reachable: ' + e.message;
    }
    setTimeout(() => {
      this.app.state.faultMsg = '';
    }, 6000);
    await this.refreshTwin(false);
  }

  injectFault(item) {
    return this.twinPost('/api/fault', item.active === 'Y' ? { name: item.key, severity: 0, ramp_min: 0.1 } : { name: item.key, severity: 1, ramp_min: item.ramp || 5 });
  }

  clearFaults() {
    return this.twinPost('/api/clear', {});
  }

  resetTwin() {
    return this.twinPost('/api/reset', {});
  }

  tick() {
    const page = this.app.currentPage && this.app.currentPage.name;
    if (page === 'twin') {
      this.refreshTwin(false);
    } else {
      this.refreshPortfolio();
    }
  }

  // ── work (Maximo) ─────────────────────────────────────────────────────────
  async refreshWork() {
    const t = this.current;
    const ds = this.ds('woDS');
    if (!t || !ds) {
      return;
    }
    try {
      ds.clearQBE && ds.clearQBE();
      ds.setQBE('assetnum', '=', t.assetnum);
      ds.setQBE('siteid', '=', t.siteid);
      await ds.searchQBE();
    } catch (e) {
      log.e(TAG, 'work orders', e);
    }
  }

  async askWorkOrder(item) {
    const t = this.current;
    if (!t) {
      return;
    }
    this.app.state.woCond = item.severity + ' · ' + item.name + ': ' + item.text;
    this.app.state.woAction = item.action;
    const f = this.ds('woFormDS');
    const desc = (t.assetnum + ' ' + item.name.replace(/^PUMP_|^CHILLER_|^TOWER_|^VALVE_/, '').replace(/_/g, ' ').toLowerCase() + ': ' + item.action);
    await this.loadJson('woFormDS', [{ formid: '1', description: desc.slice(0, 100), priority: item.severity === 'Critical' || item.severity === 'High' ? '1' : '2' }]);
    if (f) {
      f.lastQuery = {};
    }
    this.app.showDialog('woDialog');
  }

  async createWorkOrder() {
    const t = this.current;
    const f = this.ds('woFormDS').item;
    const ds = this.ds('woDS');
    if (!t || !ds) {
      return;
    }
    try {
      await ds.addNew();
      ds.item.siteid = t.siteid;
      ds.item.assetnum = t.assetnum;
      ds.item.description = String(f.description || '').slice(0, 100);
      ds.item.worktype = 'CM';
      ds.item.wopriority = parseInt(f.priority, 10) || 2;
      await ds.save();
      const wonum = ds.item && ds.item.wonum;
      this.app.toast(this.app.getLocalizedLabel('wo_created', 'Work order {0} created on {1}.', [wonum || '', t.assetnum]), 'success');
    } catch (e) {
      log.e(TAG, 'create work order', e);
      this.app.toast('Work order not created: ' + e.message, 'error');
    }
    await this.refreshWork();
  }
}

export default AppController;
