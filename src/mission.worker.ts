import {monitors,rng,simulate,type Config} from './engine'
import {evaluateImport,type Mission} from './imports'

self.onmessage=(event:MessageEvent<{config:Config;count:number;thresholds:number[];confidence:number}>)=>{
  const {config,count,thresholds,confidence}=event.data
  const random=rng(config.seed), missions:Mission[]=[]
  const seed=()=>Math.floor(random()*4294967296)
  try{
    for(let i=0;i<count;i++){
      for(const cohort of ['healthy','changed'] as const){
        const inputSeed=seed()
        for(const [j,monitor] of monitors.entries()){
          const run=simulate({...config,monitor,threshold:thresholds[j],seed:inputSeed},cohort==='healthy')
          missions.push({id:String(i),scenario:config.scenario,monitor,cohort,horizon:run.frames.at(-1)!.t,source:'Seeded exploratory browser model',
            cost:j===0?0:j===1?2:j===2?17:85,first:run.alarm,delay:run.alarm!==null&&run.alarm>=run.onset?run.alarm-run.onset:null,
            onset:run.onset,deadline:run.deadline,rows:[],
            flags:cohort==='healthy'?{fa:Number(run.alarm!==null)}:{miss:Number(run.opportunity===false),risk:Number(run.hazard)}})
        }
      }
      if(i%16===0)self.postMessage({progress:i/count})
    }
    self.postMessage({result:evaluateImport(missions,confidence,true),cohorts:count})
  }catch(e){self.postMessage({error:(e as Error).message})}
}
