// Блоки полного монтажа (Манифест, черновик 2.1): спокойнее, крупнее, дольше на экране.
// Сплит: графика в верхней панели 0–660, лицо ниже (центр лица ~1030), субтитры под подбородком.
import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export const K = {
  red: '#e60f13', redDeep: '#b60b0e', ink: '#f4f2ee', ink2: '#a9a7a2', line: '#2a2a30', panel: 'rgba(20,20,24,.92)',
  dark: 'rgba(12,12,14,.85)', bg: '#0c0c0f',
};
export const DISP = 'Oswald, "Arial Narrow", sans-serif';
export const UI = '"Golos Text", system-ui, sans-serif';
const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const POP = Easing.bezier(0.2, 0.9, 0.3, 1.2);
const OUT = Easing.bezier(0.2, 0.8, 0.2, 1);
export const useT = () => {const f = useCurrentFrame(); const {fps} = useVideoConfig(); return f / fps;};
const vis = (t: number, t0: number, t1: number, fi = 0.3, fo = 0.3) =>
  Math.min(interpolate(t, [t0, t0 + fi], [0, 1], {...cl, easing: OUT}), interpolate(t, [t1 - fo, t1], [1, 0], {...cl, easing: OUT}));
const pop = (t: number, at: number, d = 0.4) => interpolate(t, [at, at + d], [0, 1], {...cl, easing: POP});

// ---------- раскладки ----------
export type Layout = {type: 'layout'; mode: 'split' | 'window'; t0: number; t1: number};
export const SPLIT_Y = 660;
export const baseGeom = (t: number, layouts: Layout[], zooms: {t0: number; t1: number; from: number; to: number}[]) => {
  let box = [0, 0, 1080, 1920], inner = [0, 0, 1], bg = 0;
  for (const L of layouts) {
    const p = Math.min(interpolate(t, [L.t0, L.t0 + 0.35], [0, 1], {...cl, easing: OUT}),
      interpolate(t, [L.t1 - 0.3, L.t1], [1, 0], {...cl, easing: OUT}));
    if (p <= 0) continue;
    const T = L.mode === 'split'
      ? {box: [0, SPLIT_Y, 1080, 1920 - SPLIT_Y], inner: [0, -440, 1]}
      : {box: [60, 150, 380, 500], inner: [-80, -150, 0.52]};
    box = box.map((v, i) => v + (T.box[i] - v) * p);
    inner = inner.map((v, i) => v + (T.inner[i] - v) * p);
    bg = Math.max(bg, p);
  }
  let z = 1;
  for (const Z of zooms) {
    if (t >= Z.t0 && t <= Z.t1) z = interpolate(t, [Z.t0, Z.t1], [Z.from, Z.to], {...cl, easing: Easing.inOut(Easing.quad)});
  }
  return {box, inner, bg, z};
};

export const Stage: React.FC<{a: number}> = ({a}) => (
  <AbsoluteFill style={{opacity: a, background: K.bg}}>
    <AbsoluteFill style={{background: 'radial-gradient(90% 45% at 50% 18%, rgba(230,15,19,.16), transparent 70%)'}} />
    <AbsoluteFill style={{backgroundImage: 'linear-gradient(rgba(255,255,255,.035) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,.035) 2px, transparent 2px)',
      backgroundSize: '90px 90px'}} />
  </AbsoluteFill>
);

