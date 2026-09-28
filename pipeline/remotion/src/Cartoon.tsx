// Мультяшные сцены «бумажная аппликация» (референс @not_morozov) под голос манифеста.
// Приёмы: вырезанная бумага с тенью, «кипящий» контур (смена seed шума каждые 4 кадра),
// зерно бумаги, пружинные появления по словам, смена сцен листом бумаги.
import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill, Audio, continueRender, delayRender, Easing, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';

type W = {w: string; t0: number; t1: number};
export type CartoonProps = {duration: number; audio?: string; words: W[]};
export const cartoonDefaults: CartoonProps = {duration: 28.75, audio: 'media/head.wav', words: []};

const P = {
  cream: '#f3e6cc', paper: '#fbf4e4', ink: '#2a2530', navy: '#27295a', navy2: '#3b3d7a',
  mustard: '#e8b23a', red: '#e0412f', teal: '#3fa89b', pink: '#f2a7b0', brown: '#6b3f2a',
  hair: '#4a2a1c', skin: '#f1c7a5', grey: '#b9b6b0', purple: '#8a4fd8', blue: '#2f6fe0', yellow: '#ffcc00',
};
const HAND = 'Caveat, cursive';
const UI = '"Golos Text", sans-serif';
const DISP = 'Oswald, sans-serif';
const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const useFonts = () => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const f = [
      new FontFace('Caveat', `url(${staticFile('fonts/Caveat.ttf')})`, {weight: '400 700'}),
      new FontFace('Golos Text', `url(${staticFile('fonts/GolosText.ttf')})`, {weight: '400 900'}),
      new FontFace('Oswald', `url(${staticFile('fonts/Oswald700.ttf')})`, {weight: '400 900'}),
    ];
    Promise.all(f.map((x) => x.load())).then((l) => {l.forEach((x) => document.fonts.add(x)); continueRender(h);})
      .catch(() => continueRender(h));
  }, [h]);
};

// пружинное появление в момент at (сек, глобально)
const usePop = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (at: number, damping = 9) => spring({frame: frame - Math.round(at * fps), fps, config: {damping, stiffness: 140, mass: 0.7}});
};
const useT = () => useCurrentFrame() / 30;

// ---------- общие фильтры ----------
const Defs: React.FC = () => {
  const seed = Math.floor(useCurrentFrame() / 4) % 7;
  return (
    <defs>
      <filter id="boil" x="-5%" y="-5%" width="110%" height="110%">
        <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed={seed} result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="5" />
      </filter>
      <filter id="cut" x="-10%" y="-10%" width="120%" height="130%">
        <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed={seed} result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="5" result="d" />
        <feDropShadow dx="0" dy="7" stdDeviation="5" floodColor="#2a1a10" floodOpacity="0.28" />
      </filter>
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed={seed} />
        <feColorMatrix type="saturate" values="0" />
        <feComponentTransfer><feFuncA type="linear" slope="0.5" /></feComponentTransfer>
      </filter>
      <pattern id="lines" width="1080" height="56" patternUnits="userSpaceOnUse">
        <rect width="1080" height="56" fill={P.paper} />
        <line x1="0" y1="55" x2="1080" y2="55" stroke="#9fb7d6" strokeWidth="2" />
      </pattern>
    </defs>
  );
};
const Grain: React.FC = () => <rect width="1080" height="1920" filter="url(#grain)" opacity="0.18" style={{mixBlendMode: 'multiply'}} />;

