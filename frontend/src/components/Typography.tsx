import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

interface ScrambleTextProps {
  text: string;
  className?: string;
  duration?: number;
  delay?: number;
}

const CHARS = '!<>-_\\/[]{}—=+*^?#0123456789ABCDEFGHIJKLMNOP';

export function ScrambleText({ text, className, duration = 800, delay = 0 }: ScrambleTextProps) {
  const [output, setOutput] = useState(text);

  useEffect(() => {
    let raf = 0;
    let started = false;
    const startTimer = setTimeout(() => {
      started = true;
      const start = performance.now();
      const tick = (now: number) => {
        const t = Math.min(1, (now - start) / duration);
        const reveal = Math.floor(t * text.length);
        let s = '';
        for (let i = 0; i < text.length; i++) {
          if (i < reveal) s += text[i];
          else if (text[i] === ' ') s += ' ';
          else s += CHARS[Math.floor(Math.random() * CHARS.length)];
        }
        setOutput(s);
        if (t < 1) raf = requestAnimationFrame(tick);
        else setOutput(text);
      };
      raf = requestAnimationFrame(tick);
    }, delay);
    return () => {
      clearTimeout(startTimer);
      if (started) cancelAnimationFrame(raf);
    };
  }, [text, duration, delay]);

  return <span className={className}>{output}</span>;
}

interface SplitWordsProps {
  text: string;
  className?: string;
  wordClassName?: string;
  delay?: number;
  stagger?: number;
}

export function SplitWords({ text, className, wordClassName, delay = 0, stagger = 0.06 }: SplitWordsProps) {
  const words = text.split(' ');
  return (
    <span className={className}>
      {words.map((w, i) => (
        <motion.span
          key={i}
          className={`inline-block mr-[0.25em] ${wordClassName ?? ''}`}
          initial={{ y: '110%', opacity: 0, filter: 'blur(8px)' }}
          animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
          transition={{ duration: 0.8, delay: delay + i * stagger, ease: [0.16, 1, 0.3, 1] }}
        >
          {w}
        </motion.span>
      ))}
    </span>
  );
}