// ---------- график выручки/прибыли, компактный; «÷7» — типографикой в панели ----------
export type Chart = {type: 'chart'; t0: number; t1: number; title: string; rev: [number, number]; prof: [number, number]; revLabelT: number; profLabelT: number; divT: number};
export const ChartBlock: React.FC<{o: Chart}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.35, 0.3);   // та же кривая, что у панели: исчезают вместе
  const W = 760, H = 380;
  const pr = interpolate(t, [o.rev[0], o.rev[1]], [0, 1], {...cl, easing: Easing.inOut(Easing.quad)});
  const pp = interpolate(t, [o.prof[0], o.prof[1]], [0, 1], {...cl, easing: Easing.in(Easing.quad)});
  const revPts = [[40, 250], [160, 236], [280, 226], [380, 190], [500, 172], [600, 136], [720, 100]];
  const profPts = [[40, 200], [160, 196], [280, 222], [380, 246], [500, 290], [600, 318], [720, 346]];
  const path = (pts: number[][]) => pts.map((p, i) => `${i ? 'L' : 'M'} ${p[0]} ${p[1]}`).join(' ');
  const len = 800;
  const rl = pop(t, o.revLabelT), pl = pop(t, o.profLabelT);
  const d = interpolate(t, [o.divT, o.divT + 0.3], [0, 1], {...cl, easing: POP});
  const shake = t > o.divT && t < o.divT + 0.22 ? Math.sin(t * 80) * 4 : 0;
  return (
    <div style={{position: 'absolute', left: 70, top: 96, width: 940, opacity: a, transform: `translateX(${shake}px)`}}>
      <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 36, letterSpacing: '0.14em', textTransform: 'uppercase', color: K.ink2}}>{o.title}</div>
      <svg width={W} height={H + 40} style={{marginTop: 10, overflow: 'visible'}}>
        {[100, 180, 260, 340].map((y) => <line key={y} x1={40} x2={740} y1={y} y2={y} stroke="rgba(255,255,255,.07)" strokeWidth={2} />)}
        <line x1={40} x2={740} y1={370} y2={370} stroke="rgba(255,255,255,.28)" strokeWidth={3} />
        <text x={40} y={404} fill={K.ink2} fontFamily={UI} fontSize={26}>2 года назад</text>
        <text x={740} y={404} fill={K.ink2} fontFamily={UI} fontSize={26} textAnchor="end">сейчас</text>
        <path d={path(revPts)} stroke="#f4f2ee" strokeWidth={10} fill="none" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={len} strokeDashoffset={len * (1 - pr)} />
        <path d={path(profPts)} stroke={K.red} strokeWidth={10} fill="none" strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={len} strokeDashoffset={len * (1 - pp)} style={{filter: 'drop-shadow(0 0 12px rgba(230,15,19,.6))'}} />
        <g opacity={rl}>
          <text x={360} y={70} fontFamily={DISP} fontWeight={700} fontSize={40} fill="#fff" letterSpacing="2">ВЫРУЧКА</text>
          <text x={548} y={74} fontFamily={DISP} fontWeight={700} fontSize={58} fill="#fff">×1,5</text>
        </g>
        <g opacity={pl}>
          <text x={430} y={344} fontFamily={DISP} fontWeight={700} fontSize={40} fill={K.red} letterSpacing="2">ПРИБЫЛЬ</text>
        </g>
      </svg>
      {/* «÷7» — крупная типографика справа, без перекрытия экрана */}
      <div style={{position: 'absolute', right: 0, top: 150, opacity: Math.min(1, d * 1.5), transform: `scale(${1.6 - 0.6 * d})`, transformOrigin: '70% 50%',
        fontFamily: DISP, fontWeight: 700, fontSize: 230, lineHeight: 1, color: K.red, textShadow: '0 10px 0 #4a0405, 0 0 60px rgba(230,15,19,.45)'}}>÷7</div>
    </div>
  );
};

