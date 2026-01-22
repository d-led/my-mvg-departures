import * as esbuild from "esbuild";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync, cpSync, rmSync, watch } from "fs";
import { readdir, stat } from "fs/promises";
import { join, dirname, extname } from "path";
import { fileURLToPath } from "url";
import { compile } from "svelte/compiler";

const isWatch = process.argv.includes("--watch");

// Constants
const DIST_DIR = "dist";
const TEMP_DIR = ".svelte-temp";
const STATIC_DIR = "static";

// Helper function to ensure dist directory exists
function ensureDistDir() {
  if (!existsSync(DIST_DIR)) {
    mkdirSync(DIST_DIR, { recursive: true });
  }
}

// Compile Svelte components to JavaScript
async function compileSvelte(filePath) {
  const content = readFileSync(filePath, "utf8");
  const result = compile(content, {
    filename: filePath,
    generate: "dom",
    css: "injected",
    dev: isWatch,
  });
  return result.js.code;
}

// Find all Svelte files recursively
async function findSvelteFiles(dir, fileList = []) {
  const files = await readdir(dir);
  for (const file of files) {
    const filePath = join(dir, file);
    const fileStat = await stat(filePath);
    if (fileStat.isDirectory()) {
      await findSvelteFiles(filePath, fileList);
    } else if (extname(file) === ".svelte") {
      fileList.push(filePath);
    }
  }
  return fileList;
}

// Pre-compile Svelte components to a temp directory
async function precompileSvelte() {
  const svelteFiles = await findSvelteFiles("src");
  
  if (existsSync(TEMP_DIR)) {
    // Clean temp dir
    rmSync(TEMP_DIR, { recursive: true, force: true });
  }
  mkdirSync(TEMP_DIR, { recursive: true });

  for (const file of svelteFiles) {
    const compiled = await compileSvelte(file);
    const relativePath = file.replace("src/", "").replace(".svelte", ".svelte.js");
    const outputPath = join(TEMP_DIR, relativePath);
    const outputDir = dirname(outputPath);
    mkdirSync(outputDir, { recursive: true });
    writeFileSync(outputPath, compiled);
  }

  return TEMP_DIR;
}

function copyStaticFiles() {
  ensureDistDir();

  // Copy CSS
  if (existsSync(join(STATIC_DIR, "css", "departures.css"))) {
    const cssDest = join(DIST_DIR, "css");
    mkdirSync(cssDest, { recursive: true });
    copyFileSync(
      join(STATIC_DIR, "css", "departures.css"),
      join(cssDest, "departures.css")
    );
  }

  // Copy static assets if they exist
  const assetsDir = join(STATIC_DIR, "assets");
  if (existsSync(assetsDir)) {
    const assetsDest = join(DIST_DIR, "assets");
    mkdirSync(assetsDest, { recursive: true });
    // Copy all assets
    cpSync(assetsDir, assetsDest, { recursive: true });
  }

  // Copy img directory if it exists (for status icons)
  const imgDir = join(STATIC_DIR, "img");
  if (existsSync(imgDir)) {
    const imgDest = join(DIST_DIR, "img");
    mkdirSync(imgDest, { recursive: true });
    cpSync(imgDir, imgDest, { recursive: true });
  }
}

function copyExampleConfig() {
  // Copy config.example.toml from project root to dist for runtime reference
  // Try multiple possible paths to find the config file
  const buildScriptDir = dirname(fileURLToPath(import.meta.url));
  const possiblePaths = [
    join(process.cwd(), "..", "config.example.toml"), // From spa directory (most common in CI)
    join(process.cwd(), "config.example.toml"), // If already in project root
    join(buildScriptDir, "..", "config.example.toml"), // Relative to build.js location
  ];
  
  let exampleConfigSrc = null;
  for (const path of possiblePaths) {
    if (existsSync(path)) {
      exampleConfigSrc = path;
      break;
    }
  }
  
  const exampleConfigDest = join(DIST_DIR, "config.example.toml");
  
  if (exampleConfigSrc) {
    ensureDistDir();
    copyFileSync(exampleConfigSrc, exampleConfigDest);
    console.log(`✓ Copied config.example.toml from ${exampleConfigSrc} to ${exampleConfigDest}`);
  } else {
    console.error(`✗ config.example.toml not found. Tried paths: ${possiblePaths.join(", ")}`);
    process.exit(1); // Fail the build if config file is missing
  }
}

