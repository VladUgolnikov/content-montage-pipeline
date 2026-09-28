// MAOS Reels — композиция по согласованному визуальному языку (артефакт «Визуальный язык MAOS»).
// Всё время в props — секунды итогового таймлайна (после ускорения).
import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill, Audio, Easing, Img, OffthreadVideo, Sequence, continueRender, delayRender,
  interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {
  baseGeom, Stage, ChartBlock, LogosBlock, ThirtyBlock, WordBlock, TagBlock, ReportBlock, BadgeBlock, CardsBlock, SystemBlock, WindowsBlock, DaysBlock, HookBlock,
  Layout, Chart, Logos, Thirty, Word, Tag, Report, Badge, Cards, System, Windows, Days, Hook,
} from './Blocks';
import {JugScene} from './Jug';

// ---------- токены дизайна ----------
const C = {
  red: '#e60f13', redDeep: '#b60b0e', ink: '#f4f2ee', ink2: '#a9a7a2', line: '#2a2a30',
  grey: '#6a6a74', panel: 'rgba(20,20,24,.9)', dark: 'rgba(12,12,14,.85)',
};
const DISP = 'Oswald, "Arial Narrow", sans-serif';
const UI = '"Golos Text", system-ui, sans-serif';
const POP = Easing.bezier(0.2, 0.9, 0.3, 1.2);
const OUT = Easing.bezier(0.2, 0.8, 0.2, 1);
const SAFE = {left: 60, right: 890, top: 120, bottom: 1530};
const SAFE_CX = (SAFE.left + SAFE.right) / 2;

// ---------- типы ----------
type SubWord = {text: string; t: number; acc?: boolean};
type SubLine = {t0: number; t1: number; words: SubWord[]};
type Ov =
  | {type: 'chip'; t0: number; t1: number; text: string; pulses?: number[]}
  | {type: 'lower'; t0: number; t1: number; name: string; role: string}
  | {type: 'bars'; t0: number; t1: number; title: string; rows: {label: string; from: number; to: number; value: string; red?: boolean; t: number}[]}
  | {type: 'bignum'; t0: number; t1: number; from?: number; to: number; prefix?: string; suffix?: string; caption?: string; y?: number; count?: boolean}
  | {type: 'checklist'; t0: number; t1: number; items: {text: string; t: number}[]; y?: number}
  | {type: 'endcard'; t0: number; t1: number; label: string; big: string; chip: string; note?: string; noteT?: number}
  | {type: 'spot'; t0: number; t1: number; big: string; caption?: string; sub?: string}
  | Layout | Chart | Logos | Thirty | Word | Tag | Report | Badge | Cards | System | Windows | Days
  | {type: 'jug'; t0: number; t1: number}
  | {type: 'zoom'; t0: number; t1: number; from: number; to: number}
  | {type: 'stage'; t0: number; t1: number};
type Music = {src: string; vol: number; duck: number; mutes?: [number, number][]; fadeFrom?: number; fadeTo?: number; startFrom?: number};
export type ReelProps = {
  duration: number;
  base?: string;        // видео-основа (media/base.mp4)
  baseImage?: string;   // для отладки кадров без видео
  subs: SubLine[];
  overlays: Ov[];
  sfx?: {t: number; src: string; vol?: number}[];
  subSize?: number;     // кегль субтитров (по умолчанию 96)
  music?: Music;        // подложка с дакингом под речь
  speech?: [number, number][];   // интервалы речи (для дакинга)
  nosubs?: [number, number][];   // где субтитры прячем (крупное слово на чёрном и т.п.)
};
export const defaultProps: ReelProps = {duration: 5, subs: [], overlays: []};

// ---------- утилиты ----------
const useT = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return f / fps;
};
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const vis = (t: number, t0: number, t1: number, fi = 0.25, fo = 0.25) =>
  Math.min(interpolate(t, [t0, t0 + fi], [0, 1], clamp), interpolate(t, [t1 - fo, t1], [1, 0], clamp));