// ---------- логотипы площадок (белые карточки на стене над головой) ----------
export type Logos = {type: 'logos'; t0: number; t1: number; items: {src?: string; text?: string; t: number; h?: number}[]};
export const LogosBlock: React.FC<{o: Logos}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.2, 0.3);
  return (
    <div style={{position: 'absolute', left: 60, top: 130, width: 960, display: 'flex', flexWrap: 'wrap', gap: 24, justifyContent: 'center', opacity: a}}>
      {o.items.map((it, i) => {
        const p = pop(t, it.t, 0.4);
        return (
          <div key={i} style={{width: 440, height: 140, borderRadius: 26, background: it.src ? '#fff' : 'rgba(20,20,24,.85)', opacity: t < it.t ? 0 : Math.min(1, p * 1.6),
            transform: `translateY(${(1 - p) * -30}px) scale(${0.85 + 0.15 * p})`, boxShadow: '0 14px 40px rgba(0,0,0,.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 34px'}}>
            {it.src ? <Img src={staticFile(it.src)} style={{height: it.h ?? 56, maxWidth: 372, objectFit: 'contain'}} />
              : <span style={{fontFamily: DISP, fontWeight: 700, fontSize: 54, color: '#fff', textTransform: 'uppercase'}}>{it.text}</span>}
          </div>
        );
      })}
    </div>
  );
};

// ---------- крупное слово на чёрном ----------
export type Word = {type: 'word'; t0: number; t1: number; text: string; color?: string};
export const WordBlock: React.FC<{o: Word}> = ({o}) => {
  const t = useT();
  const p = pop(t, o.t0, 0.22);
  const fs = Math.min(360, 1800 / Math.max(1, o.text.length));
  return (
    <AbsoluteFill style={{background: '#050506', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{fontFamily: DISP, fontWeight: 700, fontSize: fs, lineHeight: 1, color: o.color || K.red,
        transform: `scale(${1.25 - 0.25 * p})`, opacity: Math.min(1, p * 2), textShadow: '0 12px 0 #4a0405, 0 0 90px rgba(230,15,19,.45)',
        letterSpacing: '0.02em', marginTop: -120}}>{o.text}</div>
    </AbsoluteFill>
  );
};

// ---------- «30 офигенных советов селлеру»: удар-цифра с объёмом, светом и искрами ----------
export type Thirty = {type: 'thirty'; t0: number; t1: number; t: number; num: number; words: {text: string; t: number}[]};
export const ThirtyBlock: React.FC<{o: Thirty}> = ({o}) => {
  const t = useT();
  const f = useCurrentFrame();
  const a = vis(t, o.t0, o.t1, 0.15, 0.12);
  const s = interpolate(t, [o.t, o.t + 0.28], [0, 1], {...cl, easing: Easing.bezier(0.2, 1.5, 0.4, 1)});
  const n = Math.round(interpolate(t, [o.t, o.t + 0.45], [1, o.num], cl));
  const ring = interpolate(t, [o.t + 0.1, o.t + 0.7], [0, 1], cl);
  const sweep = interpolate(t, [o.t + 0.35, o.t + 1.1], [-40, 140], cl);
  const depth = Array.from({length: 14}).map((_, i) => `${i * 1.2}px ${i * 2}px 0 ${i < 13 ? '#7d0608' : '#2a0203'}`).join(',');
  return (
    <AbsoluteFill style={{opacity: a}}>
      <Stage a={1} />
      <div style={{position: 'absolute', left: 540, top: 700, width: 900 * ring, height: 900 * ring, marginLeft: -450 * ring, marginTop: -450 * ring,
        borderRadius: '50%', border: `${14 * (1 - ring)}px solid rgba(230,15,19,${0.8 * (1 - ring)})`}} />
      {Array.from({length: 18}).map((_, i) => {
        const ang = (i / 18) * Math.PI * 2 + 0.3, sp = interpolate(t, [o.t + 0.05, o.t + 0.8], [0, 1], {...cl, easing: Easing.out(Easing.quad)});
        const d = 120 + 420 * sp * (0.7 + ((i * 37) % 10) / 20);
        return <div key={i} style={{position: 'absolute', left: 540 + Math.cos(ang) * d, top: 700 + Math.sin(ang) * d, width: 10, height: 10, borderRadius: 5,
          background: i % 3 ? '#ffcf8a' : K.red, opacity: sp > 0 && sp < 1 ? 1 - sp : 0, boxShadow: '0 0 16px #ff8a3d'}} />;
      })}
      <div style={{position: 'absolute', left: 0, right: 0, top: 380, textAlign: 'center', transform: `scale(${2.2 - 1.2 * s}) rotate(${-6 * (1 - s)}deg)`,
        opacity: Math.min(1, s * 3), filter: `blur(${(1 - s) * 8}px)`}}>
        <span style={{position: 'relative', display: 'inline-block', fontFamily: DISP, fontWeight: 700, fontSize: 520, lineHeight: 1, color: K.red,
          textShadow: `${depth}, 0 40px 80px rgba(0,0,0,.6)`, fontVariantNumeric: 'tabular-nums',
          WebkitMaskImage: 'none'}}>
          {n}
          <span style={{position: 'absolute', inset: 0, background: `linear-gradient(100deg, transparent ${sweep - 12}%, rgba(255,255,255,.55) ${sweep}%, transparent ${sweep + 12}%)`,
            WebkitBackgroundClip: 'text', color: 'transparent', textShadow: 'none'}}>{n}</span>
        </span>
      </div>
      <div style={{position: 'absolute', left: 60, right: 60, top: 980, textAlign: 'center'}}>
        {o.words.map((w, i) => {
          const p = pop(t, w.t, 0.3);
          return <span key={i} style={{display: 'inline-block', margin: '0 12px', fontFamily: DISP, fontWeight: 700, fontSize: 84, color: '#fff',
            textTransform: 'uppercase', opacity: t < w.t ? 0 : Math.min(1, p * 2), transform: `translateY(${(1 - p) * 40}px)`,
            letterSpacing: '0.03em'}}>{w.text}</span>;
        })}
      </div>
      <div style={{position: 'absolute', inset: 0, background: '#fff', opacity: interpolate(t, [o.t, o.t + 0.05, o.t + 0.2], [0, 0.35, 0], cl)}} />
      <span style={{display: 'none'}}>{f}</span>
    </AbsoluteFill>
  );
};

// ---------- ярлык поверх вставки ----------
export type Tag = {type: 'tag'; t0: number; t1: number; text: string; y?: number};
export const TagBlock: React.FC<{o: Tag}> = ({o}) => {
  const t = useT();
  const p = pop(t, o.t0);
  const a = interpolate(t, [o.t1 - 0.15, o.t1], [1, 0], cl);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: o.y ?? 260, textAlign: 'center', opacity: a}}>
      <span style={{display: 'inline-block', transform: `scale(${0.6 + 0.4 * p}) rotate(-3deg)`, opacity: Math.min(1, p * 2),
        background: K.red, color: '#fff', fontFamily: DISP, fontWeight: 700, fontSize: 84, padding: '6px 34px', borderRadius: 16,
        boxShadow: `0 10px 0 ${K.redDeep}, 0 20px 50px rgba(0,0,0,.5)`, textTransform: 'uppercase'}}>{o.text}</span>
    </div>
  );
};

