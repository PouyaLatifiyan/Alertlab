import {useEffect,useMemo,useState} from 'react'
import {defaults,monitors,simulate,type Config,type Scenario} from './engine'
import {Header,Num,Pick,useLab} from './common'
import {colors,download,getSeries,Plot,Trajectory} from './visuals'
import {scenarios} from './scenarios'

const labels={truth:'True trajectory',estimate:'Unprotected estimate',protected:'Protected estimate',measurement:'GNSS observations'}
const parameters:[keyof Config,string,number,number,number][]=[
  ['duration','Mission duration (s)',20,240,1],['dt','Simulation step (s)',.1,2,.1],['seed','Random seed',0,4294967295,1],
  ['onset','Disturbance onset (s)',0,240,.5],['span','Disturbance duration (s)',1,240,.5],['bias','Initial east bias (m)',-30,30,.1],['drift','East bias drift (m/s)',-3,3,.01],
  ['severity','Quality loss proxy (dB)',0,40,1],['tracking','Tracking threshold (proxy dB-Hz)',5,60,1],
  ['sigma','Nominal GNSS noise (m)',.1,10,.1],['gnssRate','GNSS rate (Hz)',.05,10,.05],['availability','Baseline fix probability',0,1,.01],['imuDrift','Inertial east drift (m/s)',-3,3,.005],
  ['radioRate','5G update rate (Hz)',0,10,.1],['radioSigma','5G position noise (m)',.1,20,.1],['gain','Correction gain',.01,1,.01],
  ['limit','Position-error limit (m)',.5,40,.1],['latency','Action latency (s)',0,60,.5],['effectiveness','Fallback weight',0,1,.05],['threshold','Alarm threshold',-5,200,.1]
]
function Regime(){
  const {paper,regime,setRegime,cap,setCap}=useLab()
  return <><Pick label="Frozen regime" value={regime} options={Object.keys(paper?.design.scenarios??{[regime]:null})} onChange={setRegime}/>
    <Pick label="Calibration target" value={String(cap)} options={['0.005','0.02','0.08']} onChange={s=>setCap(+s)}/></>
}
function Controls(){
  const {config:c,setConfig:set,setIndex,threshold}=useLab()
  const published=c.scenario==='published'
  const interference=c.scenario==='jamming'||(c.scenario==='hybrid'&&c.disturbance==='interference')
  const shown=parameters.filter(([k])=>published?k==='seed':(['bias','drift'].includes(k)?!interference:['severity','tracking'].includes(k)?interference:['radioRate','radioSigma'].includes(k)?c.scenario==='hybrid':true))
  return <aside className="panel controls">
    <div className="sectionbar"><h2>Mission inputs</h2></div>
    <Pick label="Scenario" value={c.scenario} options={[...Object.entries(scenarios).map(([k,v])=>[k,v.name] as [string,string]),['published','Published scalar model']]} onChange={s=>{set(defaults(s as Scenario));setIndex(0)}}/>
    <Pick label="Existing monitor" value={c.monitor} options={[...monitors]} onChange={s=>set({...c,monitor:s as Config['monitor']})}/>
    {published?<><Regime/><p>Frozen threshold <strong>{threshold.toPrecision(5)}</strong>. Seed changes the browser demonstration only.</p></>:<>
      {c.scenario==='hybrid'&&<Pick label="Disturbance type" value={c.disturbance} options={['bias','interference']} onChange={s=>set({...c,disturbance:s as Config['disturbance']})}/>}
      <Pick label="Protection policy" value={c.fallback} options={c.scenario==='hybrid'?['inertial','hold','radio']:['inertial','hold']} onChange={s=>set({...c,fallback:s as Config['fallback']})}/></>}
    <div className="inputs">{shown.map(([key,label,min,max,step])=><Num key={key} label={label} value={c[key] as number} min={min} max={key==='onset'?c.duration:max} step={step} onChange={v=>set({...c,[key]:Math.max(min,Math.min(key==='onset'?c.duration:max,key==='seed'?Math.round(v):v)),...(key==='duration'?{onset:Math.min(c.onset,v)}:{})})}/>)}</div>
    {!published&&(c.gnssRate>1/c.dt||(c.scenario==='hybrid'&&c.radioRate>1/c.dt))&&<p className="hint">A channel can supply at most one fix per simulation step.</p>}
    <div className="actions"><button onClick={()=>{set(defaults(c.scenario));setIndex(0)}}>Reset scenario</button><button onClick={()=>{set(defaults('published'));setIndex(0)}}>Load published model</button></div>
  </aside>
}
export function Simulator(){
  const {run,config,index:i,setIndex,limit,threshold,regime,cap,paper}=useLab()
  const [playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1)
  const [layers,setLayers]=useState({truth:true,estimate:true,protected:true,measurement:false})
  const times=useMemo(()=>run.frames.map(f=>f.t),[run])
  const step=run.units==='m'?config.dt:1
  useEffect(()=>{if(playing){const id=setTimeout(()=>{if(i>=times.length-1)setPlaying(false);else setIndex(i+1)},Math.max(16,step*1000/speed));return()=>clearTimeout(id)}},[i,playing,speed,step,times.length,setIndex])
  const f=run.frames[i]
  const events=[{t:run.onset,name:'Onset',color:colors.threshold},{t:run.alarm,name:'First alarm',color:colors.measurement},{t:run.deadline,name:'Dispatch deadline',color:colors.estimate},{t:run.completion,name:'Completion',color:colors.protected}]
  const position=(j:number)=>[getSeries(run.frames,'Truth',colors.truth,f=>f.truth[j]),getSeries(run.frames,'Estimate',colors.estimate,f=>f.estimate[j]),getSeries(run.frames,'Protected',colors.protected,f=>f.protected[j])]
  const line=(v:number,name:string)=>getSeries(run.frames,name,colors.threshold,()=>v)
  const unit=run.units==='m'?'s':'epochs'
  const stamp=(v:number|null)=>v===null?'—':v.toFixed(2)+' '+unit
  return <><Header eyebrow="INTERACTIVE MISSION" title="Trajectory simulator">Follow the simulated state, alarm, and intervention on a shared time axis.</Header>
  {config.scenario==='published'&&!paper?<p className="panel detail" role="status">The published configuration is unavailable. Select an exploratory scenario to continue locally.</p>:null}
  <div className="sim-grid"><Controls/><div className="stack">
    <section className="panel"><div className="sectionbar"><h2>State in 3D</h2><span className="badge">{run.units==='m'?'Exploratory demonstration':'Frozen-model demonstration'}</span></div>
      <Trajectory run={run} index={i} limit={limit} layers={layers}/>
      <div className="toolbar">{Object.entries(layers).map(([k,v])=><label key={k} className="check"><input type="checkbox" checked={v} onChange={e=>setLayers({...layers,[k]:e.target.checked})}/><i style={{background:colors[k as keyof typeof colors]}}/>{labels[k as keyof typeof labels]}</label>)}</div>
      <div className="playback"><button onClick={()=>{if(i===times.length-1)setIndex(0);setPlaying(p=>!p)}}>{playing?'Pause':'Play'}</button><button onClick={()=>{setIndex(0);setPlaying(false)}}>Reset</button>
        <input aria-label="Time cursor" type="range" min={0} max={times.length-1} value={i} onChange={e=>setIndex(+e.target.value)}/>
        <output>{stamp(f.t)}</output><select aria-label="Playback speed" value={speed} onChange={e=>setSpeed(+e.target.value)}>{[.5,1,2,5,10].map(r=><option key={r} value={r}>{r}×</option>)}</select>
      </div>
      <div className="readouts">{[['Onset',run.onset],['Alarm',run.alarm],['Last useful dispatch',run.deadline],['Completion',run.completion]].map(([k,v])=><div key={k}><small>{k}</small><strong>{stamp(v as number|null)}</strong></div>)}</div>
    </section>
    <section className="panel detail">
    <div className="sectionbar"><h2>Mission outcome</h2><span className={`badge ${run.hazard?'danger':'safe'}`}>{run.hazard?'Hazard reached':'Within limit on this run'}</span></div>
    <p>{run.opportunity===null?'No untreated threshold crossing in the simulated horizon.':run.opportunity?'Dispatch fell inside the actionable window.':'The actionable window was missed.'} The protected trajectory is computed separately from timing eligibility.</p>
    <div className="readouts"><div><small>Truth · {run.units}</small><strong>{f.truth.map(v=>v.toFixed(2)).join(' / ')}</strong></div><div><small>Estimate · {run.units}</small><strong>{f.estimate.map(v=>v.toFixed(2)).join(' / ')}</strong></div><div><small>Truth velocity · {run.units}/{unit}</small><strong>{f.velocity.map(v=>v.toFixed(2)).join(' / ')}</strong></div><div><small>Estimated velocity · {run.units}/{unit}</small><strong>{f.estimatedVelocity.map(v=>v.toFixed(2)).join(' / ')}</strong></div></div>
    <div className="actions"><button onClick={()=>download('alert-trajectory.json',JSON.stringify({config,regime,cap,limit,threshold,run},null,2),'application/json')}>Export trajectory and config</button></div></section>
    <div className="stack">
      <Plot title="3D position-error norm" unit={run.units} times={times} cursor={i} onCursor={setIndex} events={events} series={[getSeries(run.frames,'Unprotected error',colors.estimate,f=>f.error),getSeries(run.frames,'Protected error',colors.protected,f=>f.protectedError),line(limit,'Hazard limit')]}/>
      <Plot title="Monitor statistic" unit="score" times={times} cursor={i} onCursor={setIndex} events={events} series={[getSeries(run.frames,config.monitor,colors.truth,f=>f.statistic),line(threshold,'Alarm threshold')]}/>
      <Plot title="East innovation or benchmark observation" unit={run.units} times={times} cursor={i} onCursor={setIndex} events={events} series={[getSeries(run.frames,'Innovation',colors.truth,f=>f.innovation)]}/>
      {run.frames.some(f=>f.quality!==null)&&<><Plot title="Effective tracking quality" unit="illustrative dB-Hz proxy" times={times} cursor={i} onCursor={setIndex} events={events} series={[getSeries(run.frames,'Quality proxy',colors.truth,f=>f.quality),line(config.tracking,'Tracking threshold')]}/><Plot title="GNSS fix availability" unit="0 / 1 per step" times={times} cursor={i} onCursor={setIndex} series={[getSeries(run.frames,'Usable fix',colors.protected,f=>Number(f.available))]}/></>}
      {['X','Y','Z'].map((k,j)=><Plot key={k} title={k+' position'} unit={run.units} times={times} cursor={i} onCursor={setIndex} events={events} series={position(j)}/>)}
    </div>
  </div></div></>
}
export function Signals(){
  const {run,config,index,setIndex}=useLab()
  const [signal,setSignal]=useState('Innovation'),[from,setFrom]=useState(0),[until,setUntil]=useState(240)
  const [show,setShow]=useState(true)
  const healthy=useMemo(()=>config.scenario==='published'?null:simulate(config,true),[config])
  const times=run.frames.map(f=>f.t)
  const foundStart=times.findIndex(t=>t>=from)
  const start=foundStart<0?times.length-1:foundStart, end=Math.max(start,times.findLastIndex(t=>t<=until))
  const unit=run.units==='m'?'s':'epochs'
  const extract=(f:typeof run.frames[number])=>signal==='Innovation'?f.innovation:signal==='Normalized residual'?f.residual:signal==='Position error'?f.error:signal==='State uncertainty proxy'?f.variance:signal==='Observation variance'?f.observationVariance:signal==='Quality proxy'?f.quality:signal==='GNSS east measurement'?f.measurement?.[0]??null:signal==='5G east measurement'?f.radio?.[0]??null:Number(f.available)
  const selected=run.frames.slice(start,end+1).map(extract)
  const vals=selected.filter((v):v is number=>v!==null)
  const low=Math.min(...vals),high=Math.max(...vals),width=Math.max((high-low)/16,1e-9)
  const bins=vals.length?Array.from({length:16},(_,i)=>low+width*i):[]
  const hist=bins.map((v,i)=>vals.filter(x=>x>=v&&(i===15||x<v+width)).length)
  const sorted=[...vals].sort((a,b)=>a-b)
  const mean=vals.reduce((a,b)=>a+b,0)/vals.length
  const denom=vals.reduce((a,b)=>a+(b-mean)**2,0)
  const lag=Array.from({length:Math.min(25,selected.length)},(_,i)=>i)
  const acf=lag.map(k=>{
    const pairs=selected.flatMap((b,i)=>b!==null&&i>=k&&selected[i-k]!==null?[(b-mean)*(selected[i-k]!-mean)]:[])
    return !pairs.length||!denom?null:pairs.reduce((a,b)=>a+b,0)/denom
  })
  return <><Header eyebrow="SIGNAL PROCESSING" title="Signal and state analysis">Inspect observation gaps, residual distributions and temporal dependence within a mission.</Header>
    <div className="panel toolbar"><Pick label="Channel" value={signal} options={['Innovation','Normalized residual','Position error','State uncertainty proxy','Observation variance','Quality proxy','GNSS east measurement','5G east measurement','GNSS available']} onChange={setSignal}/>
    <Num label={`From (${unit})`} value={from} min={0} max={until} onChange={v=>setFrom(Math.max(0,Math.min(v,until,times.at(-1)!)))}/><Num label={`To (${unit})`} value={until} min={from} max={240} onChange={v=>setUntil(Math.max(from,Math.min(v,240)))}/>
    <label className="check"><input type="checkbox" disabled={!healthy} checked={show&&!!healthy} onChange={e=>setShow(e.target.checked)}/> Healthy counterfactual</label>
    <button onClick={()=>download('alert-signal-window.csv','time,value\n'+selected.map((v,i)=>[times[i+start],v].join(',')).join('\n'),'text/csv')}>Export window</button></div>
    <div className="stack">
    <Plot title={signal} unit={unit+' on horizontal axis'} times={times} cursor={index} onCursor={setIndex} domain={[start,end]} events={[{t:run.onset,name:'Change onset',color:colors.threshold},{t:run.alarm,name:'First alarm',color:colors.estimate},{t:run.deadline,name:'Last useful dispatch',color:colors.protected}]} series={[getSeries(run.frames,'Selected mission',colors.truth,extract),...(show&&healthy?[getSeries(healthy.frames,'Healthy, same seed',colors.protected,extract)]:[])]}/>
    <div className="two">
      <Plot title="Empirical histogram" unit="count per bin" times={bins.length?bins:[0]} series={[{name:'Selected nonmissing epochs',color:colors.truth,values:hist.length?hist:[null]}]}/>
      <Plot title="Autocorrelation diagnostic" unit="lag in grid steps" times={lag} series={[{name:'Centered cross-products / total sum of squares',color:colors.measurement,values:acf}]}/>
    </div>
    <div className="two"><Plot title="Empirical cumulative distribution" unit="fraction of selected observations" times={sorted.length?sorted:[0]} series={[{name:'Empirical CDF',color:colors.truth,values:sorted.length?sorted.map((_,i)=>(i+1)/sorted.length):[null]}]}/>
     <Plot title="Frozen reference samples" unit="reference index" times={run.reference.map((_,i)=>i+1)} series={[{name:'Reference score input',color:colors.measurement,values:run.reference}]}/></div>
      <section className="panel detail"><h2>Window diagnostics</h2><p>{selected.length-vals.length} missing of {selected.length} selected epochs. The estimated dependence depends on the chosen window and missingness. Adjacent epochs can be correlated and provide no independent mission replication. Fitted autocorrelation does not certify the monitor.</p><p>Physical warning margin at cursor {run.deadline===null?'is unavailable.':`is ${(run.deadline-times[index]).toFixed(2)} ${unit}.`}</p></section>
    </div>
  </>
}
