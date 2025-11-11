import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Build into ../web/dist so Flask can serve the built assets from web/
export default defineConfig({
    plugins: [react()],
    root: path.resolve(__dirname),
    build: {
        outDir: path.resolve(__dirname, "../web/dist"),
        emptyOutDir: true,
        rollupOptions: {
            input: path.resolve(__dirname, "index.html"),
        },
    },
});