// ---------- отчёт по удержаниям (как в кабинете) + вечный одометр, компактно в панели ----------
export type Report = {type: 'report'; t0: number; t1: number; rows: {week: string; other: string; fines: string; t: number}[]; markT: number; totalT: number; label: string};
export const ReportBlock: React.FC<{o: Report}> = ({o}) => {
  const t = useT();
  const f = useCurrentFrame();
  const a = vis(t, o.t0, o.t1, 0.35, 0.3);
  const tilt = interpolate(t, [o.t0, o.t1], [1, 0.6], cl);
  const mk = interpolate(t, [o.markT, o.markT + 0.5], [0, 1], {...cl, easing: OUT});
  const tp = pop(t, o.totalT);
  const spin = t - o.totalT;
  const v = Math.floor(8_000_000 + (spin * 13_700_000) % 23_000_000 + (Math.sin(f * 1.7) + 1) * 377_777);
  const RH = 58;
  return (
    <div style={{position: 'absolute', left: 80, top: 60, width: 920, opacity: a}}>
      <div style={{transform: `perspective(1600px) rotateX(${10 * tilt}deg) rotateY(${-8 * tilt}deg) rotateZ(${1.5 * tilt}deg)`, transformOrigin: '50% 0%',
        background: '#fff', borderRadius: 24, padding: '20px 28px 12px', boxShadow: '0 30px 70px rgba(0,0,0,.55)'}}>
        <div style={{display: 'grid', gridTemplateColumns: '1.05fr 1.35fr 1fr', fontFamily: UI, fontSize: 24, color: '#7b7a88', paddingBottom: 12, borderBottom: '2px solid #eeeef2'}}>
          <div>Неделя</div><div>Прочие удержания/выплаты</div><div>Общая сумма штрафов</div>
        </div>
        <div style={{position: 'relative'}}>
          {o.rows.map((r, i) => {
            const p = pop(t, r.t, 0.35);
            return (
              <div key={i} style={{display: 'grid', gridTemplateColumns: '1.05fr 1.35fr 1fr', alignItems: 'center', height: RH, fontFamily: UI, fontSize: 34,
                borderBottom: '2px solid #f2f2f5', opacity: p, transform: `translateY(${(1 - p) * 14}px)`}}>
                <div style={{color: '#222', fontSize: 27}}>{r.week}</div>
                <div style={{color: '#4b5be0', fontWeight: 500}}>{r.other}</div>
                <div style={{color: '#4b5be0'}}>{r.fines}</div>
              </div>
            );
          })}
          <svg width={420} height={o.rows.length * RH + 30} style={{position: 'absolute', left: 230, top: -14, overflow: 'visible'}}>
            <ellipse cx={170} cy={(o.rows.length * RH + 28) / 2} rx={180} ry={(o.rows.length * RH) / 2 + 16} fill="none" stroke={K.red}
              strokeWidth={8} strokeLinecap="round" strokeDasharray={1600} strokeDashoffset={1600 * (1 - mk)} transform="rotate(-2 170 160)" />
          </svg>
        </div>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 440, textAlign: 'center', opacity: Math.min(1, tp * 2), transform: `scale(${0.85 + 0.15 * tp})`}}>
        <div style={{display: 'inline-flex', alignItems: 'center', gap: 26, background: K.panel, border: `2px solid ${K.line}`, borderRadius: 22, padding: '8px 30px'}}>
          <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 32, letterSpacing: '0.12em', color: K.ink2, textTransform: 'uppercase', lineHeight: 1.1, textAlign: 'left', whiteSpace: 'pre-line'}}>{o.label}</div>
          <div style={{fontFamily: DISP, fontWeight: 700, fontSize: 96, lineHeight: 1.05, color: K.red, fontVariantNumeric: 'tabular-nums',
            filter: `blur(${spin > 0 ? 1.4 : 0}px)`, textShadow: '0 6px 0 #4a0405'}}>{v.toLocaleString('ru-RU')}</div>
        </div>
      </div>
    </div>
  );
};