// ---------- персонаж (Влад из бумаги) ----------
const Vlad: React.FC<{x: number; y: number; s?: number; shock?: number; talk?: boolean}> = ({x, y, s = 1, shock = 0, talk = true}) => {
  const f = useCurrentFrame();
  const blink = f % 95 < 4 ? 0.15 : 1;
  const mouth = talk ? 8 + 10 * Math.abs(Math.sin(f / 3.1)) : 6;
  const hairUp = -40 * shock;
  return (
    <g transform={`translate(${x},${y}) scale(${s})`} filter="url(#cut)">
      {/* тело */}
      <path d="M-170 380 Q-160 170 0 160 Q160 170 170 380 Z" fill={P.grey} />
      <path d="M-40 168 Q0 205 40 168" fill="none" stroke="#9a968f" strokeWidth="6" />
      {/* шея, голова */}
      <rect x="-30" y="120" width="60" height="60" rx="20" fill={P.skin} />
      <ellipse cx="0" cy="40" rx="105" ry="120" fill={P.skin} />
      {/* борода */}
      <path d="M-100 40 Q-95 170 0 175 Q95 170 100 40 Q70 95 0 100 Q-70 95 -100 40 Z" fill={P.brown} />
      {/* волосы-кудри */}
      <g transform={`translate(0,${hairUp})`}>
        {[-90, -55, -18, 20, 58, 92, -72, -35, 5, 42, 78].map((cx, i) => (
          <circle key={i} cx={cx} cy={i < 6 ? -62 : -88} r={i < 6 ? 34 : 30} fill={P.hair} />
        ))}
      </g>
      {/* глаза */}
      {shock > 0.3 ? (
        <>
          <circle cx="-38" cy="20" r={24 * shock} fill="#fff" stroke={P.ink} strokeWidth="4" />
          <circle cx="38" cy="20" r={24 * shock} fill="#fff" stroke={P.ink} strokeWidth="4" />
          <circle cx="-38" cy="20" r="8" fill={P.ink} /><circle cx="38" cy="20" r="8" fill={P.ink} />
        </>
      ) : (
        <>
          <ellipse cx="-38" cy="22" rx="10" ry={12 * blink} fill={P.ink} />
          <ellipse cx="38" cy="22" rx="10" ry={12 * blink} fill={P.ink} />
        </>
      )}
      <path d="M-60 -8 Q-38 -20 -16 -8 M16 -8 Q38 -20 60 -8" stroke={P.hair} strokeWidth="9" fill="none" strokeLinecap="round"
        transform={`translate(0,${-14 * shock})`} />
      {/* рот */}
      <ellipse cx="0" cy="92" rx={shock > 0.3 ? 20 : 26} ry={shock > 0.3 ? 30 * shock : mouth / 2} fill="#5a1f1a" />
      <circle cx="-70" cy="62" r="14" fill={P.pink} opacity="0.7" /><circle cx="70" cy="62" r="14" fill={P.pink} opacity="0.7" />
    </g>
  );
};

const Coin: React.FC<{x: number; y: number; r?: number; rot?: number}> = ({x, y, r = 34, rot = 0}) => (
  <g transform={`translate(${x},${y}) rotate(${rot})`}>
    <circle r={r} fill={P.mustard} stroke="#b9831d" strokeWidth={r / 6} />
    <text y={r * 0.36} textAnchor="middle" fontFamily={DISP} fontSize={r} fill="#8a5c0e">₽</text>
  </g>
);

// «вырезанные» буквы как из газеты
const Ransom: React.FC<{text: string; x: number; y: number; size: number; at: number}> = ({text, x, y, size, at}) => {
  const pop = usePop();
  const cols = [[P.paper, P.ink], [P.red, '#fff'], [P.ink, '#fff'], [P.mustard, P.ink], ['#fff', P.red]];
  const chars = [...text];
  const w = size * 0.72;
  return (
    <g filter="url(#cut)">
      {chars.map((c, i) => {
        const p = pop(at + i * 0.05, 8);
        const [bg, fg] = cols[(i * 3 + 1) % cols.length];
        const cx = x + (i - (chars.length - 1) / 2) * w;
        return c === ' ' ? null : (
          <g key={i} transform={`translate(${cx},${y}) rotate(${((i * 37) % 13) - 6}) scale(${p})`}>
            <rect x={-w * 0.46} y={-size * 0.62} width={w * 0.92} height={size * 1.1} fill={bg} />
            <text y={size * 0.3} textAnchor="middle" fontFamily={i % 2 ? DISP : 'Georgia, serif'} fontWeight="700" fontSize={size * 0.9} fill={fg}>{c}</text>
          </g>
        );
      })}
    </g>
  );
};

