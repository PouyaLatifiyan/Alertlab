import {createRoot} from 'react-dom/client'
import {useEffect,useMemo,useState} from 'react'
import {BrowserRouter,Link,NavLink,Route,Routes,useLocation} from 'react-router-dom'
import {Home,Scenarios} from './scenarios'
import {Simulator,Signals} from './simulation'
import {Framework,Evidence,Documentation} from './research'
import {Evaluation} from './evaluation'
import {Lab,dataUrl,type Paper} from './common'
import {defaults,publishedReplay,simulate,type Config} from './engine'
import 'katex/dist/katex.min.css'
import './style.css'

const nav=[['/','Home'],['/framework','Framework'],['/scenarios','Scenarios'],['/simulator','Simulator'],['/signals','Signals'],['/evaluation','Evaluation'],['/evidence','Evidence'],['/documentation','Docs']]
function stored<T>(key:string,fallback:T):T{
  try{return JSON.parse(localStorage.getItem(key)??'null')??fallback}catch{return fallback}
}
function persist(key:string,value:unknown){try{localStorage.setItem(key,JSON.stringify(value))}catch{/* Browser storage is optional. */}}
function App(){
  const [config,setConfig]=useState<Config>(()=>({...defaults(),...stored('alert.config',{})}))
  const [regime,setRegime]=useState(()=>stored('alert.regime','moderate persistent'))
  const [cap,setCap]=useState(()=>stored('alert.cap',.02))
  const [theme,setTheme]=useState(()=>stored('alert.theme','dark'))
  const [menu,setMenu]=useState(false)
  const [index,setIndex]=useState(0)
  const [paper,setPaper]=useState<Paper|null>(null),[loadError,setLoadError]=useState(false)
  const location=useLocation()
  useEffect(()=>{
    const ac=new AbortController()
    fetch(dataUrl('paper.json'),{signal:ac.signal}).then(r=>{if(!r.ok)throw Error('Failed to load frozen data');return r.json()}).then(setPaper).catch(e=>{if(e.name!=='AbortError')setLoadError(true)})
    return()=>ac.abort()
  },[])
  useEffect(()=>{document.documentElement.dataset.theme=theme;persist('alert.theme',theme)},[theme])
  useEffect(()=>{persist('alert.config',config);persist('alert.regime',regime);persist('alert.cap',cap)},[config,regime,cap])
  useEffect(()=>{setMenu(false);window.scrollTo(0,0);document.title=`${nav.find(([path])=>path===location.pathname.replace(/\/$/,'')||path===location.pathname)?.[1]??'Research'} · ALERT Lab`},[location.pathname])
  const configRun=useMemo(()=>{
    if(config.scenario==='published'&&paper?.design.scenarios[regime]){
      const th=paper.thresholds.find(t=>t.scenario===regime&&t.budget===cap&&t.method===config.monitor)
      if(th){const r=publishedReplay(config,paper.design.scenarios[regime],th.threshold);return {run:r,limit:r.limit,threshold:th.threshold}}
    }
    return {run:simulate(config),limit:config.limit,threshold:config.threshold}
  },[config,paper,regime,cap])
  return <Lab.Provider value={{config,setConfig,paper,loadError,regime,setRegime,cap,setCap,index:Math.max(0,Math.min(index,configRun.run.frames.length-1)),setIndex,...configRun}}>
    <a className="skip" href="#content">Skip to content</a>
    <header className="shell"><div className="shell-inner">
      <Link className="brand" to="/"><svg viewBox="0 0 36 36" aria-hidden="true"><rect x="1" y="1" width="34" height="34" rx="9"/><path d="M9 23l5-7 4 4 7-9m-5 0h5v5M9 27h18"/></svg><span>ALERT<span> Lab</span></span></Link>
      <button className="mobile-menu" aria-expanded={menu} aria-controls="primary-nav" onClick={()=>setMenu(m=>!m)}>Menu</button>
      <nav id="primary-nav" className={menu?'open':''} aria-label="Main navigation">{nav.map(([path,name])=><NavLink end to={path} key={path}>{name}</NavLink>)}</nav>
      <button className="theme" aria-label={theme==='dark'?'Switch to light appearance':'Switch to dark appearance'} onClick={()=>setTheme(theme==='dark'?'light':'dark')}>{theme==='dark'?'☼':'◐'}</button>
    </div></header>
    <main id="content"><Routes>
      <Route path="/" element={<Home/>}/><Route path="/framework" element={<Framework/>}/><Route path="/scenarios" element={<Scenarios/>}/><Route path="/simulator" element={<Simulator/>}/><Route path="/signals" element={<Signals/>}/><Route path="/evaluation" element={<Evaluation/>}/><Route path="/evidence" element={<Evidence/>}/><Route path="/documentation" element={<Documentation/>}/><Route path="*" element={<div className="panel detail"><h1>Page unavailable</h1><Link to="/">Return to research home</Link></div>}/>
    </Routes></main>
    <footer className="footer"><span>ALERT Lab · Mission-aware monitoring evaluation</span><Link to="/documentation">Model and data provenance</Link></footer>
  </Lab.Provider>
}
createRoot(document.getElementById('root')!).render(<BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/,'')}><App/></BrowserRouter>)
