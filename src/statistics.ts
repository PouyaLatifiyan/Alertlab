export const losses=['fa','miss','risk'] as const
export type Loss=typeof losses[number]
export type Interval=[number,number]
export type Candidate={name:string;cost:number|null; bounds:Record<Loss,Interval>; estimates:Record<Loss,number|null>}
export type Pair={a:string;b:string;metric:Loss;range:Interval}
export function select(rows:Candidate[],budgets:Record<Loss,number>,resource:number|null,pairs:Pair[],lower?:number){
  const outer=rows.filter(r=>(resource===null||r.cost===null||r.cost<=resource)&&losses.every(k=>r.bounds[k][0]<=budgets[k]))
  const inner=outer.filter(r=>(resource===null||(r.cost!==null&&r.cost<=resource))&&losses.every(k=>r.bounds[k][1]<=budgets[k]))
  const best=[...inner].sort((a,b)=>a.bounds.risk[1]-b.bounds.risk[1]||(a.cost??Infinity)-(b.cost??Infinity))[0]
  const diff=(a:Candidate,b:Candidate,k:Loss)=>{
    if(a===b)return 0
    const p=pairs.find(p=>p.metric===k&&((p.a===a.name&&p.b===b.name)||(p.a===b.name&&p.b===a.name)))
    return Math.min(a.bounds[k][1]-b.bounds[k][0],p?(p.a===a.name?p.range[1]:-p.range[0]):1)
  }
  const pareto=outer.filter(b=>!inner.some(a=>a!==b&&losses.every(k=>diff(a,b,k)<=0)&&losses.some(k=>diff(a,b,k)<0)))
  const cap=best&&lower!==undefined?best.bounds.risk[1]-lower:undefined
  const gap=best?Math.min(Math.max(...outer.map(b=>diff(best,b,'risk'))),cap!==undefined&&cap>=0?cap:1):null
  const optimum=best?[Math.max(cap!==undefined&&cap>=0?lower!:0,Math.min(...outer.map(b=>b.bounds.risk[0]))),best.bounds.risk[1]]:null
  return {inner,outer,best,gap,optimum,classGap:cap!==undefined&&cap>=0?cap:null,conflict:cap!==undefined&&cap<0,
    unique:!!best&&outer.every(b=>b===best||diff(best,b,'risk')<0),pareto}
}

// Two-sided CP inversion by bisection of the binomial tail, using log-summed terms.
export function cp(k:number,n:number,alpha:number):Interval{
  if(!Number.isInteger(k)||!Number.isInteger(n)||n<1||k<0||k>n||!(alpha>0&&alpha<1))throw Error('Invalid binomial count or error allocation.')
  const lower=(x:number)=>{
    if(x===0)return 0
    if(x===n)return (alpha/2)**(1/n)
    let logCombination=0
    for(let j=1;j<=Math.min(x,n-x);j++)logCombination+=Math.log((n+1-j)/j)
    let a=0,b=1
    for(let i=0;i<48;i++){
      const p=(a+b)/2
      let term=logCombination+x*Math.log(p)+(n-x)*Math.log1p(-p), total=term
      const logOdds=Math.log(p)-Math.log1p(-p)
      for(let j=x;j<n;j++){
        term+=Math.log((n-j)/(j+1))+logOdds
        const max=Math.max(total,term)
        total=max+Math.log1p(Math.exp(Math.min(total,term)-max))
      }
      if(total<Math.log(alpha/2))a=p
      else b=p
    }
    return a
  }
  return [lower(k),1-lower(n-k)]
}
