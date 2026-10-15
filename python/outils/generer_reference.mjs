// Génère les données de référence du portage Python à partir du code JavaScript d'origine.
//
// Le noyau thermodynamique et le catalogue sont extraits tels quels de index.html,
// exécutés avec Node (>= 22.6, option --experimental-strip-types), puis :
//   - le catalogue est écrit dans python/cycle_mci/donnees/catalogue.json ;
//   - les résultats de référence sont écrits dans python/tests/donnees/reference_js.json.
//
// Usage (depuis la racine du dépôt) :
//   node --experimental-strip-types python/outils/generer_reference.mjs

import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const racine = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const html = readFileSync(join(racine, 'index.html'), 'utf8');

function section(debut, fin) {
  const i = html.indexOf(debut), j = html.indexOf(fin, i);
  if (i < 0 || j < 0) throw new Error(`Marqueurs introuvables : ${debut} … ${fin}`);
  return html.slice(i, j);
}
const noyau = section('/* ===================== ENGINE START', '/* ===================== ENGINE END');
const catalogue = section('/* ===================== CATALOGUE MOTEURS', '/* ---------- icônes');

const dossier = mkdtempSync(join(tmpdir(), 'banc-'));
const fichier = join(dossier, 'noyau.ts');
writeFileSync(fichier, `${noyau}\n${catalogue}\nexport { computeEngine, CATALOG, specBaseInputs, calibrateP1, makeKin, volumeAt, pistonVelocity, cycleAt, defaultFiring };\n`);
const js = await import(pathToFileURL(fichier).href);

/* ---------- catalogue ---------- */
const CHAMPS = ['id', 'brand', 'code', 'name', 'apps', 'years', 'fuel', 'layout', 'angle', 'n', 'bore', 'stroke', 'rod', 'eps', 'ind', 'ps', 'rpm', 'nm', 'cc'];
const cat = js.CATALOG.map(s => Object.fromEntries(CHAMPS.map(k => [k, s[k] ?? null])));
writeFileSync(join(racine, 'python', 'cycle_mci', 'donnees', 'catalogue.json'), JSON.stringify(cat, null, 1) + '\n');

/* ---------- résultats de référence ---------- */
const THERMO = ['fuel', 'cycle', 'gammaMode', 'boreMm', 'strokeMm', 'rodMm', 'nCyl', 'eps', 'p1Bar', 't1C', 'rpm', 'lambda', 'pciMJ', 'afrSt', 'etaCombPct', 'xvPct', 'gamma'];
const SORTIES = ['gamma', 'cv', 'cp', 'gammaIterations', 'Vd', 'Vc', 'Vtot', 'mAir', 'mFuel', 'mFuelBurnt', 'Qfuel', 'Qadd', 'Qout', 'Qloss',
  'Wnet', 'etaTh', 'etaFuel', 'etaOttoRef', 'pmiBar', 'powerW', 'torqueNm', 'isfc', 'airKgH', 'fuelKgH', 'rc', 'alphaP', 'xv', 'pmaxBar', 'tmaxK', 'capped'];

function cas(nom, inp) {
  const r = js.computeEngine(inp);
  const k = js.makeKin(inp, r);
  const angles = [0, 45, 90, 180, 270, 360, 400, 450, 540, 630];
  return {
    nom,
    entrees: Object.fromEntries(THERMO.map(c => [c, inp[c]])),
    sorties: Object.fromEntries(SORTIES.map(c => [c, r[c]])),
    etats: r.states.map(s => ({ id: s.id, P: s.P, T: s.T, V: s.V, s: s.s, u: s.u, h: s.h })),
    transformations: r.processes.map(p => ({ id: p.id, Q: p.Q, W: p.W, dU: p.dU })),
    avertissements: r.warnings.map(w => w.text),
    cinematique: angles.map(th => {
      const c = js.cycleAt(r, k, th);
      return { theta: th, V: js.volumeAt(k, th), vitesse: js.pistonVelocity(k, th, inp.rpm), P: c.P, T: Number.isFinite(c.T) ? c.T : null };
    }),
  };
}

const ref = { catalogue: [], cas_particuliers: [] };
for (const sp of js.CATALOG) {
  const inp = js.specBaseInputs(sp);
  inp.p1Bar = js.calibrateP1(sp);
  ref.catalogue.push(cas(sp.id, inp));
}

const base = js.specBaseInputs(js.CATALOG.find(s => s.id === 'vw-14tsi'));
for (const cycle of ['otto', 'diesel', 'sabathe']) {
  for (const gammaMode of ['auto', 'manuel']) {
    for (const lambda of [0.8, 1.0, 1.6]) {
      ref.cas_particuliers.push(cas(`${cycle}-${gammaMode}-lambda${lambda}`, { ...base, cycle, gammaMode, lambda, gamma: 1.33, xvPct: 60 }));
    }
  }
}
// Phase isobare tronquée au PMB (faible taux de compression, forte charge)
ref.cas_particuliers.push(cas('diesel-tronque', { ...base, fuel: 'diesel', cycle: 'diesel', eps: 4, lambda: 1.0, gammaMode: 'manuel', gamma: 1.4 }));
// Diesel suralimenté, mélange pauvre
ref.cas_particuliers.push(cas('diesel-pauvre', { ...base, fuel: 'diesel', cycle: 'sabathe', eps: 17, p1Bar: 2.5, lambda: 1.1, xvPct: 30, pciMJ: 42.6, afrSt: 14.5 }));

writeFileSync(join(racine, 'python', 'tests', 'donnees', 'reference_js.json'), JSON.stringify(ref) + '\n');
console.log(`Catalogue : ${cat.length} moteurs · référence : ${ref.catalogue.length} moteurs + ${ref.cas_particuliers.length} cas particuliers`);
