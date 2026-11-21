import React from 'react';
import { Calculator, BadgePercent, Check, Coins } from 'lucide-react';

export default function HeroMotion() {
  return <div className="hero-motion" aria-hidden="true">
    <div className="motion-orbit orbit-one"/><div className="motion-orbit orbit-two"/>
    <span className="motion-satellite satellite-percent"><BadgePercent size={23}/></span>
    <span className="motion-satellite satellite-coins"><Coins size={22}/></span>
    <span className="motion-calculator"><Calculator size={40} strokeWidth={1.4}/><i><Check size={13}/></i></span>
    <span className="motion-spark spark-one"/><span className="motion-spark spark-two"/>
  </div>;
}
