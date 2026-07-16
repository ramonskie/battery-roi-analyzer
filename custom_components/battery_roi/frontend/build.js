import { build } from "esbuild";

const production = process.env.NODE_ENV === "production";

await build({
  entryPoints: ["src/battery-roi-card.js"],
  bundle: true,
  format: "esm",
  minify: production,
  sourcemap: !production,
  target: "es2020",
  outfile: "battery-roi-card.js",
  // Lit uses some node-specific APIs that need to be shimmed
  define: {
    "process.env.NODE_ENV": JSON.stringify(
      production ? "production" : "development"
    ),
  },
}).catch((err) => {
  console.error(err);
  process.exit(1);
});
