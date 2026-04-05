import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Check, Zap } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const platforms = [
  { name: 'Kimi K2.5', savings: '7.5×', color: '#4B6BFF' },
  { name: 'Qwen', savings: '6.7×', color: '#7C3AED' },
  { name: 'Gemini Pro', savings: '7.2×', color: '#059669' },
  { name: 'Claude', savings: '6.8×', color: '#DC2626' },
  { name: 'ChatGPT', savings: '6.5×', color: '#0891B2' },
  { name: 'Cursor', savings: '7.0×', color: '#EA580C' },
  { name: 'Windsurf', savings: '7.0×', color: '#7C2D12' },
  { name: 'Zed', savings: '6.5×', color: '#BE185D' },
];

export default function AIPlatforms() {
  const sectionRef = useRef<HTMLElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);
  const statsRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const ctx = gsap.context(() => {
      const cards = cardsRef.current.filter(Boolean);

      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=120%',
          pin: true,
          scrub: 0.6,
        }
      });

      // ENTRANCE (0-30%)
      scrollTl
        .fromTo(headerRef.current,
          { opacity: 0, y: -30 },
          { opacity: 1, y: 0, ease: 'power2.out' },
          0
        )
        .fromTo(cards,
          { opacity: 0, y: 40, scale: 0.95 },
          { opacity: 1, y: 0, scale: 1, stagger: 0.02, ease: 'power2.out' },
          0.08
        )
        .fromTo(statsRef.current,
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, ease: 'power2.out' },
          0.2
        );

      // SETTLE (30-70%): Hold

      // EXIT (70-100%)
      scrollTl
        .fromTo([headerRef.current, statsRef.current],
          { opacity: 1 },
          { opacity: 0, ease: 'power2.in' },
          0.7
        )
        .fromTo(cards,
          { opacity: 1, y: 0 },
          { opacity: 0, y: -20, stagger: 0.01, ease: 'power2.in' },
          0.72
        );

    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section 
      ref={sectionRef} 
      className="section-pinned bg-[#0B0F17] z-25 flex items-center justify-center"
    >
      <div className="w-full max-w-6xl mx-auto px-6">
        {/* Header */}
        <div ref={headerRef} className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-[#4B6BFF]" />
            <span className="mono text-xs text-[#4B6BFF] tracking-[0.12em] uppercase">
              Universal Compatibility
            </span>
          </div>
          <h2 className="text-[clamp(32px,4vw,52px)] font-semibold text-[#F2F5FA] mb-4">
            Works with <span className="text-[#4B6BFF]">ALL</span> AI Assistants
          </h2>
          <p className="text-[#A7B1C6] text-lg max-w-2xl mx-auto">
            One MCP server. Every platform. Massive token savings across the board.
          </p>
        </div>

        {/* Platform Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {platforms.map((platform, index) => (
            <div
              key={platform.name}
              ref={el => { cardsRef.current[index] = el; }}
              className="blueprint-card p-5 hover:border-[#4B6BFF]/50 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <span 
                  className="text-sm font-medium"
                  style={{ color: platform.color }}
                >
                  {platform.name}
                </span>
                <Check className="w-4 h-4 text-[#4B6BFF] opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold text-[#F2F5FA]">
                  {platform.savings}
                </span>
                <span className="text-sm text-[#A7B1C6]">savings</span>
              </div>
            </div>
          ))}
        </div>

        {/* Stats */}
        <div 
          ref={statsRef}
          className="flex justify-center gap-8 md:gap-16 flex-wrap"
        >
          <div className="text-center">
            <div className="text-4xl font-bold text-[#4B6BFF] mb-1">8+</div>
            <div className="text-sm text-[#A7B1C6]">AI Platforms</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-[#4B6BFF] mb-1">6-8×</div>
            <div className="text-sm text-[#A7B1C6]">Token Savings</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-[#4B6BFF] mb-1">1</div>
            <div className="text-sm text-[#A7B1C6]">MCP Server</div>
          </div>
        </div>
      </div>
    </section>
  );
}
