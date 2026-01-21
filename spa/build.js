import * as esbuild from "esbuild";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync, cpSync, rmSync, watch } from "fs";
import { readdir, stat } from "fs/promises";
import { join, dirname, extname } from "path";
import { compile } from "svelte/compiler";

const isWatch = process.argv.includes("--watch");

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
  const tempDir = ".svelte-temp";
  
  if (existsSync(tempDir)) {
    // Clean temp dir
    rmSync(tempDir, { recursive: true, force: true });
  }
  mkdirSync(tempDir, { recursive: true });

  for (const file of svelteFiles) {
    const compiled = await compileSvelte(file);
    const relativePath = file.replace("src/", "").replace(".svelte", ".svelte.js");
    const outputPath = join(tempDir, relativePath);
    const outputDir = dirname(outputPath);
    mkdirSync(outputDir, { recursive: true });
    writeFileSync(outputPath, compiled);
  }

  return tempDir;
}

function copyStaticFiles() {
  const staticDir = "static";
  const distDir = "dist";
  
  if (!existsSync(distDir)) {
    mkdirSync(distDir, { recursive: true });
  }

  // Copy CSS
  if (existsSync(join(staticDir, "css", "departures.css"))) {
    const cssDest = join(distDir, "css");
    mkdirSync(cssDest, { recursive: true });
    copyFileSync(
      join(staticDir, "css", "departures.css"),
      join(cssDest, "departures.css")
    );
  }

  // Copy static assets if they exist
  const assetsDir = join(staticDir, "assets");
  if (existsSync(assetsDir)) {
    const assetsDest = join(distDir, "assets");
    mkdirSync(assetsDest, { recursive: true });
    // Copy all assets
    cpSync(assetsDir, assetsDest, { recursive: true });
  }

  // Copy img directory if it exists (for status icons)
  const imgDir = join(staticDir, "img");
  if (existsSync(imgDir)) {
    const imgDest = join(distDir, "img");
    mkdirSync(imgDest, { recursive: true });
    cpSync(imgDir, imgDest, { recursive: true });
  }
}

function copyHtml() {
  const src = "departures.html";
  const dest = "dist/index.html";
  
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
  
  // Ensure dist directory exists
  const distDir = "dist";
  if (!existsSync(distDir)) {
    mkdirSync(distDir, { recursive: true });
  }
  
  writeFileSync(dest, cleanHtml);
}

  const jsOptions = {
  entryPoints: ["src/main.ts"],
  bundle: true,
  outfile: "dist/bundle.js",
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
  const tempDir = await precompileSvelte();
  
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
          const compiledPath = join(process.cwd(), tempDir, relativePath);
          
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
          if (args.importer && args.importer.includes(".svelte-temp")) {
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

  console.log("Building bundle...");
  try {
    await esbuild.build(jsOptions);
  } catch (error) {
    console.error("Build error:", error);
    throw error;
  }
  
  copyHtml();
  copyStaticFiles();
  
  // Clean up temp directory
  if (!isWatch && existsSync(tempDir)) {
    rmSync(tempDir, { recursive: true, force: true });
  }
  
  console.log("✓ Build complete!");
}

if (isWatch) {
  let buildContext;
  let tempDir;
  
  async function rebuild() {
    try {
      if (tempDir && existsSync(tempDir)) {
        rmSync(tempDir, { recursive: true, force: true });
      }
      tempDir = await precompileSvelte();
      
      if (buildContext) {
        await buildContext.dispose();
      }
      
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
              const compiledPath = join(process.cwd(), tempDir, relativePath);
              
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
              if (args.importer && args.importer.includes(".svelte-temp")) {
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
      
      buildContext = await esbuild.context(jsOptions);
      await buildContext.rebuild();
      copyHtml();
      copyStaticFiles();
      console.log("✓ Rebuild complete");
    } catch (error) {
      console.error("✗ Rebuild failed:", error);
    }
  }

  // Initial build
  await rebuild();
  
  // Watch for changes
  watch("src", { recursive: true }, () => {
    rebuild();
  });
  watch("departures.html", () => {
    copyHtml();
    console.log("✓ HTML updated");
  });

  // Serve - bind to all interfaces (0.0.0.0) to allow remote access
  const { port, host } = await buildContext.serve({ 
    servedir: "dist", 
    port: 8000,
    host: "0.0.0.0" // Allow access from remote hosts (e.g., cmr-r)
  });
  console.log(`\n🚀 Server running at http://${host}:${port}\n`);

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