const useFonts = () => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const faces = [
      new FontFace('Oswald', `url(${staticFile('fonts/Oswald700.ttf')})`, {weight: '400 900'}),
      new FontFace('Golos Text', `url(${staticFile('fonts/GolosText.ttf')})`, {weight: '400 900'}),
      new FontFace('Caveat', `url(${staticFile('fonts/Caveat.ttf')})`, {weight: '400 700'}),
    ];
    Promise.all(faces.map((f) => f.load()))
      .then((ls) => { ls.forEach((f) => document.fonts.add(f)); continueRender(h); })
      .catch(() => continueRender(h));
  }, [h]);
};

// ---------- субтитры: капс, пословное появление, акцент — красный бокс ----------
const Subs: React.FC<{subs: SubLine[]; size?: number}> = ({subs, size = 96}) => {
  const k = size / 96;
  const t = useT();
  const cur = subs.find((s) => t >= s.t0 && t < s.t1);
  if (!cur) return null;
  return (
    <div style={{
      position: 'absolute', left: SAFE.left, width: SAFE.right - SAFE.left, bottom: 1920 - SAFE.bottom,
      textAlign: 'center', fontFamily: DISP, fontWeight: 700, fontSize: size, lineHeight: 1.12,
      textTransform: 'uppercase', letterSpacing: '0.005em', color: '#fff',
    }}>
      {cur.words.map((w, i) => {
        const p = interpolate(t - w.t, [0, 0.34], [0, 1], {...clamp, easing: POP});
        const shown = t >= w.t;
        const base: React.CSSProperties = {
          display: 'inline-block', margin: '0 0.11em', opacity: shown ? Math.min(1, p * 1.6) : 0,
          transform: `translateY(${(1 - p) * 20}px) scale(${0.9 + 0.1 * p})`,
        };
        const st: React.CSSProperties = w.acc
          ? {...base, background: C.red, padding: '0.02em 0.2em', borderRadius: 12,
             boxShadow: `0 8px 0 ${C.redDeep}, 0 10px 30px rgba(0,0,0,.35)`}
          : {...base, WebkitTextStroke: `${5 * k}px #000`, paintOrder: 'stroke fill',
             textShadow: `0 ${5 * k}px 0 #000, 0 0 ${34 * k}px rgba(0,0,0,.65), 0 ${10 * k}px ${50 * k}px rgba(0,0,0,.6)`};
        return <span key={i} style={st}>{w.text}</span>;
      })}
    </div>
  );
};

// ---------- красный чип сверху (якорь сериальности) ----------
const Chip: React.FC<{o: Extract<Ov, {type: 'chip'}>}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.4, 0.3);
  const dy = interpolate(t, [o.t0, o.t0 + 0.4], [-15, 0], {...clamp, easing: OUT});
  const pulse = (o.pulses || []).reduce((m, p) => Math.max(m,
    interpolate(t, [p, p + 0.18, p + 0.6], [0, 1, 0], clamp)), 0);
  return (
    <div style={{
      position: 'absolute', top: 150, left: 540, opacity: a,
      transform: `translate(-50%, ${dy}px) scale(${1 + 0.16 * pulse})`,
      fontFamily: DISP, fontWeight: 700, fontSize: 52, textTransform: 'uppercase', letterSpacing: '0.03em',
      color: '#fff', background: C.red, padding: '0.1em 0.5em', borderRadius: 12,
      boxShadow: `0 9px 0 ${C.redDeep}`, whiteSpace: 'nowrap',
    }}>{o.text}</div>
  );
};

// ---------- плашка-титр ----------
const Lower: React.FC<{o: Extract<Ov, {type: 'lower'}>}> = ({o}) => {
  const t = useT();
  const x = interpolate(t, [o.t0, o.t0 + 0.5], [-118, 0], {...clamp, easing: OUT});
  const a = interpolate(t, [o.t1 - 0.3, o.t1], [1, 0], clamp);
  return (
    <div style={{
      position: 'absolute', left: 70, top: 1130, opacity: a, transform: `translateX(${x}%)`,
      background: C.dark, borderLeft: `8px solid ${C.red}`, borderRadius: 10, padding: '22px 34px 24px',
    }}>
      <div style={{fontFamily: DISP, fontWeight: 700, fontSize: 54, color: '#fff', letterSpacing: '0.01em'}}>{o.name}</div>
      <div style={{fontFamily: UI, fontSize: 31, color: C.ink2, marginTop: 4}}>{o.role}</div>
    </div>
  );
};

