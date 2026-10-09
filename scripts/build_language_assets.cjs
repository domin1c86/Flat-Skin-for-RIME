// Rasterize the approved artwork without retypesetting or stretching its parts.
// Requires Node.js and sharp only when rebuilding the checked-in resources.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(__dirname, 'assets/language-source.png')).toString('base64');
const width = 380, height = 410;

function artwork(active, inactive, english) {
  const clip = `<clipPath id="cn"><rect x="180" y="130" width="240" height="196"/><rect x="260" y="322" width="70" height="70"/></clipPath><clipPath id="en"><rect x="340" y="328" width="235" height="224"/></clipPath><clipPath id="tr"><rect x="450" y="195" width="125" height="122"/></clipPath><clipPath id="bl"><rect x="180" y="395" width="125" height="125"/></clipPath>`;
  const filter = (id, color) => `<filter id="${id}" x="0" y="0" width="100%" height="100%"><feFlood flood-color="${color}"/><feComposite in2="SourceAlpha" operator="in"/></filter>`;
  const parts = ['cn','en','tr','bl'].map(part => `<g clip-path="url(#${part})"><use xlink:href="#source" filter="url(#${part === (english ? 'en' : 'cn') ? 'active' : 'inactive'})"/></g>`).join('');
  return Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${width}" height="${height}" viewBox="190 140 380 410"><defs><image id="source" width="1312" height="1199" xlink:href="data:image/png;base64,${source}"/>${clip}${filter('active', active)}${filter('inactive', inactive)}</defs>${parts}</svg>`);
}

(async () => {
  const embedded = {};
  for (const [scheme, active, inactive] of [['light','#000000','#A1A3A6'],['dark','#F4F4F6','#91939B']]) {
    const tiles = await Promise.all([false,true].map(english => sharp(artwork(active,inactive,english)).png().toBuffer()));
    const atlas = await sharp({create:{width:width*2,height,channels:4,background:{r:0,g:0,b:0,alpha:0}}}).composite(tiles.map((input,i)=>({input,left:i*width,top:0}))).png().toBuffer();
    const folder = path.join(root,'default',scheme,'resources');
    fs.mkdirSync(folder,{recursive:true});
    fs.writeFileSync(path.join(folder,'language.png'),atlas);
    const descriptor = Object.fromEntries(['chinese','english'].map((name,i)=>[name,{rect:{x:i*width,y:0,width,height},insets:{top:0,left:0,bottom:0,right:0}}]));
    fs.writeFileSync(path.join(folder,'language.yaml'),JSON.stringify(descriptor,null,2)+'\n');
    // The preview must use individual tiles. An SVG viewBox is a camera,
    // not a crop: aspect-fit letterboxing can reveal the adjacent atlas tile.
    embedded[scheme] = Object.fromEntries(await Promise.all(['zh','en'].map(async (language,i)=> {
      const tile = await sharp(atlas).extract({left:i*width,top:0,width,height}).png().toBuffer();
      return [language,'data:image/png;base64,'+tile.toString('base64')];
    })));
  }
  const preview = path.join(root,'preview/index.html');
  const html = fs.readFileSync(preview,'utf8');
  if (!html.includes('/* LANGUAGE_ATLASES_START */')) throw new Error('Missing preview atlas markers');
  fs.writeFileSync(preview,html.replace(/\/\* LANGUAGE_ATLASES_START \*\/[\s\S]*?\/\* LANGUAGE_ATLASES_END \*\//,`/* LANGUAGE_ATLASES_START */\n    const languageImages = ${JSON.stringify(embedded)};\n    /* LANGUAGE_ATLASES_END */`));
  console.log('Built two native language atlases and four isolated offline preview images.');
})().catch(error=>{console.error(error);process.exit(1)});
