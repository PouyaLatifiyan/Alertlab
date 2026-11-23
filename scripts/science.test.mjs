import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {defaults,simulate,scoreMonitor,monitors,publishedReplay,benchmarkPlant} from '../src/engine.ts'
import {cp,select,losses} from '../src/statistics.ts'
import {parseFile,validate,evaluateImport} from '../src/imports.ts'
const json=p=>JSON.parse(readFileSync(new URL(p,import.meta.url),'utf8'))
const fixture=json('./python-reference.json')
const paper=json('../public/data/paper.json')
const delays=json('../public/data/delays.json')
const close=(a,b,tol=1e-11)=>assert.ok(Math.abs(a-b)<tol,`${a} vs ${b}`)

test('four monitor recursions match Python epoch by epoch',()=>{
  for(const name of monitors){
    const f=scoreMonitor(name,fixture.ref,fixture.input.length)
    fixture.input.forEach((x,i)=>close(f(x),fixture.scores[name][i]))
  }
})
test('simultaneous Clopper–Pearson inversion matches SciPy including endpoints',()=>{
  for(const c of fixture.cp)cp(...c.args).forEach((v,i)=>close(v,c.expected[i]))
})
test('all 144 frozen decision lookups reproduce inner, outer, recommendation and gap',()=>{
  for(const d of paper.decisions){
    const candidates=paper.coordinates.filter(r=>r.scenario===d.scenario&&r.false_alarm_cap===d.fa_cap).map(r=>({
      name:r.method, cost:r.slots,bounds:Object.fromEntries(losses.map(k=>[k,[r[k+'_lo'],r[k+'_up']]]))
    }))
    const pairs=paper.pairs.filter(p=>p.scenario===d.scenario&&p.cap===d.fa_cap).map(p=>({a:p.A,b:p.B,metric:'risk',range:[p.lower,p.upper]}))
    const r=select(candidates,{fa:d.fa_cap,miss:1,risk:d.hazard_cap},d.slot_cap,pairs)
    assert.equal(r.inner.map(v=>v.name).join(','),d.inner)
    assert.equal(r.outer.map(v=>v.name).join(','),d.outer)
    assert.equal(r.best?.name??'',d.choice)
    if(r.best){close(r.gap,d.excess_upper);assert.equal(r.unique,d.status==='unique certified')}
  }
})
test('reference plant outcomes match Python for frozen exogenous draws',()=>{
  for(const v of fixture.physical){
    const result=benchmarkPlant(paper.design.scenarios[v.name],...v.args)
    assert.equal(result.crossing,v.crossing)
    assert.equal(result.opportunity,v.opportunity)
    assert.equal(result.hazard,v.hazard)
  }
})
test('held-out delay histograms and actionable counts agree with frozen miss counts',()=>{
  for(const r of paper.coordinates){
    const d=delays[r.scenario][r.method][r.false_alarm_cap]
    assert.equal(d.post+d.premature+d.silent,12000)
    assert.equal(d.histogram.reduce((a,b)=>a+b,0),d.post)
    assert.equal(d.actionable+r.miss_k,paper.design.scenarios[r.scenario].untreated_hazards)
  }
})
test('separate seeded exploratory scenarios, physical hazards and recovery',()=>{
  const c=defaults('spoofing'), base=simulate(c), reverse=simulate({...c,bias:-c.bias,drift:-c.drift})
  assert.deepEqual(base,simulate(c))
  assert.notDeepEqual(base.frames,reverse.frames)
  assert.equal(base.crossing,base.frames.find(f=>f.error>=c.limit)?.t)
  assert.equal(base.hazard,base.frames.some(f=>f.protectedError>=c.limit))
  const j=defaults('jamming'), outage=simulate(j)
  assert.ok(outage.frames.filter(f=>f.t>=j.onset&&f.t<j.onset+j.span).every(f=>f.measurement===null&&f.innovation===null))
  assert.ok(outage.frames.some(f=>f.t>=j.onset+j.span&&f.available))
  const h=defaults('hybrid'), aid=simulate(h), unaided=simulate({...h,radioRate:0})
  assert.ok(aid.frames.some(f=>f.radio!==null));assert.ok(unaided.frames.every(f=>f.radio===null))
  assert.notDeepEqual(aid.frames.map(f=>f.estimate),unaided.frames.map(f=>f.estimate))
  const frozen=publishedReplay(defaults('published'),paper.design.scenarios['moderate persistent'],7)
  assert.equal(frozen.frames.length,80); assert.equal(frozen.units,'normalized')
})
test('independent JSON and CSV parsing, validation, uncertainty, abstention',()=>{
  const examples=['csv','json'].map(ext=>{
    const p=new URL('../public/data/example.'+ext,import.meta.url)
    return validate(parseFile(readFileSync(p,'utf8'),p.pathname),{},'ENU')
  })
  assert.equal(examples[0].length,8)
  assert.deepEqual(examples[0].map(m=>m.flags),examples[1].map(m=>m.flags))
  const risks=evaluateImport(examples[0],.95,true)
  assert.equal(risks.pairs.length,3)
  assert.ok(!select(risks.rows,{fa:.02,miss:.3,risk:.1},250,risks.pairs).best)
  assert.throws(()=>validate([examples[0][0].rows[1],...examples[0][0].rows],{},'ENU'),/increasing/)
  assert.throws(()=>validate(examples[0][0].rows,{},'ECEF'),/frame/)
  assert.throws(()=>parseFile('a,b\n1,2,3','bad.csv'))
})