// ---------- бейдж «в процессе» ----------
export type Badge = {type: 'badge'; t0: number; t1: number; text: string};
export const BadgeBlock: React.FC<{o: Badge}> = ({o}) => {
  const t = useT();
  const p = pop(t, o.t0);
  const a = interpolate(t, [o.t1 - 0.25, o.t1], [1, 0], cl);
  const blink = 0.35 + 0.65 * Math.abs(Math.sin(t * 5));
  return (
    <div style={{position: 'absolute', top: 170, left: 0, right: 0, textAlign: 'center', opacity: a}}>
      <span style={{display: 'inline-flex', alignItems: 'center', gap: 18, transform: `translateY(${(1 - p) * -30}px)`, opacity: Math.min(1, p * 2),
        background: K.dark, border: `2px solid ${K.line}`, borderRadius: 60, padding: '14px 36px', fontFamily: DISP, fontWeight: 700, fontSize: 48,
        letterSpacing: '0.06em', color: '#fff', textTransform: 'uppercase'}}>
        <span style={{width: 28, height: 28, borderRadius: 14, background: K.red, opacity: blink, boxShadow: '0 0 20px rgba(230,15,19,.9)'}} />
        {o.text}
      </span>
    </div>
  );
};

// ---------- веер карточек-утечек (в верхней панели) ----------
export type Cards = {type: 'cards'; t0: number; t1: number; n: number; total: number; pickT: number; y?: number; s?: number};
export const CardsBlock: React.FC<{o: Cards}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.3, 0.3);
  const pk = interpolate(t, [o.pickT, o.pickT + 0.5], [0, 1], {...cl, easing: OUT});
  const cy = o.y ?? 360, S = o.s ?? 0.72;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 700, opacity: a}}>
      {Array.from({length: o.n}).map((_, j) => {
        const i = o.n - 1 - j;
        const p = pop(t, o.t0 + 0.1 * i, 0.45);
        const ang = (i - (o.n - 1) / 2) * 10;
        const lift = i === 0 ? pk : 0;
        const x = 540 + (i - (o.n - 1) / 2) * 90 * (1 - lift);
        const y = cy - lift * 30;
        return (
          <div key={i} style={{position: 'absolute', left: x - 170, top: y - 230, width: 340, height: 460, borderRadius: 26,
            background: i === 0 ? '#16161b' : '#1d1d23', border: `4px solid ${i === 0 ? K.red : '#34343c'}`,
            transform: `translateY(${(1 - p) * 400}px) rotate(${ang * (1 - lift) * p}deg) scale(${S * (1 + 0.2 * lift)})`, transformOrigin: '50% 100%',
            boxShadow: '0 30px 60px rgba(0,0,0,.6)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: i === 0 ? 10 : 5 - i}}>
            <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 40, letterSpacing: '0.16em', color: K.ink2}}>УТЕЧКА</div>
            <div style={{fontFamily: DISP, fontWeight: 700, fontSize: 150, lineHeight: 1, color: i === 0 ? K.red : '#fff'}}>{i + 1}</div>
            <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 44, color: K.ink2}}>/ {o.total}</div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- схема системы (в верхней панели) ----------
export type System = {type: 'system'; t0: number; t1: number; center: string; nodes: {text: string; t: number}[]; cx?: number; cy?: number; R?: number};
export const SystemBlock: React.FC<{o: System}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.3, 0.25);
  const cx = o.cx ?? 540, cy = o.cy ?? 350, R = o.R ?? 300;
  const cp = pop(t, o.t0 + 0.15, 0.5);
  const glow = 0.5 + 0.5 * Math.sin(t * 5);
  const pos = (i: number) => {
    const ang = (180 + i * (180 / Math.max(1, o.nodes.length - 1))) * Math.PI / 180;
    return [cx + Math.cos(ang) * R, cy + 40 + Math.sin(ang) * R * 0.75];
  };
  return (
    <div style={{position: 'absolute', inset: 0, opacity: a}}>
      <svg width={1080} height={700} style={{position: 'absolute', inset: 0}}>
        {o.nodes.map((n, i) => {
          const [x, y] = pos(i);
          const lp = interpolate(t, [n.t, n.t + 0.45], [0, 1], cl);
          return <line key={i} x1={x} y1={y} x2={x + (cx - x) * lp} y2={y + (cy - y) * lp} stroke={K.red} strokeWidth={6} strokeDasharray="14 12"
            strokeDashoffset={-t * 50} opacity={lp > 0 ? 0.9 : 0} />;
        })}
      </svg>
      <div style={{position: 'absolute', left: cx - 130, top: cy - 130, width: 260, height: 260, borderRadius: 130, background: K.red,
        transform: `scale(${cp})`, boxShadow: `0 0 ${50 + 40 * glow}px rgba(230,15,19,.75)`, display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: DISP, fontWeight: 700, fontSize: 48, color: '#fff', letterSpacing: '0.06em'}}>{o.center}</div>
      {o.nodes.map((n, i) => {
        const [x, y] = pos(i);
        const p = pop(t, n.t);
        if (t < n.t) return null;
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, transform: `translate(-50%,-50%) scale(${p})`, background: K.panel,
            border: `3px solid ${K.red}`, borderRadius: 20, padding: '12px 26px', fontFamily: DISP, fontWeight: 700, fontSize: 46, color: '#fff',
            whiteSpace: 'nowrap', textTransform: 'uppercase'}}>{n.text}</div>
        );
      })}
    </div>
  );
};

