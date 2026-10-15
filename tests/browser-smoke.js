/* Evaluate this async function in the browser at /?debug=1. No test libraries. */
async () => {
  const results=[];
  const check=(condition,message)=>{if(!condition)throw new Error(message);results.push(message);};
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const d=Tutti.debug,g=d.game,canvas=document.querySelector('#game');
  const key=(code,type='keydown')=>window.dispatchEvent(new KeyboardEvent(type,{code,bubbles:true,cancelable:true}));
  d.manual=true;g.start();for(let i=0;i<96;i++)g.step({mask:0});
  check(g.phase==='playing','Start / get ready reaches playable state');
  canvas.focus();d.manual=false;
  const before=g.player.x;key('ArrowLeft');await sleep(380);key('ArrowLeft','keyup');
  await sleep(100);d.manual=true;
  check(g.player.x<before,'Keyboard input moves the actual animated game');
  check(d.keys.size===0,'Key release clears held input');
  key('KeyP');check(g.paused,'P pauses');
  const tick=g.tick;d.manual=false;await sleep(100);d.manual=true;check(g.tick===tick,'Pause freezes simulation');
  key('KeyP');check(!g.paused,'P resumes');
  document.querySelector('#help').click();check(document.querySelector('#help-dialog').open&&g.paused,'Help opens and pauses');
  document.querySelector('#help-dialog [data-close]').click();await sleep(30);check(!document.querySelector('#help-dialog').open&&!g.paused,'Closing help resumes previous state');
  g.pause(true);document.querySelector('#scores').click();document.querySelector('#scores-dialog [data-close]').click();await sleep(30);
  check(g.paused,'Closing a dialog preserves a pre-existing pause');g.pause(false);
  const enabled=d.audio.enabled;key('KeyM');check(d.audio.enabled!==enabled,'M toggles audio');key('KeyM');
  g.round=3;g.loadRound(0);g.phase='playing';g.map.fill(0);g.map[191]=4;g.enemySpeed=0;g.enemies=[{active:false,spawn:9999}];
  g.player.x=8;g.player.y=8;g.player.stopped=true;g.put(2,1,5);g.put(5,1,7);
  const right=document.querySelector('[data-input="right"]'),fire=document.querySelector('[data-input="fire"]');
  // Synthetic DOM events exercise simultaneous pointer bookkeeping without a device driver.
  const rightCapture=right.setPointerCapture,fireCapture=fire.setPointerCapture;
  right.setPointerCapture=fire.setPointerCapture=()=>{};
  right.dispatchEvent(new PointerEvent('pointerdown',{pointerId:11,bubbles:true,cancelable:true}));
  fire.dispatchEvent(new PointerEvent('pointerdown',{pointerId:12,bubbles:true,cancelable:true}));
  check(d.pointers.get(11)==='right'&&d.pointers.get(12)==='fire','Touch supports direction plus fire simultaneously');
  d.manual=false;await sleep(90);d.manual=true;
  check(g.sliding!==null||g.tile(4,1)===5,'Touch input starts pushing a puzzle block');
  right.dispatchEvent(new PointerEvent('pointercancel',{pointerId:11,bubbles:true}));
  fire.dispatchEvent(new PointerEvent('pointerup',{pointerId:12,bubbles:true}));
  right.setPointerCapture=rightCapture;fire.setPointerCapture=fireCapture;
  check(d.pointers.size===0&&!document.querySelector('.pressed'),'Touch release and cancellation clear controls');
  window.dispatchEvent(new Event('blur'));check(g.paused,'Losing window focus pauses');g.pause(false);
  g.phase='playing';g.score=9876;g.lives=1;g.die();for(let i=0;i<192;i++)g.step({mask:0});
  check(g.phase==='gameover'&&JSON.parse(localStorage.getItem('tutti.highscores')).includes(9876),'Game over persists highscore');
  await sleep(120);document.querySelector('#primary-action').click();check(g.phase==='ready'&&g.score===0&&g.lives===5,'Replay button starts a fresh game');
  const resources=performance.getEntriesByType('resource').map(x=>new URL(x.name).origin);
  check(resources.every(origin=>origin===location.origin),'All runtime requests stay on the static host');
  check(document.documentElement.scrollWidth<=innerWidth,'No horizontal overflow at current viewport');
  check(document.querySelector('#game').getContext('2d').getImageData(0,0,320,200).data.some(v=>v>20),'Canvas contains rendered game pixels');
  return {passed:results.length,results,viewport:[innerWidth,innerHeight],audio:d.audio.context?.state||'not unlocked'};
}
