// Мультсцена «Дырявый кувшин МАРЖА СЕЛЛЕРА» v2: из дыр выскальзывают купюры и планируют вниз как бумага,
// хитрые лисы (фиолетовая и синяя) крадутся, хватают по купюре, подмигивают и удирают.
// Стиль — бумажная аппликация: вырезанная бумага с тенью, «кипящий» контур, зерно.
import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const PAL = {
  bg: '#f1e4c9', bg2: '#e8d4b0', floor: '#caa77a', floor2: '#b98f5f', clay: '#c96f45', clayDark: '#96482a', clayLight: '#e89466',
  hole: '#2a1710', sticker: '#fdf8ec', ink: '#2a2530', tape: '#efd98f',
  bill: '#e46a3c', billDark: '#b7462a', billLight: '#f8b894', cream: '#fff3e0', nose: '#1c1420',
};
const FLOOR = 1300;
const rnd = (i: number) => {const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x);};

const Defs: React.FC = () => {
  const seed = Math.floor(useCurrentFrame() / 4) % 7;
  return (
    <defs>
      <filter id="jcut" x="-15%" y="-15%" width="130%" height="140%">
        <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed={seed} result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="3" result="d" />
        <feDropShadow dx="0" dy="8" stdDeviation="5" floodColor="#2a1a10" floodOpacity="0.3" />
      </filter>
      <filter id="jsoft"><feDropShadow dx="0" dy="4" stdDeviation="3" floodColor="#2a1a10" floodOpacity="0.28" /></filter>
      <filter id="jgrain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed={seed} />
        <feColorMatrix values="0 0 0 0 0.2  0 0 0 0 0.15  0 0 0 0 0.1  0 0 0 0.08 0" />
      </filter>
      <radialGradient id="jclay" cx="38%" cy="40%" r="70%">
        <stop offset="0%" stopColor={PAL.clayLight} /><stop offset="55%" stopColor={PAL.clay} /><stop offset="100%" stopColor={PAL.clayDark} />
      </radialGradient>
      <radialGradient id="jvig" cx="50%" cy="42%" r="75%">
        <stop offset="60%" stopColor="#000" stopOpacity="0" /><stop offset="100%" stopColor="#3a2410" stopOpacity="0.35" />
      </radialGradient>
      {['p', 'b'].map((k) => (
        <linearGradient key={k} id={`fox_${k}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={k === 'p' ? '#9a5cff' : '#3f86ff'} />
          <stop offset="100%" stopColor={k === 'p' ? '#5d25c9' : '#1146c7'} />
        </linearGradient>
      ))}
    </defs>
  );
};

// купюра «похожая на 5000»: оранжево-красная, рамка, медальон, крупное 5000
const Bill: React.FC<{x: number; y: number; r: number; s?: number; sy?: number; fx?: number}> = ({x, y, r, s = 1, sy = 1, fx = 1}) => (
  <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s * fx} ${s * sy})`} filter="url(#jsoft)">
    <rect x={-80} y={-40} width={160} height={80} rx={5} fill={PAL.bill} />
    <rect x={-72} y={-32} width={144} height={64} rx={3} fill="none" stroke={PAL.billLight} strokeWidth={2.5} />
    <path d="M -72 -8 C -40 -22 -10 6 20 -6 S 60 -14 72 -4" stroke={PAL.billLight} strokeWidth={1.5} fill="none" opacity={0.7} />
    <ellipse cx={-40} cy={2} rx={18} ry={22} fill={PAL.billDark} opacity={0.5} />
    <text x={26} y={14} textAnchor="middle" fontFamily="Oswald, sans-serif" fontWeight={700} fontSize={36} fill={PAL.cream}>5000</text>
  </g>
);

type FoxProps = {mirrored?: boolean; main: string; dark: string; grad: string; phase: number; speed: number; moving: boolean; carry: boolean; dip: number; wink: number; smirk: number};
// лиса сбоку, смотрит вправо; детализированная: подшёрсток, «носочки», пушистые щёки, прищур
const Fox: React.FC<FoxProps> = ({mirrored, main, dark, grad, phase, speed, moving, carry, dip, wink, smirk}) => {
  const P = phase * Math.PI * 2;
  const amp = moving ? (speed > 2 ? 38 : 22) : 0;
  const bob = moving ? -Math.abs(Math.sin(P)) * (speed > 2 ? 16 : 8) : 0;
  const tilt = moving ? Math.sin(P) * (speed > 2 ? 4 : 2) : 0;
  const leg = (x: number, off: number, back: boolean, front: boolean) => {
    const a = Math.sin(P + off) * amp;
    const knee = Math.max(0, Math.sin(P + off + 1.2)) * (moving ? 30 : 0);
    return (
      <g transform={`rotate(${a} ${x} -10)`}>
        <path d={`M ${x - 16} -20 Q ${x - 18} 20 ${x - 10} 30 L ${x + 12} 30 Q ${x + 18} 10 ${x + 16} -20 Z`} fill={back ? dark : `url(#${grad})`} />
        <g transform={`rotate(${front ? -knee : knee} ${x} 28)`}>
          <rect x={x - 9} y={24} width={18} height={40} rx={9} fill={back ? dark : main} />
          <ellipse cx={x + 4} cy={66} rx={16} ry={9} fill={PAL.nose} />
        </g>
      </g>
    );
  };
  return (
    <g transform={`translate(0 ${bob}) rotate(${tilt})`}>
      {/* хвост: пушистый, с белым кончиком и зубчиками шерсти */}
      <g transform={`rotate(${-12 + Math.sin(P * 0.5 + 1) * (moving ? 12 : 5)} -100 -40)`}>
        <path d="M -96 -46 C -150 -120 -250 -120 -300 -60 C -300 -30 -280 -10 -250 -8 C -200 -4 -140 -10 -100 -20 Z" fill={`url(#${grad})`} />
        <path d="M -262 -84 C -290 -76 -304 -58 -300 -40 C -292 -24 -276 -14 -254 -10 L -262 -28 L -244 -34 L -258 -50 L -240 -60 L -256 -70 Z" fill={PAL.cream} />
        <path d="M -140 -86 l 14 10 M -180 -96 l 12 12 M -210 -94 l 10 12" stroke={dark} strokeWidth={5} strokeLinecap="round" opacity={0.6} />
      </g>
      <g transform="translate(0 34)">{leg(-70, Math.PI, true, false)}{leg(58, 0, true, true)}</g>
      {/* тело */}
      <ellipse cx={-4} cy={-14} rx={118} ry={60} fill={`url(#${grad})`} />
      <path d="M -90 -40 C -40 -70 40 -70 90 -46" stroke={dark} strokeWidth={9} fill="none" opacity={0.35} strokeLinecap="round" />
      <path d="M 20 18 C 60 40 100 30 120 0 L 112 -28 C 90 0 50 12 20 18 Z" fill={PAL.cream} />
      {/* грудка-воротник */}
      <path d="M 70 -40 L 130 -20 L 118 6 L 132 20 L 108 30 L 118 44 L 88 36 L 74 10 Z" fill={PAL.cream} />
      <g transform="translate(0 34)">{leg(-46, 0, false, false)}{leg(78, Math.PI, false, true)}</g>
      {/* голова */}
      <g transform={`translate(116 -70) rotate(${dip * 30 + (moving ? Math.sin(P) * 3 : 0)})`}>
        {/* уши */}
        <g transform={`rotate(${moving ? Math.sin(P * 2) * 6 : 0} -14 -50)`}>
          <path d="M -40 -40 L -26 -126 L 8 -52 Z" fill={`url(#${grad})`} />
          <path d="M -30 -52 L -24 -106 L -2 -56 Z" fill={dark} />
        </g>
        <path d="M 4 -50 L 40 -124 L 58 -44 Z" fill={dark} />
        <path d="M 16 -54 L 40 -104 L 50 -52 Z" fill={PAL.nose} opacity={0.5} />
        {/* череп + морда */}
        <path d="M -54 -8 C -58 -66 44 -80 70 -34 L 142 4 C 124 28 70 40 16 36 C -28 32 -52 16 -54 -8 Z" fill={`url(#${grad})`} />
        {/* пушистые щёки */}
        <path d="M -50 0 L -34 22 L -20 10 L -6 30 L 8 16 L 24 34 L 34 18 L 16 36 C -24 34 -48 20 -50 0 Z" fill={PAL.cream} />
        <path d="M 30 10 L 142 4 C 124 28 70 40 16 36 Z" fill={PAL.cream} />
        {/* нос */}
        <ellipse cx={144} cy={2} rx={11} ry={9} fill={PAL.nose} />
        <circle cx={140} cy={-1} r={3} fill="#fff" opacity={0.8} />
        {/* усы-точки */}
        {[0, 1, 2].map((i) => <circle key={i} cx={106 + i * 9} cy={16 + (i % 2) * 5} r={2.4} fill={PAL.nose} opacity={0.6} />)}
        {/* глаз: миндаль + зрачок + хитрое веко; при подмигивании закрывается */}
        <g transform="translate(40 -30)">
          <path d="M -20 0 Q 0 -16 22 -2 Q 2 10 -20 0 Z" fill="#fffbe6" opacity={1 - wink} />
          <circle cx={6} cy={-2} r={6.5} fill={PAL.nose} opacity={1 - wink} />
          <circle cx={8} cy={-4} r={2} fill="#fff" opacity={1 - wink} />
          <path d={`M -22 ${-2 - 8 * (1 - wink)} Q 0 ${-14 + 10 * wink} 24 ${-4}`} stroke={PAL.nose} strokeWidth={5} fill={`url(#${grad})`} strokeLinecap="round" />
          <path d="M -18 -22 Q 2 -30 26 -18" stroke={dark} strokeWidth={5} fill="none" strokeLinecap="round" />
        </g>
        {/* ухмылка */}
        <path d={`M 76 ${22 - 2 * smirk} Q 96 ${30 + 4 * smirk} 118 ${16 - 6 * smirk}`} stroke={PAL.nose} strokeWidth={4} fill="none" strokeLinecap="round" />
        {carry ? <Bill x={128} y={34} r={-14} s={0.6} fx={mirrored ? -1 : 1} /> : null}
      </g>
    </g>
  );
};

export const JugScene: React.FC<{t0: number; t1: number}> = ({t0, t1}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps - t0;
  const D = t1 - t0;
  const inA = interpolate(t, [0, 0.16], [0, 1], cl);
  const outA = interpolate(t, [D - 0.14, D], [1, 0], cl);
  const jugY = interpolate(t, [0, 0.38], [-760, 0], {...cl, easing: Easing.bezier(0.3, 1.35, 0.5, 1)});
  const squash = interpolate(t, [0.36, 0.46, 0.6], [1, 0.94, 1], cl);
  const wob = Math.sin(t * 8) * interpolate(t, [0.4, 1.2], [3, 0.6], cl);
  const holes = [{x: 420, y: 940, dir: -1}, {x: 556, y: 1010, dir: 1}, {x: 676, y: 925, dir: 1}];
  // купюры: выскальзывают из дыр и планируют вниз (покачивание, переворот, падение с «парусностью»)
  const bills: React.ReactNode[] = [];
  let k = 0;
  for (let s = 0.42; s < D - 0.3; s += 0.11) {
    const h = holes[k % 3];
    const age = t - s;
    if (age > 0) {
      const ph = rnd(k) * 6.28, ph2 = rnd(k + 7) * 6.28;
      let x: number, y: number, r: number, sy = 1, sc = 0.82;
      if (age < 0.2) {             // выскальзывает из дыры
        const e = age / 0.2;
        x = h.x + h.dir * 60 * e; y = h.y + 8 * e; r = h.dir * 10 * e; sc = 0.35 + 0.47 * e;
      } else {
        const a = age - 0.2;
        const v = 330 + rnd(k + 3) * 120;
        x = h.x + h.dir * (60 + (40 + rnd(k + 1) * 90) * a) + 50 * Math.sin(2 * Math.PI * 1.2 * a + ph);
        y = h.y + 8 + v * a + 120 * a * a;
        r = h.dir * 10 + 30 * Math.sin(2 * Math.PI * 1.05 * a + ph2);
        sy = 0.3 + 0.7 * Math.abs(Math.cos(2 * Math.PI * 0.8 * a + ph));
        const land = FLOOR + 10 - (k % 5) * 5;
        if (y > land) {y = land; r = (rnd(k + 5) - 0.5) * 24; sy = 0.42;}
      }
      bills.push(<Bill key={k} x={x} y={y} r={r} s={sc} sy={sy} />);
    }
    k++;
  }
  const fox = (from: number, to: number, enter: number, grad: string, main: string, dark: string, key: string) => {
    const arrive = enter + 0.62, grab = arrive + 0.12, winkT = grab + 0.22, leave = grab + 0.55;
    const e1 = interpolate(t, [enter, arrive], [0, 1], {...cl, easing: Easing.out(Easing.quad)});
    const e2 = interpolate(t, [leave, leave + 0.75], [0, 1], {...cl, easing: Easing.in(Easing.cubic)});
    const x = t < leave ? from + (to - from) * e1 : to + (from - to) * 1.35 * e2;
    const facingRight = t < leave ? to > from : from > to;
    const moving = (t > enter && t < arrive) || t > leave;
    const speed = t > leave ? 3.2 : 1.6;
    const dip = interpolate(t, [grab - 0.12, grab, grab + 0.16], [0, 1, 0], cl);
    const wink = interpolate(t, [winkT, winkT + 0.07, winkT + 0.22, winkT + 0.3], [0, 1, 1, 0], cl);
    const smirk = interpolate(t, [grab, winkT + 0.1], [0, 1], cl);
    if (t < enter) return null;
    return (
      <g key={key} transform={`translate(${x} ${FLOOR - 92}) scale(${facingRight ? 1.05 : -1.05} 1.05)`} filter="url(#jcut)">
        <Fox mirrored={!facingRight} main={main} dark={dark} grad={grad} phase={t * speed} speed={speed} moving={moving} carry={t > grab} dip={dip} wink={wink} smirk={smirk} />
      </g>
    );
  };
  return (
    <AbsoluteFill style={{opacity: Math.min(inA, outA)}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920">
        <Defs />
        <rect width={1080} height={1920} fill={PAL.bg} />
        <circle cx={540} cy={720} r={540} fill={PAL.bg2} opacity={0.75} />
        <rect x={0} y={FLOOR} width={1080} height={1920 - FLOOR} fill={PAL.floor} />
        {[0, 1, 2, 3].map((i) => <rect key={i} x={0} y={FLOOR + 60 + i * 90} width={1080} height={4} fill={PAL.floor2} opacity={0.5} />)}
        <rect x={0} y={FLOOR} width={1080} height={10} fill={PAL.floor2} />
        <ellipse cx={540} cy={FLOOR + 4} rx={260 * squash} ry={22} fill="#7a5530" opacity={0.28 * interpolate(t, [0.2, 0.38], [0, 1], cl)} />
        {/* кувшин */}
        <g transform={`translate(0 ${jugY}) rotate(${wob} 540 ${FLOOR}) translate(540 ${FLOOR}) scale(${2 - squash} ${squash}) translate(-540 ${-FLOOR})`} filter="url(#jcut)">
          <path d="M 468 360 L 612 360 L 602 452 C 770 520 812 704 782 902 C 756 1084 648 1292 540 1302 C 432 1292 324 1084 298 902 C 268 704 310 520 478 452 Z" fill="url(#jclay)" />
          <path d="M 318 790 C 380 760 700 760 762 790 L 766 836 C 700 806 380 806 314 836 Z" fill={PAL.clayDark} opacity={0.55} />
          {Array.from({length: 11}).map((_, i) => <path key={i} d={`M ${338 + i * 38} 842 l 16 22 l 16 -22 Z`} fill={PAL.clayDark} opacity={0.5} />)}
          <path d="M 442 338 L 638 338 L 644 374 L 436 374 Z" fill={PAL.clayDark} />
          <path d="M 436 350 C 396 318 376 296 398 286 C 430 296 452 318 472 350 Z" fill={PAL.clay} />
          <path d="M 756 560 C 896 556 912 772 780 806" stroke={PAL.clayDark} strokeWidth={36} fill="none" strokeLinecap="round" />
          <path d="M 372 560 C 392 520 436 498 470 492" stroke={PAL.clayLight} strokeWidth={16} fill="none" strokeLinecap="round" opacity={0.75} />
          {holes.map((h, i) => (
            <g key={i}>
              <path d={`M ${h.x - 34} ${h.y - 14} l 14 6 M ${h.x + 34} ${h.y + 14} l -14 -6 M ${h.x + 10} ${h.y - 30} l -3 12 M ${h.x - 8} ${h.y + 30} l 2 -12`} stroke={PAL.clayDark} strokeWidth={5} strokeLinecap="round" />
              <ellipse cx={h.x} cy={h.y} rx={30} ry={22} fill={PAL.clayDark} />
              <ellipse cx={h.x} cy={h.y + 2} rx={24} ry={17} fill={PAL.hole} />
            </g>
          ))}
          {/* наклейка МАРЖА СЕЛЛЕРА — бумажный стикер со скотчем */}
          <g transform="rotate(-4 540 660)">
            <path d="M 370 578 L 710 572 L 716 748 L 376 756 Z" fill={PAL.sticker} />
            <path d="M 690 572 L 710 572 L 716 600 Z" fill="#e6dac2" />
            <rect x={500} y={556} width={84} height={30} fill={PAL.tape} opacity={0.85} transform="rotate(3 542 571)" />
            <text x={542} y={662} textAnchor="middle" fontFamily="Caveat, cursive" fontWeight={700} fontSize={96} fill={PAL.ink}>МАРЖА</text>
            <text x={542} y={730} textAnchor="middle" fontFamily="Caveat, cursive" fontWeight={700} fontSize={64} fill="#c0392b">селлера</text>
          </g>
        </g>
        {bills}
        {fox(-340, 235, 0.95, 'fox_p', '#8a4bf5', '#4f1fb3', 'p')}
        {fox(1420, 865, 1.12, 'fox_b', '#2f74ff', '#0f3db8', 'b')}
        <rect width={1080} height={1920} fill="url(#jvig)" />
        <rect width={1080} height={1920} filter="url(#jgrain)" opacity={0.9} />
      </svg>
    </AbsoluteFill>
  );
};
