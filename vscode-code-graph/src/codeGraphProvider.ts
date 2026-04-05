import * as vscode from 'vscode';
import { MCPServerManager } from './mcpServer';

export class SymbolItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly symbolType: string,
        public readonly filePath: string,
        public readonly lineStart: number,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly children?: SymbolItem[]
    ) {
        super(label, collapsibleState);
        
        this.tooltip = `${symbolType}: ${label}\nFile: ${filePath}\nLine: ${lineStart}`;
        this.description = `${filePath.split('/').pop()}:${lineStart}`;
        
        // Set icon based on symbol type
        switch (symbolType) {
            case 'function':
                this.iconPath = new vscode.ThemeIcon('symbol-function');
                break;
            case 'class':
                this.iconPath = new vscode.ThemeIcon('symbol-class');
                break;
            case 'method':
                this.iconPath = new vscode.ThemeIcon('symbol-method');
                break;
            case 'import':
                this.iconPath = new vscode.ThemeIcon('symbol-namespace');
                break;
            default:
                this.iconPath = new vscode.ThemeIcon('symbol-variable');
        }

        this.contextValue = 'symbol';
        
        this.command = {
            command: 'codeGraph.openSymbol',
            title: 'Open Symbol',
            arguments: [this]
        };
    }
}

export class CategoryItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState = vscode.TreeItemCollapsibleState.Collapsed
    ) {
        super(label, collapsibleState);
        
        switch (label) {
            case 'Functions':
                this.iconPath = new vscode.ThemeIcon('list-flat');
                break;
            case 'Classes':
                this.iconPath = new vscode.ThemeIcon('list-tree');
                break;
            case 'Files':
                this.iconPath = new vscode.ThemeIcon('files');
                break;
            case 'Statistics':
                this.iconPath = new vscode.ThemeIcon('graph-line');
                break;
            default:
                this.iconPath = new vscode.ThemeIcon('folder');
        }
        
        this.contextValue = 'category';
    }
}

export class CodeGraphProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<vscode.TreeItem | undefined | null | void> = new vscode.EventEmitter<vscode.TreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<vscode.TreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private symbols: any[] = [];
    private stats: any = null;
    private graphBuilt: boolean = false;

    constructor(
        private context: vscode.ExtensionContext,
        private mcpServer: MCPServerManager
    ) {
        // Listen for graph updates
        this.mcpServer.onGraphUpdated((data) => {
            this.symbols = data.symbols || [];
            this.stats = data.stats || null;
            this.graphBuilt = true;
            vscode.commands.executeCommand('setContext', 'codeGraphHasData', true);
            vscode.commands.executeCommand('setContext', 'workspaceHasCodeGraph', true);
            this.refresh();
        });
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: vscode.TreeItem): Promise<vscode.TreeItem[]> {
        if (!this.graphBuilt) {
            return [new vscode.TreeItem('No graph built yet. Click "Build Code Graph" to start.')];
        }

        if (!element) {
            // Root level
            return [
                new CategoryItem('Statistics', vscode.TreeItemCollapsibleState.Expanded),
                new CategoryItem('Functions'),
                new CategoryItem('Classes'),
                new CategoryItem('Files')
            ];
        }

        if (element instanceof CategoryItem) {
            switch (element.label) {
                case 'Statistics':
                    return this.getStatisticsItems();
                case 'Functions':
                    return this.getFunctionItems();
                case 'Classes':
                    return this.getClassItems();
                case 'Files':
                    return this.getFileItems();
            }
        }

        return [];
    }

    private getStatisticsItems(): vscode.TreeItem[] {
        if (!this.stats) {
            return [new vscode.TreeItem('No statistics available')];
        }

        const items: vscode.TreeItem[] = [];
        
        const totalItem = new vscode.TreeItem(`Total Symbols: ${this.stats.total_symbols}`);
        totalItem.iconPath = new vscode.ThemeIcon('symbol-color');
        items.push(totalItem);

        const edgesItem = new vscode.TreeItem(`Total Edges: ${this.stats.total_edges}`);
        edgesItem.iconPath = new vscode.ThemeIcon('arrow-swap');
        items.push(edgesItem);

        const filesItem = new vscode.TreeItem(`Files Indexed: ${this.stats.files_indexed}`);
        filesItem.iconPath = new vscode.ThemeIcon('files');
        items.push(filesItem);

        if (this.stats.symbol_types) {
            for (const [type, count] of Object.entries(this.stats.symbol_types)) {
                const typeItem = new vscode.TreeItem(`${type}: ${count}`);
                typeItem.iconPath = new vscode.ThemeIcon('symbol-misc');
                items.push(typeItem);
            }
        }

        return items;
    }

    private getFunctionItems(): SymbolItem[] {
        return this.symbols
            .filter(s => s.symbol_type === 'function')
            .slice(0, 50) // Limit to 50 for performance
            .map(s => new SymbolItem(
                s.name,
                s.symbol_type,
                s.file_path,
                s.line_start,
                vscode.TreeItemCollapsibleState.None
            ));
    }

    private getClassItems(): SymbolItem[] {
        return this.symbols
            .filter(s => s.symbol_type === 'class')
            .slice(0, 50)
            .map(s => new SymbolItem(
                s.name,
                s.symbol_type,
                s.file_path,
                s.line_start,
                vscode.TreeItemCollapsibleState.None
            ));
    }

    private getFileItems(): vscode.TreeItem[] {
        const files = new Set(this.symbols.map(s => s.file_path));
        return Array.from(files)
            .slice(0, 30)
            .map(filePath => {
                const fileName = filePath.split('/').pop() || filePath;
                const item = new vscode.TreeItem(fileName);
                item.iconPath = new vscode.ThemeIcon('file-code');
                item.tooltip = filePath;
                item.description = `${this.symbols.filter(s => s.file_path === filePath).length} symbols`;
                return item;
            });
    }

    isGraphBuilt(): boolean {
        return this.graphBuilt;
    }

    getSymbols(): any[] {
        return this.symbols;
    }

    getStats(): any {
        return this.stats;
    }
}
