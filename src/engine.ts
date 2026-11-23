export const monitors = ['Shewhart','CUSUM','GLR16','RankRestart'] as const
export type Monitor = typeof monitors[number]
export type Scenario = 'spoofing'|'jamming'|'hybrid'|'published'
export type Vec = [number,number,number]
export type Config = {
  scenario:Scenario; duration:number; dt:number; seed:number; onset:number; span:number;
  bias:number; drift:number; sigma:number; gnssRate:number; imuDrift:number; radioRate:number;
  radioSigma:number; availability:number; severity:number; tracking:number; limit:number;
  latency:number; effectiveness:number; gain:number; monitor:Monitor; threshold:number;
  fallback:'inertial'|'hold'|'radio'; disturbance:'bias'|'interference'
}
export function defaults(scenario:Scenario='spoofing'):Config{
  return {scenario,duration:90,dt:.5,seed:816341,onset:22,span:52,bias:1,drift:.34,sigma:.8,
    gnssRate:2,imuDrift:(scenario==='jamming'||scenario==='hybrid') ? .16 : .025,radioRate:1,radioSigma:2,availability:1,severity:24,tracking:28,limit:7,
    latency:8,effectiveness:.85,gain:.38,monitor:'CUSUM',threshold:10,
    fallback:scenario==='hybrid'?'radio':'inertial',disturbance:'interference'}
}
export type Frame = {t:number; truth:Vec; velocity:Vec; estimate:Vec; estimatedVelocity:Vec;
  measurement:Vec|null; radio:Vec|null; protected:Vec; innovation:number|null; residual:number|null;
  quality:number|null; variance:number; observationVariance:number; available:boolean; error:number; protectedError:number; statistic:number|null}
export type Run = {frames:Frame[]; onset:number; alarm:number|null; crossing:number|null; deadline:number|null;
  completion:number|null; hazard:boolean; opportunity:boolean|null; reference:number[]; units:'m'|'normalized'}
export type Published = {mu:number;shape:string;rho:number;noise:number;w:number;onset_lo:number;onset_hi:number;
  drive:number;duration:number;delay:number;latency_lo:number;latency_hi:number;fault_probability:number}
export function rng(seed:number){
  let state=seed>>>0
  return ()=>{state=(state+0x6D2B79F5)>>>0;let v=state;v=Math.imul(v^v>>>15,v|1);v^=v+Math.imul(v^v>>>7,v|61);return ((v^v>>>14)>>>0)/4294967296}
}
const gaussian=(r:()=>number)=>Math.sqrt(-2*Math.log(1-r()))*Math.cos(2*Math.PI*r())
const add=(a:Vec,b:Vec):Vec=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]]
const sub=(a:Vec,b:Vec):Vec=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]]
const scale=(a:Vec,k:number):Vec=>[a[0]*k,a[1]*k,a[2]*k]
const norm=(a:Vec)=>Math.hypot(...a)

