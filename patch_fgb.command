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
#    - dotnet SDK ≥ 6 instalado (brew install dotnet)
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

# ── Find dotnet ───────────────────────────────────────────────
DOTNET=""
for candidate in \
    "${DOTNET_ROOT:-}/dotnet" \
    "${HOME}/homebrew/Cellar/dotnet/10.0.107/libexec/dotnet" \
    "${HOME}/.dotnet/dotnet" \
    "/usr/local/share/dotnet/dotnet" \
    "$(which dotnet 2>/dev/null || true)"; do
    if [ -f "$candidate" ] && [ -x "$candidate" ]; then
        DOTNET="$candidate"
        break
    fi
done

echo "══════════════════════════════════════════════════════"
echo "  Fross Garage Band — Patch FrossDownloadMenu"
echo "══════════════════════════════════════════════════════"
echo ""

# ── Pre-flight ────────────────────────────────────────────────
if [ ! -d "$YARG" ]; then
    echo "  ✗ YARG não encontrado em /Applications/YARG.app"
    read -p "Enter para fechar..."; exit 1
fi

if [ -z "$DOTNET" ]; then
    echo "  ✗ dotnet SDK não encontrado."
    echo "    Instale com: brew install dotnet"
    read -p "Enter para fechar..."; exit 1
fi

echo "  dotnet: $DOTNET  ($(\"$DOTNET\" --version 2>/dev/null || echo 'versão desconhecida'))"
echo "  Managed: $MANAGED"
echo ""

# ── 1. Compilar FrossDownloadMenu.cs ─────────────────────────
echo "[ 1/3 ] Compilando FrossDownloadMenu.cs..."

TMPDIR_BUILD="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BUILD"' EXIT

# Write .csproj — use placeholder, inject path after
cat > "$TMPDIR_BUILD/FrossDownloadMenu.csproj" << 'CSPROJ'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net472</TargetFramework>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
    <Nullable>disable</Nullable>
    <AssemblyName>FrossDownloadMenu</AssemblyName>
    <RootNamespace>FrossGarageBand</RootNamespace>
    <Optimize>true</Optimize>
  </PropertyGroup>
  <ItemGroup>
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
    <!-- TextAnchor, Font, FontStyle, HorizontalWrapMode, etc. -->
    <Reference Include="UnityEngine.TextRenderingModule">
      <HintPath>MANAGED_PATH/UnityEngine.TextRenderingModule.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <!-- Canvas, RenderMode, CanvasScaler, GraphicRaycaster, Mask -->
    <Reference Include="UnityEngine.UIModule">
      <HintPath>MANAGED_PATH/UnityEngine.UIModule.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <!-- JsonUtility -->
    <Reference Include="UnityEngine.JSONSerializeModule">
      <HintPath>MANAGED_PATH/UnityEngine.JSONSerializeModule.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <!-- Input (legacy input system) -->
    <Reference Include="UnityEngine.InputLegacyModule">
      <HintPath>MANAGED_PATH/UnityEngine.InputLegacyModule.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <!-- ZipFile.ExtractToDirectory lives here in .NET Framework 4.x -->
    <Reference Include="System.IO.Compression.FileSystem" />
    <Reference Include="System.IO.Compression" />
  </ItemGroup>
</Project>
CSPROJ

# Inject actual Managed path
sed -i.bak "s|MANAGED_PATH|${MANAGED}|g" "$TMPDIR_BUILD/FrossDownloadMenu.csproj"

cp "$(pwd)/FrossDownloadMenu.cs" "$TMPDIR_BUILD/"

"$DOTNET" build "$TMPDIR_BUILD/FrossDownloadMenu.csproj" \
    -c Release -o "$TMPDIR_BUILD/out" --nologo 2>&1 | tail -25

BUILT="$TMPDIR_BUILD/out/FrossDownloadMenu.dll"
if [ ! -f "$BUILT" ]; then
    echo ""
    echo "  ✗ Compilação falhou — veja erros acima"
    echo "    Dica: verifique se os DLLs do Unity existem em:"
    echo "    $MANAGED"
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
    echo "  ℹ Mono.Cecil não encontrado no Managed/. Obtendo via NuGet..."

    # Create a throwaway project to restore Mono.Cecil into the NuGet cache
    mkdir -p "$TMPDIR_BUILD/cecil_fetch"
    cat > "$TMPDIR_BUILD/cecil_fetch/fetch.csproj" << 'FETCHPROJ'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net6.0</TargetFramework></PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Mono.Cecil" Version="0.11.5" />
  </ItemGroup>