// ---------- сцены (t — глобальное время) ----------
const S1Revenue: React.FC = () => {
  const t = useT(); const pop = usePop();
  const grow = interpolate(t, [2.9, 3.8], [1, 1.5], {...cl, easing: Easing.out(Easing.back(1.6))});
  const base = 360;
  return (
    <g>
      <rect width="1080" height="1920" fill={P.cream} />
      <g transform={`rotate(${t * 6} 860 420)`}>
        {Array.from({length: 12}).map((_, i) => (
          <path key={i} d="M860 420 L1240 380 L1240 460 Z" fill={P.mustard} opacity="0.18" transform={`rotate(${i * 30} 860 420)`} />
        ))}
      </g>
      <circle cx="860" cy="420" r="110" fill={P.mustard} filter="url(#cut)" />
      <rect x="0" y="1520" width="1080" height="400" fill="#d9c49e" />
      {/* столбики из коробок */}
      {[{x: 270, h: base, lab: '2 года назад', at: 0.5}, {x: 640, h: base * grow, lab: 'сейчас', at: 1.6}].map((c, i) => {
        const p = pop(c.at);
        const n = Math.round(c.h / 90);
        return (
          <g key={i} transform={`translate(${c.x},1520) scale(1,${p})`}>
            {Array.from({length: n}).map((_, k) => (
              <g key={k} filter="url(#cut)" transform={`translate(0,${-(k + 1) * 90}) rotate(${((k * 23 + i * 7) % 7) - 3})`}>
                <rect x="-120" y="0" width="240" height="84" rx="6" fill={k % 2 ? P.red : P.teal} />
                <rect x="-120" y="0" width="240" height="20" fill="#000" opacity="0.12" />
              </g>
            ))}
            <text y="90" textAnchor="middle" fontFamily={HAND} fontSize="64" fill={P.ink}>{c.lab}</text>
          </g>
        );
      })}
      <g transform={`translate(640,${1520 - base * grow - 150}) scale(${pop(3.35)})`}>
        <text textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="150" fill={P.red} filter="url(#boil)">×1,5</text>
      </g>
      <text x="540" y="560" textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="120" fill={P.ink}
        opacity={interpolate(t, [2.2, 2.5], [0, 1], cl)} filter="url(#boil)">выручка</text>
    </g>
  );
};

const S2Profit: React.FC = () => {
  const t = useT(); const pop = usePop();
  const shrink = interpolate(t, [4.6, 5.4], [1, 0.45], {...cl, easing: Easing.in(Easing.cubic)});
  return (
    <g>
      <rect width="1080" height="1920" fill={P.navy} />
      {Array.from({length: 40}).map((_, i) => (
        <circle key={i} cx={(i * 263) % 1080} cy={(i * 811) % 1300} r={i % 5 ? 3 : 6} fill="#fff" opacity={0.4 + 0.6 * Math.abs(Math.sin(t * 3 + i))} />
      ))}
      <path d="M140 300 Q170 250 200 300 Q150 320 140 300" fill={P.mustard} />
      <g transform={`translate(540,1080) scale(${shrink * pop(4.15)})`} filter="url(#cut)">
        <ellipse rx="300" ry="230" fill={P.pink} />
        <circle cx="260" cy="-20" r="80" fill="#f58f9c" />
        <circle cx="275" cy="-20" r="12" fill={P.ink} /><circle cx="245" cy="-20" r="12" fill={P.ink} />
        <circle cx="110" cy="-90" r="16" fill={P.ink} />
        <path d="M-80 -230 L-40 -300 L0 -230 Z" fill="#f58f9c" />
        <rect x="-60" y="-236" width="120" height="16" rx="8" fill={P.ink} />
        {[-180, 120].map((lx) => <rect key={lx} x={lx} y="170" width="60" height="110" rx="20" fill="#f58f9c" />)}
        <path d="M-40 230 L-10 180 L20 230" fill={P.navy} />
      </g>
      {/* монеты высыпаются */}
      {Array.from({length: 8}).map((_, i) => {
        const tt = t - 4.3 - i * 0.12;
        if (tt < 0) return null;
        return <Coin key={i} x={520 + ((i * 47) % 90) - 45} y={1300 + tt * tt * 900} rot={tt * 300} r={30} />;
      })}
      <Ransom text="÷7" x={540} y={560} size={220} at={4.95} />
      <text x="540" y="380" textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="110" fill="#fff"
        opacity={interpolate(t, [4.2, 4.45], [0, 1], cl)} filter="url(#boil)">прибыль</text>
    </g>
  );
};