export function scoreMonitor(method:Monitor,reference:number[],horizon:number){
  let pos=0, neg=0, i=0
  const recent:number[]=[], active=[0,0,0,0,0], fractions=[.1,.25,.5,.75,.9]
  const ref=reference.map(Math.abs).sort((a,b)=>a-b), starts=Math.ceil(horizon/10)
  const eps=Math.sqrt(Math.log(4000)/(2*ref.length))
  return (z:number)=>{
    if(method==='Shewhart')return Math.abs(z)
    if(method==='CUSUM'){pos=Math.max(0,pos+z-.5);neg=Math.max(0,neg-z-.5);return Math.max(pos,neg)}
    if(method==='GLR16'){
      recent.push(z)
      if(recent.length>16)recent.shift()
      let sum=0,best=0
      for(let k=1;k<=recent.length;k++){sum+=recent[recent.length-k];best=Math.max(best,sum*sum/(2*k))}
      return best
    }
    const x=ref.filter(v=>v<Math.abs(z)).length/ref.length
    for(let j=0;j<5;j++)active[j]=(active[j]+Number(i%10===0))*(1+(x/(.5+eps)-1)*fractions[j])
    const result=Math.log((active.reduce((s,v)=>s+v,0)/5+starts-1-Math.floor(i/10))/starts)
    i++
    return result
  }
}
export function simulate(c:Config,healthy=false):Run{
  const random=rng(c.seed), n=Math.floor(c.duration/c.dt+1e-9)+1
  const ref=Array.from({length:80},()=>gaussian(random))
  const score=scoreMonitor(c.monitor,ref,n)
  const frames:Frame[]=[]
  const truthAt=(t:number):Vec=>[1.15*t,12*Math.sin(t/30),4*Math.sin(t/21)+.075*t]
  const velAt=(t:number):Vec=>[1.15,.4*Math.cos(t/30),4/21*Math.cos(t/21)+.075]
  let estimate=truthAt(0), protectedState=estimate, errorVariance=c.sigma**2
  let alarm:number|null=null, crossing:number|null=null, hazard=false
  const interference=c.scenario==='jamming'||(c.scenario==='hybrid'&&c.disturbance==='interference')
  const noise=(s:number):Vec=>[gaussian(random)*s,gaussian(random)*s,gaussian(random)*s]
  const sampled=(i:number,rate:number)=>rate>0&&(i===0||Math.floor(i*c.dt*rate+1e-8)>Math.floor((i-1)*c.dt*rate+1e-8))
  for(let i=0;i<n;i++){
    const t=i*c.dt, truth=truthAt(t),velocity=velAt(t)
    const disturbed=!healthy&&t>=c.onset&&t<c.onset+c.span
    const quality=interference?44-(disturbed?c.severity:0):null
    const sigma=c.sigma*(quality===null?1:10**((44-quality)/20))
    const available=sampled(i,c.gnssRate)&&random()<c.availability&&(quality===null||quality>=c.tracking)
    const bias=disturbed&&!interference?c.bias+c.drift*(t-c.onset):0
    const measurementNoise=noise(sigma)
    const measurement=available?add(add(truth,[bias,.35*bias,.15*bias]),measurementNoise):null
    const radioNoise=noise(c.radioSigma)
    const radio=c.scenario==='hybrid'&&sampled(i,c.radioRate)?add(truth,radioNoise):null
    const increment=i===0?[0,0,0] as Vec:add(sub(truth,truthAt(t-c.dt)),scale([c.imuDrift,.3*c.imuDrift,.15*c.imuDrift],c.dt))
    const corrected=(p:Vec,y:Vec|null,k:number)=>y?add(p,scale(sub(y,p),k)):p
    const prediction=add(estimate,increment)
    const innovation=measurement?measurement[0]-prediction[0]:null
    errorVariance+=i===0?0:(c.imuDrift*c.dt)**2
    const residual=innovation===null?null:innovation/Math.sqrt(sigma**2+errorVariance)
    const statistic=residual===null?null:score(residual)
    if(statistic!==null&&statistic>c.threshold&&alarm===null)alarm=t
    const completion=alarm===null?null:alarm+c.latency
    const k=c.gain*Math.min(1,c.sigma**2/sigma**2)
    const radioGain=c.gain/(1+c.radioSigma**2)
    const previous=estimate
    estimate=corrected(corrected(prediction,measurement,k),radio,radioGain)
    if(measurement)errorVariance=(1-k)**2*errorVariance+k*k*sigma*sigma
    if(radio)errorVariance=(1-radioGain)**2*errorVariance+radioGain**2*c.radioSigma**2
    if(completion===null||t<completion)protectedState=estimate
    else{
      const fallback=c.fallback==='hold'?protectedState:add(protectedState,increment)
      const alternative=c.fallback==='radio'?corrected(fallback,radio,c.gain):fallback
      protectedState=add(scale(alternative,c.effectiveness),scale(estimate,1-c.effectiveness))
    }
    const error=norm(sub(estimate,truth)), protectedError=norm(sub(protectedState,truth))
    if(crossing===null&&error>=c.limit)crossing=t
    hazard||=protectedError>=c.limit
    frames.push({t,truth,velocity,estimate,estimatedVelocity:i===0?velocity:scale(sub(estimate,previous),1/c.dt),measurement,radio,
      protected:protectedState,innovation,residual,quality,variance:errorVariance,observationVariance:sigma*sigma,available,error,protectedError,statistic})
  }
  const deadline=crossing===null?null:crossing-c.latency
  return {frames,onset:c.onset,alarm,crossing,deadline,completion:alarm===null?null:alarm+c.latency,hazard,
    opportunity:deadline===null?null:alarm!==null&&alarm>=c.onset&&alarm<=deadline,reference:ref,units:'m'}
}

