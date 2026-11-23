import {createContext,useContext,type ReactNode} from 'react'
import katex from 'katex'
import {type Config,type Monitor,type Published,type Run} from './engine'
export type Paper={
  design:{seed:number;epochs:number;calibration:number;heldout_per_law:number;simultaneous_statements:number;scenarios:Record<string,Published&{untreated_hazards:number}>}
  coordinates:({scenario:string;method:Monitor;false_alarm_cap:number;slots:number}&Record<`${'fa'|'miss'|'risk'}_${'k'|'lo'|'up'}`,number>)[]
  pairs:{scenario:string;cap:number;A:string;B:string;lower:number;upper:number}[]
  thresholds:{scenario:string;method:Monitor;budget:number;threshold:number}[]
  limits:{scenario:string;fa_cap:number;admissible_lower:number}[]
  decisions:Record<string,string|number>[];baseline:Record<string,string|number>[];
  clock:Record<string,string|number>[];crossing:Record<string,string|number>[];
  error:Record<string,string|number>[];oracle:Record<string,string|number>[];
  frontier:Record<string,string|number>[];regret:Record<string,string|number>[]
}
export const dataUrl=(path:string)=>import.meta.env.BASE_URL+'data/'+path
const sources=[
  ['Manuscript PDF',dataUrl('Alert_TAES_Manuscript.pdf')],
  ['Mathematical supplement PDF',dataUrl('Alert_TAES_Supplement.pdf')],
  ['Original research package','https://chatgpt.com/library?file_id=libfile_44f1f4edfbe881918d00eb6aaaf62824&account_id=personal'],
] as const
export function Sources(){return <div className="actions">{sources.map(([label,url])=><a key={url} className="button" href={url} target="_blank" rel="noreferrer">{label}</a>)}</div>}
export const Lab=createContext<{
  config:Config;setConfig:(c:Config)=>void;run:Run;paper:Paper|null;loadError:boolean;
  regime:string;setRegime:(s:string)=>void;cap:number;setCap:(n:number)=>void;
  index:number;setIndex:(i:number)=>void;limit:number;threshold:number
}|null>(null)
export const useLab=()=>useContext(Lab)!
export const pct=(n:number|null|undefined)=>n==null?'—':(n*100).toFixed(n>0&&n<.01?3:2)+'%'
export function Header({eyebrow,title,children}:{eyebrow:string;title:string;children:ReactNode}){
  return <header className="pagehead"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{children}</p></header>
}
export function Eq({tex}:{tex:string}){
  return <div className="equation" dangerouslySetInnerHTML={{__html:katex.renderToString(tex,{displayMode:true,throwOnError:true})}}/>
}
export function Num({label,value,step=1,min,max,onChange}:{label:string;value:number;step?:number;min:number;max:number;onChange:(n:number)=>void}){
  return <label className="field">{label}<input type="number" value={value} min={min} max={max} step={step} onChange={e=>{if(e.target.value!==''&&Number.isFinite(e.target.valueAsNumber))onChange(e.target.valueAsNumber)}}/></label>
}
export function Pick({label,value,options,onChange}:{label:string;value:string;options:(string|[string,string])[];onChange:(s:string)=>void}){
  return <label className="field">{label}<select aria-label={label} value={value} onChange={e=>onChange(e.target.value)}>{options.map(p=>typeof p==='string'?<option key={p}>{p}</option>:<option value={p[0]} key={p[0]}>{p[1]}</option>)}</select></label>
}
export function Table({rows,columns,limit=100}:{rows:Record<string,unknown>[];columns?:string[];limit?:number}){
  const keys=columns??Object.keys(rows[0]??{})
  return <div className="table-scroll"><table><thead><tr>{keys.map(k=><th key={k}>{k.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{rows.slice(0,limit).map((r,i)=><tr key={i}>{keys.map(k=><td key={k}>{typeof r[k]==='number'?Number((r[k] as number).toPrecision(7)).toString():String(r[k]??'—')||'—'}</td>)}</tr>)}</tbody></table></div>
}
