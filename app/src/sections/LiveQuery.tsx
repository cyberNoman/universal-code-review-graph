import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export default function LiveQuery() {
  const sectionRef = useRef<HTMLElement>(null);
  const codeCardRef = useRef<HTMLDivElement>(null);
  const terminalCardRef = useRef<HTMLDivElement>(null);
  const connectorRef = useRef<HTMLDivElement>(null);
  const captionRef = useRef<HTMLParagraphElement>(null);
  const codeLinesRef = useRef<(HTMLDivElement | null)[]>([]);
  const terminalLinesRef = useRef<(HTMLDivElement | null)[]>([]);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const ctx = gsap.context(() => {
      const codeLines = codeLinesRef.current.filter(Boolean);
      const terminalLines = terminalLinesRef.current.filter(Boolean);

      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=140%',
          pin: true,
          scrub: 0.6,
        }
      });

      // ENTRANCE (0-30%)
      scrollTl
        .fromTo(codeCardRef.current,
          { x: '-50vw', opacity: 0 },
          { x: 0, opacity: 1, ease: 'power2.out' },
          0
        )
        .fromTo(terminalCardRef.current,
          { x: '50vw', opacity: 0 },
          { x: 0, opacity: 1, ease: 'power2.out' },
          0.08
        )
        .fromTo(connectorRef.current,
          { scaleX: 0 },
          { scaleX: 1, ease: 'power2.out' },
          0.15
        )
        .fromTo(codeLines,
          { opacity: 0, y: 10 },
          { opacity: 1, y: 0, stagger: 0.015, ease: 'power2.out' },
          0.12
        )
        .fromTo(terminalLines,
          { opacity: 0, y: 10 },
          { opacity: 1, y: 0, stagger: 0.012, ease: 'power2.out' },
          0.18
        )
        .fromTo(captionRef.current,
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, ease: 'power2.out' },
          0.25
        );

      // SETTLE (30-70%): Hold

      // EXIT (70-100%)
      scrollTl
        .fromTo([codeCardRef.current, terminalCardRef.current],
          { y: 0, opacity: 1 },
          { y: '-18vh', opacity: 0, stagger: 0.02, ease: 'power2.in' },
          0.7
        )
        .fromTo(connectorRef.current,
          { opacity: 1 },
          { opacity: 0, ease: 'power2.in' },
          0.75
        )
        .fromTo(captionRef.current,
          { opacity: 1 },
          { opacity: 0, ease: 'power2.in' },
          0.78
        );

    }, section);

    return () => ctx.revert();
  }, []);

  const codeContent = [
    { text: '# Ask the graph for impacted symbols', class: 'comment' },
    { text: 'review = graph.review([', class: 'default' },
    { text: '    "src/engine/parser.py",', class: 'string' },
    { text: '    "src/engine/graph.py"', class: 'string' },
    { text: '])', class: 'default' },
    { text: 'print(review.impacted)', class: 'default' },
  ];

  const terminalContent = [
    { text: 'Impacted (7)', class: 'header' },
    { text: '─────────────', class: 'divider' },
    { text: 'parse_source()', class: 'function' },
    { text: 'build_call_graph()', class: 'function' },
    { text: 'resolve_imports()', class: 'function' },
    { text: 'get_neighbors()', class: 'function' },
    { text: 'to_json()', class: 'function' },
    { text: 'export_dot()', class: 'function' },
    { text: 'validate_graph()', class: 'function cursor-blink' },
  ];

  return (
    <section 
      ref={sectionRef} 
      className="section-pinned bg-[#0B0F17] z-30 flex items-center justify-center"
    >
      {/* Code Card */}
      <div 
        ref={codeCardRef}
        className="blueprint-card absolute left-[6vw] top-[16vh] w-[40vw] h-[68vh] p-6 flex flex-col"
      >
        <span className="mono text-xs text-[#4B6BFF] tracking-[0.12em] uppercase mb-6">
          Query
        </span>
        <div className="flex-1 font-mono text-sm leading-relaxed overflow-hidden">
          {codeContent.map((line, i) => (
            <div 
              key={i}
              ref={el => { codeLinesRef.current[i] = el; }}
              className={`
                ${line.class === 'comment' ? 'text-[#8b949e]' : ''}
                ${line.class === 'string' ? 'text-[#a5d6ff]' : ''}
                ${line.class === 'default' ? 'text-[#F2F5FA]' : ''}
              `}
            >
              {line.text}
            </div>
          ))}
        </div>
      </div>

      {/* Connector line */}
      <div 
        ref={connectorRef}
        className="absolute left-[46vw] top-[50vh] w-[8vw] h-px accent-line"
        style={{ transformOrigin: 'left' }}
      />

      {/* Terminal Card */}
      <div 
        ref={terminalCardRef}
        className="blueprint-card absolute left-[54vw] top-[16vh] w-[40vw] h-[68vh] p-6 flex flex-col"
      >
        <span className="mono text-xs text-[#4B6BFF] tracking-[0.12em] uppercase mb-6">
          Result
        </span>
        <div className="flex-1 font-mono text-sm leading-relaxed overflow-hidden">
          {terminalContent.map((line, i) => (
            <div 
              key={i}
              ref={el => { terminalLinesRef.current[i] = el; }}
              className={`
                ${line.class === 'header' ? 'text-[#F2F5FA] font-semibold' : ''}
                ${line.class === 'divider' ? 'text-[#A7B1C6]' : ''}
                ${line.class === 'function' ? 'text-[#7ee787]' : ''}
                ${line.class === 'function cursor-blink' ? 'text-[#7ee787]' : ''}
              `}
            >
              {line.text}
            </div>
          ))}
        </div>
      </div>

      {/* Caption */}
      <p 
        ref={captionRef}
        className="absolute bottom-[6vh] left-1/2 -translate-x-1/2 text-[#A7B1C6] text-lg text-center"
      >
        No guessing. No noise. Just the blast radius.
      </p>
    </section>
  );
}