</Project>
FETCHPROJ

    "$DOTNET" restore "$TMPDIR_BUILD/cecil_fetch/fetch.csproj" --nologo 2>&1 | tail -5

    # Locate the net40 or netstandard2.0 build in the NuGet cache
    NUGET_CACHE="${NUGET_PACKAGES:-${HOME}/.nuget/packages}/mono.cecil"
    FOUND_CECIL=""
    for subdir in "net40" "netstandard2.0" "."; do
        FOUND_CECIL=$(find "$NUGET_CACHE" -name "Mono.Cecil.dll" -path "*/${subdir}/*" 2>/dev/null | sort -V | tail -1)
        [ -n "$FOUND_CECIL" ] && break
    done

    if [ -n "$FOUND_CECIL" ]; then
        cp "$FOUND_CECIL" "$MANAGED/Mono.Cecil.dll"
        CECIL_DLL="$MANAGED/Mono.Cecil.dll"
        echo "  ✓ Mono.Cecil obtido: $FOUND_CECIL"
    else
        echo "  ✗ Não foi possível localizar Mono.Cecil.dll no cache NuGet."
        echo "    Baixe manualmente de: https://github.com/jbevain/cecil/releases"
        echo "    e coloque em: $MANAGED/Mono.Cecil.dll"
        read -p "Enter para fechar..."; exit 1
    fi
fi
echo "  ✓ Mono.Cecil: $CECIL_DLL"

# ── 3. Patch Assembly-CSharp.dll via Mono.Cecil ───────────────
echo ""
echo "[ 3/3 ] Patching Assembly-CSharp.dll..."

ASM="$MANAGED/Assembly-CSharp.dll"
BAK="${ASM}.bak_fgb"

if [ ! -f "$BAK" ]; then
    cp "$ASM" "$BAK"
    echo "  ✓ Backup criado: Assembly-CSharp.dll.bak_fgb"
else
    echo "  — Backup já existe"
fi

# Always restore the clean original before patching.
# This prevents re-patching an already-patched DLL and recovers from
# any corruption left by a previous failed write.
cp "$BAK" "$ASM"
echo "  ✓ DLL restaurado do backup (garante estado limpo)"

