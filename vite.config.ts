import {defineConfig} from 'vite'
import {copyFileSync,mkdirSync} from 'node:fs'

export default defineConfig({
  base: process.env.PAGES_BASE || '/',
  plugins:[{name:'static-route-entries',closeBundle(){
    for(const route of ['framework','scenarios','simulator','signals','evaluation','evidence','documentation']){
      mkdirSync(`dist/${route}`,{recursive:true})
      copyFileSync('dist/index.html',`dist/${route}/index.html`)
    }
  }}]
})