const S3Seller: React.FC = () => {
  const t = useT(); const pop = usePop(); const f = useCurrentFrame();
  const shops = [{lab: 'WB', c: P.purple, at: 9.55, x: 200}, {lab: 'Ozon', c: P.blue, at: 10.15, x: 540}, {lab: 'Я.Маркет', c: P.yellow, at: 10.9, x: 880}];
  return (
    <g>
      <rect width="1080" height="1920" fill="#f0c95a" />
      <rect x="0" y="0" width="1080" height="1920" fill="#e9b949" opacity="0.5" />
      {/* окно */}
      <g filter="url(#cut)"><rect x="620" y="560" width="340" height="420" fill={P.navy} /><rect x="620" y="760" width="340" height="12" fill={P.paper} /><rect x="784" y="560" width="12" height="420" fill={P.paper} /></g>
      <circle cx="720" cy="640" r="30" fill={P.paper} opacity="0.9" />
      {/* календарь «7 лет» */}
      <g transform={`translate(230,700) scale(${pop(6.0)}) rotate(-6)`} filter="url(#cut)">
        <rect x="-130" y="-150" width="260" height="300" fill={P.paper} />
        <rect x="-130" y="-150" width="260" height="70" fill={P.red} />
        <text y="90" textAnchor="middle" fontFamily={DISP} fontSize="170" fill={P.ink}>7</text>
        <text y="-100" textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="54" fill="#fff">лет</text>
      </g>
      {/* вывески площадок на верёвочках */}
      {shops.map((s, i) => {
        const p = pop(s.at, 7);
        const sw = Math.sin((f - s.at * 30) / 6) * 6 * Math.exp(-Math.max(0, t - s.at) * 1.2);
        return (
          <g key={i} transform={`translate(${s.x},${-260 + 520 * p}) rotate(${sw})`}>
            <line x1="-60" y1="-300" x2="-60" y2="0" stroke={P.ink} strokeWidth="4" /><line x1="60" y1="-300" x2="60" y2="0" stroke={P.ink} strokeWidth="4" />
            <g filter="url(#cut)"><rect x="-140" y="0" width="280" height="130" rx="18" fill={s.c} />
              <text y="88" textAnchor="middle" fontFamily={DISP} fontSize={s.lab.length > 4 ? 58 : 78} fill={s.lab === 'Я.Маркет' ? P.ink : '#fff'}>{s.lab}</text></g>
          </g>
        );
      })}
      <Vlad x={540} y={1170} s={1.25} />
      {/* стол и коробки */}
      <rect x="0" y="1560" width="1080" height="360" fill={P.brown} filter="url(#cut)" />
      {[0, 1, 2].map((k) => (
        <g key={k} transform={`translate(${160 + k * 20},${1560 - (k + 1) * 70}) scale(${pop(6.75 + k * 0.12)})`} filter="url(#cut)">
          <rect x="-110" y="0" width="220" height="64" fill={[P.red, P.teal, P.mustard][k]} />
          <text x="0" y="44" textAnchor="middle" fontFamily={DISP} fontSize="30" fill="#fff">GAME</text>
        </g>
      ))}
      <g transform={`translate(880,1490) scale(${pop(7.4)})`} filter="url(#cut)">
        <circle r="60" fill={P.teal} /><circle cx="-24" cy="-10" r="10" fill={P.ink} /><circle cx="24" cy="-10" r="10" fill={P.ink} />
        <path d="M-25 20 Q0 40 25 20" stroke={P.ink} strokeWidth="6" fill="none" />
      </g>
    </g>
  );
};

