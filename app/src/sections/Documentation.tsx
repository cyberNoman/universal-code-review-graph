import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowRight, Terminal, Search, GitBranch, Map, BarChart2, FileCode, Download, Zap } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const tools = [
  {
    name: 'build_graph',
    params: '(repo_path)',
    badge: 'run once',
    badgeColor: 'bg-[#4B6BFF]/20 text-[#4B6BFF]',
    description: 'Parse every source file, build the call graph, and persist it to .code_graph.db. Survives server restarts — you never re-index unless you want to.',
    icon: Terminal
  },
  {
    name: 'review_changes',
    params: '(changed_files[])',
    badge: '6–8× token savings',
    badgeColor: 'bg-[#7ee787]/20 text-[#7ee787]',
    description: 'The core feature. Given a list of changed files, returns the exact blast radius — the minimal set of symbols and files your AI needs to read.',
    icon: Zap
  },
  {
    name: 'get_impact',
    params: '(symbol)',
    badge: 'refactoring',
    badgeColor: 'bg-[#e3b341]/20 text-[#e3b341]',
    description: 'Find every function that calls a symbol (upstream) and every function it calls (downstream). Know your blast radius before you change anything.',
    icon: GitBranch
  },
  {
    name: 'find_paths',
    params: '(source, target)',
    badge: 'debugging',
    badgeColor: 'bg-[#f78166]/20 text-[#f78166]',
    description: 'Trace all call chains between two symbols. Useful for understanding how a high-level entry point eventually reaches a low-level function.',
    icon: Map
  },
  {
    name: 'search_symbols',
    params: '(query)',
    badge: 'exploration',
    badgeColor: 'bg-[#4B6BFF]/20 text-[#4B6BFF]',
    description: 'Find symbols by name or wildcard pattern (parse*, *handler, User*). Supports filtering by type: function, class, method.',
    icon: Search
  },
  {
    name: 'get_symbol_details',
    params: '(symbol)',
    badge: 'deep dive',
    badgeColor: 'bg-[#A7B1C6]/20 text-[#A7B1C6]',
    description: 'Get the exact file, line, callers, and callees for any symbol. The fastest way to understand a function without reading its file.',
    icon: FileCode
  },
  {
    name: 'export_graph',
    params: '(format)',
    badge: 'json · dot · summary',
    badgeColor: 'bg-[#A7B1C6]/20 text-[#A7B1C6]',
    description: 'Export the full graph as JSON, Graphviz DOT, or a summary. Use JSON for custom tooling, DOT for visualization.',
    icon: Download
  },
  {
    name: 'get_stats',
    params: '()',
    badge: 'health check',
    badgeColor: 'bg-[#A7B1C6]/20 text-[#A7B1C6]',
    description: 'Symbol counts by type, total edges, most-connected nodes. Highly connected nodes are your highest-risk change points.',
    icon: BarChart2
  },
];

const navItems = [
  { label: 'Quickstart', id: 'quickstart' },
  { label: 'How it works', id: 'how-it-works' },
  { label: '9 tools', id: 'tools' },
  { label: 'AI configs', id: 'ai-configs' },
];

const aiConfigs = [
  {
    name: 'Claude Code',
    code: `claude mcp add code-graph \\
  python3 /path/to/universal-code-graph/server.py`,
  },
  {
    name: 'Cursor',
    code: `// ~/.cursor/mcp.json
{
  "servers": {
    "code-graph": {
      "command": "python3",
      "args": ["/path/to/server.py"],
      "type": "stdio"
    }
  }
}`,
  },
  {
    name: 'Kimi / Qwen / ChatGPT / Windsurf',
    code: `{
  "mcpServers": {
    "code-graph": {
      "command": "python3",
      "args": ["/path/to/server.py"]
    }
  }
}`,
  },
];

