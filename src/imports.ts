import Papa from 'papaparse'
import {cp,losses,type Candidate,type Loss,type Pair,type Interval} from './statistics.ts'
export type Raw=Record<string,unknown>
export const required=['mission_id','scenario','monitor','cohort','time_s','horizon_s','observation_status','alarm','source'] as const
export const optional=['onset_s','deadline_s','need','hazard','missed_window','cost_slots','dispatch','response_complete','x_m','y_m','z_m','vx_mps','vy_mps','vz_mps','ref_x_m','ref_y_m','ref_z_m','measurement','frame'] as const
export type Mission={id:string;scenario:string;monitor:string;cohort:'healthy'|'changed';horizon:number;source:string;cost:number|null;
  flags:Partial<Record<Loss,number>>;first:number|null;delay:number|null;onset:number|null;deadline:number|null;rows:Raw[]}

export function parseFile(text:string,filename:string):Raw[]{
  let rows:unknown
  if(filename.toLowerCase().endsWith('.json')){
    const parsed=JSON.parse(text)
    if(parsed?.schema_version!==undefined&&parsed.schema_version!==1)throw Error('Unsupported JSON schema_version. Expected 1.')
    rows=Array.isArray(parsed)?parsed:parsed?.rows
  }else{
    const out=Papa.parse(text,{header:true,skipEmptyLines:'greedy'})
    if(out.errors.length)throw Error(out.errors[0].message)
    if(Object.keys(out.meta.renamedHeaders??{}).length)throw Error('Duplicate CSV header.')
    rows=out.data
  }
  if(!Array.isArray(rows)||!rows.length||rows.length>100000||rows.some(r=>!r||typeof r!=='object'||Array.isArray(r)))throw Error('Expected 1–100,000 row objects.')
  return rows as Raw[]
}
const empty=(v:unknown)=>v===null||v===undefined||v===''
function numeric(v:unknown,label:string){
  if((typeof v!=='number'&&typeof v!=='string')||String(v).trim()===''||!Number.isFinite(Number(v)))throw Error(`${label} must be numeric with declared units.`)
  return Number(v)
}
function bit(v:unknown,label:string){
  if(v===true||v===1||v==='1')return 1
  if(v===false||v===0||v==='0')return 0
  throw Error(`${label} must be 0 or 1.`)
}
export function validate(rows:Raw[],mapping:Record<string,string>,frame:string):Mission[]{
  const groups=new Map<string,{mission:Mission;times:number[];alarms:number[];meta:string;need:number|null;hazard:number|null;miss:number|null}>()
  rows.forEach((raw,i)=>{
    const get=(key:string)=>raw[mapping[key]||key]
    try{
      const id=String(get('mission_id')??'').trim(), monitor=String(get('monitor')??'').trim()
      const scenario=String(get('scenario')??'').trim(),source=String(get('source')??'').trim()
      const cohort=get('cohort')
      if(!id||!monitor||!scenario||!source||!(cohort==='healthy'||cohort==='changed'))throw Error('Mission, scenario, monitor, source and healthy/changed cohort are required.')
      const t=numeric(get('time_s'),'time_s'),horizon=numeric(get('horizon_s'),'horizon_s')
      if(t<0||t>horizon||horizon<=0)throw Error('Time must lie in [0, horizon_s].')
      const numberOrNull=(k:string)=>empty(get(k))?null:numeric(get(k),k)
      const bitOrNull=(k:string)=>empty(get(k))?null:bit(get(k),k)
      const onset=numberOrNull('onset_s'), deadline=numberOrNull('deadline_s'), cost=numberOrNull('cost_slots'),need=bitOrNull('need'),hazard=bitOrNull('hazard'),miss=bitOrNull('missed_window')
      if(need===0&&miss===1)throw Error('A mission without a required episode cannot have a missed-window loss.')
      if((onset!==null&&(onset<0||onset>horizon))||(deadline!==null&&deadline>horizon)||(cost!==null&&cost<0))throw Error('Invalid onset, deadline, or resource cost.')
      if(get('observation_status')!=='valid'&&get('observation_status')!=='missing')throw Error('observation_status must be valid or missing.')
      if(!empty(get('frame'))&&get('frame')!==frame)throw Error('Coordinate frame must match the declared ENU or ECEF convention.')
      for(const vector of [['x_m','y_m','z_m'],['vx_mps','vy_mps','vz_mps'],['ref_x_m','ref_y_m','ref_z_m']]){
        const count=vector.filter(k=>!empty(get(k))).length
        if(count&&count!==3)throw Error('Position, velocity, and reference vectors require all three components.')
        if(count)vector.forEach(k=>numeric(get(k),k))
      }
      numberOrNull('measurement');bitOrNull('dispatch');bitOrNull('response_complete')
      const alarm=bit(get('alarm'),'alarm')
      const key=JSON.stringify([scenario,cohort,id,monitor])
      const meta=JSON.stringify([horizon,source,cost,onset,deadline,need,hazard,miss])
      if(!groups.has(key))groups.set(key,{mission:{id,monitor,scenario,cohort,source,horizon,cost,flags:{},first:null,delay:null,onset,deadline,rows:[]},times:[],alarms:[],meta,need,hazard,miss})
      const group=groups.get(key)!
      if(group.meta!==meta)throw Error('Mission-level metadata must be constant across rows.')
      if(group.times.length&&t<=group.times.at(-1)!)throw Error('Times must be strictly increasing within a mission and monitor.')
      group.times.push(t)
      if(alarm)group.alarms.push(t)
      group.mission.rows.push(Object.fromEntries([...required,...optional].map(k=>[k,get(k)])))
    }catch(e){throw Error(`Row ${i+1}: ${(e as Error).message}`)}
  })
  return [...groups.values()].map(({mission:m,times,alarms,need,hazard,miss})=>{
    if(times[0]!==0||times.at(-1)!==m.horizon)throw Error(`Mission ${m.id} / ${m.monitor} must include t=0 and horizon_s.`)
    m.first=alarms[0]??null
    if(m.cohort==='healthy')m.flags.fa=Number(m.first!==null)
    else{
      if(hazard!==null)m.flags.risk=hazard
      if(miss!==null)m.flags.miss=miss
      else if(need===0)m.flags.miss=0
      else if(need===1&&m.onset!==null&&m.deadline!==null)m.flags.miss=Number(m.first===null||m.first<m.onset||m.first>m.deadline)
      if(m.onset!==null&&m.first!==null&&m.first>=m.onset)m.delay=m.first-m.onset
    }
    return m
  })
}
export function evaluateImport(missions:Mission[],confidence:number,qualified:boolean){
  const names=[...new Set(missions.map(m=>m.monitor))]
  if(names.length>24)throw Error('Up to 24 candidate configurations per analysis.')
  const pairs:Pair[]=[]
  const alpha=(1-confidence)/(Math.max(1,names.length*3+6*names.length*(names.length-1)/2))
  const samples=(name:string,k:Loss)=>missions.filter(m=>m.monitor===name&&m.cohort===(k==='fa'?'healthy':'changed'))
  const rows=names.map((name):Candidate=>{
    const bounds={} as Candidate['bounds'], estimates={} as Candidate['estimates']
    for(const k of losses){
      const sample=samples(name,k)
      const known=sample.filter(m=>m.flags[k]!==undefined)
      const sum=known.reduce((s,m)=>s+m.flags[k]!,0)
      estimates[k]=sample.length&&known.length===sample.length?sum/sample.length:null
      bounds[k]=qualified&&estimates[k]!==null?cp(sum,sample.length,alpha):[0,1]
    }
    const costs=[...new Set(missions.filter(m=>m.monitor===name).map(m=>m.cost))]
    return {name,cost:costs.length===1?costs[0]:null,bounds,estimates}
  })
  if(qualified){
    for(let i=0;i<names.length;i++)for(let j=i+1;j<names.length;j++)for(const metric of losses){
      const a=samples(names[i],metric),b=new Map(samples(names[j],metric).map(m=>[m.id,m]))
      if(!a.length||a.length!==b.size||!a.every(m=>m.flags[metric]!==undefined&&b.get(m.id)?.flags[metric]!==undefined))continue
      let n10=0,n01=0
      for(const m of a){const d=m.flags[metric]!-b.get(m.id)!.flags[metric]!;n10+=Number(d===1);n01+=Number(d===-1)}
      const x=cp(n10,a.length,alpha),y=cp(n01,a.length,alpha)
      pairs.push({a:names[i],b:names[j],metric,range:[x[0]-y[1],x[1]-y[0]] as Interval})
    }
  }
  return {rows,pairs}
}