// ---------- каскад окон таблиц/сервисов с ценами и перечёркивание ----------
export type Windows = {type: 'windows'; t0: number; t1: number; items: {title: string; price?: string; t: number}[]; strikeT: number};
const FakeSheet: React.FC<{seed: number}> = ({seed}) => (
  <div style={{display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', background: '#fff'}}>
    {Array.from({length: 25}).map((_, i) => {
      const hdr = i < 5;
      const w = 30 + ((Math.sin((i + seed) * 12.9898) * 43758.5) % 1 + 1) % 1 * 60;
      return (
        <div key={i} style={{height: 30, borderRight: '1px solid #e3e3e8', borderBottom: '1px solid #e3e3e8', background: hdr ? '#f1f3f7' : '#fff', padding: '8px 8px'}}>
          <div style={{height: 12, width: `${w}%`, borderRadius: 3, background: hdr ? '#b9bfcc' : (i % 7 === 3 ? '#4b5be0' : '#d4d7de')}} />
        </div>
      );
    })}
  </div>
);
export const WindowsBlock: React.FC<{o: Windows}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.2, 0.2);
  const sk = interpolate(t, [o.strikeT, o.strikeT + 0.3], [0, 1], {...cl, easing: OUT});
  const fall = interpolate(t, [o.strikeT + 0.3, o.t1], [0, 1], {...cl, easing: Easing.in(Easing.quad)});
  return (
    <AbsoluteFill style={{opacity: a}}>
      {o.items.map((it, i) => {
        const p = pop(t, it.t, 0.35);
        if (t < it.t) return null;
        const x = 60 + (i % 3) * 60 + (i % 2) * 30, y = 150 + i * 158;
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y + fall * (500 + i * 120), width: 840, borderRadius: 16, overflow: 'hidden',
            transform: `scale(${0.75 + 0.25 * p}) rotate(${(i % 2 ? 1.2 : -1.2) + fall * (i % 2 ? 14 : -14)}deg)`, opacity: Math.min(1, p * 2),
            boxShadow: '0 24px 60px rgba(0,0,0,.55)', background: '#fff'}}>
            <div style={{height: 60, background: '#e9eaee', display: 'flex', alignItems: 'center', gap: 10, padding: '0 18px'}}>
              {['#ff5f57', '#febc2e', '#28c840'].map((c) => <span key={c} style={{width: 18, height: 18, borderRadius: 9, background: c}} />)}
              <span style={{marginLeft: 14, fontFamily: UI, fontSize: 27, color: '#333', flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{it.title}</span>
              {it.price ? <span style={{fontFamily: DISP, fontWeight: 700, fontSize: 44, color: K.red, whiteSpace: 'nowrap',
                transform: `scale(${pop(t, it.t + 0.15, 0.35)})`}}>{it.price}</span> : null}
            </div>
            <FakeSheet seed={i * 7} />
          </div>
        );
      })}
      <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
        <line x1={80} y1={1340} x2={80 + 920 * sk} y2={1340 - 1100 * sk} stroke={K.red} strokeWidth={34} strokeLinecap="round"
          style={{filter: 'drop-shadow(0 8px 0 #6d0507)'}} opacity={sk > 0 ? 1 : 0} />
      </svg>
    </AbsoluteFill>
  );
};

