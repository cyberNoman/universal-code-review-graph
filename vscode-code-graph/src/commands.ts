import * as vscode from 'vscode';
import { MCPServerManager } from './mcpServer';
import { CodeGraphProvider } from './codeGraphProvider';

export class CodeGraphCommands {
    constructor(
        private context: vscode.ExtensionContext,
        private mcpServer: MCPServerManager,
        private graphProvider: CodeGraphProvider
    ) {}

    async buildGraph(repoPath?: string): Promise<void> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        const targetPath = repoPath || workspaceFolders[0].uri.fsPath;
        const config = vscode.workspace.getConfiguration('codeGraph');
        const excludePatterns = config.get('excludePatterns') as string[];

        // Show progress
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Building code graph...',
            cancellable: false
        }, async (progress) => {
            try {
                progress.report({ increment: 0, message: 'Parsing source files...' });
                
                const result = await this.mcpServer.buildGraph(targetPath, {
                    excludePatterns
                });

                if (result.status === 'success') {
                    vscode.window.showInformationMessage(
                        `Graph built! ${result.stats.files_processed} files, ${result.stats.symbols_found} symbols, ${result.stats.edges_found} edges.`
                    );
                    
                    // Show the graph explorer
                    vscode.commands.executeCommand('setContext', 'codeGraphHasData', true);
                    vscode.commands.executeCommand('setContext', 'workspaceHasCodeGraph', true);
                    
                    // Ask if user wants to copy MCP config
                    const copyConfig = await vscode.window.showInformationMessage(
                        'Graph built! Copy MCP config for your AI assistant?',
                        'Copy Config',
                        'Dismiss'
                    );
                    
                    if (copyConfig === 'Copy Config') {
                        await this.copyMCPConfig();
                    }
                } else {
                    vscode.window.showErrorMessage('Failed to build graph: ' + result.message);
                }
            } catch (error: any) {
                vscode.window.showErrorMessage('Error building graph: ' + error.message);
            }
        });
    }

    async reviewChanges(): Promise<void> {
        if (!this.graphProvider.isGraphBuilt()) {
            const build = await vscode.window.showWarningMessage(
                'No graph built yet. Build it first?',
                'Build Graph',
                'Cancel'
            );
            if (build === 'Build Graph') {
                await this.buildGraph();
            }
            return;
        }

        // Get changed files from git
        const changedFiles = await this.getChangedFiles();
        if (changedFiles.length === 0) {
            vscode.window.showInformationMessage('No changed files detected');
            return;
        }

        // Let user select files
        const selectedFiles = await vscode.window.showQuickPick(
            changedFiles.map(f => ({ label: f, picked: true })),
            {
                canPickMany: true,
                placeHolder: 'Select files to review'
            }
        );

        if (!selectedFiles || selectedFiles.length === 0) {
            return;
        }

        const config = vscode.workspace.getConfiguration('codeGraph');
        
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Analyzing changes...',
            cancellable: false
        }, async () => {
            try {
                const result = await this.mcpServer.reviewChanges(
                    selectedFiles.map(f => f.label),
                    {
                        includeUpstream: config.get('includeUpstream', true),
                        includeDownstream: config.get('includeDownstream', true),
                        maxDepth: config.get('maxDepth', 3)
                    }
                );

                // Show results in a webview panel
                this.showReviewResults(result);
            } catch (error: any) {
                vscode.window.showErrorMessage('Error reviewing changes: ' + error.message);
            }
        });
    }

    async getImpact(symbol: string): Promise<void> {
        if (!this.graphProvider.isGraphBuilt()) {
            vscode.window.showWarningMessage('Build the graph first!');
            return;
        }

        const config = vscode.workspace.getConfiguration('codeGraph');
        
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `Analyzing impact of ${symbol}...`,
            cancellable: false
        }, async () => {
            try {
                const result = await this.mcpServer.getImpact(
                    symbol,
                    config.get('maxDepth', 5)
                );

                // Show results
                const panel = vscode.window.createWebviewPanel(
                    'codeGraphImpact',
                    `Impact: ${symbol}`,
                    vscode.ViewColumn.One,
                    {}
                );

                panel.webview.html = this.getImpactHtml(result);
            } catch (error: any) {
                vscode.window.showErrorMessage('Error getting impact: ' + error.message);
            }
        });
    }

    async findPaths(): Promise<void> {
        if (!this.graphProvider.isGraphBuilt()) {
            vscode.window.showWarningMessage('Build the graph first!');
            return;
        }

        const source = await vscode.window.showInputBox({
            prompt: 'Enter source symbol',
            placeHolder: 'e.g., main'
        });

        if (!source) return;

        const target = await vscode.window.showInputBox({
            prompt: 'Enter target symbol',
            placeHolder: 'e.g., validate_graph'
        });

        if (!target) return;

        vscode.window.showInformationMessage(`Finding paths from ${source} to ${target}...`);
        // Implementation would call mcpServer.findPaths
    }

    async searchSymbols(): Promise<void> {
        if (!this.graphProvider.isGraphBuilt()) {
            vscode.window.showWarningMessage('Build the graph first!');
            return;
        }

        const query = await vscode.window.showInputBox({
            prompt: 'Search for symbols',
            placeHolder: 'e.g., parse* or *handler'
        });

        if (!query) return;

        const result = await this.mcpServer.searchSymbols(query, { limit: 20 });
        
        if (result.symbols && result.symbols.length > 0) {
            const selected = await vscode.window.showQuickPick(
                result.symbols.map((s: any) => ({
                    label: s.name,
                    description: `${s.symbol_type} - ${s.file_path}:${s.line_start}`,
                    symbol: s
                })),
                { placeHolder: 'Select a symbol' }
            );

            if (selected) {
                const uri = vscode.Uri.file(selected.symbol.file_path);
                const doc = await vscode.workspace.openTextDocument(uri);
                const editor = await vscode.window.showTextDocument(doc);
                const position = new vscode.Position(selected.symbol.line_start - 1, 0);
                editor.selection = new vscode.Selection(position, position);
                editor.revealRange(new vscode.Range(position, position));
            }
        } else {
            vscode.window.showInformationMessage('No symbols found');
        }
    }

    async exportGraph(): Promise<void> {
        if (!this.graphProvider.isGraphBuilt()) {
            vscode.window.showWarningMessage('Build the graph first!');
            return;
        }

        const format = await vscode.window.showQuickPick(
            ['JSON', 'DOT (Graphviz)', 'Summary'],
            { placeHolder: 'Select export format' }
        );

        if (!format) return;

        const formatMap: { [key: string]: string } = {
            'JSON': 'json',
            'DOT (Graphviz)': 'dot',
            'Summary': 'summary'
        };

        // Implementation would call mcpServer.exportGraph
        vscode.window.showInformationMessage(`Exporting graph as ${format}...`);
    }

    async viewStats(): Promise<void> {
        const stats = this.graphProvider.getStats();
        if (!stats) {
            vscode.window.showWarningMessage('No graph data available');
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'codeGraphStats',
            'Code Graph Statistics',
            vscode.ViewColumn.One,
            {}
        );

        panel.webview.html = this.getStatsHtml(stats);
    }

    async copyMCPConfig(): Promise<void> {
        const config = vscode.workspace.getConfiguration('codeGraph');
        const aiAssistant = config.get('aiAssistant') as string;

        const configs: { [key: string]: any } = {
            kimi: {
                mcpServers: {
                    'code-graph': {
                        command: 'python3',
                        args: ['${workspaceFolder}/.code_graph/server.py']
                    }
                }
            },
            claude: {
                mcpServers: {
                    'code-graph': {
                        command: 'python3',
                        args: ['${workspaceFolder}/.code_graph/server.py']
                    }
                }
            },
            cursor: {
                servers: {
                    'code-graph': {
                        command: 'python3',
                        args: ['${workspaceFolder}/.code_graph/server.py'],
                        type: 'stdio'
                    }
                }
            },
            windsurf: {
                mcpServers: {
                    'code-graph': {
                        command: 'python3',
                        args: ['${workspaceFolder}/.code_graph/server.py'],
                        type: 'stdio'
                    }
                }
            }
        };

        const mcpConfig = configs[aiAssistant] || configs.kimi;
        const configJson = JSON.stringify(mcpConfig, null, 2);

        await vscode.env.clipboard.writeText(configJson);
        vscode.window.showInformationMessage(
            `MCP config for ${aiAssistant} copied to clipboard! Paste it into your AI assistant's MCP settings.`
        );
    }

    private async getChangedFiles(): Promise<string[]> {
        // Simple implementation - in real extension, use git API
        const { exec } = require('child_process');
        const util = require('util');
        const execAsync = util.promisify(exec);

        try {
            const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
            if (!workspacePath) return [];

            const { stdout } = await execAsync(
                'git diff --name-only HEAD',
                { cwd: workspacePath }
            );

            return stdout.trim().split('\n').filter((f: string) => f);
        } catch {
            return [];
        }
    }

    private showReviewResults(result: any): void {
        const panel = vscode.window.createWebviewPanel(
            'codeGraphReview',
            'Code Review Results',
            vscode.ViewColumn.One,
            {}
        );

        panel.webview.html = `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        h1 { color: var(--vscode-foreground); }
        .stat { margin: 10px 0; padding: 10px; background: var(--vscode-editor-inactiveSelectionBackground); border-radius: 4px; }
        .symbol { padding: 5px 10px; margin: 5px 0; background: var(--vscode-list-hoverBackground); border-radius: 3px; }
        .upstream { border-left: 3px solid #4B6BFF; }
        .downstream { border-left: 3px solid #7ee787; }
    </style>
</head>
<body>
    <h1>🔍 Code Review Impact</h1>
    
    <div class="stat">
        <strong>Changed Files:</strong> ${result.changed_files?.length || 0}
    </div>
    
    <div class="stat">
        <strong>Total Impacted:</strong> ${result.total_impacted || 0} symbols
    </div>
    
    <div class="stat">
        <strong>Upstream:</strong> ${result.upstream_count || 0} 
        <strong>Downstream:</strong> ${result.downstream_count || 0}
    </div>

    <h2>Impacted Symbols</h2>
    ${result.impacted_symbols?.map((s: string) => `
        <div class="symbol">${s}</div>
    `).join('') || '<p>No symbols impacted</p>'}

    <h2>Files to Review</h2>
    ${result.files_to_review?.map((f: string) => `
        <div class="symbol">${f}</div>
    `).join('') || '<p>No additional files</p>'}
</body>
</html>`;
    }

    private getImpactHtml(result: any): string {
        return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        h1 { color: var(--vscode-foreground); }
        .section { margin: 20px 0; }
        .symbol { padding: 5px 10px; margin: 3px 0; background: var(--vscode-list-hoverBackground); border-radius: 3px; }
    </style>
</head>
<body>
    <h1>📊 Impact Analysis: ${result.symbol}</h1>
    
    <div class="section">
        <h2>Upstream (${result.upstream_count})</h2>
        <p>Functions that call <strong>${result.symbol}</strong>:</p>
        ${result.upstream?.map((s: string) => `
            <div class="symbol">${s}</div>
        `).join('') || '<p>No upstream dependencies</p>'}
    </div>
    
    <div class="section">
        <h2>Downstream (${result.downstream_count})</h2>
        <p>Functions called by <strong>${result.symbol}</strong>:</p>
        ${result.downstream?.map((s: string) => `
            <div class="symbol">${s}</div>
        `).join('') || '<p>No downstream dependencies</p>'}
    </div>
</body>
</html>`;
    }

    private getStatsHtml(stats: any): string {
        return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        h1 { color: var(--vscode-foreground); }
        .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }
        .stat-card { padding: 20px; background: var(--vscode-editor-inactiveSelectionBackground); border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #4B6BFF; }
        .stat-label { color: var(--vscode-descriptionForeground); margin-top: 5px; }
    </style>
</head>
<body>
    <h1>📈 Code Graph Statistics</h1>
    
    <div class="stat-grid">
        <div class="stat-card">
            <div class="stat-number">${stats.total_symbols}</div>
            <div class="stat-label">Total Symbols</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.total_edges}</div>
            <div class="stat-label">Call Edges</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.files_indexed}</div>
            <div class="stat-label">Files Indexed</div>
        </div>
    </div>

    <h2>Symbol Types</h2>
    ${stats.symbol_types ? Object.entries(stats.symbol_types).map(([type, count]) => `
        <div style="margin: 10px 0;">
            <strong>${type}:</strong> ${count}
        </div>
    `).join('') : '<p>No type data available</p>'}
</body>
</html>`;
    }
}
