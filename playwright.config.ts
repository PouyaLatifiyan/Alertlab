import {defineConfig} from '@playwright/test'
export default defineConfig({
  testDir:'tests', timeout:30000, workers:1,
  use:{baseURL:'http://127.0.0.1:4173/alert-integrity-framework/',viewport:{width:1440,height:1000},
    launchOptions:{executablePath:process.env.CHROMIUM_PATH,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}},
  webServer:{command:'node scripts/serve-production.mjs',url:'http://127.0.0.1:4173/alert-integrity-framework/',reuseExistingServer:!process.env.CI}
})
