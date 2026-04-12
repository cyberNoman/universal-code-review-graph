@echo off
REM Build VS Code extension .vsix for manual installation
REM Usage: build.bat

echo 📦 Building Universal Code Graph VS Code Extension...

REM Install dependencies
echo 📥 Installing dependencies...
call npm install
if errorlevel 1 (
    echo ❌ npm install failed
    exit /b 1
)

REM Compile TypeScript
echo 🔨 Compiling TypeScript...
call npm run compile
if errorlevel 1 (
    echo ❌ Compilation failed
    exit /b 1
)

REM Install vsce if not present
echo 📥 Installing vsce...
call npm install -g @vscode/vsce

REM Build .vsix package
echo 📦 Building .vsix package...
call vsce package --no-dependencies
if errorlevel 1 (
    echo ❌ Package build failed
    exit /b 1
)

echo.
echo ✅ Build complete! Install with:
echo    code --install-extension universal-code-graph-*.vsix
echo.
pause
