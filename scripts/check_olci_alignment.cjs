// QA cartográfico independiente del visor; reutiliza el PNG sin nuevas consultas API.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const folder=path.resolve(process.argv[2]);
const meta=JSON.parse(fs.readFileSync(path.join(folder,'metadata.json')));
const geometry=JSON.parse(fs.readFileSync(path.join(root,'cemec-sitio-estatico/data/v-79544d8e805b0b1d/units/region-peten.geojson'))).geometry;
const cache=path.join(root,'.conda-env/.npm-cache/_npx');
const library=fs.readdirSync(cache).map(n=>path.join(cache,n,'node_modules/playwright')).find(p=>fs.existsSync(path.join(p,'package.json'))&&JSON.parse(fs.readFileSync(path.join(p,'package.json'))).version==='1.58.2');
const {chromium}=require(library);
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage();
  await page.setContent('<canvas id="map"></canvas>');
  const result=await page.evaluate(async({meta,geometry,image})=>{
   const canvas=document.querySelector('canvas'),[width,height]=meta.dimensions;
   canvas.width=width;canvas.height=height;
   const ctx=canvas.getContext('2d',{willReadFrequently:true});
   const png=new Image();png.src=image;await png.decode();
   if(png.width!==width||png.height!==height)throw Error('Dimensiones inesperadas');
   ctx.drawImage(png,0,0);const rgba=ctx.getImageData(0,0,width,height).data;
   const [west,south,east,north]=meta.output_bbox;
   const position=([lon,lat])=>[(6378137*lon*Math.PI/180-west)/(east-west)*width,
    (north-6378137*Math.log(Math.tan(Math.PI/4+lat*Math.PI/360)))/(north-south)*height];
   const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
   const territory=new Path2D();
   for(const polygon of polygons)for(const ring of polygon){ring.forEach((p,i)=>{const [x,y]=position(p);i?territory.lineTo(x,y):territory.moveTo(x,y)});territory.closePath()}
   const mask=document.createElement('canvas');mask.width=width;mask.height=height;
   const mc=mask.getContext('2d',{willReadFrequently:true});mc.fill(territory,'evenodd');
   const inside=mc.getImageData(0,0,width,height).data;
   let withData=0,territoryPixels=0,territoryWithData=0;
   for(let p=3;p<rgba.length;p+=4){if(rgba[p])withData++;if(inside[p]>=128){territoryPixels++;if(rgba[p])territoryWithData++}}
   ctx.strokeStyle='#151515';ctx.lineWidth=5;ctx.stroke(territory);
   ctx.strokeStyle='#ffe94f';ctx.lineWidth=2;ctx.stroke(territory);
   return {bbox_fraction_with_data:withData/(width*height),territory_fraction_with_data:territoryWithData/territoryPixels,
    territory_pixels:territoryPixels,note:'Fracción de píxeles con alpha > 0; no mide nubosidad ni precisión geodésica independiente.'};
  },{meta,geometry,image:'data:image/png;base64,'+fs.readFileSync(path.join(folder,'olci-rgb.png')).toString('base64')});
  assert.ok(result.territory_pixels>0);
  await page.locator('canvas').screenshot({path:path.join(folder,'peten-overlay.png')});
  fs.writeFileSync(path.join(folder,'coverage.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