const S4Idea: React.FC = () => {
  const t = useT(); const pop = usePop();
  const glow = interpolate(t, [12.1, 12.4], [0, 1], cl);
  const boxX = interpolate(t, [14.1, 14.6], [540, 720], {...cl, easing: Easing.inOut(Easing.cubic)});
  const boxY = interpolate(t, [14.1, 14.6], [1180, 900], {...cl, easing: Easing.inOut(Easing.cubic)});
  const star = pop(15.9, 6);
  return (
    <g>
      <rect width="1080" height="1920" fill="url(#lines)" />
      <rect x="120" y="0" width="4" height="1920" fill="#e38a8a" />
      {/* лампочка */}
      <g transform={`translate(270,560) scale(${pop(12.0)})`}>
        <circle r={150 * glow} fill={P.yellow} opacity="0.35" />
        <g filter="url(#cut)"><circle r="95" fill={glow > 0.5 ? P.yellow : '#f7ecc4'} /><rect x="-40" y="80" width="80" height="70" rx="10" fill={P.grey} /></g>
      </g>
      <text x="270" y="800" textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="80" fill={P.ink} opacity={glow} filter="url(#boil)">идея</text>
      {/* стрелка-карандаш */}
      <path d="M380 620 Q540 560 620 760" stroke={P.ink} strokeWidth="8" fill="none" strokeLinecap="round" filter="url(#boil)"
        strokeDasharray="600" strokeDashoffset={interpolate(t, [12.5, 13.3], [600, 0], cl)} />
      {/* полка */}
      <g transform={`translate(${interpolate(t, [13.9, 14.3], [1300, 0], {...cl, easing: Easing.out(Easing.cubic)})},0)`} filter="url(#cut)">
        <rect x="520" y="1000" width="440" height="30" fill={P.brown} />
        <rect x="560" y="1030" width="20" height="60" fill={P.brown} /><rect x="900" y="1030" width="20" height="60" fill={P.brown} />
        {[0, 1].map((k) => <rect key={k} x={560 + k * 70} y="880" width="56" height="120" fill={[P.teal, P.purple][k]} />)}
      </g>
      {/* коробка игры */}
      <g transform={`translate(${boxX},${boxY}) scale(${pop(13.6)}) rotate(${interpolate(t, [14.1, 14.6], [-8, 0], cl)})`} filter="url(#cut)">
        <rect x="-150" y="-110" width="300" height="220" rx="10" fill={P.red} />
        <rect x="-150" y="-110" width="300" height="60" fill="#b8302a" />
        <text y="30" textAnchor="middle" fontFamily={DISP} fontSize="64" fill="#fff">ИГРА</text>
        <circle cx="-90" cy="72" r="16" fill={P.yellow} /><circle cx="-40" cy="72" r="16" fill={P.teal} /><circle cx="10" cy="72" r="16" fill="#fff" />
      </g>
      {/* розетка №1 */}
      <g transform={`translate(${boxX + 130},${boxY - 160}) scale(${star}) rotate(${-12 + 12 * star})`} filter="url(#cut)">
        {Array.from({length: 16}).map((_, i) => <path key={i} d="M0 0 L20 -150 L-20 -150 Z" fill={P.mustard} transform={`rotate(${i * 22.5})`} />)}
        <circle r="115" fill={P.mustard} /><circle r="92" fill="#fff4cf" />
        <text y="10" textAnchor="middle" fontFamily={DISP} fontSize="90" fill={P.red}>№1</text>
        <text y="55" textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="38" fill={P.ink}>в России</text>
      </g>
      <text x="540" y="1480" textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="96" fill={P.ink}
        opacity={interpolate(t, [16.2, 16.5], [0, 1], cl)} filter="url(#boil)">самая продаваемая</text>
    </g>
  );
};