# ── Patcher inline ────────────────────────────────────────────
cat > "$TMPDIR_BUILD/Patcher.cs" << 'PATCHER_CS'
using System;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class Patcher
{
    static int Main(string[] args)
    {
        if (args.Length < 3) {
            Console.Error.WriteLine("Usage: Patcher <Assembly-CSharp.dll> <FrossDownloadMenu.dll> <Managed/>");
            return 1;
        }
        string asmPath    = args[0];   // destination (Assembly-CSharp.dll)
        string fgbPath    = args[1];
        string managedDir = args[2];

        // Read from the clean backup — avoids reading from the same path
        // we will write to, which causes Cecil's EndOfStreamException.
        string srcPath = asmPath + ".bak_fgb";
        if (!System.IO.File.Exists(srcPath)) srcPath = asmPath;
        Console.WriteLine("  Reading from: " + srcPath);

        var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(managedDir);
        var rp = new ReaderParameters { AssemblyResolver = resolver };

        var asm = AssemblyDefinition.ReadAssembly(srcPath, rp);
        var fgb = AssemblyDefinition.ReadAssembly(fgbPath, rp);

        // ── Find MainMenu ──────────────────────────────────────
        var mainMenu = asm.MainModule.Types.FirstOrDefault(t => t.Name == "MainMenu");
        if (mainMenu == null) {
            Console.Error.WriteLine("ERROR: MainMenu type not found.");
            Console.Error.WriteLine("Types in assembly:");
            foreach (var t in asm.MainModule.Types.Take(30))
                Console.Error.WriteLine("  " + t.FullName);
            return 2;
        }

        // ── Find Credits() ─────────────────────────────────────
        // YARG uses a method named "Credits" with no params on the MainMenu class
        var creditsMethod = mainMenu.Methods
            .FirstOrDefault(m => m.Name == "Credits" && m.Parameters.Count == 0);

        if (creditsMethod == null) {
            // Fallback: any method whose name contains "Credits"
            creditsMethod = mainMenu.Methods
                .FirstOrDefault(m => m.Name.IndexOf("Credits", StringComparison.OrdinalIgnoreCase) >= 0
                                     && m.Parameters.Count == 0);
        }

        if (creditsMethod == null) {
            Console.Error.WriteLine("ERROR: Credits() method not found in MainMenu.");
            Console.Error.WriteLine("Methods in MainMenu:");
            foreach (var m in mainMenu.Methods)
                Console.Error.WriteLine("  " + m.Name +
                    "(" + string.Join(", ", m.Parameters.Select(p => p.ParameterType.Name)) + ")");
            return 3;
        }
        Console.WriteLine("  Target: " + mainMenu.FullName + "::" + creditsMethod.Name);

        // ── Find FrossDownloadMenu.Show() ──────────────────────
        var fgbType = fgb.MainModule.Types.FirstOrDefault(t => t.Name == "FrossDownloadMenu");
        if (fgbType == null) { Console.Error.WriteLine("ERROR: FrossDownloadMenu type not found."); return 4; }

        var showMethod = fgbType.Methods
            .FirstOrDefault(m => m.Name == "Show" && m.IsStatic && m.Parameters.Count == 0);
        if (showMethod == null) { Console.Error.WriteLine("ERROR: FrossDownloadMenu.Show() not found."); return 5; }

        // ── Rewrite Credits() body ─────────────────────────────
        // Before: pushes MenuManager.Menu.Credits and calls PushMenu
        // After:  call void FrossGarageBand.FrossDownloadMenu::Show()
        //         ret
        var showRef = asm.MainModule.ImportReference(showMethod);
        var il = creditsMethod.Body.GetILProcessor();
        creditsMethod.Body.Instructions.Clear();
        creditsMethod.Body.Variables.Clear();
        creditsMethod.Body.ExceptionHandlers.Clear();
        il.Append(il.Create(OpCodes.Call, showRef));
        il.Append(il.Create(OpCodes.Ret));
        // OptimizeMacros() removed in Cecil 0.11.5 — not needed for correctness

        Console.WriteLine("  Patched: " + creditsMethod.FullName + " → FrossDownloadMenu.Show()");

        // Write to MemoryStream first, then dispose (closes file handle),
        // then save bytes to disk — avoids Cecil's EndOfStreamException when
        // reading and writing the same path simultaneously.
        byte[] patchedBytes;
        using (var ms = new System.IO.MemoryStream()) {
            asm.Write(ms, new WriterParameters { WriteSymbols = false });
            patchedBytes = ms.ToArray();
        }
        asm.Dispose();
        System.IO.File.WriteAllBytes(asmPath, patchedBytes);
        Console.WriteLine("  Written: " + asmPath + " (" + patchedBytes.Length + " bytes)");
        return 0;
    }
}
PATCHER_CS

# Note: Patcher targets net6.0 so dotnet can run it natively (no Mono needed)
cat > "$TMPDIR_BUILD/Patcher.csproj" << PATCHER_PROJ
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net9.0</TargetFramework>
    <AssemblyName>Patcher</AssemblyName>
    <Nullable>disable</Nullable>
    <RollForward>Major</RollForward>
    <!-- Only compile Patcher.cs — prevent MSBuild from globbing FrossDownloadMenu.cs -->
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="Patcher.cs" />
    <Reference Include="Mono.Cecil">
      <HintPath>${CECIL_DLL}</HintPath>
      <Private>true</Private>
    </Reference>
  </ItemGroup>
</Project>
PATCHER_PROJ

"$DOTNET" build "$TMPDIR_BUILD/Patcher.csproj" \
    -c Release -o "$TMPDIR_BUILD/patcher_out" --nologo 2>&1 | tail -10

# dotnet publish produces a platform-native binary; use dotnet exec on the DLL
PATCHER_DLL="$TMPDIR_BUILD/patcher_out/Patcher.dll"
if [ ! -f "$PATCHER_DLL" ]; then
    echo "  ✗ Compilação do patcher falhou"
    read -p "Enter para fechar..."; exit 1
fi

echo "  Executando patcher..."
"$DOTNET" exec "$PATCHER_DLL" "$ASM" "$DLL_DEST" "$MANAGED"
PATCH_CODE=$?

if [ $PATCH_CODE -ne 0 ]; then
    echo ""
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
echo "  No jogo: Menu Principal → 'Download Music'"
echo "    → busca Rhythmverse com filtros por formato"
echo "    → selecione → Baixar Música"
echo "    → instalado em ~/Library/Application Support/YARG/songs/"
echo ""
echo "  Para reverter: bash restore_yarg.command"
echo "══════════════════════════════════════════════════════"
echo ""
read -p "Pressione Enter para fechar..."