// ---------- пропорциональный бар-чарт (было → стало) ----------
const Bars: React.FC<{o: Extract<Ov, {type: 'bars'}>}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.3, 0.3);
  const dy = interpolate(t, [o.t0, o.t0 + 0.35], [24, 0], {...clamp, easing: OUT});
  const max = Math.max(...o.rows.flatMap((r) => [r.from, r.to]));
  return (
    <div style={{
      position: 'absolute', left: SAFE.left + 10, width: SAFE.right - SAFE.left - 20, top: 120, opacity: a,
      transform: `translateY(${dy}px)`, background: C.panel, border: `2px solid ${C.line}`, borderRadius: 32,
      padding: '30px 36px 34px', boxShadow: '0 20px 60px rgba(0,0,0,.45)',
    }}>
      <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 34, letterSpacing: '0.06em', textTransform: 'uppercase', color: C.ink2, marginBottom: 18}}>{o.title}</div>
      {o.rows.map((r, i) => {
        const shown = interpolate(t, [o.t0 + 0.15 * i, o.t0 + 0.15 * i + 0.3], [0, 1], clamp);
        const g = interpolate(t, [r.t, r.t + 1.0], [0, 1], {...clamp, easing: OUT});
        const w = (r.from + (r.to - r.from) * g) / max;
        const va = interpolate(t, [r.t + 0.5, r.t + 0.9], [0, 1], clamp);
        return (
          <div key={i} style={{opacity: shown, marginTop: i ? 22 : 0}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
              <span style={{fontFamily: DISP, fontWeight: 700, fontSize: 44, textTransform: 'uppercase', color: '#fff', letterSpacing: '0.02em'}}>{r.label}</span>
              <span style={{fontFamily: DISP, fontWeight: 700, fontSize: 64, color: r.red ? C.red : '#fff', opacity: va, fontVariantNumeric: 'tabular-nums'}}>{r.value}</span>
            </div>
            <div style={{position: 'relative', height: 34, marginTop: 8, background: 'rgba(255,255,255,.06)', borderRadius: 8}}>
              <div style={{position: 'absolute', left: `${(r.from / max) * 100}%`, top: -6, bottom: -6, width: 3, background: 'rgba(255,255,255,.35)'}} />
              <div style={{height: '100%', width: `${w * 100}%`, borderRadius: 8, background: r.red ? C.red : C.grey,
                boxShadow: r.red ? `0 5px 0 ${C.redDeep}` : 'none'}} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- крупная цифра / одометр ----------
const BigNum: React.FC<{o: Extract<Ov, {type: 'bignum'}>}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.2, 0.3);
  const p = interpolate(t, [o.t0, o.t0 + 0.35], [0, 1], {...clamp, easing: POP});
  const c = interpolate(t, [o.t0, o.t0 + 1.3], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const v = o.count === false ? o.to : Math.round((o.from ?? 0) + (o.to - (o.from ?? 0)) * c);
  return (
    <div style={{position: 'absolute', left: SAFE.left, width: SAFE.right - SAFE.left, top: o.y ?? 200, textAlign: 'center',
      opacity: a, transform: `scale(${0.85 + 0.15 * p})`}}>
      <div style={{fontFamily: DISP, fontWeight: 700, fontSize: 250, lineHeight: 1, color: C.red,
        fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap',
        textShadow: '0 10px 0 #4a0405, 0 0 70px rgba(230,15,19,.35)'}}>
        {o.prefix || ''}{v.toLocaleString('ru-RU')}{o.suffix || ''}
      </div>
      {o.caption ? (
        <div style={{display: 'inline-block', marginTop: 18, fontFamily: DISP, fontWeight: 600, fontSize: 44,
          textTransform: 'uppercase', letterSpacing: '0.1em', color: '#fff', background: C.dark,
          padding: '8px 22px', borderRadius: 10}}>{o.caption}</div>
      ) : null}
    </div>
  );
};

// ---------- список (сколько стоит / как проверить / как исправить) ----------
const Checklist: React.FC<{o: Extract<Ov, {type: 'checklist'}>}> = ({o}) => {
  const t = useT();
  const a = interpolate(t, [o.t1 - 0.3, o.t1], [1, 0], clamp);
  return (
    <div style={{position: 'absolute', left: SAFE.left + 30, top: o.y ?? 190, opacity: a}}>
      {o.items.map((it, i) => {
        const p = interpolate(t, [it.t, it.t + 0.35], [0, 1], {...clamp, easing: POP});
        if (t < it.t) return null;
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, marginBottom: 20,
            opacity: Math.min(1, p * 1.5), transform: `translateX(${(1 - p) * -40}px)`,
            background: 'rgba(12,12,14,.82)', border: `2px solid ${C.line}`, borderRadius: 50, padding: '16px 34px 16px 22px'}}>
            <div style={{width: 46, height: 46, borderRadius: 23, background: C.red, color: '#fff', fontFamily: DISP,
              fontWeight: 700, fontSize: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 0 8px rgba(230,15,19,.2)'}}>{i + 1}</div>
            <div style={{fontFamily: DISP, fontWeight: 700, fontSize: 54, textTransform: 'uppercase', letterSpacing: '0.03em', color: '#fff'}}>{it.text}</div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- финальная карточка ----------
const EndCard: React.FC<{o: Extract<Ov, {type: 'endcard'}>}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.3, 0.01);
  const dy = interpolate(t, [o.t0, o.t0 + 0.4], [30, 0], {...clamp, easing: OUT});
  const ca = interpolate(t, [o.t0 + 0.35, o.t0 + 0.7], [0, 1], {...clamp, easing: POP});
  const na = interpolate(t, [(o.noteT ?? o.t0 + 0.8), (o.noteT ?? o.t0 + 0.8) + 0.4], [0, 1], clamp);
  return (
    <div style={{position: 'absolute', left: SAFE.left + 10, width: SAFE.right - SAFE.left - 20, top: 150, opacity: a,
      transform: `translateY(${dy}px)`, background: C.panel, border: `2px solid ${C.line}`, borderRadius: 32,
      padding: '34px 40px 38px', boxShadow: '0 20px 60px rgba(0,0,0,.45)'}}>
      <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 34, letterSpacing: '0.12em', textTransform: 'uppercase', color: C.ink2}}>{o.label}</div>
      <div style={{display: 'flex', alignItems: 'center', gap: 24, marginTop: 10}}>
        <span style={{fontFamily: DISP, fontWeight: 700, fontSize: 130, lineHeight: 1, color: '#fff', textTransform: 'uppercase'}}>{o.big}</span>
        <span style={{fontFamily: DISP, fontWeight: 700, fontSize: 80, color: '#fff', background: C.red, padding: '0 0.3em',
          borderRadius: 12, boxShadow: `0 8px 0 ${C.redDeep}`, transform: `scale(${0.8 + 0.2 * ca})`, opacity: ca}}>{o.chip}</span>
      </div>
      {o.note ? <div style={{fontFamily: UI, fontSize: 36, color: C.ink, marginTop: 18, opacity: na}}>{o.note}</div> : null}
    </div>
  );
};

// ---------- чёрный экран-акцент (силуэт света + крупная цифра) ----------
const Spot: React.FC<{o: Extract<Ov, {type: 'spot'}>}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.1, 0.14);
  const p = interpolate(t, [o.t0 + 0.05, o.t0 + 0.4], [0, 1], {...clamp, easing: POP});
  return (
    <AbsoluteFill style={{opacity: a, background: '#050506'}}>
      <AbsoluteFill style={{background: 'radial-gradient(120% 60% at 50% 8%, rgba(255,255,255,.16), transparent 55%)'}} />
      <div style={{position: 'absolute', top: 560, left: 0, right: 0, textAlign: 'center', transform: `scale(${0.8 + 0.2 * p})`}}>
        {o.caption ? <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 56, letterSpacing: '0.14em', textTransform: 'uppercase', color: C.ink2, marginBottom: 10}}>{o.caption}</div> : null}
        <div style={{fontFamily: DISP, fontWeight: 700, fontSize: 380, lineHeight: 1, color: C.red,
          textShadow: '0 12px 0 #4a0405, 0 0 90px rgba(230,15,19,.4)'}}>{o.big}</div>
        {o.sub ? <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 52, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#fff', marginTop: 16}}>{o.sub}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------- сборка ----------
export const Reel: React.FC<ReelProps> = (props) => {
  useFonts();
  const {fps} = useVideoConfig();
  const t = useT();
  const layouts = props.overlays.filter((o) => o.type === 'layout') as Layout[];
  const zooms = props.overlays.filter((o) => o.type === 'zoom') as {t0: number; t1: number; from: number; to: number}[];
  const g = baseGeom(t, layouts, zooms);
  const stageA = g.bg;
  const hideSubs = (props.nosubs || []).some(([a, b]) => t >= a && t < b);
  const mv = (f: number) => {
    const m = props.music!; const tt = f / fps;
    if ((m.mutes || []).some(([a, b]) => tt >= a - 0.02 && tt < b)) return 0;
    const sp = (props.speech || []).some(([a, b]) => tt >= a - 0.12 && tt < b + 0.25);
    let v = sp ? m.duck : m.vol;
    // мягкий вход после паузы-мьюта
    for (const [, b] of m.mutes || []) if (tt >= b && tt < b + 0.25) v *= (tt - b) / 0.25;
    if (m.fadeFrom !== undefined && m.fadeTo !== undefined) v *= interpolate(tt, [m.fadeFrom, m.fadeTo], [1, 0], clamp);
    return v;
  };
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <Stage a={stageA} />
      {props.base ? (
        <div style={{position: 'absolute', left: g.box[0], top: g.box[1], width: g.box[2], height: g.box[3], overflow: 'hidden',
          borderRadius: g.bg > 0 && layouts.some((L) => L.mode === 'window' && t >= L.t0 && t < L.t1) ? 28 * g.bg : 0,
          boxShadow: g.bg > 0 ? '0 20px 60px rgba(0,0,0,.6)' : 'none'}}>
          <div style={{position: 'absolute', left: g.inner[0], top: g.inner[1], width: 1080, height: 1920,
            transform: `scale(${g.inner[2] * g.z})`, transformOrigin: g.z !== 1 ? '540px 700px' : '0 0'}}>
            <OffthreadVideo src={staticFile(props.base)} style={{width: 1080, height: 1920}} />
          </div>
        </div>
      ) : null}
      {props.baseImage ? <Img src={staticFile(props.baseImage)} style={{width: 1080, height: 1920}} /> : null}
      {props.overlays.filter((o) => t >= o.t0 && t < o.t1).map((o, i) => {
        switch (o.type) {
          case 'chip': return <Chip key={i} o={o} />;
          case 'lower': return <Lower key={i} o={o} />;
          case 'bars': return <Bars key={i} o={o} />;
          case 'bignum': return <BigNum key={i} o={o} />;
          case 'checklist': return <Checklist key={i} o={o} />;
          case 'endcard': return <EndCard key={i} o={o} />;
          case 'spot': return <Spot key={i} o={o} />;
          case 'chart': return <ChartBlock key={i} o={o} />;
          case 'logos': return <LogosBlock key={i} o={o} />;
          case 'thirty': return <ThirtyBlock key={i} o={o} />;
          case 'word': return <WordBlock key={i} o={o} />;
          case 'tag': return <TagBlock key={i} o={o} />;
          case 'report': return <ReportBlock key={i} o={o} />;
          case 'badge': return <BadgeBlock key={i} o={o} />;
          case 'cards': return <CardsBlock key={i} o={o} />;
          case 'system': return <SystemBlock key={i} o={o} />;
          case 'windows': return <WindowsBlock key={i} o={o} />;
          case 'days': return <DaysBlock key={i} o={o} />;
          case 'hook': return <HookBlock key={i} o={o as Hook} />;
          case 'jug': return <JugScene key={i} t0={o.t0} t1={o.t1} />;
          case 'stage': return <Stage key={i} a={Math.min(interpolate(t, [o.t0, o.t0 + 0.2], [0, 1], clamp), interpolate(t, [o.t1 - 0.2, o.t1], [1, 0], clamp))} />;
          default: return null;
        }
      })}
      {hideSubs ? null : <Subs subs={props.subs} size={props.subSize} />}
      {props.music ? <Audio src={staticFile(props.music.src)} volume={mv} startFrom={Math.round((props.music.startFrom || 0) * fps)} /> : null}
      {(props.sfx || []).map((s, i) => (
        <Sequence key={i} from={Math.round(s.t * fps)}>
          <Audio src={staticFile(s.src)} volume={s.vol ?? 0.5} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
