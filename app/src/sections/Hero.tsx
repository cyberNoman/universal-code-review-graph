import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowRight, BookOpen, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

gsap.registerPlugin(ScrollTrigger);

const aiLogos = [
  { name: 'Kimi', abbr: 'K' },
  { name: 'Qwen', abbr: 'Q' },
  { name: 'Gemini', abbr: 'G' },
  { name: 'Claude', abbr: 'C' },
  { name: 'ChatGPT', abbr: 'O' },
  { name: 'Cursor', abbr: 'Cu' },
];

export default function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const portraitRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const subheadRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const microLabelRef = useRef<HTMLSpanElement>(null);
  const topLineRef = useRef<HTMLDivElement>(null);
  const leftTick1Ref = useRef<HTMLDivElement>(null);
  const leftTick2Ref = useRef<HTMLDivElement>(null);
  const aiLogosRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const card = cardRef.current;
    const portrait = portraitRef.current;
    const headline = headlineRef.current;
    const subhead = subheadRef.current;
    const cta = ctaRef.current;
    const microLabel = microLabelRef.current;
    const topLine = topLineRef.current;
    const leftTick1 = leftTick1Ref.current;
    const leftTick2 = leftTick2Ref.current;
    const aiLogos = aiLogosRef.current;

    if (!section || !card || !portrait || !headline || !subhead || !cta || !microLabel) return;

    const ctx = gsap.context(() => {
      // Initial states (hidden)
      gsap.set(card, { opacity: 0, y: '6vh' });
      gsap.set(portrait, { opacity: 0, x: '-4vw', scale: 1.03 });
      gsap.set(headline.children, { opacity: 0, y: 24 });
      gsap.set(subhead, { opacity: 0, y: 16 });
      gsap.set(cta.children, { opacity: 0, y: 12 });
      gsap.set(microLabel, { opacity: 0 });
      gsap.set(topLine, { scaleY: 0, transformOrigin: 'top' });
      gsap.set([leftTick1, leftTick2], { scaleX: 0, transformOrigin: 'left' });
      if (aiLogos) {
        gsap.set(aiLogos.children, { opacity: 0, y: 10 });
      }

      // Load animation timeline
      const loadTl = gsap.timeline({ delay: 0.2 });
      
      loadTl
        .to(card, { opacity: 1, y: 0, duration: 0.9, ease: 'power2.out' })
        .to(portrait, { opacity: 1, x: 0, scale: 1, duration: 0.9, ease: 'power2.out' }, 0.15)
        .to(headline.children, { opacity: 1, y: 0, duration: 0.7, stagger: 0.08, ease: 'power2.out' }, 0.3)
        .to(subhead, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, 0.5)
        .to(cta.children, { opacity: 1, y: 0, duration: 0.5, stagger: 0.1, ease: 'power2.out' }, 0.6)
        .to(microLabel, { opacity: 1, duration: 0.5 }, 0.7)
        .to(topLine, { scaleY: 1, duration: 0.8, ease: 'power2.out' }, 0.4)
        .to([leftTick1, leftTick2], { scaleX: 1, duration: 0.6, stagger: 0.1, ease: 'power2.out' }, 0.5);
      
      if (aiLogos) {
        loadTl.to(aiLogos.children, { 
          opacity: 1, 
          y: 0, 
          duration: 0.4, 
          stagger: 0.05, 
          ease: 'power2.out' 
        }, 0.8);
      }

      // Scroll-driven exit animation
      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=130%',
          pin: true,
          scrub: 0.6,
        }
      });

      // EXIT (70-100%)
      scrollTl
        .fromTo(card, 
          { y: 0, opacity: 1 },
          { y: '-18vh', opacity: 0, ease: 'power2.in' },
          0.7
        )
        .fromTo(portrait,
          { x: 0, opacity: 1 },
          { x: '-10vw', opacity: 0.35, ease: 'power2.in' },
          0.7
        )
        .fromTo(headline,
          { x: 0, opacity: 1 },
          { x: '8vw', opacity: 0.25, ease: 'power2.in' },
          0.7
        )
        .fromTo([leftTick1, leftTick2],
          { scaleX: 1 },
          { scaleX: 0, ease: 'power2.in' },
          0.75
        )
        .fromTo(topLine,
          { scaleY: 1 },
          { scaleY: 0, transformOrigin: 'bottom', ease: 'power2.in' },
          0.75
        );

    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section 
      ref={sectionRef} 
      className="section-pinned bg-[#0B0F17] z-10 flex items-center justify-center"
    >
      {/* Blueprint decorative lines */}
      <div 
        ref={topLineRef}
        className="absolute left-1/2 top-0 w-px h-[19vh] accent-line pulse-line"
      />
      <div 
        ref={leftTick1Ref}
        className="absolute left-0 top-[30vh] h-px w-[6vw] blueprint-line"
      />
      <div 
        ref={leftTick2Ref}
        className="absolute left-0 top-[70vh] h-px w-[6vw] blueprint-line"
      />

      {/* Main card */}
      <div 
        ref={cardRef}
        className="blueprint-card w-[84vw] max-w-[1180px] h-[62vh] relative flex"
      >
        {/* Portrait */}
        <div 
          ref={portraitRef}
          className="absolute left-[6%] top-[10%] w-[34%] h-[80%] overflow-hidden"
        >
          <img 
            src="/hero_portrait.jpg" 
            alt="Developer at work"
            className="w-full h-full object-cover"
            decoding="async"
          />
          <div className="scanline" />
        </div>

        {/* Content */}
        <div className="absolute left-[46%] top-[14%] w-[44%]">
          {/* Universal Badge */}
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-[#4B6BFF]" />
            <span className="mono text-xs text-[#4B6BFF] tracking-[0.12em] uppercase">
              Universal MCP Server
            </span>
          </div>

          <div ref={headlineRef}>
            <h1 className="text-[clamp(36px,4.5vw,64px)] font-semibold text-[#F2F5FA] leading-[1.1] mb-6">
              <span className="block">Review only</span>
              <span className="block">what matters.</span>
            </h1>
          </div>
          
          <p 
            ref={subheadRef}
            className="text-[#A7B1C6] text-lg md:text-xl leading-relaxed mb-6 max-w-[90%]"
          >
            A universal code-review graph that works with <strong className="text-[#F2F5FA]">ALL AI assistants</strong>. 
            Kimi, Qwen, Gemini, Claude, ChatGPT—save 6–8× tokens on every review.
          </p>

          {/* AI Platform Logos */}
          <div 
            ref={aiLogosRef}
            className="flex items-center gap-2 mb-6 flex-wrap"
          >
            {aiLogos.map((ai) => (
              <div 
                key={ai.name}
                className="w-9 h-9 rounded-md bg-[#4B6BFF]/10 border border-[#4B6BFF]/30 flex items-center justify-center"
                title={ai.name}
              >
                <span className="text-[#4B6BFF] text-xs font-semibold">{ai.abbr}</span>
              </div>
            ))}
            <span className="text-[#A7B1C6] text-sm ml-2">+ more</span>
          </div>

          <div ref={ctaRef} className="flex gap-4 flex-wrap">
            <Button 
              className="bg-[#4B6BFF] hover:bg-[#3d5ce6] text-white px-6 py-3 h-auto text-base font-medium rounded-md flex items-center gap-2"
            >
              Get Started
              <ArrowRight className="w-4 h-4" />
            </Button>
            <Button 
              variant="outline"
              className="border-white/30 text-[#F2F5FA] hover:bg-white/10 px-6 py-3 h-auto text-base font-medium rounded-md flex items-center gap-2"
            >
              <BookOpen className="w-4 h-4" />
              Read the Docs
            </Button>
          </div>
        </div>

        {/* Micro label */}
        <span 
          ref={microLabelRef}
          className="absolute bottom-[8%] left-[6%] mono text-xs text-[#A7B1C6] tracking-[0.08em] uppercase"
        >
          Universal MCP v1.0
        </span>

        {/* Corner coordinates */}
        <span className="absolute bottom-[8%] right-[4%] mono text-xs text-[#A7B1C6]/50">
          x: 0.12 / y: 0.88
        </span>
      </div>
    </section>
  );
}
