import {useEffect,useId,useRef,useState} from 'react'
import * as THREE from 'three'
import {OrbitControls} from 'three/addons/controls/OrbitControls.js'
import type {Frame, Run, Vec} from './engine'
export const colors={truth:'#30cbe8',estimate:'#ff8d78',protected:'#67d7a0',measurement:'#9c9bf2',threshold:'#edb459',muted:'#869bb4'}
export const download=(name:string,body:string,type='text/plain')=>{
  const url=URL.createObjectURL(new Blob([body],{type}))
  const a=document.createElement('a');a.href=url;a.download=name;a.click()
  setTimeout(()=>URL.revokeObjectURL(url),2000)
}
export type Series={name:string;color:string;values:(number|null)[]}
export const getSeries=(frames:Frame[],name:string,color:string,get:(f:Frame)=>number|null):Series=>({name,color,values:frames.map(get)})
export function Plot({title,unit,times,series,cursor,onCursor,events=[],domain}:{
  title:string;unit:string;times:number[];series:Series[];cursor?:number;onCursor?:(i:number)=>void;
  events?:{t:number|null;name:string;color:string}[];domain?:[number,number]
}){
  const id=useId(), ref=useRef<SVGSVGElement>(null), drag=useRef<number|null>(null)
  const [range,setRange]=useState<[number,number]|null>(null)
  useEffect(()=>setRange(null),[times.length,times[0],times.at(-1),domain?.[0],domain?.[1]])
  const start=range?.[0]??domain?.[0]??0, end=range?.[1]??domain?.[1]??times.length-1
  const vals=series.flatMap(s=>s.values.slice(start,end+1)).filter((v):v is number=>v!==null&&Number.isFinite(v))
  const min=vals.reduce((m,v)=>Math.min(m,v),0),max=vals.reduce((m,v)=>Math.max(m,v),vals.length?Math.max(0,min+1e-9):1)
  const span=(times[end]??0)-(times[start]??0)
  const x=(i:number)=>58+716*(span>0?((times[i]??0)-times[start])/span:(i-start)/Math.max(1,end-start))
  const y=(v:number)=>142-113*(v-min)/(max-min)
  const xy=(e:React.PointerEvent)=>{const box=ref.current!.getBoundingClientRect();const target=(e.clientX-box.left)/box.width*800;let lo=start,hi=end;while(lo<hi){const m=(lo+hi)>>1;if(x(m)<target)lo=m+1;else hi=m}return lo>start&&Math.abs(x(lo-1)-target)<Math.abs(x(lo)-target)?lo-1:lo}
  return <figure className="plot">
    <div className="plothead"><figcaption>{title} <small>{unit}</small></figcaption><div>
    {range&&<><button className="small" aria-label="Pan earlier" onClick={()=>{const first=Math.max(domain?.[0]??0,start-Math.max(1,Math.floor((end-start)/2)));setRange([first,first+end-start])}}>‹</button><button className="small" aria-label="Pan later" onClick={()=>{const last=Math.min(domain?.[1]??times.length-1,end+Math.max(1,Math.floor((end-start)/2)));setRange([last-(end-start),last])}}>›</button><button className="small" onClick={()=>setRange(null)}>Reset zoom</button></>}
    <button className="small" onClick={()=>{const svg=ref.current!.cloneNode(true) as SVGSVGElement;svg.setAttribute('xmlns','http://www.w3.org/2000/svg');svg.setAttribute('style','font-family:system-ui;fill:#8192a6');download(title.toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.svg',svg.outerHTML,'image/svg+xml')}}>SVG</button></div></div>
    <svg ref={ref} viewBox="0 0 800 172" role="img" aria-label={title} onPointerDown={e=>{drag.current=xy(e);e.currentTarget.setPointerCapture(e.pointerId);onCursor?.(drag.current)}} onPointerMove={e=>{if(e.pointerType==='mouse'||drag.current!==null)onCursor?.(xy(e))}} onPointerUp={e=>{const end=xy(e);if(drag.current!==null&&Math.abs(end-drag.current)>2)setRange([Math.min(drag.current,end),Math.max(drag.current,end)]);drag.current=null}} onPointerCancel={()=>drag.current=null}>
      <defs><clipPath id={id}><rect x="58" y="18" width="716" height="124"/></clipPath></defs>
      {[0,.25,.5,.75,1].map(p=><g key={p}><line x1="58" x2="774" y1={y(min+p*(max-min))} y2={y(min+p*(max-min))} stroke="#8192a6" opacity=".23"/><text x="48" y={y(min+p*(max-min))+4} textAnchor="end">{+(min+p*(max-min)).toPrecision(3)}</text><text x={58+716*p} y="162" textAnchor="middle">{+((times[start]??0)+p*span).toFixed(3)}</text></g>)}
      <g clipPath={`url(#${id})`}>
      {events.map(e=>{if(e.t===null||e.t<times[0]||e.t>times.at(-1)!)return null;const i=times.findIndex(t=>t>=e.t!);return i<start||i>end?null:<g key={e.name}><line x1={x(i)} x2={x(i)} y1="19" y2="143" stroke={e.color} strokeDasharray="4 4"/><title>{e.name} · {e.t}</title></g>})}
      {series.map(s=>{let fresh=true;const d=s.values.slice(start,end+1).map((v,i)=>{if(v===null){fresh=true;return ''}const code=fresh?'M':'L';fresh=false;return `${code}${x(i+start).toFixed(2)} ${y(v).toFixed(2)}`}).join(' ');return <g key={s.name}><path d={d} stroke={s.color} strokeWidth="2" fill="none" strokeLinejoin="round"/>{s.values.slice(start,end+1).map((v,i)=>v!==null&&(i===0||s.values[start+i-1]===null)&&(i===end-start||s.values[start+i+1]===null)?<circle key={i} cx={x(start+i)} cy={y(v)} r="2" fill={s.color}/>:null)}</g>})}
      {cursor!==undefined&&<line x1={x(cursor)} x2={x(cursor)} y1="18" y2="143" stroke="#a5bed5"/>}</g>
    </svg>
    <div className="legend">{series.map(s=><span key={s.name}><i style={{background:s.color}}/>{s.name}</span>)}{events.filter(e=>e.t!==null).map(e=><span key={e.name}><i style={{background:e.color}}/>{e.name}</span>)}</div>
  </figure>
}
type Layers={truth:boolean;estimate:boolean;protected:boolean;measurement:boolean}
const defaults:Layers={truth:true,estimate:true,protected:true,measurement:false}
const to3=(v:Vec)=>new THREE.Vector3(v[0],v[2],-v[1])
export function Trajectory({run,index,limit,layers=defaults,hero=false}:{run:Run;index:number;limit:number;layers?:Layers;hero?:boolean}){
  const host=useRef<HTMLDivElement>(null)
  const [fallback,setFallback]=useState(false)
  const renderState=useRef<{markers:THREE.Mesh[];boundary:THREE.Mesh;error:THREE.Line;render:()=>void}|null>(null)
  const current=run.frames[index]??run.frames[0]
  useEffect(()=>{
    const el=host.current!
    let renderer:THREE.WebGLRenderer
    try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});setFallback(false)}catch{setFallback(true);return}
    renderer.setPixelRatio(Math.min(window.devicePixelRatio,2))
    el.appendChild(renderer.domElement)
    const scene=new THREE.Scene(), center=new THREE.Box3().setFromPoints(run.frames.flatMap(f=>[to3(f.truth),to3(f.estimate),to3(f.protected)]))
    const middle=center.getCenter(new THREE.Vector3()), size=Math.max(1,center.getSize(new THREE.Vector3()).length(),limit*2)
    const camera=new THREE.PerspectiveCamera(39,1,size/1000,size*12)
    camera.position.copy(middle).add(new THREE.Vector3(.17,.58,.93).multiplyScalar(size))
    const controls=new OrbitControls(camera,renderer.domElement)
    controls.target.copy(middle);controls.update()
    const render=()=>renderer.render(scene,camera)
    controls.addEventListener('change',render)
    const grid=new THREE.GridHelper(size*1.35,14,0x426179,0x22384b)
    grid.position.set(middle.x,Math.min(0,center.min.y)-size*.08,middle.z);scene.add(grid)
    const axes=[[[size*.16,0,0],0xff746f],[[0,size*.16,0],0x69b3fb],[[0,0,size*.16],0x75d69e]] as [Vec,number][]
    for(const [v,color] of axes){
      const direction=to3(v).normalize()
      scene.add(new THREE.ArrowHelper(direction,new THREE.Vector3(),size*.16,color,size*.025,size*.015))
    }
    const keys=['truth','estimate','protected','measurement'] as const
    for(const key of keys){
      if(!layers[key])continue
      const points=run.frames.flatMap(f=>{const v=f[key];return v?[to3(v)]:[]})
      const geometry=new THREE.BufferGeometry().setFromPoints(points)
      scene.add(key==='measurement'?new THREE.Points(geometry,new THREE.PointsMaterial({color:colors[key],size:size*.008})):new THREE.Line(geometry,new THREE.LineBasicMaterial({color:colors[key]})))
    }
    const markers=keys.slice(0,3).map((key)=>{
      const m=new THREE.Mesh(new THREE.SphereGeometry(size*.012,16,12),new THREE.MeshBasicMaterial({color:colors[key]}));m.visible=layers[key];scene.add(m);return m
    })
    for(const [time,color] of [[run.onset,'#edb459'],[run.alarm,'#ffffff'],[run.deadline,'#ff7183'],[run.completion,'#67d7a0']] as const){
      if(time===null||time<run.frames[0].t)continue
      const f=run.frames.find(f=>f.t>=time)
      if(!f)continue
      const m=new THREE.Mesh(new THREE.SphereGeometry(size*.007,12,8),new THREE.MeshBasicMaterial({color}))
      m.position.copy(to3(f.estimate));scene.add(m)
    }
    const boundary=new THREE.Mesh(new THREE.SphereGeometry(limit,22,14),new THREE.MeshBasicMaterial({color:0xff8d78,wireframe:true,transparent:true,opacity:.19}))
    scene.add(boundary)
    const errGeometry=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);errGeometry.boundingSphere=new THREE.Sphere(new THREE.Vector3(),size*3)
    const error=new THREE.Line(errGeometry,new THREE.LineBasicMaterial({color:0xedb459}));error.frustumCulled=false;scene.add(error)
    renderState.current={markers,boundary,error,render}
    const resize=new ResizeObserver(()=>{const w=el.clientWidth,h=el.clientHeight;if(!w||!h)return;const updateDistance=camera.aspect===1
      camera.aspect=w/h
      if(updateDistance&&camera.aspect<1.4)camera.position.sub(middle).multiplyScalar(Math.max(1,1.4/camera.aspect)).add(middle)
      camera.updateProjectionMatrix();renderer.setSize(w,h);render()})
    resize.observe(el)
    return ()=>{resize.disconnect();controls.dispose();scene.traverse(o=>{if(o instanceof THREE.Mesh||o instanceof THREE.Line||o instanceof THREE.Points){o.geometry.dispose();const mats=Array.isArray(o.material)?o.material:[o.material];mats.forEach(m=>m.dispose())}});renderer.dispose();renderer.domElement.remove();renderState.current=null}
  },[run,limit,layers])
  useEffect(()=>{
    const s=renderState.current
    if(!s)return
    const pts=[current.truth,current.estimate,current.protected].map(to3)
    s.markers.forEach((m,i)=>m.position.copy(pts[i]))
    s.boundary.position.copy(pts[0])
    const p=s.error.geometry.getAttribute('position')
    p.setXYZ(0,...pts[0].toArray());p.setXYZ(1,...pts[1].toArray());p.needsUpdate=true
    s.render()
  },[current,run,limit,layers])
  return <div className={`trajectory ${hero?'hero-trajectory':''}`}>
    <div className="viewport" ref={host} aria-label="Interactive three-dimensional trajectory"/>
    {fallback&&<div className="fallback"><p>WebGL unavailable · East position over time</p><Plot title="X position" unit={run.units} times={run.frames.map(f=>f.t)} series={[getSeries(run.frames,'Truth',colors.truth,f=>f.truth[0]),getSeries(run.frames,'Estimate',colors.estimate,f=>f.estimate[0])] } cursor={index}/></div>}
    <span className="view-label">{run.units==='m'?'LOCAL ENU · m':'SCALAR STATE ON X · NORMALIZED'}<br/>X <b className="axis-x">●</b> &nbsp; Y <b className="axis-y">●</b> &nbsp; Z <b className="axis-z">●</b></span>
    <div className="view-footer"><span>Drag to orbit · Scroll to zoom · Right drag to pan</span><span>{current.t.toFixed(1)} {run.units==='m'?'s':'epoch'}</span></div>
  </div>
}
