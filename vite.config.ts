import path from "path";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [tailwindcss()],
	base: "/static/",
	build: {
		outDir: path.resolve(__dirname, "./static"),
		emptyOutDir: false,
		manifest: "manifest.json",
		rollupOptions: {
			input: {
				main: path.resolve(__dirname, "assets/js/main.ts"),
				theme_init: path.resolve(
					__dirname,
					"assets/js/theme/theme_init.ts",
				),
				flatpickr: path.resolve(
					__dirname,
					"assets/src/flatpickr_init.ts",
				),
				styles: path.resolve(__dirname, "assets/src/styles.css"),
			},
			output: {
				entryFileNames: "js/[name]-bundle.js",
			},
		},
	},
});
