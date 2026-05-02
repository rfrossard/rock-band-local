#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  Fross Garage Band — Patch principal
#
#  O que faz:
#    1. Compila FrossDownloadMenu.cs → FrossDownloadMenu.dll
#    2. Copia a DLL para o Managed/ do YARG
#    3. Usa Mono.Cecil para redirecionar MainMenu.Credits()
#       → FrossDownloadMenu.Show() (tela de busca Rhythmverse)
#    4. Re-assina Assembly-CSharp.dll
#
#  Pré-requisitos:
#    - dotnet SDK instalado (brew install dotnet)
#    - YARG em /Applications/YARG.app
#
#  Para reverter: execute restore_yarg.command
# ══════════════════════════════════════════════════════════════
cd "$(dirname "$0")"
set -euo pipefail

YARG="/Applications/YARG.app"
MANAGED="$YARG/Contents/Resources/Data/Managed"
DLL_DEST="$MANAGED/FrossDownloadMenu.dll"
DLL_SRC="$(pwd)/FrossDownloadMenu.dll"
CECIL_SRC="$MANAGED/Mono.Cecil.dll"

# Dotnet paths
DOTNET="${DOTNET_ROOT:-${HOME}/homebrew/Cellar/dotnet/10.0.107/libexec}/dotnet"
if [ ! -f "$DOTNET" ]; then
    DOTNET="$(which dotnet 2>/dev/null || echo '')"
fi

echo "══════════════════════════════════════════════════════"
echo "  Fross Garage Band — Patch FrossDownloadMenu"
echo "══════════════════════════════════════════════════════"
echo ""

# ── Pre-flight ────────────────────────────────────────────────
if [ ! -d "$YARG" ]; then
    echo "  ✗ YARG não encontrado em /Applications/YARG.app"
    read -p "Enter para fechar..."; exit 1
fi

if [ ! -f "$DOTNET" ]; then
    echo "  ✗ dotnet SDK não encontrado."
    echo "    Instale com: brew install dotnet"
    read -p "Enter para fechar..."; exit 1
fi

echo "  dotnet: $DOTNET"
echo "  Managed: $MANAGED"
echo ""

# ── 1. Compilar FrossDownloadMenu.cs ─────────────────────────
echo "[ 1/3 ] Compilando FrossDownloadMenu.cs..."

# Cria projeto temporário
TMPDIR_BUILD="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BUILD"' EXIT

cat > "$TMPDIR_BUILD/FrossDownloadMenu.csproj" << 'CSPROJ'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net472</TargetFramework>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
    <Nullable>disable</Nullable>
    <AssemblyName>FrossDownloadMenu</AssemblyName>
    <RootNamespace>FrossGarageBand</RootNamespace>
    <Optimize>true</Optimize>
    <Deterministic>true</Deterministic>
  </PropertyGroup>
  <ItemGroup>
    <!-- Unity core -->
    <Reference Include="UnityEngine">
      <HintPath>MANAGED_PATH/UnityEngine.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <Reference Include="UnityEngine.CoreModule">
      <HintPath>MANAGED_PATH/UnityEngine.CoreModule.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <Reference Include="UnityEngine.UI">
      <HintPath>MANAGED_PATH/UnityEngine.UI.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <Reference Include="UnityEngine.UnityWebRequestModule">
      <HintPath>MANAGED_PATH/UnityEngine.UnityWebRequestModule.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <Reference Include="UnityEngine.UnityWebRequestWWWModule">
      <HintPath>MANAGED_PATH/UnityEngine.UnityWebRequestWWWModule.dll</HintPath>
      <Private>false</Private>
    </Reference>
  </ItemGroup>
</Project>
CSPROJ

# Inject actual Managed path
sed -i.bak "s|MANAGED_PATH|${MANAGED}|g" "$TMPDIR_BUILD/FrossDownloadMenu.csproj"

# Copy source
cp "$(pwd)/FrossDownloadMenu.cs" "$TMPDIR_BUILD/"

# Build
"$DOTNET" build "$TMPDIR_BUILD/FrossDownloadMenu.csproj" \
    -c Release \
    -o "$TMPDIR_BUILD/out" \
    --nologo \
    2>&1 | tail -20

BUILT="$TMPDIR_BUILD/out/FrossDownloadMenu.dll"
if [ ! -f "$BUILT" ]; then
    echo "  ✗ Compilação falhou — veja erros acima"
    read -p "Enter para fechar..."; exit 1