const S5Leak: React.FC = () => {
  const t = useT(); const pop = usePop();
  const shock = interpolate(t, [23.55, 23.8], [0, 1], {...cl, easing: Easing.out(Easing.back(2))});
  const zoom = interpolate(t, [23.5, 23.8], [1, 1.9], {...cl, easing: Easing.inOut(Easing.cubic)});
  const holes = [[-120, 60], [-40, 140], [60, 90], [130, 170], [-10, 30]];
  return (
    <g transform={`translate(330,840) scale(${zoom}) translate(-330,-840)`}>
      <rect width="1080" height="1920" fill={P.navy2} />
      <rect y="1500" width="1080" height="420" fill={P.navy} />
      {/* ведро «маржа» */}
      <g transform={`translate(700,1260) scale(${pop(18.0)})`}>
        <g filter="url(#cut)">
          <path d="M-190 -170 L190 -170 L150 210 L-150 210 Z" fill={P.grey} />
          <ellipse cx="0" cy="-170" rx="190" ry="40" fill="#8f8b85" />
          <text y="-30" textAnchor="middle" fontFamily={DISP} fontSize="72" fill={P.ink}>МАРЖА</text>
        </g>
        {holes.map(([hx, hy], i) => {
          const on = t > 19.6 + i * 0.35;
          return (
            <g key={i}>
              <circle cx={hx} cy={hy} r="12" fill={P.ink} opacity={on ? 1 : 0} />
              {on && Array.from({length: 4}).map((_, k) => {
                const ph = ((t * 1.6 + k * 0.25 + i * 0.13) % 1);
                return <Coin key={k} x={hx + (hx > 0 ? 1 : -1) * ph * 260} y={hy + ph * ph * 520} r={20} rot={ph * 400} />;
              })}
            </g>
          );
        })}
      </g>
      {/* лупа */}
      <g transform={`translate(${520 + 30 * Math.sin(t * 2)},1180) rotate(-30) scale(${pop(18.7)})`} filter="url(#cut)">
        <circle r="95" fill="#cfe8ff" opacity="0.6" stroke={P.ink} strokeWidth="18" />
        <rect x="-16" y="100" width="32" height="170" rx="12" fill={P.brown} />
      </g>
      <Vlad x={300} y={860} s={1.05} shock={shock} talk={t < 23.5} />
      {/* команда — силуэты */}
      {[[150, 1080], [240, 1130]].map(([x, y], i) => (
        <g key={i} transform={`translate(${x},${y}) scale(${pop(18.44 + i * 0.1)})`} filter="url(#cut)" opacity="0.9">
          <circle cy="-120" r="55" fill="#1e1f45" /><path d="M-80 60 Q-70 -60 0 -60 Q70 -60 80 60 Z" fill="#1e1f45" />
        </g>
      ))}
    </g>
  );
};

const S5Shock: React.FC = () => {
  const t = useT();
  return t > 23.6 ? <Ransom text="АХ*ЕЛИ" x={540} y={1450} size={130} at={23.62} /> : null;
};

const S6Series: React.FC = () => {
  const t = useT(); const pop = usePop();
  const line = 'серия: 30 утечек маржи';
  const shown = Math.floor(interpolate(t, [25.0, 26.6], [0, line.length], cl));
  const circle = interpolate(t, [26.9, 27.5], [900, 0], cl);
  return (
    <g>
      <rect width="1080" height="1920" fill={P.cream} />
      <g transform="rotate(-3 540 960)" filter="url(#cut)">
        <rect x="110" y="330" width="860" height="1200" fill="url(#lines)" />
        {Array.from({length: 11}).map((_, i) => <circle key={i} cx={170 + i * 75} cy="360" r="14" fill={P.cream} />)}
      </g>
      <g transform="rotate(-3 540 960)">
        <text x="190" y="560" fontFamily={HAND} fontWeight="700" fontSize="92" fill={P.ink} filter="url(#boil)">{line.slice(0, shown)}</text>
        <g transform={`translate(540,930) scale(${pop(26.9, 7)})`}>
          <text textAnchor="middle" y="120" fontFamily={DISP} fontSize="360" fill={P.red} filter="url(#boil)">30</text>
          <ellipse rx="300" ry="210" cx="0" cy="0" fill="none" stroke={P.red} strokeWidth="12" strokeDasharray="900" strokeDashoffset={circle} filter="url(#boil)" />
        </g>
        {['реклама', 'СПП', 'логистика', 'неликвид', 'сервисы'].map((w, i) => (
          <g key={i} transform={`translate(${250 + (i % 3) * 270},${1270 + Math.floor(i / 3) * 110}) scale(${pop(27.4 + i * 0.18)}) rotate(${(i % 2 ? 4 : -4)})`}>
            <rect x="-115" y="-50" width="230" height="78" rx="10" fill={[P.teal, P.mustard, P.pink, P.purple, P.blue][i]} filter="url(#cut)" />
            <text y="8" textAnchor="middle" fontFamily={HAND} fontWeight="700" fontSize="54" fill={i === 1 ? P.ink : '#fff'}>{w}</text>
          </g>
        ))}
      </g>
      <g transform={`translate(${860 + 20 * Math.sin(t * 9)},${700 + 12 * Math.cos(t * 9)}) rotate(35)`} filter="url(#cut)" opacity={t > 25 && t < 26.8 ? 1 : 0}>
        <rect x="-18" y="-160" width="36" height="220" fill={P.mustard} /><path d="M-18 60 L0 110 L18 60 Z" fill={P.skin} />
      </g>
    </g>
  );
};

