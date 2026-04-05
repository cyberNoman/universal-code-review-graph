import * as vscode from 'vscode';
import { CodeGraphProvider } from './codeGraphProvider';
import { CodeGraphCommands } from './commands';
import { MCPServerManager } from './mcpServer';

let mcpServer: MCPServerManager;
let graphProvider: CodeGraphProvider;
let commands: CodeGraphCommands;

export function activate(context: vscode.ExtensionContext) {
    console.log('Universal Code Graph extension is now active!');

    // Initialize MCP server manager
    mcpServer = new MCPServerManager(context);

    // Initialize tree view provider
    graphProvider = new CodeGraphProvider(context, mcpServer);
    vscode.window.registerTreeDataProvider('codeGraphExplorer', graphProvider);

    // Initialize commands
    commands = new CodeGraphCommands(context, mcpServer, graphProvider);

    // Register all commands
    const disposables = [
        // Build graph command
        vscode.commands.registerCommand('codeGraph.buildGraph', async () => {
            await commands.buildGraph();
        }),

        // Review changes command
        vscode.commands.registerCommand('codeGraph.reviewChanges', async () => {
            await commands.reviewChanges();
        }),

        // Get impact command
        vscode.commands.registerCommand('codeGraph.getImpact', async (item?: any) => {
            const symbol = item?.label || await vscode.window.showInputBox({
                prompt: 'Enter symbol name',
                placeHolder: 'e.g., parse_source'
            });
            if (symbol) {
                await commands.getImpact(symbol);
            }
        }),

        // Find paths command
        vscode.commands.registerCommand('codeGraph.findPaths', async () => {
            await commands.findPaths();
        }),

        // Search symbols command
        vscode.commands.registerCommand('codeGraph.searchSymbols', async () => {
            await commands.searchSymbols();
        }),

        // Export graph command
        vscode.commands.registerCommand('codeGraph.exportGraph', async () => {
            await commands.exportGraph();
        }),

        // View stats command
        vscode.commands.registerCommand('codeGraph.viewStats', async () => {
            await commands.viewStats();
        }),

        // Refresh command
        vscode.commands.registerCommand('codeGraph.refresh', () => {
            graphProvider.refresh();
            vscode.window.showInformationMessage('Code Graph refreshed!');
        }),

        // Open symbol command
        vscode.commands.registerCommand('codeGraph.openSymbol', async (item: any) => {
            if (item?.filePath && item?.lineStart) {
                const uri = vscode.Uri.file(item.filePath);
                const doc = await vscode.workspace.openTextDocument(uri);
                const editor = await vscode.window.showTextDocument(doc);
                const position = new vscode.Position(item.lineStart - 1, 0);
                editor.selection = new vscode.Selection(position, position);
                editor.revealRange(new vscode.Range(position, position));
            }
        }),

        // Copy MCP config command
        vscode.commands.registerCommand('codeGraph.copyMCPConfig', async () => {
            await commands.copyMCPConfig();
        }),

        // Status bar item
        createStatusBarItem()
    ];

    context.subscriptions.push(...disposables);

    // Auto-build if enabled
    const config = vscode.workspace.getConfiguration('codeGraph');
    if (config.get('autoBuild')) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders && workspaceFolders.length > 0) {
            setTimeout(() => {
                commands.buildGraph(workspaceFolders[0].uri.fsPath);
            }, 3000);
        }
    }

    // Show welcome message
    showWelcomeMessage();
}

function createStatusBarItem(): vscode.Disposable {
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left,
        100
    );
    statusBarItem.text = "$(graph) Code Graph";
    statusBarItem.tooltip = "Universal Code Review Graph - Click to build";
    statusBarItem.command = 'codeGraph.buildGraph';
    statusBarItem.show();
    
    return statusBarItem;
}

async function showWelcomeMessage() {
    const result = await vscode.window.showInformationMessage(
        'Universal Code Graph is ready! Build your first graph?',
        'Build Graph',
        'Copy MCP Config',
        'Dismiss'
    );

    if (result === 'Build Graph') {
        vscode.commands.executeCommand('codeGraph.buildGraph');
    } else if (result === 'Copy MCP Config') {
        vscode.commands.executeCommand('codeGraph.copyMCPConfig');
    }
}

export function deactivate() {
    if (mcpServer) {
        mcpServer.stop();
    }
    console.log('Universal Code Graph extension is now deactivated.');
}
