/**
 * EXPERIMENT_REPORT.md → docs/experiments/EXPERIMENT_REPORT.pdf
 * 실행: npm run report:pdf  (루트에서)
 */
const fs = require("node:fs");
const path = require("node:path");
const { mdToPdf } = require("md-to-pdf");

const REPO_ROOT = path.join(__dirname, "..", "..");
const MD_PATH = path.join(REPO_ROOT, "docs", "experiments", "EXPERIMENT_REPORT.md");
const CSS_PATH = path.join(REPO_ROOT, "docs", "experiments", "pdf-print.css");
const OUT_PATH = path.join(REPO_ROOT, "docs", "experiments", "EXPERIMENT_REPORT.pdf");
const TMP_PATH = path.join(REPO_ROOT, "docs", "experiments", "_EXPERIMENT_REPORT_pdf_tmp.md");

async function main() {
  let md = fs.readFileSync(MD_PATH, "utf8");
  md = md.replace(
    /```mermaid\n[\s\S]*?```/g,
    "> ※ PDF 변환 시 Mermaid 다이어그램은 그림으로 렌더되지 않습니다. 흐름: `samples.json` → `run_matrix.py` → `latency.csv` 및 `T{n}/p{i}-g{j}.png`.\n\n",
  );
  fs.writeFileSync(TMP_PATH, md, "utf8");

  await mdToPdf(
    { path: TMP_PATH },
    {
      dest: OUT_PATH,
      pdf_options: {
        format: "A4",
        printBackground: true,
        margin: { top: "12mm", bottom: "14mm", left: "14mm", right: "14mm" },
      },
      stylesheet: CSS_PATH,
      launch_options: { args: ["--no-sandbox", "--disable-setuid-sandbox"] },
    },
  );

  fs.unlinkSync(TMP_PATH);
  console.log("Wrote:", OUT_PATH);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