// ---------- смена сцен листом бумаги ----------
const SCENES: {t0: number; t1: number; C: React.FC}[] = [
  {t0: 0, t1: 4.1, C: S1Revenue}, {t0: 4.1, t1: 5.6, C: S2Profit}, {t0: 5.6, t1: 11.95, C: S3Seller},
  {t0: 11.95, t1: 17.7, C: S4Idea}, {t0: 17.7, t1: 24.3, C: S5Leak}, {t0: 24.3, t1: 99, C: S6Series},
];

const Caption: React.FC<{words: W[]}> = ({words}) => {
  const t = useT();
  // фраза: слова текущего «окна» из 3–6 слов
  const groups: W[][] = []; let cur: W[] = [];
  words.forEach((w, i) => {
    const prev = words[i - 1];
    if (cur.length && (cur.length >= 6 || (prev && w.t0 - prev.t1 > 0.35) || cur.map((x) => x.w).join(' ').length > 30)) {groups.push(cur); cur = [];}
    cur.push(w);
  });
  if (cur.length) groups.push(cur);
  const g = groups.find((gr, i) => t >= gr[0].t0 - 0.05 && t < (groups[i + 1]?.[0].t0 ?? 99) - 0.05);
  if (!g) return null;
  return (
    <div style={{position: 'absolute', top: 150, left: 0, right: 0, textAlign: 'center'}}>
      <span style={{display: 'inline-block', background: '#111', color: '#fff', fontFamily: UI, fontWeight: 600, fontSize: 40,
        padding: '10px 22px', borderRadius: 8, letterSpacing: '0.01em', maxWidth: 900}}>
        {g.map((w, i) => <span key={i} style={{opacity: t >= w.t0 - 0.03 ? 1 : 0.35}}>{w.w}{i < g.length - 1 ? ' ' : ''}</span>)}
      </span>
    </div>
  );
};

export const Cartoon: React.FC<CartoonProps> = ({audio, words}) => {
  useFonts();
  const t = useT();
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <Defs />
        {SCENES.map((s, i) => {
          if (t < s.t0 - 0.01 || t >= s.t1 + 0.4) return null;
          // вход: лист выезжает снизу с поворотом (кроме первой)
          const k = i === 0 ? 1 : spring({frame: frame - Math.round(s.t0 * fps), fps, config: {damping: 14, stiffness: 120}});
          const y = (1 - k) * 1920; const r = (1 - k) * 8;
          return (
            <g key={i} transform={`translate(0,${y}) rotate(${r} 540 1920)`} style={{filter: i ? 'drop-shadow(0 -12px 18px rgba(0,0,0,.35))' : undefined}}>
              <s.C />
              {i === 4 ? <S5Shock /> : null}
            </g>
          );
        })}
        <Grain />
      </svg>
      <Caption words={words} />
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
