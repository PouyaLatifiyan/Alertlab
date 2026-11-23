import {useEffect,useMemo,useRef,useState} from 'react'
import {Header,Num,Pick,Table,dataUrl,pct,useLab} from './common'
import {losses,select,type Loss,type Candidate,type Pair} from './statistics'
import {evaluateImport,optional,parseFile,required,validate,type Mission,type Raw} from './imports'
import {colors,download,Plot} from './visuals'
import {monitors,type Config} from './engine'
const metrics={fa:'Healthy false alerts',miss:'Missed window',risk:'Physical hazard'}
type Delay={histogram:number[];post:number;premature:number;silent:number;actionable:number}
type Delays=Record<string,Record<string,Record<string,Delay>>>

function Importer({accept}:{accept:(m:Mission[],q:boolean)=>void}){
  const [raw,setRaw]=useState<Raw[]>([]),[map,setMap]=useState<Record<string,string>>({}),[frame,setFrame]=useState('ENU'),[error,setError]=useState(''),[status,setStatus]=useState('')
  const [qualified,setQualified]=useState(false)
  const keys=useMemo(()=>[...new Set(raw.flatMap(Object.keys))], [raw])
  return <section className="panel detail"><h2>Import complete mission histories</h2><p>Upload CSV or JSON with a common scenario, policy definition and time convention. Files stay in this browser session.</p>
    <input aria-label="Mission history file" type="file" accept=".csv,.json" onChange={async e=>{
      const f=e.target.files?.[0];if(!f)return
      setError('');setStatus('');setMap({});setRaw([]);accept([],false)
      try{if(f.size>32*1024*1024)throw Error('File exceeds 32 MiB.');setRaw(parseFile(await f.text(),f.name))}catch(e){setError((e as Error).message)}
    }}/>
    {!!raw.length&&<><details><summary>Map input columns</summary><div className="inputs">{[...required,...optional].map(k=><Pick key={k} label={k} value={map[k]??(keys.includes(k)?k:'')} options={([['','Default'],...keys.map(v=>[v,v])] as [string,string][])} onChange={s=>setMap({...map,[k]:s})}/>)}</div></details>
    <Pick label="Coordinate convention" value={frame} options={['ENU','ECEF']} onChange={setFrame}/>
    <label className="check import-check"><input type="checkbox" checked={qualified} onChange={e=>setQualified(e.target.checked)}/> I confirm independent representative complete missions within each cohort, frozen policies, and shared mission IDs only for genuinely paired runs. Compute simultaneous confidence bounds conditional on these assumptions.</label>
    <button onClick={()=>{setError('');setStatus('');try{
      const m=validate(raw,map,frame)
      if(new Set(m.map(r=>r.monitor)).size>24)throw Error('Limit the file to 24 monitoring configurations.')
      accept(m,qualified);setStatus(`${m.length} complete mission-policy histories validated.`)
    }catch(e){accept([],false);setError((e as Error).message)}}}>Validate and evaluate</button></>}
    {error&&<p role="alert" className="danger-text">{error}</p>}{status&&<p role="status">{status}</p>}
    <div className="actions"><a className="button" href={dataUrl('example.csv')} download>CSV example</a><a className="button" href={dataUrl('example.json')} download>JSON example</a></div>
  </section>
}
function ImportedTrace({missions}:{missions:Mission[]}){
  const [index,setIndex]=useState(0)
  const position=(v:unknown)=>v===''||v==null?null:Number(v)
  const m=missions[Math.min(index,missions.length-1)]
  return <details><summary>Inspect an imported mission trace</summary>
    <Pick label="Mission-policy run" value={String(Math.min(index,missions.length-1))} options={missions.map((r,i)=>[String(i),`${r.id} / ${r.monitor} / ${r.cohort}`])} onChange={v=>setIndex(+v)}/>
    <Plot title="Position trace from import" unit="m · native declared frame" times={m.rows.map(r=>Number(r.time_s))}
      series={['x','y','z'].flatMap((a,i)=>[{name:a.toUpperCase(),color:Object.values(colors)[i],values:m.rows.map(r=>position(r[a+'_m']))},
        {name:'Reference '+a.toUpperCase(),color:Object.values(colors)[i+3],values:m.rows.map(r=>position(r['ref_'+a+'_m']))}])}
      events={[{t:m.onset,name:'Onset',color:colors.threshold},{t:m.first,name:'First alarm',color:colors.measurement},{t:m.deadline,name:'Deadline',color:colors.estimate}]}/>
  </details>
}
function Exploratory({config}:{config:Config}){
  const [thresholds,setThresholds]=useState<number[]>(()=>monitors.map(()=>config.threshold))
  const [count,setCount]=useState(160),[confidence,setConfidence]=useState(.95)
  const [budgets,setBudgets]=useState({fa:.05,miss:.3,risk:.2})
  const [out,setOut]=useState<{rows:Candidate[];pairs:Pair[]}|null>(null)
  const [stamp,setStamp]=useState(''),[progress,setProgress]=useState<number|null>(null),[error,setError]=useState('')
  const worker=useRef<Worker|null>(null)
  useEffect(()=>()=>worker.current?.terminate(),[])
  const fingerprint=JSON.stringify({config,count,thresholds,confidence})
  const stale=stamp!==fingerprint
  const decision=out&&!stale?select(out.rows,budgets,null,out.pairs):null
  const supported=decision?.best
  return <div className="decision-grid"><aside className="panel controls"><h2>Model trial controls</h2>
    {monitors.map((m,i)=><Num key={m} label={m+' score threshold'} value={thresholds[i]} min={-20} max={500} step={.1} onChange={v=>setThresholds(thresholds.map((x,j)=>j===i?Math.max(-20,Math.min(500,v)):x))}/>)}
    <Num label="Replicates per law" value={count} min={30} max={600} onChange={v=>setCount(Math.round(Math.max(30,Math.min(600,v))))}/>
    <Num label="Joint confidence (%)" value={confidence*100} min={50} max={99.99} step={.1} onChange={v=>setConfidence(Math.min(.9999,Math.max(.5,v/100)))}/>
    {losses.map(k=><Num key={k} label={metrics[k]+' budget (%)'} value={+(budgets[k]*100).toFixed(6)} min={0} max={100} step={.1} onChange={v=>setBudgets({...budgets,[k]:Math.max(0,Math.min(1,v/100))})}/>)}
    <button className="primary" disabled={config.scenario==='published'||progress!==null} onClick={()=>{
      setOut(null);setStamp(fingerprint);setError('');setProgress(0)
      try{
        const active=new Worker(new URL('./mission.worker.ts',import.meta.url),{type:'module'})
        worker.current=active
        const stop=()=>{active.terminate();worker.current=null;setProgress(null)}
        active.onmessage=e=>{if(e.data.result){setOut(e.data.result);stop()}else if(e.data.error){setError(e.data.error);stop()}else setProgress(e.data.progress)}
        active.onerror=e=>{setError(e.message||'The simulation worker failed.');stop()}
        active.postMessage({config,count,thresholds,confidence})
      }catch(e){setError((e as Error).message);setProgress(null)}
    }}>Run paired missions</button>
    {progress!==null&&<button onClick={()=>{worker.current?.terminate();worker.current=null;setProgress(null)}}>Cancel</button>}
  </aside><div className="stack"><section className="panel decision"><span className="badge">Exploratory simulation · model-conditional bounds</span>
    <h2>{supported?supported.name+' · model-only selection':decision&&!decision.outer.length?'No feasible candidate in this model':'Insufficient evidence for certified selection'}</h2>
    <p>Uses the active Simulator configuration ({config.scenario}). Thresholds are frozen for each batch. Separate healthy and changed draws are paired across candidate policies. Confidence bounds are conditional on the specified synthetic population and do not validate a receiver, actuator, jamming ranking, or deployment population.</p>
    {config.scenario==='published'&&<p>Choose an exploratory scenario in the Simulator, or use the Benchmark tab for the published scalar model.</p>}
    {progress!==null&&<p role="status">Simulating {Math.floor(100*progress)}% of paired trial sets…</p>}
    {error&&<p role="alert">{error}</p>}{out&&stale&&<p role="status">Inputs changed. Run a new batch to evaluate this configuration.</p>}
    {decision&&out&&<><Table rows={out.rows.map(r=>({monitor:r.name,...Object.fromEntries(losses.map(k=>[metrics[k],`${pct(r.estimates[k])} [${r.bounds[k].map(pct).join(', ')}]`])),status:decision.inner.includes(r)?'Feasible in model':decision.outer.includes(r)?'Unresolved':'Infeasible in model'}))}/>
    <p>Candidate excess upper bound {supported?pct(decision.gap):'—'}. Exposure {Math.floor(config.duration/config.dt+1e-9)*config.dt} s.</p>
    <div className="actions"><button onClick={()=>download('alert-model-evaluation.json',JSON.stringify({config,count,thresholds,confidence,budgets,out,decision},null,2),'application/json')}>Export model comparison</button></div></>}
  </section></div></div>
}
export function Evaluation(){
  const {paper,loadError,regime,setRegime,cap,setCap,config}=useLab()
  const [mode,setMode]=useState('Benchmark'),[budgets,setBudgets]=useState({fa:.02,miss:.3,risk:.6}),[resource,setResource]=useState(250),[useResource,setUseResource]=useState(true)
  const [confidence,setConfidence]=useState(.95),[missions,setMissions]=useState<Mission[]>([]),[qualified,setQualified]=useState(false),[importScenario,setImportScenario]=useState('')
  const [menu,setMenu]=useState<string[]>([...monitors]),[delay,setDelay]=useState<Delays|null>(null)
  const benchmark=mode==='Benchmark', certified=benchmark?!!paper:qualified
  useEffect(()=>{if(benchmark&&!delay)fetch(dataUrl('delays.json')).then(r=>r.ok?r.json():null).then(setDelay).catch(()=>{})},[benchmark,delay])
  const activeMissions=useMemo(()=>missions.filter(m=>m.scenario===importScenario),[missions,importScenario])
  const exposure=useMemo(()=>[...new Set(activeMissions.map(m=>m.horizon))],[activeMissions])
  const result=useMemo(()=>{
    if(!benchmark)return exposure.length===1?evaluateImport(activeMissions,confidence,qualified):{rows:[],pairs:[]}
    const rows:Candidate[]=(paper?.coordinates??[]).filter(r=>r.scenario===regime&&r.false_alarm_cap===cap&&menu.includes(r.method)).map(r=>({
      name:r.method,cost:r.slots,
      bounds:Object.fromEntries(losses.map(k=>[k,[r[`${k}_lo`],r[`${k}_up`]]])) as Candidate['bounds'],
      estimates:Object.fromEntries(losses.map(k=>[k,r[`${k}_k`]/paper!.design.heldout_per_law])) as Candidate['estimates']
    }))
    const pairs:Pair[]=(paper?.pairs??[]).filter(r=>r.scenario===regime&&r.cap===cap&&menu.includes(r.A)&&menu.includes(r.B)).map(r=>({a:r.A,b:r.B,range:[r.lower,r.upper],metric:'risk'}))
    return {rows,pairs}
  },[benchmark,activeMissions,confidence,qualified,exposure,paper,regime,cap,menu])
  const lower=benchmark&&budgets.fa<=cap?paper?.limits.find(r=>r.scenario===regime&&r.fa_cap===cap)?.admissible_lower:undefined
  const decision=select(result.rows,budgets,useResource?resource:null,result.pairs,lower)
  const winner=certified?decision.best:null
  const status=winner?winner.name:certified&&result.rows.length&&!decision.outer.length?'No feasible candidate':'Insufficient evidence for certified selection'
  const disposition=(r:Candidate)=>!certified?'Unresolved':decision.inner.includes(r)?'Certified feasible':decision.outer.includes(r)?'Unresolved':'Certified infeasible'
  const hist=benchmark?delay?.[regime]:null
  const importHist=result.rows.map(r=>{const m=activeMissions.filter(v=>v.monitor===r.name&&v.cohort==='changed');return {name:r.name,post:m.filter(v=>v.delay!==null).length,silent:m.filter(v=>v.first===null).length,premature:m.filter(v=>v.first!==null&&v.onset!==null&&v.first<v.onset).length,unclassified:m.filter(v=>v.first!==null&&v.onset===null).length,actionable:m.filter(v=>v.flags.miss===0&&Number(v.rows[0]?.need)===1).length}})
  const report={status,mode,regime:benchmark?regime:importScenario,confidence:benchmark ? .95:qualified?confidence:null,
    exposure:benchmark?80:exposure,budgets,resource:useResource?resource:null,results:result.rows.map(r=>({...r,status:disposition(r)})),pairs:result.pairs,
    inner:certified?decision.inner.map(r=>r.name):[],outer:certified?decision.outer.map(r=>r.name):[],candidateGap:winner?decision.gap:null,classGap:winner?decision.classGap:null}
  const changeBudget=(k:Loss,v:number)=>setBudgets({...budgets,[k]:Math.max(0,Math.min(1,v))})
  return <><Header eyebrow="MISSION DECISION" title="Evaluation and selection">Set the mission budgets and compare frozen monitoring policies using complete-mission evidence.</Header>
    <div className="segmented" aria-label="Evidence source">{['Benchmark','Active simulation','Imported missions'].map(m=><button key={m} aria-pressed={mode===m} onClick={()=>setMode(m)}>{m}</button>)}</div>
    {mode==='Active simulation'?<Exploratory config={config}/>:<>
    {!benchmark&&<Importer accept={(m,q)=>{setMissions(m);setQualified(q);setImportScenario(m[0]?.scenario??'')}}/>}
    {!benchmark&&exposure.length>1&&<p role="alert">This scenario contains multiple exposure horizons. Import one common horizon per scenario.</p>}
    <div className="decision-grid">
      <aside className="panel controls"><h2>Requirements</h2>
        {benchmark?<><Pick label="Validation regime" value={regime} options={Object.keys(paper?.design.scenarios??{[regime]:null})} onChange={setRegime}/>
        <Pick label="Frozen calibration target" value={String(cap)} options={['0.005','0.02','0.08']} onChange={s=>{setCap(+s);changeBudget('fa',+s)}}/>
        <details><summary>Candidate menu</summary>{monitors.map(m=><label key={m} className="check"><input type="checkbox" checked={menu.includes(m)} onChange={e=>setMenu(e.target.checked?[...menu,m]:menu.filter(n=>n!==m))}/>{m}</label>)}</details></>:<>
        {!!missions.length&&<Pick label="Imported scenario" value={importScenario} options={[...new Set(missions.map(m=>m.scenario))]} onChange={setImportScenario}/>}
        <Num label="Joint confidence (%)" value={confidence*100} min={50} max={99.99} step={.1} onChange={v=>setConfidence(Math.min(.9999,Math.max(.5,v/100)))}/></>}
        {losses.map(k=><Num key={k} label={metrics[k]+' budget (%)'} value={+(100*budgets[k]).toFixed(6)} min={0} max={100} step={.1} onChange={v=>changeBudget(k,v/100)}/>)}
        <label className="check"><input type="checkbox" checked={useResource} onChange={e=>setUseResource(e.target.checked)}/> Apply resource constraint</label>
        {useResource&&<Num label="Maximum state slots" value={resource} min={0} max={10000} onChange={v=>setResource(Math.max(0,v))}/>}
      </aside>
      <div className="stack"><section className="panel decision">
        <span className={`badge ${winner?'safe':''}`}>{benchmark?'95% simultaneous confidence · synthetic':qualified?'Confidence-bound result · declared assumptions':'Empirical evidence only'}</span>
        <h2>{status}</h2>
        {loadError&&benchmark&&<p role="alert">The frozen data failed to load. Reload to retry.</p>}
        <p>{winner?`${winner.name} has the lowest hazard upper bound among certified feasible policies. ${decision.unique?'Every possible rival is strictly separated on the hazard criterion.':'The available bounds leave the ordering of possible rivals unresolved.'}`:decision.outer.length&&certified?'Every possibly feasible candidate has at least one unresolved budget.':'A selection requires complete evidence and a candidate whose upper bounds satisfy every budget.'}</p>
        <div className="readouts"><div><small>Exposure</small><strong>{benchmark?'80 epochs':exposure.length===1?exposure[0]+' s':'—'}</strong></div><div><small>Best feasible candidate risk</small><strong>{winner&&decision.optimum?decision.optimum.map(pct).join(' – '):'—'}</strong></div><div><small>Candidate excess upper bound</small><strong>{winner?pct(decision.gap):'—'}</strong></div><div><small>Admissible-class gap</small><strong>{winner?pct(decision.classGap):'—'}</strong></div></div>
        {decision.conflict&&<p role="alert">The class lower bound exceeds the selected upper bound. Review the assumptions.</p>}
        <p className="hint">{benchmark?'Frozen thresholds and 12,000 held-out missions per law. The analytical class envelope applies only under the benchmark physical and observation assumptions, at or below the calibrated false-alert cap.':'Unknown outcomes have interval [0, 1]. The chosen budgets apply to the imported policy and fixed-deadline labels.'}</p></section>
      <section className="panel detail"><h2>Candidate comparison</h2><p>Empirical estimate [simultaneous interval]. A missing outcome or unqualified cohort uses the uncertainty envelope [0%, 100%].</p>
      <Table rows={result.rows.map(r=>({'Monitor':r.name,...Object.fromEntries(losses.map(l=>[metrics[l],`${pct(r.estimates[l])} [${r.bounds[l].map(pct).join(', ')}]`])),
       'Slots':r.cost,'Decision':disposition(r)}))}/>
      <div className="actions"><button onClick={()=>download('alert-evaluation.json',JSON.stringify(report,null,2),'application/json')}>Export metrics and decision</button>
      <button onClick={()=>download('alert-evaluation-report.md',`# ALERT Lab mission evaluation\n\n${status}\n\nEvidence: ${mode}\n\n`+Object.entries(report).map(([k,v])=>`- ${k}: ${JSON.stringify(v)}`).join('\n'),'text/markdown')}>Download report</button></div></section>
      </div></div>
    {!!result.rows.length&&<div className="two report-panels">
      <section className="panel detail"><h2>Feasibility plane</h2><p>Horizontal axis is false alerts. Vertical axis is hazard. Boxes span simultaneous bounds. Missed windows and slots apply in the comparison table.</p>
      <svg viewBox="0 0 400 235" role="img" aria-label="False alarm and hazard interval diagram" className="feasibility">
        <rect x="47" y={195-160*budgets.risk} width={320*budgets.fa} height={160*budgets.risk} fill={colors.protected} opacity=".22"/>
        <path d="M47 29V195H373" stroke={colors.muted} fill="none"/><text x="47" y="218">0%</text><text x="337" y="218">100%</text><text x="6" y="42">100%</text>
        {result.rows.map((r,i)=>{const [x,y]=r.bounds.fa,[l,u]=r.bounds.risk;return <g key={r.name}><rect x={47+x*320} y={195-u*160} width={Math.max(1,320*(y-x))} height={Math.max(1,160*(u-l))} fill="none" stroke={Object.values(colors)[i%6]}/><title>{r.name}</title></g>})}
      </svg><p>Possible feasible Pareto set: {certified?decision.pareto.map(r=>r.name).join(', ')||'empty':'unresolved'}.</p></section>
      <section className="panel detail"><h2>Paired risk differences</h2><p>First policy minus second policy on the same missions. An upper endpoint below zero supports lower risk for the first policy.</p>
      {result.pairs.length?<Table rows={result.pairs.map(p=>({A:p.a,B:p.b,loss:metrics[p.metric],lower:pct(p.range[0]),upper:pct(p.range[1])}))}/>:<p>No qualified paired contrasts.</p>}</section>
    </div>}
    {benchmark&&paper&&<section className="panel detail"><h2>Operating-regime sensitivity</h2>
      <p>The same mission requirements below are applied across frozen regimes. Each row evaluates the thresholds calibrated for that regime and target. Inspect the evidence page for the frozen hazard-only comparison.</p>
      <details><summary>Inspect recommendations across all 12 regimes</summary><Table rows={Object.keys(paper.design.scenarios).map(name=>{
        const options:Candidate[]=paper.coordinates.filter(r=>r.scenario===name&&r.false_alarm_cap===cap&&menu.includes(r.method)).map(r=>({
          name:r.method,cost:r.slots,bounds:Object.fromEntries(losses.map(k=>[k,[r[`${k}_lo`],r[`${k}_up`]]])) as Candidate['bounds'],
          estimates:Object.fromEntries(losses.map(k=>[k,r[`${k}_k`]/paper.design.heldout_per_law])) as Candidate['estimates']
        }))
        const contrasts:Pair[]=paper.pairs.filter(r=>r.scenario===name&&r.cap===cap).map(r=>({a:r.A,b:r.B,metric:'risk',range:[r.lower,r.upper]}))
        const d=select(options,budgets,useResource?resource:null,contrasts)
        return {regime:name,chosen:d.best?.name??(d.outer.length?'Unresolved':'Infeasible'),certified_feasible:d.inner.map(r=>r.name).join(', '),possibly_feasible:d.outer.map(r=>r.name).join(', '),gap:pct(d.gap)}
      })}/></details></section>}
    {hist&&<section className="panel detail"><h2>Actionable warnings and detection delay</h2><p>Actionable probability is conditional on an untreated crossing. Delay uses post-onset detections. Premature and silent paths retain their own counts.</p>
    <Table rows={result.rows.map(r=>{const h=hist[r.name]?.[String(cap)],need=paper!.design.scenarios[regime].untreated_hazards;return {monitor:r.name,actionable_given_need:h&&need?pct(h.actionable/need):'—',actionable:h?.actionable,required_episode:need,post_onset:h?.post,premature:h?.premature,silent_through_exposure:h?.silent}})}/>
    <Plot title="Post-onset detection delay distribution" unit="epochs since onset" times={Array.from({length:80},(_,i)=>i)} series={result.rows.map((r,i)=>({name:r.name,color:Object.values(colors)[i],values:hist[r.name][String(cap)].histogram}))}/></section>}
    {!benchmark&&!!activeMissions.length&&<section className="panel detail"><h2>Recorded alert histories</h2><Table rows={importHist}/><p>Counts are descriptive. An alert after onset has a delay, while a silent mission is right-censored at its listed horizon.</p>
    <Table limit={30} rows={activeMissions.map(m=>({mission:m.id,monitor:m.monitor,cohort:m.cohort,first_alarm:m.first,delay:m.delay,deadline:m.deadline,hazard:m.flags.risk,source:m.source}))}/>
    <ImportedTrace missions={activeMissions}/>
    <button onClick={()=>download('alert-imported-normalized.json',JSON.stringify({rows:activeMissions.flatMap(m=>m.rows)},null,2),'application/json')}>Export normalized histories</button></section>}
    </>}
  </>
}
