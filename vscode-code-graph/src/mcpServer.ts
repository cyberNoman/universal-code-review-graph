/**
 * MCPServerManager
 *
 * Bridges the VS Code extension to the Python code_graph backend.
 * All arguments are passed via --args-json (JSON string) to a dedicated
 * run_tool.py helper script — never via string interpolation into -c strings,
 * which would be a command-injection vulnerability.
 */

import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

interface GraphUpdateCallback {
    (data: { symbols: any[]; stats: any }): void;
}

export class MCPServerManager {
    private graphUpdateCallbacks: GraphUpdateCallback[] = [];
    private outputChannel: vscode.OutputChannel;

    constructor(private context: vscode.ExtensionContext) {
        this.outputChannel = vscode.window.createOutputChannel('Universal Code Graph');
    }

    onGraphUpdated(callback: GraphUpdateCallback) {
        this.graphUpdateCallbacks.push(callback);
    }

    private notifyGraphUpdated(data: { symbols: any[]; stats: any }) {
        this.graphUpdateCallbacks.forEach(cb => cb(data));
    }

    showOutput() {
        this.outputChannel.show();
    }

    // ─────────────────────────────────────────────────────────────
    // Core: safe subprocess call via run_tool.py
    // ─────────────────────────────────────────────────────────────

    /**
     * Runs run_tool.py with --tool <name> --args-json <json>.
     * Arguments are NEVER interpolated into a shell string — they are
     * passed as discrete argv elements, so special characters cannot
     * escape into shell commands.
     */
    private async runTool(toolName: string, args: Record<string, unknown>): Promise<any> {
        const scriptPath = this.getRunToolPath();
        if (!scriptPath) {
            throw new Error(
                'run_tool.py not found. Please reinstall the extension.\n' +
                'Expected location: <extension>/server/run_tool.py'
            );
        }

        const argsJson = JSON.stringify(args);
        this.outputChannel.appendLine(`[run_tool] ${toolName} — args: ${argsJson}`);

        return new Promise((resolve, reject) => {
            // Safe: arguments are array elements, not a shell string
            const proc: ChildProcess = spawn('python3', [
                scriptPath,
                '--tool', toolName,
                '--args-json', argsJson,
            ], {
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                stdio: ['ignore', 'pipe', 'pipe'],
            });

            let stdout = '';
            let stderr = '';

            proc.stdout?.on('data', (chunk: Buffer) => { stdout += chunk.toString(); });
            proc.stderr?.on('data', (chunk: Buffer) => {
                const text = chunk.toString();
                stderr += text;
                this.outputChannel.append(text);
            });

            const timeout = setTimeout(() => {
                proc.kill();
                reject(new Error(`Tool '${toolName}' timed out after 120s`));
            }, 120_000);

            proc.on('close', (code) => {
                clearTimeout(timeout);
                const lastLine = stdout.trim().split('\n').pop() || '';
                try {
                    const result = JSON.parse(lastLine);
                    if (result?.error) {
                        reject(new Error(result.error));
                    } else {
                        resolve(result);
                    }
                } catch {
                    reject(new Error(
                        `run_tool.py (${toolName}) returned non-JSON output.\n` +
                        `stdout: ${stdout}\nstderr: ${stderr}`
                    ));
                }
            });

            proc.on('error', (err) => {
                clearTimeout(timeout);
                reject(new Error(`Failed to start Python: ${err.message}\nMake sure python3 is on your PATH.`));
            });
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Public tool wrappers
    // ─────────────────────────────────────────────────────────────

    async buildGraph(repoPath: string, options: { excludePatterns?: string[] } = {}): Promise<any> {
        const result = await this.runTool('build_graph', {
            repo_path: repoPath,
            exclude_patterns: options.excludePatterns ?? [],
        });

        // Notify sidebar
        if (result?.symbols && result?.graph_stats) {
            this.notifyGraphUpdated({
                symbols: result.symbols,
                stats: result.graph_stats,
            });
        }

        return result;
    }

    async reviewChanges(
        changedFiles: string[],
        options: { includeUpstream?: boolean; includeDownstream?: boolean; maxDepth?: number } = {},
        repoPath?: string
    ): Promise<any> {
        const workspacePath = repoPath ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!workspacePath) throw new Error('No workspace open');

        return this.runTool('review_changes', {
            repo_path: workspacePath,
            changed_files: changedFiles,
            include_upstream: options.includeUpstream ?? true,
            include_downstream: options.includeDownstream ?? true,
            max_depth: options.maxDepth ?? 3,
        });
    }

    async getImpact(symbol: string, maxDepth: number = 5, repoPath?: string): Promise<any> {
        const workspacePath = repoPath ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!workspacePath) throw new Error('No workspace open');

        return this.runTool('get_impact', {
            repo_path: workspacePath,
            symbol,
            max_depth: maxDepth,
        });
    }

    async searchSymbols(
        query: string,
        options: { symbolType?: string; limit?: number } = {},
        repoPath?: string
    ): Promise<any> {
        const workspacePath = repoPath ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!workspacePath) throw new Error('No workspace open');

        return this.runTool('search_symbols', {
            repo_path: workspacePath,
            query,
            symbol_type: options.symbolType ?? 'any',
            limit: options.limit ?? 20,
        });
    }

    async getStats(repoPath?: string): Promise<any> {
        const workspacePath = repoPath ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!workspacePath) throw new Error('No workspace open');

        return this.runTool('get_stats', { repo_path: workspacePath });
    }

    // ─────────────────────────────────────────────────────────────
    // Path resolution
    // ─────────────────────────────────────────────────────────────

    private getRunToolPath(): string | null {
        const candidates = [
            path.join(this.context.extensionPath, 'server', 'run_tool.py'),
            path.join(this.context.extensionPath, 'run_tool.py'),
        ];
        for (const p of candidates) {
            if (fs.existsSync(p)) return p;
        }
        return null;
    }

    /** Path to server.py for users who want the standalone MCP server. */
    getServerScriptPath(): string | null {
        const candidates = [
            path.join(this.context.extensionPath, 'server', 'server.py'),
            path.join(this.context.extensionPath, 'server.py'),
        ];
        for (const p of candidates) {
            if (fs.existsSync(p)) return p;
        }
        return null;
    }

    /** Stub — kept for API compatibility; the new design doesn't use a persistent process. */
    stop() {
        // No-op: we no longer keep a persistent Python process running
    }
}
