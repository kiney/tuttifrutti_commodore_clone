/* Browser-independent game rules. Coordinates use the original 8 units per tile.
   One fixed tick = 1/50 s. No DOM, network, timers or audio dependencies. */
(() => {
  'use strict';
  const T = globalThis.Tutti;
  const TILE = Object.freeze({ EMPTY: 0, EARTH: 1, CHERRY: 2, APPLE: 3, CHERRY_BLOCK: 4, APPLE_BLOCK: 5, WALL: 6, WALL2: 7 });
  const DX = [-1, 1, 0, 0], DY = [0, 0, -1, 1], BITS = [4, 8, 1, 2];
  const SPEED = [120,128,136,144,152,160,168,176,180,184,188,192,196,200,204,208];
  const RESERVE = [0,1,2,3,3,3,4,4,5,5,6,6,7,7,7,8];
  const direction = mask => [3,2,1,0].find(d => mask & BITS[d]);
  const aligned = p => p.x % 8 === 0 && p.y % 8 === 0;
  const near = (a,b,n) => Math.abs(a.x-b.x) < n && Math.abs(a.y-b.y) < n;
  const actor = () => ({ x: 56, y: 48, direction: 1, active: false, stopped: false, spawn: -1 });

  class Game {
    constructor({ seed = 0x45a127, onEvent = () => {}, highScores = [] } = {}) {
      this.onEvent = onEvent;
      this.seed = seed & 0xffffff;
      this.highScores = highScores.filter(Number.isFinite).map(n=>Math.max(0,Math.floor(n))).sort((a,b)=>b-a).slice(0,8);
      this.phase = 'title';
      this.paused = false;
      this.tick = 0;
      this.round = 1;
      this.score = 0;
      this.lives = 5;
      this.seconds = 0;
      this.input = { mask: 0, fire: false };
      this.map = T.assets.maps[1].slice();
      this.player = { ...actor(), x: 56, y: 8, direction: 3, active: true, stopped: true };
      this.enemies = Array.from({length:5}, actor);
      this.apples = [];
      this.sliding = null;
      this.shot = null;
      this.cooldown = 0;
      this.breaking = null;
      this.timer = 0;
      this.bonus = 599;
      this.reserve = 0;
      this.pendingScore = false;
    }
    emit(type, detail = {}) { this.onEvent({ type, ...detail }); }
    get mapIndex() { return (this.round-1) % 6; }
    get mode() { return (this.mapIndex % 3 + 1) * 2; }
    get cherries() { return this.map.reduce((n,t)=>n+(t===TILE.CHERRY),0); }
    get bottomApples() { return this.map.slice(176).filter(t=>t===TILE.APPLE).length; }
    get cornerApples() { return [0,15,176,191].filter(i=>this.map[i]===TILE.APPLE_BLOCK).length; }
    get best() { return Math.max(this.score, this.highScores[0] || 0); }
    tile(x,y) { return x>=0 && x<16 && y>=0 && y<12 ? this.map[y*16+x] : 15; }
    put(x,y,t) { if (x>=0 && x<16 && y>=0 && y<12) this.map[y*16+x] = t; }
    random() { this.seed = (this.seed+0xb13579)&0xffffff; return this.seed>>>16; }
    addScore(points) { this.score = (this.score+points)%100000; this.emit('score', { points }); }
    start() {
      this.round=1; this.score=0; this.lives=5; this.seconds=0; this.clock=0;
      this.tick=0; this.paused=false; this.pendingScore=false;
      this.loadRound(96);
      this.emit('start');
    }
    loadRound(readyTicks = 128) {
      this.map=T.assets.maps[this.mapIndex+1].slice();
      this.apples=T.assets.apples[this.mapIndex].map(([x,y])=>({x,y,dx:0,dy:1,state:'idle',wait:0,active:false,direction:2}));
      this.sliding=null;
      this.breaking=null;
      const difficulty=Math.min(this.round-1,15);
      this.reserve=RESERVE[difficulty];
      this.enemySpeed=SPEED[difficulty];
      this.resetActors();
      this.phase='ready'; this.timer=readyTicks;
      this.emit('level', { round:this.round, mode:this.mode });
    }
    resetActors() {
      this.player={...actor(),x:56,y:8,direction:3,active:true,stopped:true};
      this.enemies=Array.from({length:5},(_,i)=>({...actor(),spawn:32+i*16}));
      this.enemyClock=0; this.bonusClock=0;
      this.shot=null; this.cooldown=0; this.breaking=null;
      this.bonus=[599,799,999][this.mapIndex%3];
    }
    pause(force = !this.paused) {
      if (['title','gameover'].includes(this.phase)) return;
      this.paused=force;
      this.emit('pause',{ paused:this.paused });
    }
    step(input = this.input) {
      this.input={mask:input.mask||0,fire:!!input.fire};
      if (this.paused) return;
      this.tick++;
      if (this.phase==='title' || this.phase==='gameover') return;
      if (this.phase==='ready') {
        if (--this.timer<=0) {this.phase='playing';this.emit('play');}
        return;
      }
      if (this.phase==='clear') {
        if (--this.timer===128) {this.round++;this.loadRound(128);}
        return;
      }
      if (this.phase==='dying') {
        if (--this.timer<=0) {
          if (--this.lives<=0) {
            this.phase='gameover';
            this.highScores=[...this.highScores,this.score].sort((a,b)=>b-a).slice(0,8);
            this.emit('gameover',{score:this.score,highScores:this.highScores.slice()});
          } else {
            this.settleObjects();
            this.resetActors();
            this.phase='ready';this.timer=64;
            this.emit('respawn');
          }
        }
        return;
      }
      this.moveObjects();
      this.choosePlayerDirection();
      if (!(this.tick&1) && !this.player.stopped) {
        this.player.x+=DX[this.player.direction];this.player.y+=DY[this.player.direction];
      }
      this.dig();
      if (this.checkGoal()) return;
      this.tryPush();
      this.findFallingApples();
      this.animateBreaking();
      this.tryShoot();
      this.moveShot();
      this.moveEnemies();
      if (this.phase!=='playing') return;
      this.hits();
      this.scheduleEnemies();
      if (!this.reserve && this.enemies.every(e=>!e.active && e.spawn<0)) {
        this.clear(false);return;
      }
      if (this.enemies.some(e=>e.active && near(e,this.player,4)) ||
          this.apples.some(a=>a.active && near(a,this.player,4))) {
        this.die();return;
      }
      if (++this.clock===60) {this.clock=0;this.seconds=(this.seconds+1)%3600;}
    }
    choosePlayerDirection() {
      const p=this.player;
      let mask=this.input.mask;
      if (!aligned(p)) {
        const axis=p.x%8 ? 12 : 3;
        mask &= axis;
        if (!mask) mask=BITS[p.direction]&axis;
        const d=direction(mask);
        if (d!==undefined) p.direction=d;
        p.stopped=false;
        return;
      }
      const free=this.freeMask(p.x/8,p.y/8,true);
      let d=direction(mask&free);
      p.stopped=d===undefined;
      if (d===undefined) d=direction(mask);
      if (d!==undefined) p.direction=d;
    }
    freeMask(x,y,player=false) {
      let mask=0;
      for (let d=0;d<4;d++) {
        const t=this.tile(x+DX[d],y+DY[d]);
        if (player?t<3:t===0) mask|=BITS[d];
      }
      return mask;
    }
    dig() {
      const p=this.player, x=Math.floor(p.x/8), y=Math.floor(p.y/8);
      this.digTile(x,y);
      if (!aligned(p) && !p.stopped) {
        if (p.direction<2) this.digTile(x+1,y);
        else this.digTile(x,y+1);
      }
    }
    digTile(x,y) {
      const t=this.tile(x,y);
      if (t===TILE.APPLE || t>=4) return;
      if (t===TILE.CHERRY) {this.addScore(25);this.emit('cherry');}
      this.put(x,y,TILE.EMPTY);
    }
    tryShoot() {
      if (!this.input.fire || this.mode===6 || this.shot || this.cooldown>0) return;
      const p=this.player;
      this.shot={x:Math.floor(p.x/8)*8+4,y:Math.floor(p.y/8)*8,
        dx:[-2,2,2,-2][p.direction],dy:[2,-2,-2,2][p.direction],away:false};
      this.emit('shoot');
    }
    moveShot() {
      const s=this.shot;
      if (!s) return;
      let bounced=false;
      if (this.tile(Math.floor((s.x+s.dx)/8),Math.floor(s.y/8))!==0) {s.dx=-s.dx;bounced=true;}
      if (this.tile(Math.floor(s.x/8),Math.floor((s.y+s.dy)/8))!==0) {s.dy=-s.dy;bounced=true;}
      if (this.tile(Math.floor((s.x+s.dx)/8),Math.floor((s.y+s.dy)/8))!==0) {
        s.dx=-s.dx;s.dy=-s.dy;bounced=true;
      }
      // Bounds remain solid even if both components reverse at a tight corner.
      s.x=Math.max(0,Math.min(126,s.x+s.dx));s.y=Math.max(0,Math.min(94,s.y+s.dy));
      if (bounced) this.emit('bounce');
      const atPlayer=Math.floor(s.x/8)===Math.floor(this.player.x/8) && Math.floor(s.y/8)===Math.floor(this.player.y/8);
      if (atPlayer && s.away) {this.shot=null;this.emit('catch');}
      else if (!atPlayer) s.away=true;
    }
    moveEnemies() {
      this.enemyClock+=this.enemySpeed;
      if (this.enemyClock<256) return;
      this.enemyClock-=256;
      for (const e of this.enemies) {
        if (e.spawn>=0) {
          if (e.spawn===0) {e.x=56;e.y=48;e.direction=1;e.active=true;this.emit('spawn');}
          e.spawn--;
        }
      }
      for (const e of this.enemies) {
        if (!e.active) continue;
        e.x+=DX[e.direction];e.y+=DY[e.direction];
        if (!aligned(e)) continue;
        const free=this.freeMask(e.x/8,e.y/8), opposite=e.direction^1;
        const choices=free&~BITS[opposite];
        if (!choices) {
          if (free&BITS[opposite]) e.direction=opposite;
          else {e.x-=DX[e.direction];e.y-=DY[e.direction];} // No exit: stay inside.
        } else {
          // Sampling the original deterministic sequence; bounded against malformed maps.
          for (let n=0;n<256;n++) {
            const d=this.random()&3;
            if (choices&BITS[d]) {e.direction=d;break;}
          }
        }
        if (this.tile(e.x/8,e.y/8)===0) this.put(e.x/8,e.y/8,0);
      }
      this.bonusClock^=1;
      if (!this.bonusClock && --this.bonus<=0) this.die();
    }
    scheduleEnemies() {
      for (const e of this.enemies) {
        if (!this.reserve) break;
        if (!e.active && e.spawn<0) {
          this.reserve--;e.spawn=64+(this.random()&63);e.x=56;e.y=48;
        }
      }
    }
    hits() {
      if (this.cooldown>0) {
        if (--this.cooldown===32) this.emit('recharge');
      }
      for (const e of this.enemies) {
        if (!e.active) continue;
        if (this.shot && near(e,this.shot,6)) {
          e.active=false;this.shot=null;this.cooldown=128+(this.random()&63);
          this.addScore(100);this.emit('hit');
        }
      }
      const objects=this.apples.filter(a=>a.active);
      if (this.sliding) objects.push(this.sliding);
      for (const o of objects) for (const e of this.enemies) {
        if (e.active && near(e,o,6)) {
          e.active=false;this.addScore(this.mode===6?100:250);this.emit('hit');
        }
      }
    }
    findFallingApples() {
      if (this.mode===6) return;
      for (const a of this.apples) {
        if (!aligned(a)) continue;
        const x=a.x/8,y=a.y/8;
        if (y<11 && this.tile(x,y+1)===0) {
          if (a.state==='idle') {a.state='wobble';a.wait=32;a.active=true;}
        } else if (a.state==='fall') {
          a.state='idle';a.active=false;this.put(x,y,TILE.APPLE);this.emit('land');
        }
      }
    }
    moveObjects() {
      for (const a of this.apples) {
        if (a.state==='wobble') {
          if (--a.wait<=0) {this.put(a.x/8,a.y/8,0);a.state='fall';this.emit('fall');}
        } else if (a.state==='fall') {
          a.y++;
        }
      }
      const b=this.sliding;
      if (!b) return;
      b.x+=b.dx;b.y+=b.dy;
      if (aligned(b) && this.tile(b.x/8+b.dx,b.y/8+b.dy)!==0) {
        this.put(b.x/8,b.y/8,b.type);this.sliding=null;this.emit('land');
      }
    }
    tryPush() {
      const p=this.player;
      if (!this.input.fire || !aligned(p) || this.sliding || this.breaking) return;
      const d=p.direction, dx=DX[d],dy=DY[d],x=p.x/8+dx,y=p.y/8+dy;
      const type=this.tile(x,y), beyond=this.tile(x+dx,y+dy);
      if ((type===4 || type===5) && beyond===0) {
        this.sliding={x:x*8,y:y*8,dx,dy,type,direction:d,active:true};
        this.put(x,y,0);this.emit('push');
      } else if (type===4 && beyond!==0) {
        this.breaking={x,y,timer:32};this.addScore(25);this.emit('break');
      }
    }
    animateBreaking() {
      if (this.breaking && --this.breaking.timer<=0) {
        this.put(this.breaking.x,this.breaking.y,0);this.breaking=null;
      }
    }
    checkGoal() {
      if (!aligned(this.player)) return false;
      const done=this.mode===2 ? this.cherries===0 : this.mode===4 ? this.cherries===0 && this.bottomApples===6 : this.cornerApples===4;
      if (done) {this.clear(true);return true;}
      return false;
    }
    clear(mapGoal) {
      if (this.phase!=='playing') return;
      this.addScore(this.bonus+(mapGoal?(this.mapIndex%3+1)*1000:0));
      this.phase='clear';this.timer=224;this.shot=null;
      this.emit('clear',{mapGoal});
    }
    die() {
      if (this.phase!=='playing') return;
      this.phase='dying';this.timer=192;this.shot=null;this.emit('death');
    }
    settleObjects() {
      // Keep the excavated map, but settle partial movements safely on respawn.
      for (const a of this.apples) {
        if (a.active) {
          a.x=Math.max(0,Math.min(120,Math.floor(a.x/8)*8));
          a.y=Math.max(0,Math.min(88,Math.floor(a.y/8)*8));
          this.put(a.x/8,a.y/8,TILE.APPLE);
          a.active=false;a.state='idle';a.wait=0;
        }
      }
      if (this.sliding) {
        const b=this.sliding;
        this.put(Math.max(0,Math.min(15,Math.floor(b.x/8))),Math.max(0,Math.min(11,Math.floor(b.y/8))),b.type);
        this.sliding=null;
      }
    }
  }
  T.Game=Game;
  T.rules={TILE,DX,DY,BITS};
})();