function benchmarkProfile(age:number,s:Published){
  return s.shape==='ramp'?Math.max(0,Math.min(1,(age+1)/16)):Number(age>=0&&(s.shape!=='pulse'||age<s.duration))
}

export function benchmarkPlant(s:Published,onset:number,limit:number,load:number,latency:number,works:boolean,alarm:number|null){
  let crossing:number|null=null,state=0,closed=0,hazard=false
  const completion=alarm===null?null:alarm+latency
  const trajectory=Array.from({length:80},(_,i)=>{
    const t=i+1,age=t-onset
    const force=s.drive*load*(s.shape==='pulse'&&s.duration===1?Number(age>=s.delay&&age<s.delay+19):benchmarkProfile(age-s.delay,s))
    const protecting=completion!==null&&t>=completion&&works
    const previous=state
    state=.985*state+force
    closed=protecting?.68*closed+.12*force:.985*closed+force
    if(crossing===null&&state>=limit)crossing=t
    hazard||=closed>=limit
    return {t,untreated:state,closed,velocity:state-previous}
  })
  const deadline=crossing===null?null:crossing-latency
  return {trajectory,crossing,deadline,completion,hazard,opportunity:deadline===null?null:alarm!==null&&alarm>=onset&&alarm<=deadline}
}

export function publishedReplay(c:Config,s:Published,threshold:number):Run & {limit:number;threshold:number}{
  const r=rng(c.seed)
  const ar=(n:number)=>{let x=0;return Array.from({length:n},(_,i)=>{
    x=(i?s.rho*x:0)+(i?Math.sqrt(1-s.rho**2):1)*gaussian(r);return x*s.noise
  })}
  const samples=ar(80), reference=ar(s.w)
  const onset=s.onset_lo+Math.floor(r()*(s.onset_hi-s.onset_lo+1))
  const limit=.85+.3*r(), load=.85+.3*r()
  const latency=s.latency_lo+Math.floor(r()*(s.latency_hi-s.latency_lo+1)), works=r()>=s.fault_probability
  const scorer=scoreMonitor(c.monitor,reference,80)
  let alarm:number|null=null
  const inputs=samples.map((z,i)=>{
    const v=z+s.mu*benchmarkProfile(i+1-onset,s), statistic=scorer(v)
    if(alarm===null&&statistic>threshold)alarm=i+1
    return {v,statistic}
  })
  const {trajectory,...outcome}=benchmarkPlant(s,onset,limit,load,latency,works,alarm)
  const frames=trajectory.map(({t,untreated,closed,velocity},i):Frame=>{
    const {v,statistic}=inputs[i]
    return {t,truth:[0,0,0],estimate:[untreated,0,0],protected:[closed,0,0],velocity:[0,0,0],estimatedVelocity:[velocity,0,0],
      measurement:null,radio:null,innovation:v,residual:v,quality:null,variance:s.noise**2,observationVariance:s.noise**2,available:true,error:untreated,protectedError:closed,statistic}
  })
  return {frames,onset,alarm,...outcome,reference,units:'normalized',limit,threshold}
}
