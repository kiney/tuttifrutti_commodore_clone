(() => {
  'use strict';
  const T=globalThis.Tutti;
  const $=id=>document.getElementById(id);
  const canvas=$('game'),renderer=new T.Renderer(canvas);
  const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback;}catch(_){return fallback;}};
  const store=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));}catch(_){/* Private mode/quota: keep playing in memory. */}};
  const audio=new T.Audio(read('tutti.sound',true)!==false);
  const saved=read('tutti.highscores',[]);
  const keys=new Set(),pointers=new Map();
  let overlayState='',lastUI=0,lastTime=0,accumulator=0,dialogWasPaused=false;
  const game=new T.Game({highScores:Array.isArray(saved)?saved:[],onEvent:event=>{
    audio.event(event);
    if (event.type==='gameover') store('tutti.highscores',event.highScores);
    if (event.type==='level') $('announcement').textContent=`Round ${event.round}. ${missions[(event.round-1)%3].title}`;
    if (event.type==='death') $('announcement').textContent=`Caught. ${Math.max(0,game.lives-1)} ${game.lives===2?'life':'lives'} remaining.`;
    if (event.type==='gameover') $('announcement').textContent=`Game over. ${event.score} points.`;
    updateUI();
  }});
  const missions=[
    {title:'Cherry picking.',description:'Dig your way through the orchard and collect every cherry.'},
    {title:'Watch for falling apples.',description:'Collect every cherry and bring all six apples down to the bottom row.'},
    {title:'Into the corners.',description:'Push the four apple blocks into the corners. Hold Fire + a direction to push. Blocked cherry blocks break.'}
  ];
  function focusGame() {canvas.focus({preventScroll:true});}
  function clearInput() {
    keys.clear();pointers.clear();
    document.querySelectorAll('.pressed').forEach(e=>e.classList.remove('pressed'));
  }
  function input() {
    const pressed=new Set([...keys,...pointers.values()]);
    let mask=0;
    if(pressed.has('left'))mask|=4;if(pressed.has('right'))mask|=8;
    if(pressed.has('up'))mask|=1;if(pressed.has('down'))mask|=2;
    return {mask,fire:pressed.has('fire')};
  }
  function startGame() {clearInput();audio.unlock();game.start();focusGame();}
  function primaryAction() {
    if(game.paused){game.pause(false);focusGame();}
    else if(['title','gameover'].includes(game.phase))startGame();
  }
  function togglePause() {clearInput();game.pause();focusGame();}
  function toggleSound() {audio.setEnabled(!audio.enabled);store('tutti.sound',audio.enabled);updateUI();focusGame();}
  $('primary-action').addEventListener('click',primaryAction);
  $('restart-action').addEventListener('click',startGame);
  $('pause').addEventListener('click',togglePause);
  $('sound').addEventListener('click',toggleSound);
  canvas.addEventListener('pointerdown',()=>{focusGame();audio.unlock();});
  $('fullscreen').addEventListener('click',async()=>{
    try {if(document.fullscreenElement)await document.exitFullscreen();else await document.querySelector('.arcade').requestFullscreen();}
    catch(_){$('announcement').textContent='Fullscreen is not available in this browser.';}
    focusGame();
  });
  if(!document.documentElement.requestFullscreen)$('fullscreen').hidden=true;

  const mapping={ArrowLeft:'left',KeyA:'left',ArrowRight:'right',KeyD:'right',ArrowUp:'up',KeyW:'up',ArrowDown:'down',KeyS:'down',Space:'fire',KeyF:'fire'};
  function dialogOpen(){return !!document.querySelector('dialog[open]');}
  window.addEventListener('keydown',event=>{
    if(dialogOpen()||event.ctrlKey||event.metaKey||event.altKey)return;
    if(event.code==='Tab')return;
    if(event.code==='KeyM'&&!event.repeat){event.preventDefault();toggleSound();return;}
    if((event.code==='KeyP'||event.code==='Escape')&&!event.repeat){event.preventDefault();togglePause();return;}
    if(['Enter','Space'].includes(event.code)&&(['title','gameover'].includes(game.phase)||game.paused)) {
      if(event.target instanceof HTMLButtonElement && event.target!==$('primary-action'))return;
      event.preventDefault();if(!event.repeat)primaryAction();return;
    }
    if(event.target instanceof HTMLButtonElement && document.activeElement!==canvas)return;
    const action=mapping[event.code];
    if(action){event.preventDefault();keys.add(action);audio.unlock();}
  });
  window.addEventListener('keyup',event=>{const action=mapping[event.code];if(action)keys.delete(action);});
  for(const button of document.querySelectorAll('[data-input]')) {
    button.addEventListener('pointerdown',event=>{
      event.preventDefault();audio.unlock();
      pointers.set(event.pointerId,button.dataset.input);button.classList.add('pressed');
      button.setPointerCapture(event.pointerId);
      if(['title','gameover'].includes(game.phase)&&button.dataset.input==='fire') {
        game.start();focusGame();
      }
    });
    const release=event=>{
      pointers.delete(event.pointerId);
      if(![...pointers.values()].includes(button.dataset.input))button.classList.remove('pressed');
    };
    button.addEventListener('pointerup',release);button.addEventListener('pointercancel',release);button.addEventListener('lostpointercapture',release);
    button.addEventListener('contextmenu',event=>event.preventDefault());
  }
  function backgroundPause(){clearInput();if(!['title','gameover'].includes(game.phase))game.pause(true);}
  window.addEventListener('blur',backgroundPause);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)backgroundPause();});

  function openDialog(dialog) {
    dialogWasPaused=game.paused;
    clearInput();game.pause(true);
    dialog.showModal();
  }
  $('help').addEventListener('click',()=>openDialog($('help-dialog')));
  $('scores').addEventListener('click',()=>{
    const list=$('score-list');list.replaceChildren();
    if(game.highScores.length===0){const li=document.createElement('li');li.className='empty';li.textContent='No harvests yet. Your first completed game will appear here.';list.append(li);}
    else for(const score of game.highScores){const li=document.createElement('li'),strong=document.createElement('strong');li.append('HARVEST');strong.textContent=String(score).padStart(5,'0');li.append(strong);list.append(li);}
    openDialog($('scores-dialog'));
  });
  for(const dialog of document.querySelectorAll('dialog')) {
    for(const button of dialog.querySelectorAll('[data-close]'))button.addEventListener('click',()=>dialog.close());
    dialog.addEventListener('close',()=>{if(!dialogWasPaused)game.pause(false);focusGame();});
    dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
  }
  function updateUI() {
    const phase=game.paused?'paused':game.phase;
    const state=`${phase}:${game.round}`;
    const primary=$('primary-action'),hint=$('overlay-hint'),description=$('overlay-description');
    $('overlay').hidden=phase==='playing';
    if(state!==overlayState) {
      overlayState=state;
      primary.hidden=!['title','paused','gameover'].includes(phase);
      $('restart-action').hidden=phase!=='paused';hint.hidden=false;
      if(phase==='title') {
        $('overlay-kicker').textContent='SIX MAPS. FIVE LIVES.';
        $('overlay-title').innerHTML='FRESH FROM<br><span>THE ORCHARD.</span>';
        description.innerHTML='Pick the cherries. Drop the apples.<br>And stay one step ahead of the gang.';
        primary.textContent='Start game ↗';hint.textContent='OR PRESS ENTER / SPACE';
      } else if(phase==='paused') {
        $('overlay-kicker').textContent='THE ORCHARD CAN WAIT.';
        $('overlay-title').innerHTML='TAKE A<br><span>BREATHER.</span>';
        description.textContent='Your strawberry will be right here.';
        primary.textContent='Resume game ↗';hint.textContent='OR PRESS P';
      } else if(phase==='gameover') {
        $('overlay-kicker').textContent='THE HARVEST IS IN.';
        $('overlay-title').innerHTML='SWEET<br><span>EFFORT.</span>';
        description.textContent=`${String(game.score).padStart(5,'0')} points · Round ${game.round}. Ready for another orchard?`;
        primary.textContent='Play again ↗';hint.textContent='ENTER / SPACE';
      } else if(phase==='ready') {
        $('overlay-kicker').textContent=`ROUND ${String(game.round).padStart(2,'0')} · MAP ${game.mapIndex+1} / 6`;
        $('overlay-title').innerHTML='<span>READY?</span>';
        description.textContent=missions[game.mapIndex%3].description;
        hint.textContent='GET READY TO GO';
      } else if(phase==='clear') {
        $('overlay-kicker').textContent='ANOTHER HARVEST AWAITS.';
        $('overlay-title').innerHTML='SWEET<br><span>SUCCESS.</span>';
        description.textContent='Remaining bonus collected. On to the next orchard!';
        hint.textContent='PREPARING THE NEXT ROUND';
      } else if(phase==='dying') {
        $('overlay-kicker').textContent='WATCH OUT FOR THE GANG.';
        $('overlay-title').innerHTML='<span>CAUGHT.</span>';
        description.textContent=game.lives>1?`Take a breath. You have ${game.lives-1} ${game.lives===2?'life':'lives'} left.`:'That was your last strawberry.';
        hint.textContent=game.lives>1?'BACK TO THE ORCHARD SOON':'COUNTING YOUR HARVEST';
      }
    }
    $('pause').disabled=['title','gameover'].includes(game.phase);
    $('pause').innerHTML=game.paused?'<span aria-hidden="true">▶</span> Resume <kbd>P</kbd>':'<span aria-hidden="true">Ⅱ</span> Pause <kbd>P</kbd>';
    $('sound').setAttribute('aria-pressed',String(audio.enabled));
    $('sound').innerHTML=`<span aria-hidden="true">♪</span> Sound ${audio.enabled?'on':'off'} <kbd>M</kbd>`;
    const mission=missions[game.mapIndex%3];
    $('round-tag').textContent=`${String(game.mapIndex+1).padStart(2,'0')} / 06`;
    $('mission-title').textContent=mission.title;$('mission-description').textContent=mission.description;
    const total=T.assets.maps[game.mapIndex+1].filter(t=>t===2).length;
    if(game.mode===6){$('progress-label').textContent='Filled corners';$('progress-value').textContent=`${game.cornerApples} / 4`;$('progress-bar').style.width=`${game.cornerApples/4*100}%`;}
    else {
      $('progress-label').textContent=game.mode===4?`Cherries · Apples down ${game.bottomApples}/6`:'Cherries';
      $('progress-value').textContent=`${total-game.cherries} / ${total}`;
      $('progress-bar').style.width=`${(total-game.cherries)/Math.max(1,total)*100}%`;
    }
  }
  for(const icon of document.querySelectorAll('[data-icon]'))renderer.icon(icon,Number(icon.dataset.icon));
  const enemyIcon=$('enemy-icon');enemyIcon.width=enemyIcon.height=16;
  const ec=enemyIcon.getContext('2d');
  for(let i=0;i<4;i++)ec.drawImage(renderer.glyph(0xa4+30+i,0x79),(i%2)*8,(i>>1)*8);

  const debug=new URLSearchParams(location.search).has('debug')?{game,renderer,audio,keys,pointers,manual:false}:null;
  if(debug)T.debug=debug;
  function frame(time) {
    if(!lastTime)lastTime=time;
    const delta=Math.min(100,time-lastTime);lastTime=time;
    if(!debug?.manual) {
      accumulator+=delta;
      while(accumulator>=20){game.step(input());audio.tick(game);accumulator-=20;}
    } else accumulator=0;
    renderer.draw(game,time);
    if(time-lastUI>100){updateUI();lastUI=time;}
    requestAnimationFrame(frame);
  }
  updateUI();renderer.draw(game);requestAnimationFrame(frame);
})();
