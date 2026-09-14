// 消息自动化场景说明 · HTML → A4 PDF 导出（咨询报告体家族 · 含每页运行页脚）
// 用法: NODE_PATH=../../GEO客户启动书/scripts/node_modules node export_pdf.js [源HTML] [输出PDF] [页脚文档名]
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const srcArg = process.argv[2] || '../design-demos/consulting-report.html';
  const outArg = process.argv[3] || '../消息自动化与AI客户经营-客户场景说明.pdf';
  const docLabel = process.argv[4] || '客户场景说明';

  const src = 'file://' + path.resolve(__dirname, srcArg);
  const out = path.resolve(__dirname, outArg);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(src, { waitUntil: 'networkidle' });
  await page.pdf({
    path: out,
    format: 'A4',
    printBackground: true,
    margin: { top: '8mm', right: 0, bottom: '16mm', left: 0 },
    scale: 1,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: `
      <div style="width:100%; padding:0 13mm 0; font-family:-apple-system,'PingFang SC',sans-serif;
                  font-size:8px; color:#7E93A2; display:flex; justify-content:space-between;">
        <span>【服务方名称】 · 消息自动化与 AI 客户经营 · ${docLabel}</span>
        <span>第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页</span>
      </div>`,
  });
  await browser.close();
  console.log('PDF written:', out);
})();
