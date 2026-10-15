/* Draw the original character graphics at their native 320 × 200 resolution. */
(() => {
  'use strict';
  const T=globalThis.Tutti,A=T.assets;
  const HUES=[0,0,0,180,280,120,240,60,30,45,90,330,155,210,260,80];
  function color(value) {
    const hue=value&15,lum=(value>>4)&7;
    if (!hue) return '#080c0d';
    if (hue===1) return `hsl(52 22% ${24+lum*10}%)`;
    return `hsl(${HUES[hue]} ${hue===9?48:62}% ${23+lum*7}%)`;
  }
  class Renderer {
    constructor(canvas) {
      this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});
      this.ctx.imageSmoothingEnabled=false;
      this.cache=new Map();
    }
    glyph(code,attr) {
      const key=code+attr*256;
      if (this.cache.has(key)) return this.cache.get(key);
      const tile=document.createElement('canvas');tile.width=tile.height=8;
      const c=tile.getContext('2d');
      const colors=[color(0),color(0x32),color(0x35),color((attr&0x70)|(attr&7))];
      c.fillStyle=colors[0];c.fillRect(0,0,8,8);
      for (let y=0;y<8;y++) {
        const bits=A.charset[(code&255)*8+y]||0;
        if (attr&8) {
          for (let x=0;x<4;x++) {c.fillStyle=colors[(bits>>(6-x*2))&3];c.fillRect(x*2,y,2,1);}
        } else {
          c.fillStyle=color(attr);
          for (let x=0;x<8;x++) if (bits&(128>>x)) c.fillRect(x,y,1,1);
        }
      }
      this.cache.set(key,tile);return tile;
    }
    char(code,x,y,attr=0x71) {this.ctx.drawImage(this.glyph(code,attr),Math.floor(x),Math.floor(y));}
    text(text,x,y,attr=0x71) {
      for (const ch of text.toUpperCase()) {
        let code=0;
        if (ch>='A'&&ch<='Z') code=ch.charCodeAt(0)-64;
        else if (ch>='0'&&ch<='9') code=0x1c+Number(ch);
        else if (ch===':') code=0x2a;
        else if (ch==='-') code=0x26;
        this.char(code,x,y,attr);x+=8;
      }
    }
    tile(type,x,y,mode=2) {
      let attr=A.tileColors[type];
      if (type>0&&type<4) attr=A.rowColors[(mode===4?12:0)+y];
      const codes=A.tiles[type]||A.tiles[0];
      for (let i=0;i<4;i++) this.char(codes[i],x*16+(i%2)*8,y*16+(i>>1)*8,attr);
    }
    object(obj,type,mode) {
      const vertical=obj.direction>=2;
      const phase=(vertical?obj.y:obj.x)&3;
      const index=(vertical?4:0)+phase;
      const start=A.objectStarts[index],end=A.objectEnds[index];
      const baseX=Math.floor(obj.x/4)*8,baseY=Math.floor(obj.y/4)*8;
      for (let i=start;i<end;i++) {
        const off=A.objectOffsets[i];
        this.char(A.objectChars[i]+(type===4?40:0),baseX+(off%40)*8,baseY+Math.floor(off/40)*8,mode===6?0x5a:0x08);
      }
    }
    figure(p,enemy=false) {
      if (!p.active) return;
      const d=Math.min(p.direction,2);
      const phase=((d===2?p.y:p.x)&2)>>1;
      const index=d*2+phase,start=A.figureStarts[index],end=A.figureEnds[index];
      const baseX=Math.floor(p.x/4)*8,baseY=Math.floor(p.y/4)*8;
      for (let i=start;i<end;i++) {
        const off=A.figureOffsets[i];
        this.char(A.figureChars[i]+(enemy?30:0),baseX+(off%40)*8,baseY+Math.floor(off/40)*8,0x79);
      }
    }
    draw(game,time=0) {
      const c=this.ctx;
      c.fillStyle=color(0);c.fillRect(0,0,320,200);
      for (let y=0;y<12;y++) for (let x=0;x<16;x++) this.tile(game.map[y*16+x],x,y,game.mode);
      // Shared enemy spawn marker. Its color signals an imminent arrival.
      const imminent=game.enemies.some(e=>e.spawn>=0&&e.spawn<50);
      c.fillStyle=color((imminent?0x0e:0x0a)|((game.tick&7)<<4));c.fillRect(112,96,16,16);
      for (const apple of game.apples) {
        if (!apple.active) continue;
        if (apple.state==='wobble') {
          c.fillStyle=color(0);c.fillRect(apple.x*2,apple.y*2,16,16);
          this.object({...apple,x:apple.x+(Math.floor(apple.wait/4)%2)},3,game.mode);
        } else this.object(apple,3,game.mode);
      }
      if (game.sliding) this.object(game.sliding,game.sliding.type,game.mode);
      if (game.breaking) {
        const b=game.breaking,code=0x30+4*Math.min(3,Math.floor((32-b.timer)/8));
        for (let i=0;i<4;i++) this.char(code+i,b.x*16+(i%2)*8,b.y*16+(i>>1)*8,0x5a);
      }
      for (const e of game.enemies) this.figure(e,true);
      if (game.phase!=='dying'||Math.floor(game.timer/6)%2===0) this.figure(game.player);
      if (game.shot) {
        const s=game.shot;
        this.char(0x2c|((s.x&2)>>1)|(s.y&2),Math.floor(s.x/4)*8,Math.floor(s.y/4)*8,0x71);
      }
      // Native sidebar: the same 40-column screen layout as the original.
      c.fillStyle='#606349';c.fillRect(260,0,1,192);
      this.text('SCORE',272,0,0x51);
      this.text(String(game.score).padStart(5,'0'),272,12);
      this.text('TIME',272,28,0x51);
      const mm=String(Math.floor(game.seconds/60)).padStart(2,'0'),ss=String(game.seconds%60).padStart(2,'0');
      this.text(`${mm}:${ss}`,272,40);
      this.text('BONUS',272,56,0x51);this.text(String(game.bonus).padStart(3,'0'),280,68);
      this.text('LIVES',272,84,0x51);this.text(String(game.lives),288,96);
      this.text('LEVEL',272,112,0x51);this.text(String(game.round).padStart(2,'0'),284,124);
      this.text('BEST',272,144,0x51);this.text(String(game.best).padStart(5,'0').slice(-5),272,156);
      this.text(game.mode===6?'PUSH':game.cooldown?'WAIT':'FIRE',272,180,game.cooldown?0x32:0x65);
      c.fillStyle='#2e382e';c.fillRect(0,194,320,1);
      if (game.phase==='title') {
        // A real level behind the HTML title overlay, no fabricated screenshots.
        this.text('TUTTI FRUTTI',16,184,0x71);
      }
    }
    icon(canvas,type) {
      canvas.width=canvas.height=16;
      const c=canvas.getContext('2d');c.imageSmoothingEnabled=false;
      const codes=A.tiles[type];
      for (let i=0;i<4;i++) c.drawImage(this.glyph(codes[i],A.tileColors[type]),(i%2)*8,(i>>1)*8);
    }
  }
  T.Renderer=Renderer;
})();