// ---------- «100 дней» и сетка (в верхней панели) ----------
export type Days = {type: 'days'; t0: number; t1: number; t: number; fillT: number; caption?: string};
export const DaysBlock: React.FC<{o: Days}> = ({o}) => {
  const t = useT();
  const a = vis(t, o.t0, o.t1, 0.3, 0.3);
  const p = pop(t, o.t, 0.45);
  const pulse = t > o.fillT ? 0.6 + 0.4 * Math.abs(Math.sin((t - o.fillT) * 5)) : 0;
  return (
    <div style={{position: 'absolute', left: 90, top: 80, width: 900, opacity: a, textAlign: 'center'}}>
      <div style={{fontFamily: DISP, fontWeight: 700, fontSize: 170, lineHeight: 0.95, color: '#fff', transform: `scale(${0.7 + 0.3 * p})`,
        opacity: Math.min(1, p * 2), whiteSpace: 'nowrap'}}>100 <span style={{color: K.red}}>ДНЕЙ</span></div>
      {o.caption ? <div style={{fontFamily: DISP, fontWeight: 600, fontSize: 38, letterSpacing: '0.14em', color: K.ink2, marginTop: 8}}>{o.caption}</div> : null}
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(20, 1fr)', gap: 8, marginTop: 26, padding: '0 40px'}}>
        {Array.from({length: 100}).map((_, i) => {
          const c = interpolate(t, [o.t0 + 0.2 + i * 0.01, o.t0 + 0.4 + i * 0.01], [0, 1], cl);
          const first = i === 0 && t > o.fillT;
          return <div key={i} style={{height: 26, borderRadius: 6, opacity: c, background: first ? K.red : 'rgba(255,255,255,.12)',
            boxShadow: first ? `0 0 ${20 * pulse}px rgba(230,15,19,.9)` : 'none', transform: first ? `scale(${1 + 0.25 * pulse})` : 'none'}} />;
        })}
      </div>
    </div>
  );
};

