import React from 'react';
import {AbsoluteFill, Composition, Still, Sequence, Img, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import {Audio} from '@remotion/media';
import data from './data.json';

const colors = {bg:'#101d29', fg:'#f4f0e7', accent:'#a9e1ba', muted:'#9caebb'};
const base: React.CSSProperties = {background: colors.bg, color: colors.fg, fontFamily:'"PingFang SC", "Noto Sans CJK SC", sans-serif'};
const Safe: React.FC<React.PropsWithChildren<{bottom?: number}>> = ({children, bottom = 400}) => <div style={{position:'absolute',left:90,right:180,top:210,bottom}}>{children}</div>;
const Scene: React.FC<{scene: typeof data.scenes[number]}> = ({scene}) => {
  const f = useCurrentFrame();
  return <Safe bottom={600}><div style={{opacity:interpolate(f,[0,8],[0,1],{extrapolateRight:'clamp'}),translate:`0 ${interpolate(f,[0,10],[18,0],{extrapolateRight:'clamp'})}px`}}>
    <div style={{fontSize:30,color:colors.muted,letterSpacing:3,marginBottom:60}}>{data.title}</div>
    <div style={{fontSize:86,fontWeight:800,lineHeight:1.25,textWrap:'balance',whiteSpace:'pre-line',overflowWrap:'anywhere',marginBottom:66}}>{scene.heading}</div>
    {scene.image && <Img src={staticFile(scene.image)} style={{width:'100%',height:240,objectFit:'contain',borderRadius:20,marginBottom:22}}/>}
    {scene.points.map((p,i)=><div key={i} style={{display:'flex',gap:24,padding:'20px 0',borderBottom:'1px solid #334552',fontSize:48,lineHeight:1.4}}><span style={{color:colors.accent}}>•</span><span>{p}</span></div>)}
  </div></Safe>;
};
const Video = () => {
  const frame = useCurrentFrame();
  const ms = frame / 30 * 1000;
  const caption = data.captions.find(c=>ms>=c.startMs && ms<c.endMs);
  return <AbsoluteFill style={base}>
    <div style={{position:'absolute',width:640,height:640,right:-330,top:-310,border:'2px solid #466251',borderRadius:'50%'}}/>
    <Audio src={staticFile('narration.wav')}/>
    {data.scenes.map((scene,i)=><Sequence key={i} from={scene.startFrame} durationInFrames={scene.endFrame-scene.startFrame}><Scene scene={scene}/></Sequence>)}
    {caption && <div style={{position:'absolute',left:90,right:180,bottom:390,textAlign:'center',fontSize:46,lineHeight:1.5,fontWeight:600,whiteSpace:'pre-wrap',background:'#101d29ed',borderRadius:20,padding:'20px 8px'}}>{caption.text}</div>}
  </AbsoluteFill>;
};
const Cover = () => <AbsoluteFill style={base}><Safe>
  <div style={{fontSize:30,letterSpacing:6,color:colors.accent,marginBottom:90}}>一分钟 · 讲清楚</div>
  <div style={{fontSize:102,fontWeight:900,lineHeight:1.22,whiteSpace:'pre-line',overflowWrap:'anywhere',marginBottom:95}}>{data.coverTitle}</div>
  {data.framework.map((p,i)=><div key={i} style={{display:'flex',alignItems:'center',gap:26,marginBottom:22,padding:'28px 24px',background:'#203440',borderRadius:18,fontSize:46,lineHeight:1.4}}><span style={{fontSize:30,color:colors.accent}}>0{i+1}</span><span>{p}</span></div>)}
</Safe></AbsoluteFill>;
const Root = () => <><Composition id="Video" component={Video} width={1080} height={1920} fps={30} durationInFrames={data.durationInFrames}/><Still id="Cover" component={Cover} width={1080} height={1920}/></>;
registerRoot(Root);
