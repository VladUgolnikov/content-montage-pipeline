import React from 'react';
import {Composition} from 'remotion';
import {Reel, defaultProps, ReelProps} from './Reel';
import {Cartoon, cartoonDefaults, CartoonProps} from './Cartoon';

export const RemotionRoot: React.FC = () => (
  <>
  <Composition
    id="Reel"
    component={Reel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={300}
    defaultProps={defaultProps}
    calculateMetadata={({props}: {props: ReelProps}) => ({
      durationInFrames: Math.max(1, Math.round(props.duration * 30)),
    })}
  />
  <Composition id="Cartoon" component={Cartoon} width={1080} height={1920} fps={30} durationInFrames={863}
    defaultProps={cartoonDefaults}
    calculateMetadata={({props}: {props: CartoonProps}) => ({durationInFrames: Math.round(props.duration * 30)})} />
  </>
);
