// Shared centered outlines for native PNG resources and the offline preview.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const root = path.resolve(__dirname, '..');
const outlines = JSON.parse(fs.readFileSync(path.join(__dirname,'assets/punctuation.json'),'utf8'));
const width = 200, height = 200;
(async () => {
  for (const [scheme,color] of [['light','#000000'],['dark','#F4F4F6']]) {
    const tiles = await Promise.all(Object.values(outlines).map(shape => sharp(Buffer.from(
      `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200" color="${color}">${shape}</svg>`
    )).png().toBuffer()));
    const folder = path.join(root,'default',scheme,'resources');
    const atlas = await sharp({create:{width:width*2,height,channels:4,background:{r:0,g:0,b:0,alpha:0}}})
      .composite(tiles.map((input,i)=>({input,left:i*width,top:0}))).png().toBuffer();
    fs.writeFileSync(path.join(folder,'punctuation.png'),atlas);
    fs.writeFileSync(path.join(folder,'punctuation.yaml'),JSON.stringify(Object.fromEntries(
      Object.keys(outlines).map((name,i)=>[name,{rect:{x:i*width,y:0,width,height},insets:{top:0,bottom:0,left:0,right:0}}])
    ),null,2)+'\n');
  }
  const preview = path.join(root,'preview/index.html');
  const html = fs.readFileSync(preview,'utf8');
  if(!html.includes('/* PUNCTUATION_START */')) throw Error('Missing punctuation markers');
  fs.writeFileSync(preview,html.replace(/\/\* PUNCTUATION_START \*\/[\s\S]*?\/\* PUNCTUATION_END \*\//,
    `/* PUNCTUATION_START */\n    const punctuationShapes = ${JSON.stringify(outlines)};\n    /* PUNCTUATION_END */`));
  console.log('Built centered punctuation resources and synchronized preview outlines.');
})().catch(error=>{console.error(error);process.exit(1)});
