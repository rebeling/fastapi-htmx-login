import fs from "fs";
import path from "path";
import mjml2html from "mjml";
import { minify } from "html-minifier-terser";

const inputDir = "src";
const outputDir = "build";

fs.mkdirSync(outputDir, { recursive: true });

for (const file of fs.readdirSync(inputDir)) {
  if (file.endsWith(".mjml")) {
    const name = path.basename(file, ".mjml"); // yields magic_link_email
    const mjmlPath = path.join(inputDir, file);
    const htmlPath = path.join(outputDir, `${name}.html`);

    // Compile MJML
    const { html } = mjml2html(fs.readFileSync(mjmlPath, "utf8"), {
      minify: false,
    });

    // Minify HTML
    const minified = await minify(html, {
      collapseWhitespace: true,
      removeComments: true,
      minifyCSS: true,
      minifyJS: true,
    });

    fs.writeFileSync(htmlPath, minified);
    console.log(`Built ${htmlPath}`);
  }
}
