import {Link,useNavigate} from 'react-router-dom'
import {Header,useLab,Eq,Sources} from './common'
import {defaults,simulate,type Scenario} from './engine'
import {Trajectory} from './visuals'
import {useEffect,useMemo,useState} from 'react'

export const scenarios={
  spoofing:{name:'GNSS spoofing',kind:'Observation bias',description:'Inspect how a signed observation bias drives navigation error in a local ENU frame.',model:'Persistent or ramped bias in position measurements. Independent aiding may constrain the position error.',failure:'A slowly moving bias can push the estimate across the error limit while the normalized innovation stays small.',channels:'GNSS position, east innovation, inertial increments',color:'#f2a26e',icon:'↗'},
  jamming:{name:'GNSS jamming',kind:'Interference and outage',description:'Explore degradation, loss of fixes, inertial drift and receiver recovery.',model:'An illustrative effective quality loss inflates variance and removes GNSS fixes below a tracking threshold. GNSS measurements carry zero added position bias.',failure:'Measurement-dependent monitors receive no updates in an outage. Inertial errors accumulate while fixes are unavailable.',channels:'Quality proxy, observation availability, residual when present',color:'#7db2f5',icon:'≋'},
  hybrid:{name:'Hybrid GNSS / IMU / 5G',kind:'Multi-sensor fallback',description:'Compare navigation error while changing aiding availability, update schedules and intervention.',model:'Independent position observations are fused with inertial increments. The 5G channel represents an illustrative position aid with configurable variance.',failure:'Aiding can contain drift during an outage. Poor aiding or a delayed response can still leave a limit crossing.',channels:'GNSS position, inertial increments, optional 5G position aid',color:'#77d6aa',icon:'◇'}
} as const
export function Home(){
  const c=useMemo(()=>({...defaults(),bias:3,drift:.24,threshold:8,latency:6}),[])
  const run=useMemo(()=>simulate(c),[c])
  const [i,setI]=useState(Math.round(c.onset/c.dt))
  const [playing,setPlaying]=useState(()=>!matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(()=>{if(playing){const id=setInterval(()=>setI(i=>(i+1)%run.frames.length),100);return ()=>clearInterval(id)}},[run,playing])
  const f=run.frames[i]
  return <>
    <section className="hero">
      <div className="hero-copy"><span className="eyebrow">MISSION-AWARE MONITORING EVALUATION</span><h1>ALERT <em>Lab</em></h1>
      <h2>A Unified Mathematical Framework for Evaluating Detection Reliability, Alert Timeliness, and Safety in Dynamical Systems</h2>
      <p>We evaluate existing monitoring systems to determine whether their warnings are trustworthy, timely, and capable of supporting physical safety under specified mission conditions.</p>
      <div className="actions"><Link className="button primary" to="/simulator">Open simulator</Link><Link className="button" to="/evaluation">Compare monitors</Link></div>
      <div className="byline">Research by <strong>Pouya Latifiyan</strong> and <strong>Yanhong Kou</strong></div></div>
      <div className="hero-figure panel">
        <div className="sectionbar"><strong>Intervention window</strong><span className="badge">Simulated demonstration</span></div>
        <Trajectory run={run} index={i} limit={c.limit} hero/>
        <div className="hero-metrics"><div><small>Position error</small><strong>{f.error.toFixed(2)} m</strong></div><div><small>Hazard limit</small><strong>{c.limit.toFixed(1)} m</strong></div><div><small>Dispatch margin</small><strong>{run.deadline===null?'—':(run.deadline-f.t).toFixed(1)+' s'}</strong></div><button onClick={()=>setPlaying(p=>!p)} aria-label={playing?'Pause demonstration':'Play demonstration'}>{playing?'Ⅱ':'▶'}</button></div>
      </div>
    </section>
    <div className="sectionbar lower"><h2>Three constraints, one mission</h2><Link to="/framework">Mathematical framework</Link></div>
    <div className="cards pillars">
      {[['Reliability','How often does a monitor interrupt healthy operation during the specified exposure?','◉'],['Timeliness','Does the warning arrive while the specified response can still complete in time?','◷'],['Safety','After the response, does the state remain within the physical limits?','◇']].map(([title,body,icon])=><article className="panel" key={title}><span className="symbol">{icon}</span><h3>{title}</h3><p>{body}</p></article>)}
    </div>
    <section className="panel callout"><div><h2>Select for the mission</h2><p>Compare frozen monitor–response policies using the same mission definition. A fast alarm can still exceed the healthy alert budget, miss the response window, or trigger an action that fails to contain the hazard.</p></div><Link className="button" to="/scenarios">Scenario library</Link></section>
    <Sources/>
  </>
}
export function Scenarios(){
  const nav=useNavigate(),{setConfig,paper}=useLab()
  const [selected,setSelected]=useState<keyof typeof scenarios>('spoofing')
  const s=scenarios[selected]
  const load=(scenario:Scenario)=>{setConfig(defaults(scenario));nav('/simulator')}
  return <><Header eyebrow="MISSION DESIGN" title="Scenario library">Choose a physical disturbance and an observation model before you compare monitoring policies.</Header>
    <div className="cards">{Object.entries(scenarios).map(([id,v])=><button className={`scenario panel ${selected===id?'selected':''}`} onClick={()=>setSelected(id as keyof typeof scenarios)} key={id} style={{'--scenario':v.color} as React.CSSProperties}>
      <span className="scenario-icon">{v.icon}</span><span className="eyebrow">{v.kind}</span><h2>{v.name}</h2><p>{v.description}</p></button>)}</div>
    <article className="panel detail"><div className="sectionbar"><h2>{s.name}</h2><span className="badge">Exploratory model</span></div>
    <div className="two"><div><h3>Physical model</h3><p>{s.model}</p><h3>Observation channels</h3><p>{s.channels}</p></div><div><h3>Failure mechanism</h3><p>{s.failure}</p><h3>Hazard and response</h3><p>A hazard occurs when 3D position error reaches the configured limit. An alarm can dispatch fallback, subject to its latency and configured effectiveness.</p></div></div>
    <Eq tex={selected==='spoofing'?String.raw`y_k=x_k+[1,0.35,0.15]^\top b_k+\epsilon_k`:selected==='jamming'?String.raw`\sigma_k=\sigma_0 10^{(44-q_k)/20},\qquad y_k\text{ missing if }q_k<q_{\mathrm{track}}`:String.raw`\hat x_k=\hat x_k^-+K_g(y_k-\hat x_k^-),\qquad \hat x_k\leftarrow \hat x_k+K_r(y_k^r-\hat x_k)`}/>
    <p>Shewhart, CUSUM, GLR16 and RankRestart can be inspected on available east innovations. The benchmark thresholds and confidence statements apply only to their frozen scalar test laws. Adjust disturbance, sensor rates, receiver or aiding quality, the error limit and response settings in the Simulator.</p>
    <button className="primary" onClick={()=>load(selected)}>Load {s.name}</button></article>
    <section className="panel callout"><div><h2>Manuscript benchmark</h2><p>{paper?.design.epochs??80} epochs · 12 validated synthetic regimes · frozen thresholds and scalar physical dynamics.</p></div><button onClick={()=>load('published')}>Load benchmark model</button></section>
  </>
}