fi

cp "$BUILT" "$DLL_SRC"
cp "$BUILT" "$DLL_DEST"
echo "  ✓ FrossDownloadMenu.dll compilado e copiado para Managed/"

# ── 2. Verificar / obter Mono.Cecil ──────────────────────────
echo ""
echo "[ 2/3 ] Verificando Mono.Cecil..."

CECIL_DLL="$MANAGED/Mono.Cecil.dll"
if [ ! -f "$CECIL_DLL" ]; then
    echo "  ℹ Mono.Cecil não encontrado no Managed/. Baixando via NuGet..."
    NUGET_DIR="$(mktemp -d)"
    "$DOTNET" nuget add source https://api.nuget.org/v3/index.json --name nuget.org 2>/dev/null || true
    "$DOTNET" tool install --global dotnet-script 2>/dev/null || true
    # Download Mono.Cecil package
    "$DOTNET" add "$TMPDIR_BUILD/FrossDownloadMenu.csproj" package Mono.Cecil --version 0.11.5 2>/dev/null || true
    # Try to find Mono.Cecil.dll in NuGet cache
    NUGET_CACHE="$HOME/.nuget/packages/mono.cecil"
    if [ -d "$NUGET_CACHE" ]; then
        FOUND_CECIL=$(find "$NUGET_CACHE" -name "Mono.Cecil.dll" -path "*/net40/*" 2>/dev/null | head -1)
        if [ -n "$FOUND_CECIL" ]; then
            cp "$FOUND_CECIL" "$MANAGED/Mono.Cecil.dll"
            CECIL_DLL="$MANAGED/Mono.Cecil.dll"
            echo "  ✓ Mono.Cecil obtido do cache NuGet"
        fi
    fi
    if [ ! -f "$CECIL_DLL" ]; then
        echo "  ✗ Não foi possível obter Mono.Cecil automaticamente."
        echo "    Baixe Mono.Cecil.dll manualmente de:"
        echo "    https://github.com/jbevain/cecil/releases"
        echo "    e coloque em: $MANAGED/"
        read -p "Enter para fechar..."; exit 1
    fi
fi
echo "  ✓ Mono.Cecil: $CECIL_DLL"

# ── 3. Patch Assembly-CSharp.dll via Mono.Cecil ───────────────
echo ""
echo "[ 3/3 ] Patching Assembly-CSharp.dll..."

ASM="$MANAGED/Assembly-CSharp.dll"
BAK="${ASM}.bak_fgb"

# Backup
if [ ! -f "$BAK" ]; then
    cp "$ASM" "$BAK"
    echo "  ✓ Backup criado: Assembly-CSharp.dll.bak_fgb"
fi