function copyHtml() {
  const dest = join(DIST_DIR, "index.html");
  
  // Create minimal HTML template for Svelte
  // Svelte will handle all the rendering, so we just need the basic structure
  const cleanHtml = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
<!-- Minimal DaisyUI for theme support only -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet" type="text/css" />
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style>
    /* CSS custom properties - will be set by Svelte based on config */
    :root {
        --font-size-route-number: 4rem;
        --font-size-destination: 3.5rem;
        --font-size-platform: 2.5rem;
        --font-size-time: 4rem;
        --font-size-no-departures: 2.5rem;
        --font-size-direction-header: 2.5rem;
        --font-size-stop-header: 3rem;
        --font-size-pagination-indicator: 2rem;
        --font-size-countdown-text: 1.8rem;
        --font-size-status-header: 1.875rem;
        --font-size-delay-amount: 2rem;
        --banner-color: #087BC4;
    }
</style>
<!-- Custom CSS -->
<link rel="stylesheet" type="text/css" href="css/departures.css" />
<script>
    // Apply theme - default to auto (follows system preference)
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
    }
</script>
<!-- Svelte app bundle -->
<script src="bundle.js"></script>
</head>
<body class="min-h-screen bg-base-100" style="width: 100vw; max-width: 100vw; margin: 0; padding: 0;">
<!-- Skip to main content link for keyboard navigation -->
<a href="#departures" class="skip-link">Skip to main content</a>

<!-- ARIA live region for status announcements -->
<div id="aria-live-status" aria-live="polite" aria-atomic="true" class="sr-only"></div>
<!-- ARIA live region for departure updates -->
<div id="aria-live-departures" aria-live="polite" aria-atomic="false" class="sr-only"></div>

