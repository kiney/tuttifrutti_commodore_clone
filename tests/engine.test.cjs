'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
require('../web/assets.js');require('../web/engine.js');
const {Game,assets,rules}=globalThis.Tutti;
const neutral={mask:0,fire:false};
function advance(g,n,input=neutral){for(let i=0;i<n;i++)g.step(input);}
function fixture(round=1){
  const g=new Game({seed:1});g.round=round;g.loadRound(0);g.phase='playing';g.clock=0;
  // Isolate rules from enemy AI; keep an unspawned enemy to prevent the alternate goal.
  g.enemySpeed=0;g.enemies=[{active:false,spawn:999999}];return g;
}
function emptyFixture(round=1){const g=fixture(round);g.map.fill(0);g.put(15,11,2);g.apples=[];return g;}

test('assets match the original PRG byte-for-byte, including all six maps',()=>{
  const file=fs.readFileSync('tuttifrutti.prg'),base=file.readUInt16LE(0),get=(a,n)=>[...file.subarray(a-base+2,a-base+2+n)];
  assert.equal(assets.maps.length,7);
  for(let i=0;i<7;i++)assert.deepEqual(assets.maps[i],get(0x3500+i*96,96).flatMap(b=>[b>>4,b&15]));
  assert.deepEqual(assets.charset.slice(0,2047),get(0x3800,2047));
  assert.deepEqual(assets.maps.slice(1).map(m=>m.filter(t=>t===2).length),[32,6,0,40,6,0]);
});
test('new game, get-ready countdown, five lives and pause freeze all state',()=>{
  const g=new Game();g.start();assert.equal(g.phase,'ready');assert.equal(g.lives,5);
  advance(g,96);assert.equal(g.phase,'playing');
  g.pause(true);const before=JSON.stringify(g);advance(g,500);assert.equal(JSON.stringify(g),before);
  g.pause(false);g.step();assert.equal(g.tick,97);
});
test('player digs, collects cherries once, respects walls and finishes a move after key release',()=>{
  const g=emptyFixture();g.player.x=16;g.player.y=16;g.put(3,2,2);g.put(4,2,3);
  advance(g,16,{mask:8});assert.equal(g.player.x,24);assert.equal(g.score,25);assert.equal(g.tile(3,2),0);
  advance(g,16,{mask:8});assert.equal(g.player.x,24);assert.equal(g.score,25);
  g.put(4,2,1);advance(g,4,{mask:8});assert.equal(g.player.x,26);
  advance(g,12);assert.equal(g.player.x,32);assert.equal(g.tile(4,2),0);
  advance(g,2);assert.equal(g.player.x,32);
});
test('random source matches original and enemies cannot dig through earth',()=>{
  const g=fixture();g.seed=0xabcdef;g.random();assert.equal(g.seed,(0xabcdef+0xb13579)&0xffffff);
  g.map.fill(1);g.put(0,0,2);g.put(7,6,0);g.put(8,6,0);g.put(9,6,0);
  g.enemySpeed=256;g.enemies=[{x:56,y:48,direction:1,active:true,spawn:-1}];
  advance(g,16);assert.equal(g.enemies[0].x,72);assert.equal(g.enemies[0].direction,0);
  assert.equal(g.tile(9,5),1);
});
test('shot bounces, can be caught, damages enemies and recharges',()=>{
  const g=emptyFixture();g.player.x=32;g.player.y=32;g.player.direction=1;
  g.input={fire:true};g.tryShoot();assert.deepEqual([g.shot.dx,g.shot.dy],[2,-2]);
  g.shot={x:10,y:16,dx:2,dy:2,away:true};g.put(1,2,1);g.moveShot();assert.ok(g.shot);
  g.map.fill(0);g.put(15,11,2);g.player.x=32;g.player.y=32;
  g.shot={x:30,y:32,dx:2,dy:0,away:true};g.moveShot();assert.equal(g.shot,null);
  g.enemies=[{active:true,x:40,y:32,spawn:-1}];g.shot={x:40,y:32};g.hits();
  assert.equal(g.enemies[0].active,false);assert.equal(g.score,100);assert.ok(g.cooldown>=128);
  g.shot=null;const time=g.cooldown;for(let i=0;i<time;i++)g.hits();assert.equal(g.cooldown,0);
});
test('six apples have a delay, fall down shafts, stop on bottom row and kill enemies',()=>{
  const g=emptyFixture(2);g.player.x=0;g.player.y=8;
  g.apples=[{x:16,y:16,dx:0,dy:1,state:'idle',wait:0,active:false,direction:2}];g.put(2,2,3);
  g.findFallingApples();assert.equal(g.apples[0].wait,32);
  advance(g,31);assert.equal(g.apples[0].y,16);assert.equal(g.tile(2,2),3);
  advance(g,1);assert.equal(g.tile(2,2),0);advance(g,72);
  assert.equal(g.apples[0].y,88);assert.equal(g.apples[0].state,'idle');assert.equal(g.tile(2,11),3);
  g.enemies=[{active:true,x:16,y:80,spawn:-1}];g.apples[0].y=80;g.apples[0].active=true;
  g.hits();assert.equal(g.score,250);assert.equal(g.enemies[0].active,false);
});
test('puzzle blocks slide until obstructed; cherries break only against a barrier; fire is disabled',()=>{
  const g=emptyFixture(3);g.player.x=8;g.player.y=8;g.player.direction=1;
  g.put(2,1,5);g.put(5,1,7);g.input={mask:8,fire:true};g.tryPush();assert.ok(g.sliding);
  assert.equal(g.tile(2,1),0);for(let i=0;i<16;i++)g.moveObjects();
  assert.equal(g.sliding,null);assert.equal(g.tile(4,1),5);
  g.put(2,1,4);g.put(3,1,4);g.tryPush();assert.ok(g.breaking);assert.equal(g.score,25);
  for(let i=0;i<32;i++)g.animateBreaking();assert.equal(g.tile(2,1),0);
  g.tryShoot();assert.equal(g.shot,null);
});
test('all three map objectives, remaining bonus, progression and cycling past six maps',()=>{
  for(const round of [1,2,3,4,5,6,7,16]){
    const g=fixture(round);g.map.fill(0);g.player.x=0;g.player.y=0;g.bonus=123;
    if(g.mode===4)for(let x=0;x<6;x++)g.put(x,11,3);
    if(g.mode===6)for(const i of [0,15,176,191])g.map[i]=5;
    assert.equal(g.checkGoal(),true);assert.equal(g.phase,'clear');
    assert.equal(g.score,123+((round-1)%3+1)*1000);
    advance(g,96);assert.equal(g.round,round+1);assert.equal(g.phase,'ready');
    assert.deepEqual(g.map,assets.maps[(round%6)+1]);
    advance(g,128);assert.equal(g.phase,'playing');
  }
});
test('cherries alone do not finish an apple level and three corners do not finish a puzzle',()=>{
  const g=emptyFixture(2);g.map.fill(0);assert.equal(g.checkGoal(),false);
  g.round=3;g.map.fill(0);[0,15,176].forEach(i=>g.map[i]=5);assert.equal(g.checkGoal(),false);
});
test('enemy reserve must be exhausted before the alternate level goal',()=>{
  const g=fixture(4);g.enemies=[{active:false,spawn:-1}];g.reserve=1;
  g.step();assert.equal(g.phase,'playing');assert.equal(g.reserve,0);assert.ok(g.enemies[0].spawn>=64);
  g.enemies[0].spawn=-1;g.step();assert.equal(g.phase,'clear');
  assert.equal(g.score,599);
});
test('death preserves the dug map and score; five deaths end the game and record a score',()=>{
  const events=[],g=fixture();g.onEvent=e=>events.push(e);g.put(2,2,0);g.score=1234;
  for(let life=5;life>0;life--){
    g.phase='playing';g.die();advance(g,192);assert.equal(g.lives,life-1);
    if(life>1){assert.equal(g.phase,'ready');assert.equal(g.tile(2,2),0);assert.equal(g.score,1234);}
  }
  assert.equal(g.phase,'gameover');assert.deepEqual(g.highScores,[1234]);
  assert.equal(events.filter(e=>e.type==='gameover').length,1);
  g.start();assert.equal(g.lives,5);assert.equal(g.score,0);assert.deepEqual(g.highScores,[1234]);
});
test('bonus reaching zero costs a life and elapsed clock uses 60 simulation ticks',()=>{
  const g=fixture();g.enemySpeed=256;g.bonus=1;g.bonusClock=1;
  g.step();assert.equal(g.phase,'dying');
  const h=fixture();advance(h,120);assert.equal(h.seconds,2);
});
test('full cherry-map routes can be traversed and completed by normal direction input',()=>{
  for(const round of [1,4]){
    const g=fixture(round);g.apples=[];
    // Pathfinding is a test driver only: the shipped player is always human-controlled.
    for(let targetCount=0;targetCount<50&&g.phase==='playing';targetCount++){
      const start=g.player.y/8*16+g.player.x/8;
      const queue=[start],visited=new Set([start]),previous=new Map();let goal;
      while(queue.length){
        const i=queue.shift();if(g.map[i]===2){goal=i;break;}
        for(let d=0;d<4;d++){
          const x=i%16+rules.DX[d],y=Math.floor(i/16)+rules.DY[d],next=y*16+x;
          if(g.tile(x,y)<3&&!visited.has(next)){visited.add(next);previous.set(next,[i,d]);queue.push(next);}
        }
      }
      assert.notEqual(goal,undefined,`reachable cherry on round ${round}`);
      const route=[];for(let i=goal;i!==start;){const [p,d]=previous.get(i);route.unshift(d);i=p;}
      for(const d of route)advance(g,16,{mask:rules.BITS[d]});
    }
    assert.equal(g.cherries,0);assert.equal(g.phase,'clear');
    assert.equal(g.score,(round===1?32:40)*25+599+1000);
  }
});
test('long seeded games keep player, enemies, projectiles and apples inside the board',()=>{
  for(let seed=1;seed<=6;seed++){
    const g=new Game({seed});g.start();g.round=seed;g.loadRound(0);
    for(let tick=0;tick<15000&&g.phase!=='gameover';tick++){
      const d=Math.floor(tick/18)%4;g.step({mask:rules.BITS[d],fire:tick%4!==0});
      for(const a of [g.player,...g.enemies.filter(e=>e.active),...g.apples,g.shot].filter(Boolean)){
        assert.ok(a.x>=0&&a.x<=127,`x=${a.x} seed=${seed}`);
        assert.ok(a.y>=0&&a.y<=95,`y=${a.y} seed=${seed}`);
      }
      assert.equal(g.map.length,192);assert.ok(g.map.every(t=>t>=0&&t<=7));
    }
  }
});