# Patcher C# inline
cat > "$TMPDIR_BUILD/Patcher.cs" << 'PATCHER_CS'
using System;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class Patcher {
    static int Main(string[] args) {
        if (args.Length < 3) {
            Console.Error.WriteLine("Usage: Patcher <Assembly-CSharp.dll> <FrossDownloadMenu.dll> <Managed/>");
            return 1;
        }
        string asmPath = args[0];
        string fgbPath = args[1];
        string managedDir = args[2];

        var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(managedDir);

        var rp = new ReaderParameters { AssemblyResolver = resolver };

        var asm = AssemblyDefinition.ReadAssembly(asmPath, rp);
        var fgb = AssemblyDefinition.ReadAssembly(fgbPath, rp);

        // Find MainMenu type
        var mainMenu = asm.MainModule.Types
            .FirstOrDefault(t => t.Name == "MainMenu");
        if (mainMenu == null) {
            Console.Error.WriteLine("ERROR: MainMenu type not found in Assembly-CSharp.dll");
            return 2;
        }

        // Find Credits() method
        var creditsMethod = mainMenu.Methods
            .FirstOrDefault(m => m.Name == "Credits" && m.Parameters.Count == 0);
        if (creditsMethod == null) {
            // Try with underscore prefix (YARG sometimes uses _Credits)
            creditsMethod = mainMenu.Methods
                .FirstOrDefault(m => m.Name.Contains("Credits") && m.Parameters.Count == 0);
        }
        if (creditsMethod == null) {
            Console.Error.WriteLine("ERROR: Credits() method not found in MainMenu");
            Console.WriteLine("Available methods in MainMenu:");
            foreach (var m in mainMenu.Methods)
                Console.WriteLine("  " + m.Name + "(" + string.Join(", ", m.Parameters.Select(p => p.ParameterType.Name)) + ")");
            return 3;
        }
        Console.WriteLine("  Found: " + mainMenu.FullName + "::" + creditsMethod.Name);

        // Find FrossDownloadMenu.Show()
        var fgbType = fgb.MainModule.Types
            .FirstOrDefault(t => t.Name == "FrossDownloadMenu");
        if (fgbType == null) {
            Console.Error.WriteLine("ERROR: FrossDownloadMenu type not found");
            return 4;
        }
        var showMethod = fgbType.Methods
            .FirstOrDefault(m => m.Name == "Show" && m.IsStatic && m.Parameters.Count == 0);
        if (showMethod == null) {
            Console.Error.WriteLine("ERROR: FrossDownloadMenu.Show() not found");
            return 5;
        }

        // Import into target assembly
        var showRef = asm.MainModule.ImportReference(showMethod);

        // Rewrite Credits() body:
        //   call FrossGarageBand.FrossDownloadMenu::Show()
        //   ret
        var il = creditsMethod.Body.GetILProcessor();
        creditsMethod.Body.Instructions.Clear();
        creditsMethod.Body.Variables.Clear();
        creditsMethod.Body.ExceptionHandlers.Clear();
        il.Append(il.Create(OpCodes.Call, showRef));
        il.Append(il.Create(OpCodes.Ret));
        creditsMethod.Body.OptimizeMacros();

        Console.WriteLine("  Patched: " + creditsMethod.FullName + " → FrossDownloadMenu.Show()");

        // Write patched assembly
        var wp = new WriterParameters { WriteSymbols = false };
        asm.Write(asmPath, wp);
        Console.WriteLine("  Written: " + asmPath);
        return 0;
    }
}
PATCHER_CS

cat > "$TMPDIR_BUILD/Patcher.csproj" << PATCHER_PROJ
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net472</TargetFramework>
    <AssemblyName>Patcher</AssemblyName>
    <Nullable>disable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include="Mono.Cecil">
      <HintPath>${CECIL_DLL}</HintPath>
      <Private>true</Private>
    </Reference>
  </ItemGroup>
</Project>
PATCHER_PROJ

"$DOTNET" build "$TMPDIR_BUILD/Patcher.csproj" \
    -c Release -o "$TMPDIR_BUILD/patcher_out" --nologo 2>&1 | tail -10

PATCHER_EXE="$TMPDIR_BUILD/patcher_out/Patcher.exe"
if [ ! -f "$PATCHER_EXE" ]; then
    echo "  ✗ Compilação do patcher falhou"
    read -p "Enter para fechar..."; exit 1
fi

# Run patcher
MONO_BIN="$(which mono 2>/dev/null || echo '')"
if [ -n "$MONO_BIN" ]; then
    "$MONO_BIN" "$PATCHER_EXE" "$ASM" "$DLL_DEST" "$MANAGED"
else
    # Try dotnet run
    "$DOTNET" "$PATCHER_EXE" "$ASM" "$DLL_DEST" "$MANAGED"
fi

PATCH_CODE=$?
if [ $PATCH_CODE -ne 0 ]; then
    echo "  ✗ Patch falhou (código $PATCH_CODE) — restaurando backup"
    cp "$BAK" "$ASM"
    read -p "Enter para fechar..."; exit 1
fi

# Re-sign
echo ""
echo "  Re-assinando DLL..."
codesign --remove-signature "$ASM" 2>/dev/null || true
codesign -s - "$ASM" 2>/dev/null || true
echo "  ✓ Assembly-CSharp.dll re-assinado"

echo ""
echo "══════════════════════════════════════════════════════"
echo "  ✅  Patch concluído!"
echo ""
echo "  O que foi feito:"
echo "    ✓ FrossDownloadMenu.dll compilado e instalado"
echo "    ✓ MainMenu.Credits() → FrossDownloadMenu.Show()"
echo ""
echo "  No jogo:"
echo "    Menu Principal → clique 'Download Music'"
echo "    → tela de busca Rhythmverse com filtros"
echo "    → selecione uma música → Baixar Música"
echo "    → arquivo extraído em ~/Library/Application Support/YARG/songs/"
echo ""
echo "  Para reverter: execute restore_yarg.command"
echo "══════════════════════════════════════════════════════"
echo ""
read -p "Pressione Enter para fechar..."