<!-- Svelte will render into this container -->
<div class="container" data-phx-main role="main" aria-label="MVG Departures Dashboard"></div>
</body>
</html>`;
  
  ensureDistDir();
  writeFileSync(dest, cleanHtml);
}

  const jsOptions = {
  entryPoints: ["src/main.ts"],
  bundle: true,
  outfile: join(DIST_DIR, "bundle.js"),
  platform: "browser",
  format: "iife",
  target: "es2022",
  sourcemap: true,
  globalName: "MvgDeparturesApp",
  loader: {
    ".ts": "ts",
    ".js": "js",
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify(isWatch ? "development" : "production"),
  },
  external: [],
  packages: "bundle",
};

async function build() {
  console.log("Pre-compiling Svelte components...");
  await precompileSvelte();
  
  // Update entry point to use temp directory
  jsOptions.entryPoints = ["src/main.ts"];
  jsOptions.plugins = [
    {
      name: "svelte-resolver",
      setup(build) {
        // First, intercept .svelte imports and convert them to compiled .svelte.js files
        build.onResolve({ filter: /\.svelte$/ }, (args) => {
          // Don't intercept svelte package imports
          if (args.path.startsWith("svelte") || args.path.includes("node_modules")) {
            return undefined;
          }
          
          // Resolve the .svelte import to the compiled .svelte.js file
          let resolvedPath = args.path;
          if (args.path.startsWith(".") && args.importer) {
            const importerDir = dirname(args.importer);
            resolvedPath = join(importerDir, args.path);
          }
          
          // Convert to compiled path in temp directory
          const relativePath = resolvedPath.replace(/^.*[\\/]src[\\/]/, "").replace(".svelte", ".svelte.js");
          const compiledPath = join(process.cwd(), TEMP_DIR, relativePath);
          
          if (existsSync(compiledPath)) {
            return { 
              path: compiledPath,
              namespace: "file",
            };
          }
          
          // If compiled file doesn't exist, return undefined to let esbuild show the error
          return undefined;
        });
        
          // Handle relative imports from compiled Svelte files back to source
          build.onResolve({ filter: /.*/ }, (args) => {
            // If importing from a compiled Svelte file in temp directory
            if (args.importer && args.importer.includes(TEMP_DIR)) {
              // Relative imports should point back to source
              if (args.path.startsWith(".")) {
                // Get the directory of the compiled file relative to temp
                const importerPath = args.importer.replace(new RegExp(`^.*${TEMP_DIR.replace(/\./g, "\\.")}[\\\\/]`), "");
              const importerDir = dirname(importerPath);
              // Resolve the relative import
              const resolvedRelative = join(importerDir, args.path).replace(/\\/g, "/");
              // Map to source directory (remove .js extension, add .ts if needed)
              let sourceRelative = resolvedRelative.replace(/\.js$/, "");
              // Try .ts first, then .js
              const sourcePathTs = join(process.cwd(), "src", sourceRelative + ".ts");
              const sourcePathJs = join(process.cwd(), "src", sourceRelative + ".js");
              if (existsSync(sourcePathTs)) {
                return { path: sourcePathTs };
              }
              if (existsSync(sourcePathJs)) {
                return { path: sourcePathJs };
              }
            }
          }
          
          return undefined; // Let esbuild handle normally
        });
      },
    },
  ];

  console.log("Building bundle...");
  try {
    await esbuild.build(jsOptions);
  } catch (error) {
    console.error("Build error:", error);
    throw error;
  }
  
  copyHtml();
  copyStaticFiles();
  copyExampleConfig();
  
  // Clean up temp directory
  if (!isWatch && existsSync(TEMP_DIR)) {
    rmSync(TEMP_DIR, { recursive: true, force: true });
  }
  
  console.log("✓ Build complete!");
}

if (isWatch) {
  let buildContext;
  let tempDir;
  let server;
  let rebuildTimeout = null;
  let isRebuilding = false;
  
  // Create plugins that reference tempDir from outer scope (so it's always current)
  function createPlugins() {
    return [
      {
        name: "svelte-resolver",
        setup(build) {
          // First, intercept .svelte imports and convert them to compiled .svelte.js files
          build.onResolve({ filter: /\.svelte$/ }, (args) => {
            // Don't intercept svelte package imports
            if (args.path.startsWith("svelte") || args.path.includes("node_modules")) {
              return undefined;
            }
            
            // Resolve the .svelte import to the compiled .svelte.js file
            let resolvedPath = args.path;
            if (args.path.startsWith(".") && args.importer) {
              const importerDir = dirname(args.importer);
              resolvedPath = join(importerDir, args.path);
            }
            
            // Convert to compiled path in temp directory
            // Use tempDir from outer scope (always current value)
            // Guard against tempDir being undefined (shouldn't happen, but safety check)
            if (!tempDir) {
              console.error("[svelte-resolver] tempDir is undefined! This should not happen.");
              return undefined;
            }
            
            const relativePath = resolvedPath.replace(/^.*[\\/]src[\\/]/, "").replace(".svelte", ".svelte.js");
            const compiledPath = join(process.cwd(), TEMP_DIR, relativePath);
            
            if (existsSync(compiledPath)) {
              return { 
                path: compiledPath,
                namespace: "file",
              };
            }
            
            return undefined;
          });
          
          // Handle relative imports from compiled Svelte files back to source
          build.onResolve({ filter: /.*/ }, (args) => {
            // If importing from a compiled Svelte file in temp directory
            if (args.importer && args.importer.includes(TEMP_DIR)) {
              // Relative imports should point back to source
              if (args.path.startsWith(".")) {
                // Get the directory of the compiled file relative to temp
                const importerPath = args.importer.replace(/^.*\.svelte-temp[\\/]/, "");
                const importerDir = dirname(importerPath);
                // Resolve the relative import
                const resolvedRelative = join(importerDir, args.path).replace(/\\/g, "/");
                // Map to source directory (remove .js extension, add .ts if needed)
                let sourceRelative = resolvedRelative.replace(/\.js$/, "");
                // Try .ts first, then .js
                const sourcePathTs = join(process.cwd(), "src", sourceRelative + ".ts");
                const sourcePathJs = join(process.cwd(), "src", sourceRelative + ".js");
                if (existsSync(sourcePathTs)) {
                  return { path: sourcePathTs };
                }
                if (existsSync(sourcePathJs)) {
                  return { path: sourcePathJs };
                }
              }
            }
            
            return undefined; // Let esbuild handle normally
          });
        },
      },
    ];
  }
  
  async function rebuild() {
    // Prevent multiple simultaneous rebuilds
    if (isRebuilding) {
      console.log("Rebuild already in progress, skipping...");
      return;
    }
    
    isRebuilding = true;
    try {
      if (tempDir && existsSync(tempDir)) {
        rmSync(tempDir, { recursive: true, force: true });
      }
      tempDir = await precompileSvelte();
      
      // Ensure tempDir is set before creating plugins
      if (!tempDir) {
        throw new Error("Failed to create temp directory for Svelte compilation");
      }
      
      // Update plugins (they reference tempDir from outer scope, so they'll use current value)
      jsOptions.plugins = createPlugins();
      
      // Only create buildContext if it doesn't exist (first build)
      if (!buildContext) {
        buildContext = await esbuild.context(jsOptions);
      } else {
        // For subsequent rebuilds, we need to recreate the context because plugins changed
        // esbuild doesn't support updating plugins on existing context, so we must recreate
        // Note: The server will be restarted after rebuild completes
        await buildContext.dispose();
        buildContext = await esbuild.context(jsOptions);
      }
      
      await buildContext.rebuild();
      
      // Restart server if it was already running (after context recreation)
      if (server && buildContext) {
        // Stop old server (if any) and start new one
        server = await buildContext.serve({
          servedir: DIST_DIR,
          port: 8000,
          host: "0.0.0.0"
        });
      }
      
      copyHtml();
      copyStaticFiles();
      copyExampleConfig();
      console.log("✓ Rebuild complete");
    } catch (error) {
      console.error("✗ Rebuild failed:", error);
    } finally {
      isRebuilding = false;
    }
  }

  // Debounced rebuild function to prevent multiple rapid rebuilds
  function scheduleRebuild() {
    if (rebuildTimeout) {
      clearTimeout(rebuildTimeout);
    }
    rebuildTimeout = setTimeout(() => {
      rebuild();
    }, 100); // 100ms debounce
  }

  // Initial build
  await rebuild();
  
  // Start server once (it persists across rebuilds)
  const serveOptions = { 
    servedir: DIST_DIR, 
    port: 8000,
    host: "0.0.0.0" // Allow access from remote hosts (e.g., cmr-r)
  };
  server = await buildContext.serve(serveOptions);
  const port = server.port;
  // esbuild serve() may not return host, so use localhost for display (0.0.0.0 is for binding, not display)
  console.log(`\n🚀 Server running at http://localhost:${port}\n`);
  
  // Watch for changes (debounced to prevent rapid rebuilds)
  watch("src", { recursive: true }, () => {
    scheduleRebuild();
  });
  watch("departures.html", () => {
    copyHtml();
    console.log("✓ HTML updated");
  });

  process.on("SIGINT", async () => {
    if (buildContext) {
      await buildContext.dispose();
    }
    if (tempDir && existsSync(tempDir)) {
      rmSync(tempDir, { recursive: true, force: true });
    }
    process.exit(0);
  });

  await new Promise(() => {});
} else {
  try {
    await build();
  } catch (error) {
    console.error("✗ Build failed:", error);
    process.exit(1);
  }
}