// ---------- хук-заголовок в верхней панели: целиком виден с кадра 0, цифры «толкаются» на слове ----------
export type Hook = {type: 'hook'; t0: number; t1: number; top?: number; lines: {text: string; red?: boolean; size?: number; t?: number}[]};
export const HookBlock: React.FC<{o: Hook}> = ({o}) => {
  const t = useT();
  const pin = o.t0 <= 0.05 ? 1 : pop(t, o.t0, 0.3);
  const a = interpolate(t, [o.t1 - 0.25, o.t1], [1, 0], cl);
  const stroke = {WebkitTextStroke: '5px #000', paintOrder: 'stroke fill' as const, textShadow: '0 7px 0 #000, 0 0 36px rgba(0,0,0,.55)'};
  return (
    <div style={{position: 'absolute', left: 36, right: 36, top: o.top ?? 150, textAlign: 'center', fontFamily: DISP, fontWeight: 700,
      textTransform: 'uppercase', lineHeight: 1, opacity: a * Math.min(1, pin * 1.5), transform: `scale(${0.9 + 0.1 * pin})`}}>
      {o.lines.map((l, i) => {
        const k = l.t !== undefined ? interpolate(t, [l.t, l.t + 0.12, l.t + 0.4], [0, 1, 0], cl) : 0;
        const sz = l.size ?? (l.red ? 140 : 104);
        return (
          <div key={i} style={{marginTop: i ? (l.red ? 30 : 18) : 0}}>
            <span style={{display: 'inline-block', whiteSpace: 'nowrap', fontSize: sz, color: '#fff', transform: `scale(${1 + 0.1 * k})${l.red ? ' rotate(-2deg)' : ''}`,
              ...(l.red ? {background: K.red, padding: '6px 32px 14px', borderRadius: 20, boxShadow: `0 12px 0 ${K.redDeep}, 0 26px 60px rgba(0,0,0,.5)`} : stroke)}}>{l.text}</span>
          </div>
        );
      })}
    </div>
  );
};
