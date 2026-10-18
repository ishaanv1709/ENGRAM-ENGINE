import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import fs from 'node:fs';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const require=createRequire(path.join(root,'frontend/package.json'));
const {chromium}=require('@playwright/test');
const browser=await chromium.launch({headless:true});
try {
  const page=await browser.newPage({viewport:{width:1500,height:1000},deviceScaleFactor:1});
  for(const name of ['cover','architecture','memory-flow','causal-graph','procedure-flow']){
    await page.goto(pathToFileURL(path.join(here,'assets',name+'.svg')).href);
    await page.locator('svg').screenshot({path:path.join(here,'assets',name+'.png')});
  }
  const fixture=JSON.parse(fs.readFileSync(path.join(root,'data/collective/film-infrastructure-evidence.json'),'utf8')).fixture;
  const response=await page.request.post('http://127.0.0.1:8088/api/auth/login',{headers:{'X-Engram-Request':'1'},data:{email:fixture.email,password:'Integration-password-123'}});
  if(!response.ok())throw new Error('Real fixture login failed');
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://127.0.0.1:8088/');
  await page.getByLabel('Project',{exact:true}).selectOption(fixture.project);
  for(const [tab,selector,name] of [['Causal timeline','.causal-card','causal-ui'],['Procedures','.procedure-benchmark','benchmark-ui'],['Sandbox console','.security-note','security-ui']]){
    const item=page.locator('nav').getByRole('button',{name:tab,exact:true});
    if(!(await item.isVisible()))await page.locator('.nav-inspect > summary').click();
    await item.click();
    if(name==='benchmark-ui')await page.locator('.procedure-benchmark > summary').first().click();
    await page.locator(selector).first().waitFor({state:'visible'});
    if(name==='security-ui')await page.locator(selector).locator('summary').click();
    await page.locator(selector).first().screenshot({path:path.join(here,'assets',name+'.png')});
  }
  const article=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const failures=[];
  article.on('pageerror',e=>failures.push(e.message));
  await article.goto(pathToFileURL(path.join(here,'index.html')).href);
  await article.evaluate(()=>document.fonts.ready);
  const images=await article.locator('img').evaluateAll(items=>items.map(i=>({src:i.getAttribute('src'),ok:i.complete&&i.naturalWidth>0})));
  if(images.some(i=>!i.ok)||failures.length)throw new Error(JSON.stringify({images,failures}));
  await article.screenshot({path:path.join(here,'desktop-preview.png'),fullPage:false});
  const headings=await article.locator('h2').allTextContents();
  await article.setViewportSize({width:390,height:844});
  await article.screenshot({path:path.join(here,'mobile-preview.png'),fullPage:false});
  const overflow=await article.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));
  if(overflow.scroll>overflow.width+1)throw new Error('Mobile horizontal overflow: '+JSON.stringify(overflow));
  fs.writeFileSync(path.join(here,'render-check.json'),JSON.stringify({images,failures,headings,desktop:'1440x1000',mobile:'390x844',mobile_overflow:false,app_captures:'Authenticated actual local app; no mocked routes or AI task execution'},null,2));
  console.log('Rendered five diagrams, captured three real app surfaces, verified desktop/mobile article and all images.');
} finally {await browser.close();}
