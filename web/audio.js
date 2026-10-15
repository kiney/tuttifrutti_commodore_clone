/* Two square-wave voices, synthesized locally with Web Audio. */
(() => {
  'use strict';
  const T=globalThis.Tutti,A=T.assets;
  class Audio {
    constructor(enabled=true) {this.enabled=enabled;this.context=null;this.musicTick=0;this.step=0;this.melody=true;}
    async unlock() {
      try {
        const Context=globalThis.AudioContext||globalThis.webkitAudioContext;
        if (!Context) return;
        if (!this.context) {this.context=new Context();this.master=this.context.createGain();this.master.gain.value=0.12;this.master.connect(this.context.destination);}
        if (this.context.state==='suspended') await this.context.resume();
      } catch (_) { /* The game remains playable when audio is unavailable. */ }
    }
    setEnabled(value) {this.enabled=value;this.silence();if(value) this.unlock();}
    silence() {if (this.context&&this.master) this.master.gain.setTargetAtTime(this.enabled?0.12:0,this.context.currentTime,0.01);}
    note(frequency,duration,volume=0.28,slide=0) {
      if (!this.enabled||!this.context||this.context.state!=='running') return;
      const c=this.context,osc=c.createOscillator(),gain=c.createGain(),now=c.currentTime;
      osc.type='square';osc.frequency.setValueAtTime(Math.max(40,Math.min(12000,frequency)),now);
      if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(40,Math.min(12000,frequency+slide)),now+duration);
      gain.gain.setValueAtTime(0,now);gain.gain.linearRampToValueAtTime(volume,now+0.006);
      gain.gain.exponentialRampToValueAtTime(0.001,now+duration);
      osc.connect(gain);gain.connect(this.master);osc.start(now);osc.stop(now+duration+0.015);
    }
    originalNote(index,voice) {
      const low=(voice===1?A.note1Low:A.note2Low)[index]||0;
      const high=(voice===1?A.note1High:A.note2High)[index]||0;
      const value=low+((high&3)<<8);
      // PAL TED tone divider; perceptual recreation, not cycle-exact emulation.
      return 886724/(8*Math.max(1,1024-value));
    }
    tick(game) {
      if (!this.enabled || game.paused || !this.melody || !['title','playing','ready'].includes(game.phase)) return;
      if (++this.musicTick%8) return;
      const pair=A.music[this.step++%192],one=pair>>4,two=pair&15;
      if (one!==1) this.note(this.originalNote(one,1),0.145,0.13);
      if (game.phase!=='playing') this.note(this.originalNote(two,2),0.135,0.10);
    }
    event({type}) {
      const sounds={cherry:[850,.07,.24,350],shoot:[1250,.09,.16,-650],bounce:[450,.035,.15,150],
        catch:[1000,.08,.16,400],push:[160,.06,.14,40],break:[300,.16,.20,-220],
        fall:[170,.18,.16,-100],land:[95,.09,.24,-45],hit:[900,.2,.22,-700],
        death:[700,.7,.25,-650],recharge:[500,.15,.14,900],spawn:[160,.07,.08,80]};
      if (sounds[type]) this.note(...sounds[type]);
      if (['start','clear','gameover'].includes(type)) {
        const notes=type==='gameover'?[392,349,294,196]:type==='clear'?[523,659,784,1046]:[523,659,784];
        // Short independently scheduled notes; no downloaded audio files.
        notes.forEach((f,i)=>setTimeout(()=>this.note(f,.16,.18),i*110));
      }
    }
  }
  T.Audio=Audio;
})();