export default function Documentation() {
  const sectionRef = useRef<HTMLElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const quickstartRef = useRef<HTMLDivElement>(null);
  const toolRefs = useRef<(HTMLDivElement | null)[]>([]);
  const configRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(headerRef.current,
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out',
          scrollTrigger: { trigger: headerRef.current, start: 'top 80%' } }
      );

      gsap.fromTo(quickstartRef.current,
        { opacity: 0, y: 24, scale: 0.98 },
        { opacity: 1, y: 0, scale: 1, duration: 0.7, ease: 'power2.out',
          scrollTrigger: { trigger: quickstartRef.current, start: 'top 80%' } }
      );

      toolRefs.current.filter(Boolean).forEach((card, i) => {
        gsap.fromTo(card,
          { opacity: 0, y: 24 },
          { opacity: 1, y: 0, duration: 0.6, delay: i * 0.07, ease: 'power2.out',
            scrollTrigger: { trigger: card, start: 'top 88%' } }
        );
      });

      gsap.fromTo(configRef.current,
        { opacity: 0, y: 24 },
        { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out',
          scrollTrigger: { trigger: configRef.current, start: 'top 80%' } }
      );
    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} className="relative bg-[#0B0F17] z-50 py-20 min-h-screen">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 flex gap-12">

        {/* Sticky left nav */}
        <nav className="hidden lg:block w-56 flex-shrink-0">
          <div className="sticky top-24">
            <span className="mono text-xs text-[#A7B1C6] tracking-[0.12em] uppercase mb-6 block">
              Documentation
            </span>
            <ul className="space-y-3">
              {navItems.map((item) => (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    className="text-[#A7B1C6] hover:text-[#F2F5FA] text-sm transition-colors block py-1"
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </nav>

        {/* Main content */}
        <div className="flex-1 max-w-3xl">

          {/* Header */}
          <div ref={headerRef} className="mb-12">
            <h2 className="text-[clamp(32px,3.5vw,48px)] font-semibold text-[#F2F5FA] mb-4">
              Documentation
            </h2>
            <p className="text-[#A7B1C6] text-lg">
              One MCP server. Any AI. Production-ready in 5 minutes.
            </p>
          </div>

          {/* Quickstart */}
          <div ref={quickstartRef} id="quickstart" className="mb-16">
            <h3 className="text-2xl font-semibold text-[#F2F5FA] mb-2">Quickstart</h3>
            <p className="text-[#A7B1C6] mb-6">
              Install the server, connect your AI, build the graph once.
            </p>
            <div className="code-block rounded-sm mb-4">
              <code className="text-sm">
                <span className="text-[#8b949e]"># 1. Clone and install</span><br />
                <span className="text-[#F2F5FA]">git clone https://github.com/cyberNoman/universal-code-review-graph</span><br />
                <span className="text-[#F2F5FA]">cd universal-code-review-graph/universal-code-graph</span><br />
                <span className="text-[#F2F5FA]">pip install -r requirements.txt</span><br />
                <br />
                <span className="text-[#8b949e]"># 2. Add to Claude Code</span><br />
                <span className="text-[#F2F5FA]">claude mcp add code-graph python3 $(pwd)/server.py</span><br />
                <br />
                <span className="text-[#8b949e]"># 3. Tell your AI to build the graph</span><br />
                <span className="text-[#7ee787]">"Build the code graph for /path/to/my-project"</span>
              </code>
            </div>
            <p className="text-[#A7B1C6] text-sm">
              The graph is saved to <code className="text-[#7ee787]">.code_graph.db</code> and reloads automatically on restart.
              You only rebuild when you add new files.
            </p>
          </div>

          {/* How it works */}
          <div id="how-it-works" className="mb-16">
            <h3 className="text-2xl font-semibold text-[#F2F5FA] mb-4">How it works</h3>
            <div className="grid grid-cols-1 gap-3">
              {[
                { step: '01', title: 'Parse', desc: 'Tree-sitter reads every source file and builds a concrete syntax tree — no LSP, no runtime needed.' },
                { step: '02', title: 'Index', desc: 'Functions, classes, and methods are extracted as Symbol objects with file + line metadata.' },
                { step: '03', title: 'Graph', desc: 'Call relationships are stored as directed edges in a NetworkX DiGraph. Persisted to SQLite.' },
                { step: '04', title: 'Query', desc: 'Your AI calls review_changes() — gets back 4 files instead of 40. 6–8× fewer tokens. Better answers.' },
              ].map((item) => (
                <div key={item.step} className="blueprint-card p-5 flex gap-5 items-start">
                  <span className="text-[#4B6BFF] font-mono text-sm font-bold flex-shrink-0 mt-0.5">{item.step}</span>
                  <div>
                    <p className="text-[#F2F5FA] font-medium mb-1">{item.title}</p>
                    <p className="text-[#A7B1C6] text-sm">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 9 Tools */}
          <div id="tools" className="mb-16">
            <h3 className="text-2xl font-semibold text-[#F2F5FA] mb-2">9 MCP tools</h3>
            <p className="text-[#A7B1C6] mb-6">
              Your AI gets these tools automatically once the server is connected.
            </p>
            <div className="grid gap-3">
              {tools.map((tool, index) => {
                const Icon = tool.icon;
                return (
                  <div
                    key={tool.name}
                    ref={el => { toolRefs.current[index] = el; }}
                    className="blueprint-card p-5 hover:border-[#4B6BFF]/50 transition-colors"
                  >
                    <div className="flex items-start gap-4">
                      <div className="w-9 h-9 rounded-md bg-[#4B6BFF]/10 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-4 h-4 text-[#4B6BFF]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center flex-wrap gap-2 mb-1.5">
                          <code className="text-[#7ee787] font-mono text-sm">{tool.name}</code>
                          <code className="text-[#A7B1C6] font-mono text-xs">{tool.params}</code>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${tool.badgeColor}`}>
                            {tool.badge}
                          </span>
                        </div>
                        <p className="text-[#A7B1C6] text-sm leading-relaxed">{tool.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* AI Configs */}
          <div ref={configRef} id="ai-configs" className="mb-16">
            <h3 className="text-2xl font-semibold text-[#F2F5FA] mb-2">Connect your AI</h3>
            <p className="text-[#A7B1C6] mb-6">
              Add one config block — works with any MCP-compatible client.
            </p>
            <div className="grid gap-4">
              {aiConfigs.map((cfg) => (
                <div key={cfg.name} className="blueprint-card p-5">
                  <p className="text-[#F2F5FA] text-sm font-medium mb-3">{cfg.name}</p>
                  <div className="code-block rounded-sm">
                    <code className="text-sm whitespace-pre text-[#F2F5FA]">{cfg.code}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Link to full docs */}
          <a
            href="https://github.com/cyberNoman/universal-code-review-graph/tree/main/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-[#4B6BFF] hover:text-[#3d5ce6] transition-colors"
          >
            <span className="font-medium">Full documentation on GitHub</span>
            <ArrowRight className="w-4 h-4" />
          </a>

        </div>
      </div>
    </section>
  );
}
