import {createServer} from 'node:http'
import {statSync,createReadStream} from 'node:fs'
import {resolve,extname,sep} from 'node:path'
const dist=resolve('dist'), base='/alert-integrity-framework/'
const mime={'.pdf':'application/pdf','.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.csv':'text/csv','.woff2':'font/woff2','.svg':'image/svg+xml'}
createServer((req,res)=>{
  const path=new URL(req.url,'http://localhost').pathname
  if(!path.startsWith(base)){res.writeHead(404).end();return}
  let target=resolve(dist,decodeURIComponent(path.slice(base.length)))
  if(target!==dist&&!target.startsWith(dist+sep)){res.writeHead(404).end();return}
  try{
    if(statSync(target).isDirectory()){
      if(!path.endsWith('/')){res.writeHead(301,{Location:path+'/'}).end();return}
      target=resolve(target,'index.html')
    }
    if(!statSync(target).isFile())throw Error('Not a file')
    res.writeHead(200,{'Content-Type':mime[extname(target)]??'application/octet-stream'})
    createReadStream(target).pipe(res)
  }catch{res.writeHead(404).end()}
}).listen(4173,'127.0.0.1')
